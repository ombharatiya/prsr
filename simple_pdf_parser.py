import os
import re
import uuid
from typing import Dict, List, Tuple, Any, Optional
import PyPDF2
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

class SimplePDFParser:
    """
    A simpler PDF parser that uses PyPDF2 to extract text from PDFs.
    Falls back to pytesseract OCR for scanned documents.
    """
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.text = ""
        self.serial_number = str(uuid.uuid4())
    
    def _extract_text_with_pypdf(self) -> str:
        """Extract text from PDF using PyPDF2."""
        try:
            print(f"Extracting text from {self.pdf_path} using PyPDF2...")
            text = ""
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
            
            print(f"Successfully extracted {len(text)} characters of text with PyPDF2")
            return text
        except Exception as e:
            print(f"Error in PyPDF2 extraction: {str(e)}")
            return ""
    
    def _extract_text_with_ocr(self) -> str:
        """Extract text from PDF using pytesseract OCR."""
        try:
            print(f"Extracting text from {self.pdf_path} using pytesseract OCR...")
            images = convert_from_path(self.pdf_path)
            text = ""
            
            for i, image in enumerate(images):
                print(f"Processing page {i+1}/{len(images)}...")
                page_text = pytesseract.image_to_string(image)
                text += page_text + "\n"
            
            print(f"Successfully extracted {len(text)} characters of text with OCR")
            return text
        except Exception as e:
            print(f"Error in OCR extraction: {str(e)}")
            return ""
    
    def extract_text(self) -> str:
        """
        Extract text from PDF using PyPDF2, falling back to OCR if needed.
        """
        # First try PyPDF2
        text = self._extract_text_with_pypdf()
        
        # If PyPDF2 failed or didn't extract enough text, try OCR
        if len(text.strip()) < 100:
            print("Not enough text extracted with PyPDF2, trying OCR...")
            ocr_text = self._extract_text_with_ocr()
            if len(ocr_text.strip()) > len(text.strip()):
                text = ocr_text
        
        self.text = text
        return text
    
    def _extract_with_pattern(self, pattern: str, default: str = "") -> str:
        """Extract data using regex pattern."""
        match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
        if match and match.groups():
            return match.group(1).strip()
        return default
    
    def _extract_document_type(self) -> str:
        """Extract document type from the text."""
        for doc_type in ["Tax Invoice", "Delivery Challan", "Stock Transfer"]:
            if doc_type.lower() in self.text.lower():
                return doc_type
        return "Tax Invoice"  # Default
    
    def _extract_invoice_number(self) -> str:
        """Extract invoice number from the text."""
        patterns = [
            r"Document\s*No\s*:?\s*([A-Za-z0-9/\-_]+)",
            r"Invoice\s*No\.?\s*:?\s*([A-Za-z0-9/\-_]+)",
            r"Invoice\s*Number\s*:?\s*([A-Za-z0-9/\-_]+)",
            r"Bill\s*No\.?\s*:?\s*([A-Za-z0-9/\-_]+)",
            r"(Mensa/[A-Z]{2}/[A-Z]{3}/\d+)",
        ]
        
        for pattern in patterns:
            value = self._extract_with_pattern(pattern)
            if value:
                return value
        
        return "UNKNOWN"
    
    def _extract_date(self) -> str:
        """Extract invoice date from the text."""
        patterns = [
            r"Invoice\s*Date\s*:\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
            r"Date\s*:\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
            r"Date\s*:\s*(\d{1,2}[A-Za-z]{3}\d{2,4})",
            r"Invoice\s*Date\s*:?\s*(\d{1,2}[A-Za-z]{3}\d{2,4})",
        ]
        
        for pattern in patterns:
            value = self._extract_with_pattern(pattern)
            if value:
                return value
        
        # Try to find date in format dd-mm-yyyy
        date_pattern = r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})"
        return self._extract_with_pattern(date_pattern)
    
    def _extract_gstin(self, context: str) -> str:
        """Extract GSTIN based on context."""
        # GSTIN pattern: 2 digits, 5 letters, 4 digits, 1 letter, 1 alphanumeric, Z, 1 alphanumeric
        gstin_pattern = r"([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{1}[Z]{1}[0-9A-Z]{1})"
        
        # If context is for supplier, look specifically for supplier GSTIN
        if any(word in context for word in ["Supplier", "Seller", "From"]):
            supplier_patterns = [
                r"Supplier\s*GSTIN\s*:?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{1}[Z]{1}[0-9A-Z]{1})",
                r"Seller\s*GSTIN\s*:?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{1}[Z]{1}[0-9A-Z]{1})",
                r"From\s*GSTIN\s*:?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{1}[Z]{1}[0-9A-Z]{1})"
            ]
            for pattern in supplier_patterns:
                match = re.search(pattern, self.text, re.IGNORECASE)
                if match and match.groups():
                    result = match.group(1)
                    return result.strip() if result else ""
        
        # If context is for buyer/customer/consignee, look specifically for those GSTINs
        if any(word in context for word in ["Buyer", "Customer", "Bill to", "Ship to", "Consignee"]):
            buyer_patterns = [
                r"Buyer\s*GSTIN\s*:?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{1}[Z]{1}[0-9A-Z]{1})",
                r"Customer\s*GSTIN\s*:?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{1}[Z]{1}[0-9A-Z]{1})",
                r"GST\s*No\.?:?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{1}[Z]{1}[0-9A-Z]{1})",
                r"Consignee\s*GSTIN\s*:?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{1}[Z]{1}[0-9A-Z]{1})"
            ]
            for pattern in buyer_patterns:
                match = re.search(pattern, self.text, re.IGNORECASE)
                if match and match.groups():
                    result = match.group(1)
                    return result.strip() if result else ""
        
        # Try to find GSTIN with context
        try:
            # Look for context followed by GSTIN
            context_pattern = rf"{context}.*?{gstin_pattern}"
            match = re.search(context_pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match and match.groups():
                result = match.group(1)
                return result.strip() if result else ""
                
            # If not found, try searching without regex context
            if "GSTIN" in context:
                # Look for "GSTIN: XXXXXXXXXXXX" pattern
                gstin_simple = r"GSTIN\s*:?\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{1}[Z]{1}[0-9A-Z]{1})"
                match = re.search(gstin_simple, self.text, re.IGNORECASE)
                if match and match.groups():
                    result = match.group(1)
                    return result.strip() if result else ""
        except Exception as e:
            print(f"Error in GSTIN extraction with context: {str(e)}")
        
        # If not found with context, look for all GSTINs
        try:
            matches = re.findall(gstin_pattern, self.text)
            if matches and len(matches) > 0:
                # For supplier GSTIN, prefer first match
                if any(word in context for word in ["Supplier", "Seller", "From"]) and len(matches) > 0:
                    return matches[0].strip() if matches[0] else ""
                # For buyer GSTIN, prefer second match if available
                elif any(word in context for word in ["Buyer", "Customer", "Bill to"]) and len(matches) > 1:
                    return matches[1].strip() if matches[1] else ""
                # For consignee GSTIN, prefer third match if available
                elif any(word in context for word in ["Ship to", "Consignee"]) and len(matches) > 2:
                    return matches[2].strip() if matches[2] else ""
                # Default to first match
                return matches[0].strip() if matches[0] else ""
        except Exception as e:
            print(f"Error in GSTIN general extraction: {str(e)}")
        
        return ""
    
    def _extract_name_and_address(self, keywords: List[str]) -> Tuple[str, str]:
        """Extract name and address based on keywords."""
        name = ""
        address = ""
        
        # Try to find sections with these keywords
        section_text = ""
        for keyword in keywords:
            pattern = rf"(?:{keyword}|Details of {keyword}).*?(?:GSTIN|PAN|\n\s*\n)"
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                section_text = match.group(0)
                break
        
        if section_text:
            # Extract name (usually the first line after keyword)
            lines = [line.strip() for line in section_text.split('\n') if line.strip()]
            
            # Look for Legal Name or Name patterns
            name_match = re.search(r"(?:Legal|Trade)?\s*Name\s*:?\s*([^\n]+)", section_text, re.IGNORECASE)
            if name_match:
                name = name_match.group(1).strip()
            elif lines and len(lines) > 0:
                # If no specific name pattern found, use first non-keyword line
                for line in lines:
                    if not any(keyword.lower() in line.lower() for keyword in keywords):
                        name = line
                        break
            
            # Try to extract address parts
            address_match = re.search(r"Address\s*(?:1|2|Line)?\s*:?\s*([^\n]+)", section_text, re.IGNORECASE)
            if address_match:
                address = address_match.group(1).strip()
            else:
                # Address is usually the next few lines after name
                found_name = False
                address_lines = []
                for line in lines:
                    if not found_name and name in line:
                        found_name = True
                        continue
                    if found_name and not re.search(r'GSTIN|GST No|PAN', line, re.IGNORECASE):
                        address_lines.append(line)
                    elif found_name and re.search(r'GSTIN|GST No|PAN', line, re.IGNORECASE):
                        break
                
                address = ", ".join(address_lines)
        
        # Clean up name and address
        name = re.sub(r'^[:\s]+', '', name)  # Remove leading colons or spaces
        
        return name, address
    
    def _extract_numeric_value(self, pattern: str) -> float:
        """Extract numeric value based on pattern."""
        match = re.search(pattern, self.text, re.IGNORECASE)
        if match:
            # Extract the matched number and remove any commas
            number_str = re.sub(r'[^\d.]', '', match.group(1))
            try:
                return float(number_str)
            except ValueError:
                pass
        return 0.0
    
    def _extract_total_invoice_value(self) -> float:
        """Extract the total invoice value using multiple patterns."""
        patterns = [
            r"Total\s*Invoice\s*Value\s*(?:in\s*INR)?\s*:?\s*(?:₹|Rs\.?)?\s*(\d[\d,.]+\.\d+)",
            r"Total\s*Amount\s*:?\s*(?:₹|Rs\.?)?\s*(\d[\d,.]+\.\d+)",
            r"Grand\s*Total\s*:?\s*(?:₹|Rs\.?)?\s*(\d[\d,.]+\.\d+)",
            r"Total\s*Value\s*:?\s*(?:₹|Rs\.?)?\s*(\d[\d,.]+\.\d+)",
            r"Total\s*:?\s*(?:₹|Rs\.?)?\s*(\d[\d,.]+\.\d+)"
        ]
        
        for pattern in patterns:
            value = self._extract_numeric_value(pattern)
            if value > 0:
                return value
        
        # If we couldn't find with decimal, try without
        patterns_no_decimal = [
            r"Total\s*Invoice\s*Value\s*(?:in\s*INR)?\s*:?\s*(?:₹|Rs\.?)?\s*(\d[\d,.]+)",
            r"Total\s*Amount\s*:?\s*(?:₹|Rs\.?)?\s*(\d[\d,.]+)",
            r"Grand\s*Total\s*:?\s*(?:₹|Rs\.?)?\s*(\d[\d,.]+)",
            r"Total\s*Value\s*:?\s*(?:₹|Rs\.?)?\s*(\d[\d,.]+)",
            r"Total\s*:?\s*(?:₹|Rs\.?)?\s*(\d[\d,.]+)"
        ]
        
        for pattern in patterns_no_decimal:
            value = self._extract_numeric_value(pattern)
            if value > 0:
                return value
                
        # If still not found, try to extract it from the "in words" section
        words_match = re.search(r"(?:Rupees|INR)\s*(?:in\s*Words)?:?\s*(.+?)(?:Only|only|\.|\n)", self.text, re.IGNORECASE)
        if words_match:
            words = words_match.group(1).strip()
            if "lakh" in words.lower() or "lac" in words.lower():
                return 100000.0  # Just a default if we can't parse it better
        
        return 0.0
    
    def parse(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Parse the PDF and extract structured data.
        Returns a tuple of (invoice_data, item_data).
        """
        # Extract text if not already extracted
        if not self.text:
            self.extract_text()
            
        # If we still don't have text, log an error
        if not self.text:
            print("WARNING: Failed to extract any text from the PDF!")
        else:
            print(f"Successfully extracted {len(self.text)} characters of text")
            # Print first 200 chars for debugging
            print(f"First 200 characters: {self.text[:200]}")
        
        # Extract invoice-level data
        document_type = self._extract_document_type()
        invoice_number = self._extract_invoice_number()
        invoice_date = self._extract_date()
        
        # Look for the company name in the first few lines of the document
        company_name = ""
        first_lines = self.text.split('\n')[:10]  # Consider first 10 lines
        for line in first_lines:
            line = line.strip()
            # Skip headers like "TAX INVOICE"
            if document_type.upper() in line.upper():
                continue
            # Look for company name (usually in all caps or contains "PRIVATE", "LIMITED", etc.)
            if line and (line.isupper() or any(keyword in line.upper() for keyword in ["PRIVATE", "LIMITED", "PVT", "LTD"])):
                company_name = line.strip()
                break
        
        # Extract supplier information
        supplier_name, supplier_address = self._extract_name_and_address(["Supplier", "Seller", "From"])
        supplier_gstin = self._extract_gstin("Supplier|Seller|From|GSTIN")
        
        # If supplier name not found, use company name
        if not supplier_name and company_name:
            supplier_name = company_name
        
        # Extract buyer information 
        buyer_name, buyer_address = self._extract_name_and_address(["Buyer", "Bill to", "Customer", "Receiver"])
        buyer_gstin = self._extract_gstin("Buyer|Customer|Bill to|GSTIN")
        
        # Look for Legal Name in the text if buyer name not found
        if not buyer_name:
            legal_name_match = re.search(r"Legal\s*Name\s*:?\s*([^\n]+)", self.text, re.IGNORECASE)
            if legal_name_match:
                buyer_name = legal_name_match.group(1).strip()
        
        # Extract consignee information (if different from buyer)
        consignee_name, consignee_address = self._extract_name_and_address(["Consignee", "Ship to"])
        consignee_gstin = self._extract_gstin("Consignee|Ship to|GSTIN")
        
        # Use buyer info as consignee if not found
        if not consignee_name:
            consignee_name = buyer_name
            consignee_address = buyer_address
            consignee_gstin = buyer_gstin
        
        # Extract total quantity
        total_quantity = self._extract_numeric_value(r"Total\s*(?:Qty|Quantity)[^0-9]*(\d[\d,.]*)")
        
        # Extract values
        subtotal = self._extract_numeric_value(r"(?:Sub\s*Total|Taxable\s*Value|Assessable\s*Value)[^0-9]*(\d[\d,.]*)")
        cgst = self._extract_numeric_value(r"CGST[^0-9]*(\d[\d,.]*)")
        sgst = self._extract_numeric_value(r"SGST[^0-9]*(\d[\d,.]*)")
        igst = self._extract_numeric_value(r"IGST[^0-9]*(\d[\d,.]*)")
        cess = self._extract_numeric_value(r"CESS[^0-9]*(\d[\d,.]*)")
        
        # Use improved method to extract total invoice value
        total_invoice_value = self._extract_total_invoice_value()
        
        # Extract IRN and E-Way Bill numbers
        irn_no = self._extract_with_pattern(r"IRN\s*:?\s*([a-fA-F0-9]{64})")
        eway_bill_no = self._extract_with_pattern(r"e[-\s]?way\s*bill\s*no\.?:?\s*(\d+)")
        
        # Extract amount in words
        amount_in_words = self._extract_with_pattern(r"(?:Amount\s*(?:in|In)\s*Words|Total\s*in\s*words)\s*:\s*(.*?)(?:\n|$)")
        if not amount_in_words:
            amount_in_words = self._extract_with_pattern(r"(?:Rupees|Rs\.?)\s*(.*?)(?:Only|only)(?:\n|$)")
        
        # Create invoice-level data dictionary
        invoice_data = {
            "Serial Number": self.serial_number,
            "Document Type": document_type,
            "Invoice/Document Number": invoice_number,
            "Invoice/Document Date": invoice_date,
            "Supplier Name": supplier_name,
            "Supplier GSTIN": supplier_gstin,
            "Supplier Address": supplier_address,
            "Buyer Name": buyer_name,
            "Buyer GSTIN": buyer_gstin,
            "Buyer Address": buyer_address,
            "Consignee Name": consignee_name,
            "Consignee GSTIN": consignee_gstin,
            "Consignee Address": consignee_address,
            "PO Number": "",
            "SO Number": "",
            "STR Number": "",
            "Box Count": "",
            "Total Quantity": total_quantity,
            "Subtotal/Taxable Value": subtotal,
            "CGST Amount": cgst,
            "SGST Amount": sgst,
            "IGST Amount": igst,
            "CESS Amount": cess,
            "Additional Charges / Round Off": 0.0,
            "Total Invoice Value": total_invoice_value,
            "Reverse Charge": "No",
            "IRN No": irn_no,
            "E-Way Bill No": eway_bill_no,
            "Amount in Words": amount_in_words,
            "Additional Remarks": ""
        }
        
        # Extract item-level data
        item_data = self._extract_line_items(invoice_number)
        
        return invoice_data, item_data
    
    def _extract_line_items(self, invoice_number: str) -> List[Dict[str, Any]]:
        """Extract line items from the invoice."""
        item_data = []
        
        # Try to find the item table section
        table_pattern = r"(?:S\.?No\.?|Sr\.?\s*No\.?|Item Code|HSN|Description|Qty|Rate|Amount).*?(?=Total|Grand Total|Sub Total)"
        table_match = re.search(table_pattern, self.text, re.IGNORECASE | re.DOTALL)
        
        if table_match:
            table_text = table_match.group(0)
            lines = table_text.split('\n')
            
            # Filter out empty lines and headers
            item_lines = []
            for line in lines:
                line = line.strip()
                if not line or re.search(r"(S\.?No\.?|Sr\.?\s*No\.?|Item Code|HSN|Description|Qty|Rate|Amount)$", line, re.IGNORECASE):
                    continue
                item_lines.append(line)
            
            # Simple parsing: look for SKU codes and patterns
            for i, line in enumerate(item_lines):
                # Look for item code pattern (often in uppercase with numbers)
                sku_match = re.search(r"\b([A-Z0-9]+(?:_[A-Z0-9]+)*)\b", line)
                sku_code = sku_match.group(1) if sku_match else ""
                
                # Look for HSN code (8 digits usually)
                hsn_match = re.search(r"\b(\d{4,8})\b", line)
                hsn_code = hsn_match.group(1) if hsn_match else ""
                
                # Look for quantity and units
                qty_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:PCS|EA|NOS|KG|GM|MT|LT)\b", line, re.IGNORECASE)
                quantity = float(qty_match.group(1)) if qty_match else 1.0  # Default to 1 if not found
                
                # Determine UOM
                uom_match = re.search(r"\b(PCS|EA|NOS|KG|GM|MT|LT)\b", line, re.IGNORECASE) 
                uom = uom_match.group(1).upper() if uom_match else "PCS"  # Default unit of measure
                
                # Look for price/amount (numbers often at the end of the line)
                price_match = re.search(r"\b(\d+(?:,\d+)*(?:\.\d+)?)\s*(?=\s*\b(?:PER|PCS|EA|NOS|KG|GM|MT|LT)\b)", line, re.IGNORECASE)
                unit_price = float(price_match.group(1).replace(',', '')) if price_match else 0.0
                
                amount_match = re.search(r"\b(\d+(?:,\d+)*(?:\.\d+)?)\s*$", line)
                line_total = float(amount_match.group(1).replace(',', '')) if amount_match else 0.0
                
                # If we have a total but no unit price, and we have quantity, calculate unit price
                if line_total > 0 and unit_price == 0.0 and quantity > 0:
                    unit_price = line_total / quantity
                
                # Look for tax rate
                tax_match = re.search(r"(\d+(?:\.\d+)?)%", line)
                tax_rate = float(tax_match.group(1)) if tax_match else 0.0
                
                # Determine CGST, SGST, IGST based on context
                cgst_rate = f"{tax_rate/2}%" if "CGST" in self.text.upper() and tax_rate > 0 else ""
                sgst_rate = f"{tax_rate/2}%" if "SGST" in self.text.upper() and tax_rate > 0 else ""
                igst_rate = f"{tax_rate}%" if "IGST" in self.text.upper() and tax_rate > 0 else ""
                
                # If tax_rate is present but no specific tax type is identified, default to IGST
                if tax_rate > 0 and not cgst_rate and not sgst_rate and not igst_rate:
                    igst_rate = f"{tax_rate}%"
                
                # Extract item description - often between SKU code and quantity/price
                desc_match = re.search(rf"{sku_code}\s+(.*?)(?:\b{hsn_code}\b|\b{quantity}\b|\b{uom}\b)", line, re.IGNORECASE)
                description = desc_match.group(1).strip() if desc_match and desc_match.groups() else ""
                
                # If we can't extract a proper description, use the whole line
                if not description and len(line) > 5:
                    description = line[:50] if len(line) > 50 else line
                
                # Create item dictionary with meaningful values
                item = {
                    "Invoice Serial Number": self.serial_number,
                    "Invoice Number": invoice_number,
                    "Line #": i + 1,
                    "PO Identifier": "",
                    "Item/SKU Code": sku_code,
                    "Item Description": description,
                    "HSN Code": hsn_code,
                    "Quantity": quantity,
                    "UOM": uom,
                    "Unit Price": unit_price,
                    "Discount": 0.0,
                    "Tax Rate": f"{tax_rate}%" if tax_rate > 0 else "",
                    "CGST Rate": cgst_rate,
                    "SGST Rate": sgst_rate,
                    "IGST Rate": igst_rate,
                    "CGST Amount": (line_total * tax_rate/200) if cgst_rate else 0.0,
                    "SGST Amount": (line_total * tax_rate/200) if sgst_rate else 0.0,
                    "IGST Amount": (line_total * tax_rate/100) if igst_rate else 0.0,
                    "Line Total Value": line_total
                }
                item_data.append(item)
        
        # Alternative approach: Instead of looking for table, look for patterns in any line
        if not item_data:
            # Find lines that look like items (contain product codes, quantities, and amounts)
            potential_item_lines = []
            lines = self.text.split('\n')
            
            for line in lines:
                line = line.strip()
                # Skip short lines or ones that are likely headers
                if len(line) < 10 or re.search(r"(S\.?No\.?|Sr\.?\s*No\.?|Item Code|Description)$", line, re.IGNORECASE):
                    continue
                    
                # Check if line contains patterns that suggest it's an item line
                if (re.search(r"\b[A-Z0-9_-]{6,}\b", line) and 
                    (re.search(r"\b\d+\s*(?:PCS|NOS|EA|KG)\b", line, re.IGNORECASE) or 
                     re.search(r"\b\d+(?:,\d+)*(?:\.\d+)?\b", line))):
                    potential_item_lines.append(line)
            
            # Process the potential item lines
            for i, line in enumerate(potential_item_lines):
                sku_match = re.search(r"\b([A-Z0-9]+(?:[_-][A-Z0-9]+)*)\b", line)
                sku_code = sku_match.group(1) if sku_match else f"ITEM{i+1}"
                
                qty_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:PCS|NOS|EA|KG)\b", line, re.IGNORECASE)
                quantity = float(qty_match.group(1)) if qty_match else 1.0
                
                uom_match = re.search(r"\b(PCS|NOS|EA|KG)\b", line, re.IGNORECASE)
                uom = uom_match.group(1).upper() if uom_match else "PCS"
                
                # Look for numeric values that could be amounts
                amount_matches = re.findall(r"\b(\d+(?:,\d+)*(?:\.\d+)?)\b", line)
                amount_values = [float(val.replace(',', '')) for val in amount_matches if val]
                
                # Last value is likely the line total
                line_total = amount_values[-1] if amount_values else 0.0
                unit_price = line_total / quantity if quantity > 0 and line_total > 0 else 0.0
                
                item = {
                    "Invoice Serial Number": self.serial_number,
                    "Invoice Number": invoice_number,
                    "Line #": i + 1,
                    "PO Identifier": "",
                    "Item/SKU Code": sku_code,
                    "Item Description": line[:50] if len(line) > 50 else line,
                    "HSN Code": "",
                    "Quantity": quantity,
                    "UOM": uom,
                    "Unit Price": unit_price,
                    "Discount": 0.0,
                    "Tax Rate": "",
                    "CGST Rate": "",
                    "SGST Rate": "",
                    "IGST Rate": "",
                    "CGST Amount": 0.0,
                    "SGST Amount": 0.0,
                    "IGST Amount": 0.0,
                    "Line Total Value": line_total
                }
                item_data.append(item)
        
        return item_data 