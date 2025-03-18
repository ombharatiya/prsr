import os
import re
import uuid
import numpy as np
from typing import Dict, List, Tuple, Any, Optional

# Remove old OCR imports
# import pdf2image
# import pytesseract
# from PIL import Image

# Add docling imports
try:
    from docling.document_converter import extract_text_from_pdf
    HAS_DOCLING = True
except ImportError:
    HAS_DOCLING = False
    print("Warning: docling package not found. Please install it using 'pip install docling'.")

# Keep doctr as fallback
try:
    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor
    HAS_DOCTR = True
except ImportError:
    HAS_DOCTR = False
    print("Warning: doctr package not found.")

class InvoiceParser:
    """
    Parser for PDF invoices that extracts structured data for both invoice-level and item-level information.
    Supports both text-based PDFs and scanned image PDFs through OCR.
    """
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.text = ""
        self.serial_number = str(uuid.uuid4())
        
        # Initialize OCR model if needed for fallback
        self.ocr_model = None
        if HAS_DOCTR:
            try:
                self.ocr_model = ocr_predictor(pretrained=True)
                print("Loaded doctr OCR engine as fallback")
            except Exception as e:
                print(f"Error initializing doctr OCR: {str(e)}")
                self.ocr_model = None
        
    def _extract_text_with_docling(self) -> str:
        """Extract text from PDF using docling.document_converter."""
        try:
            # Use docling to extract text
            print(f"Extracting text from {self.pdf_path} using docling...")
            text = extract_text_from_pdf(self.pdf_path)
            print(f"Successfully extracted {len(text)} characters of text with docling")
            return text
        except Exception as e:
            print(f"Error in docling extraction: {str(e)}")
            return ""
    
    def _extract_text_with_ocr(self) -> str:
        """Extract text from PDF using OCR as fallback method."""
        if not HAS_DOCLING or not self._extract_text_with_docling():
            print("Falling back to OCR extraction...")
            if HAS_DOCTR and self.ocr_model:
                try:
                    # Load the document
                    doc = DocumentFile.from_pdf(self.pdf_path)
                    
                    # Run OCR on all pages
                    result = self.ocr_model(doc)
                    
                    # Extract text from OCR result
                    full_text = ""
                    for page in result.pages:
                        for block in page.blocks:
                            for line in block.lines:
                                for word in line.words:
                                    full_text += word.value + " "
                                full_text += "\n"
                    
                    print(f"Successfully extracted {len(full_text)} characters of text with doctr")
                    return full_text
                except Exception as e:
                    print(f"Error in OCR processing: {str(e)}")
            else:
                print("No OCR method available")
        return ""
    
    def _extract_document_type(self) -> str:
        """Extract document type from the text."""
        doc_types = ["Tax Invoice", "Delivery Challan", "Stock Transfer"]
        for doc_type in doc_types:
            if doc_type.lower() in self.text.lower():
                return doc_type
        return "Tax Invoice"  # Default to Tax Invoice if not found
    
    def _extract_invoice_number(self) -> str:
        """Extract invoice number from the text."""
        patterns = [
            r"Invoice\s*No\.?\s*:\s*([A-Za-z0-9/\-_]+)",
            r"Invoice\s*Number\s*:\s*([A-Za-z0-9/\-_]+)",
            r"Bill\s*No\.?\s*:\s*([A-Za-z0-9/\-_]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Try to find Mensa format invoice number
        mensa_pattern = r"(Mensa/[A-Z]{2}/[A-Z]{3}/\d+)"
        match = re.search(mensa_pattern, self.text)
        if match:
            return match.group(1).strip()
        
        return ""
    
    def _extract_date(self) -> str:
        """Extract invoice date from the text."""
        patterns = [
            r"Invoice\s*Date\s*:\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
            r"Date\s*:\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
            r"Date\s*:\s*(\d{1,2}[A-Za-z]{3}\d{2,4})",
            r"Invoice\s*Date\s*:?\s*(\d{1,2}[A-Za-z]{3}\d{2,4})",
            r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_gstin(self, context_pattern: str) -> str:
        """Extract GSTIN based on context."""
        pattern = rf"{context_pattern}.*?([0-9]{{2}}[A-Z]{{5}}[0-9]{{4}}[A-Z][0-9A-Z]{{1}}[Z]{{1}}[0-9A-Z]{{1}})"
        match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Generic GSTIN pattern search
        gstin_pattern = r"([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{1}[Z]{1}[0-9A-Z]{1})"
        matches = re.findall(gstin_pattern, self.text)
        if matches and context_pattern:
            # Find the GSTIN that appears closest to the context
            context_pos = self.text.find(context_pattern)
            if context_pos != -1:
                closest_match = None
                min_distance = float('inf')
                
                for gstin in matches:
                    gstin_pos = self.text.find(gstin)
                    distance = abs(gstin_pos - context_pos)
                    if distance < min_distance:
                        min_distance = distance
                        closest_match = gstin
                
                if closest_match and min_distance < 500:  # Arbitrary threshold
                    return closest_match
        
        return ""
    
    def _extract_address(self, entity_name: str) -> str:
        """Extract address based on entity name."""
        if not entity_name:
            return ""
        
        # Look for address after the entity name
        name_pos = self.text.find(entity_name)
        if name_pos == -1:
            return ""
        
        # Extract a chunk of text after the name
        chunk = self.text[name_pos:name_pos + 500]
        
        # Try to find address patterns
        address_patterns = [
            r"Address\s*:\s*(.*?)(?:GSTIN|PAN|Phone|Email|$)",
            r"\n(.*?(?:Road|Street|Avenue|Lane|Boulevard|Drive|Place|Highway|Expressway|Freeway).*?)(?:\n\s*\n|\n[A-Z])",
            r"\n(.*?(?:Village|Town|City|District|State|Country).*?)(?:\n\s*\n|\n[A-Z])",
            r"\n(.*?(?:\d{6}).*?)(?:\n\s*\n|\n[A-Z])"  # Look for pincode (6 digits)
        ]
        
        for pattern in address_patterns:
            match = re.search(pattern, chunk, re.IGNORECASE | re.DOTALL)
            if match:
                address = match.group(1).strip()
                # Clean up the address
                address = re.sub(r'\s+', ' ', address)
                return address
        
        # Fallback: Just take a reasonable chunk
        lines = chunk.split('\n')
        address_lines = []
        for i, line in enumerate(lines[1:6]):  # Take up to 5 lines after entity name
            if line.strip() and not re.search(r'GSTIN|PAN|Phone|Email', line, re.IGNORECASE):
                address_lines.append(line.strip())
        
        return ', '.join(address_lines)
    
    def _extract_entity_name(self, context_patterns: List[str]) -> str:
        """Extract entity name based on context patterns."""
        for pattern in context_patterns:
            match = re.search(rf"{pattern}\s*:\s*(.*?)(?:\n|GSTIN|PAN|$)", self.text, re.IGNORECASE | re.DOTALL)
            if match:
                name = match.group(1).strip()
                # Clean up the name
                name = re.sub(r'\s+', ' ', name)
                return name
        
        return ""
    
    def _extract_tax_amounts(self) -> Tuple[float, float, float, float]:
        """Extract CGST, SGST, IGST, and CESS amounts."""
        cgst = 0.0
        sgst = 0.0
        igst = 0.0
        cess = 0.0
        
        # CGST pattern
        cgst_pattern = r"CGST.*?(?:Rs\.?|INR)?\s*(\d+(?:,\d+)*(?:\.\d+)?)"
        cgst_match = re.search(cgst_pattern, self.text, re.IGNORECASE)
        if cgst_match:
            cgst_str = cgst_match.group(1).replace(',', '')
            try:
                cgst = float(cgst_str)
            except ValueError:
                pass
        
        # SGST pattern
        sgst_pattern = r"SGST.*?(?:Rs\.?|INR)?\s*(\d+(?:,\d+)*(?:\.\d+)?)"
        sgst_match = re.search(sgst_pattern, self.text, re.IGNORECASE)
        if sgst_match:
            sgst_str = sgst_match.group(1).replace(',', '')
            try:
                sgst = float(sgst_str)
            except ValueError:
                pass
        
        # IGST pattern
        igst_pattern = r"IGST.*?(?:Rs\.?|INR)?\s*(\d+(?:,\d+)*(?:\.\d+)?)"
        igst_match = re.search(igst_pattern, self.text, re.IGNORECASE)
        if igst_match:
            igst_str = igst_match.group(1).replace(',', '')
            try:
                igst = float(igst_str)
            except ValueError:
                pass
        
        # CESS pattern
        cess_pattern = r"CESS.*?(?:Rs\.?|INR)?\s*(\d+(?:,\d+)*(?:\.\d+)?)"
        cess_match = re.search(cess_pattern, self.text, re.IGNORECASE)
        if cess_match:
            cess_str = cess_match.group(1).replace(',', '')
            try:
                cess = float(cess_str)
            except ValueError:
                pass
        
        return cgst, sgst, igst, cess
    
    def _extract_numeric_value(self, context_pattern: str) -> float:
        """Extract numeric value based on context."""
        pattern = rf"{context_pattern}.*?(?:Rs\.?|INR)?\s*(\d+(?:,\d+)*(?:\.\d+)?)"
        match = re.search(pattern, self.text, re.IGNORECASE)
        if match:
            value_str = match.group(1).replace(',', '')
            try:
                return float(value_str)
            except ValueError:
                pass
        return 0.0
    
    def _extract_line_items(self, invoice_number: str) -> List[Dict[str, Any]]:
        """Extract line items from the invoice."""
        item_data = []
        
        # Find the item table section
        table_patterns = [
            r"(S\.?No\.?|Sr\.?\s*No\.?|Item Code|HSN|Description|Qty|Rate|Amount).*?(?=Total|Grand Total|Sub Total)",
            r"(Item\s*Details).*?(?=Total|Grand Total|Sub Total)"
        ]
        
        table_text = ""
        for pattern in table_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                start_pos = match.start()
                end_pos = self.text.find("Total", start_pos)
                if end_pos == -1:
                    end_pos = len(self.text)
                table_text = self.text[start_pos:end_pos]
                break
        
        if not table_text:
            return []
        
        # Split table into lines
        lines = table_text.split('\n')
        item_lines = []
        
        # Filter out empty lines and headers
        for line in lines:
            line = line.strip()
            if not line or re.search(r"(S\.?No\.?|Sr\.?\s*No\.?|Item Code|HSN|Description|Qty|Rate|Amount)", line, re.IGNORECASE):
                continue
            item_lines.append(line)
        
        # Process each item line
        for i, line in enumerate(item_lines):
            # Try to parse the line
            parts = re.split(r'\s{2,}', line)  # Split by multiple spaces
            
            if len(parts) < 3:  # Not enough data
                continue
            
            item = {
                "Invoice Serial Number": self.serial_number,
                "Invoice Number": invoice_number,
                "Line #": i + 1,
                "PO Identifier": "",
                "Item/SKU Code": "",
                "Item Description": "",
                "HSN Code": "",
                "Quantity": 0,
                "UOM": "",
                "Unit Price": 0.0,
                "Discount": 0.0,
                "Tax Rate": "",
                "CGST Rate": "",
                "SGST Rate": "",
                "IGST Rate": "",
                "CGST Amount": 0.0,
                "SGST Amount": 0.0,
                "IGST Amount": 0.0,
                "Line Total Value": 0.0
            }
            
            # Try to extract data based on position
            try:
                if len(parts) >= 7:
                    # Typical format with many columns
                    item["Item/SKU Code"] = parts[0]
                    item["Item Description"] = parts[1]
                    item["HSN Code"] = parts[2] if re.match(r'\d+', parts[2]) else ""
                    item["Quantity"] = float(re.sub(r'[^\d.]', '', parts[3])) if parts[3] else 0
                    item["UOM"] = "PCS"  # Default UOM
                    item["Unit Price"] = float(re.sub(r'[^\d.]', '', parts[4])) if parts[4] else 0.0
                    
                    # Try to find tax rate
                    tax_pattern = r'(\d+(?:\.\d+)?)%'
                    tax_match = re.search(tax_pattern, line)
                    if tax_match:
                        tax_rate = float(tax_match.group(1))
                        item["Tax Rate"] = f"GST_{int(tax_rate)}" if tax_rate.is_integer() else f"GST_{tax_rate}"
                        
                        # In the sample data, we see IGST is used
                        item["IGST Rate"] = f"{tax_rate}%"
                        
                        # Calculate IGST amount if we have unit price and quantity
                        if item["Unit Price"] > 0 and item["Quantity"] > 0:
                            subtotal = item["Unit Price"] * item["Quantity"]
                            item["IGST Amount"] = round(subtotal * (tax_rate / 100), 2)
                            item["Line Total Value"] = subtotal + item["IGST Amount"]
                    
                    # Try to extract line total directly
                    total_pattern = r'(\d+(?:,\d+)*(?:\.\d+)?)$'
                    total_match = re.search(total_pattern, line)
                    if total_match:
                        try:
                            item["Line Total Value"] = float(total_match.group(1).replace(',', ''))
                        except ValueError:
                            pass
                else:
                    # Simplified parsing for fewer columns
                    item["Item/SKU Code"] = parts[0] if parts else ""
                    item["Item Description"] = parts[1] if len(parts) > 1 else ""
                    item["Quantity"] = float(re.sub(r'[^\d.]', '', parts[2])) if len(parts) > 2 and parts[2] else 0
                    
                    # Try to extract rate from the next part
                    if len(parts) > 3:
                        try:
                            item["Unit Price"] = float(re.sub(r'[^\d.]', '', parts[3]))
                        except ValueError:
                            pass
                    
                    # Try to find tax rate
                    tax_pattern = r'(\d+(?:\.\d+)?)%'
                    tax_match = re.search(tax_pattern, line)
                    if tax_match:
                        tax_rate = float(tax_match.group(1))
                        item["Tax Rate"] = f"GST_{int(tax_rate)}" if tax_rate.is_integer() else f"GST_{tax_rate}"
                        item["IGST Rate"] = f"{tax_rate}%"
            
            except Exception as e:
                print(f"Error parsing line item: {str(e)}")
                continue
            
            item_data.append(item)
        
        # If no items were found, try alternate parsing
        if not item_data:
            # Look for specific patterns in the text
            sku_pattern = r"([A-Z0-9]+_[A-Z0-9]+)"
            hsn_pattern = r"(\d{8})"
            qty_pattern = r"(\d+)\s*(?:PCS|EA|NOS)"
            
            sku_matches = re.findall(sku_pattern, self.text)
            hsn_matches = re.findall(hsn_pattern, self.text)
            qty_matches = re.findall(qty_pattern, self.text)
            
            if sku_matches:
                for i, sku in enumerate(sku_matches[:5]):  # Limit to first 5 as fallback
                    item = {
                        "Invoice Serial Number": self.serial_number,
                        "Invoice Number": invoice_number,
                        "Line #": i + 1,
                        "PO Identifier": "",
                        "Item/SKU Code": sku,
                        "Item Description": "",
                        "HSN Code": hsn_matches[i] if i < len(hsn_matches) else "",
                        "Quantity": float(qty_matches[i]) if i < len(qty_matches) else 0,
                        "UOM": "PCS",
                        "Unit Price": 0.0,
                        "Discount": 0.0,
                        "Tax Rate": "GST_5",  # Default based on sample
                        "CGST Rate": "",
                        "SGST Rate": "",
                        "IGST Rate": "5.00%",  # Default based on sample
                        "CGST Amount": 0.0,
                        "SGST Amount": 0.0,
                        "IGST Amount": 0.0,
                        "Line Total Value": 0.0
                    }
                    item_data.append(item)
        
        return item_data
    
    def _extract_amount_in_words(self) -> str:
        """Extract amount in words from the text."""
        patterns = [
            r"Amount\s*(?:in|In)\s*Words\s*:\s*(.*?)(?:\n|$)",
            r"(?:Rupees|Rs\.?)\s*(.*?)(?:Only|only)(?:\n|$)",
            r"Total\s*in\s*words\s*:\s*(.*?)(?:\n|$)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                words = match.group(1).strip()
                # Clean up the text
                words = re.sub(r'\s+', ' ', words)
                if "only" not in words.lower():
                    words += " Only"
                return words
        
        return ""
    
    def _extract_irn_number(self) -> str:
        """Extract IRN number from the text."""
        irn_pattern = r"IRN\s*:?\s*([a-fA-F0-9]{64})"
        match = re.search(irn_pattern, self.text)
        if match:
            return match.group(1).strip()
        return ""
    
    def _extract_eway_bill_number(self) -> str:
        """Extract e-way bill number from the text."""
        eway_pattern = r"e[-\s]?way\s*bill\s*no\.?:?\s*(\d+)"
        match = re.search(eway_pattern, self.text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""
    
    def parse(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Parse the PDF invoice and extract structured data.
        Returns a tuple of (invoice_data, item_data).
        """
        # First try to extract text using docling
        if HAS_DOCLING:
            self.text = self._extract_text_with_docling()
        
        # If docling failed or is not available, fall back to OCR
        if not self.text:
            self.text = self._extract_text_with_ocr()
            
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
        
        # Extract entity information
        supplier_name = self._extract_entity_name(["Supplier", "Seller", "From", "Sold by"])
        buyer_name = self._extract_entity_name(["Buyer", "Bill to", "Customer", "Billed to"])
        consignee_name = self._extract_entity_name(["Consignee", "Ship to", "Delivered to"]) or buyer_name
        
        # Extract GSTIN
        supplier_gstin = self._extract_gstin("Supplier|Seller|From|GSTIN")
        buyer_gstin = self._extract_gstin("Buyer|Customer|Bill to|GSTIN")
        consignee_gstin = self._extract_gstin("Consignee|Ship to|GSTIN") or buyer_gstin
        
        # Extract addresses
        supplier_address = self._extract_address(supplier_name)
        buyer_address = self._extract_address(buyer_name)
        consignee_address = self._extract_address(consignee_name) or buyer_address
        
        # Extract numeric values
        total_quantity = self._extract_numeric_value("Total Qty|Quantity")
        subtotal = self._extract_numeric_value("Sub\s*Total|Taxable\s*Value|Assessable\s*Value")
        total_invoice_value = self._extract_numeric_value("Total\s*Amount|Grand\s*Total|Invoice\s*Value")
        
        # Extract tax amounts
        cgst, sgst, igst, cess = self._extract_tax_amounts()
        
        # Extract additional information
        amount_in_words = self._extract_amount_in_words()
        irn_no = self._extract_irn_number()
        eway_bill_no = self._extract_eway_bill_number()
        
        # Round float values to 2 decimal places
        subtotal = round(subtotal, 2)
        cgst = round(cgst, 2)
        sgst = round(sgst, 2)
        igst = round(igst, 2)
        cess = round(cess, 2)
        total_invoice_value = round(total_invoice_value, 2)
        
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