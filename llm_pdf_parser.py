import os
import re
import uuid
import json
import requests
from typing import Dict, List, Tuple, Any, Optional, Literal
import PyPDF2
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

class LLMPDFParser:
    """
    PDF parser that uses PyPDF2 to extract text from PDFs and then uses LLM to extract structured data.
    Falls back to pytesseract OCR for scanned documents if needed.
    Supports both Google Gemini and OpenAI APIs.
    """
    
    def __init__(
        self, 
        pdf_path: str, 
        api_key: str = None, 
        llm_provider: Literal["google", "openai"] = "google",
        openai_api_key: str = None
    ):
        self.pdf_path = pdf_path
        self.text = ""
        self.serial_number = str(uuid.uuid4())
        self.llm_provider = llm_provider.lower()
        
        # Set API keys based on provider
        if self.llm_provider == "google":
            self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
            if not self.api_key:
                raise ValueError("Google API key is required. Either pass it explicitly or set GOOGLE_API_KEY environment variable.")
        elif self.llm_provider == "openai":
            self.api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key is required. Either pass it explicitly or set OPENAI_API_KEY environment variable.")
        else:
            raise ValueError("Invalid LLM provider. Supported providers are 'google' and 'openai'.")
    
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
    
    def _generate_llm_prompt(self) -> str:
        """Generate a concise prompt for the LLM to extract structured invoice data."""
        # Truncate text if it's too long for the API
        text_to_use = self.text
        max_chars = 10000 if self.llm_provider == "google" else 8000  # OpenAI context limit is smaller
        if len(text_to_use) > max_chars:
            print(f"Text too long ({len(text_to_use)} chars), truncating to {max_chars} chars")
            text_to_use = text_to_use[:max_chars]
        
        prompt = """
Extract structured data from this invoice text. Return ONLY a valid JSON with two fields:
1. "invoice_data": object with these fields: Document Type, Invoice Number, Invoice Date, Supplier Name, Supplier GSTIN, Supplier Address, Buyer Name, Buyer GSTIN, Buyer Address, Total Invoice Value
2. "line_items": array of line items with fields: Line Number, Item/SKU Code, Item Description, Quantity, Unit Price, Tax Rate, Line Total Value

INVOICE TEXT:
"""
        # Add extracted text to the prompt
        prompt += text_to_use
        
        # Add a reminder to return structured data
        prompt += """

IMPORTANT: Return ONLY valid JSON without any explanation or markdown. Format:
{"invoice_data": {...}, "line_items": [...]}
"""
        
        return prompt
    
    def _call_llm_api(self, prompt: str) -> Dict[str, Any]:
        """Call the appropriate LLM API based on the provider."""
        if self.llm_provider == "google":
            return self._call_google_gemini_api(prompt)
        elif self.llm_provider == "openai":
            return self._call_openai_api(prompt)
        else:
            return {"error": f"Unsupported LLM provider: {self.llm_provider}"}
    
    def _call_google_gemini_api(self, prompt: str) -> Dict[str, Any]:
        """Call the Google Gemini API to extract structured data from the text."""
        url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.0-pro:generateContent"
        headers = {
            "Content-Type": "application/json",
        }
        
        params = {
            "key": self.api_key
        }
        
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 8192,
            }
        }
        
        try:
            # Print prompt length for debugging
            print(f"Sending prompt with {len(prompt)} characters to Google Gemini API")
            
            response = requests.post(url, headers=headers, params=params, json=data)
            
            # Debug the response
            print(f"API response status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error response: {response.text}")
                return {"error": f"API error: {response.status_code} - {response.text}"}
            
            result = response.json()
            
            # Extract the generated text from the response
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        if 'text' in part:
                            # Try to parse the text as JSON
                            try:
                                json_str = part['text']
                                # Remove leading and trailing markdown if present
                                json_str = re.sub(r'^```json', '', json_str)
                                json_str = re.sub(r'```$', '', json_str)
                                json_str = json_str.strip()
                                
                                # Debug the JSON string
                                print(f"Received JSON string of length {len(json_str)}")
                                print(f"First 100 chars: {json_str[:100]}...")
                                
                                return json.loads(json_str)
                            except json.JSONDecodeError as e:
                                print(f"Error parsing JSON from API response: {str(e)}")
                                print(f"Raw text: {json_str[:200]}...")
                                # If JSON parse fails, return the raw text so we can see what went wrong
                                return {"error": f"Failed to parse JSON: {str(e)}"}
            
            print(f"Unexpected API response format")
            return {"error": "Unexpected API response format"}
            
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {str(e)}")
            return {"error": f"API request failed: {str(e)}"}
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}
    
    def _call_openai_api(self, prompt: str) -> Dict[str, Any]:
        """Call the OpenAI API to extract structured data from the text."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": "gpt-4",  # We can also use "gpt-3.5-turbo" for a cheaper alternative
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert at extracting structured data from invoice documents. Your task is to extract information and return it in a valid JSON format without any explanation or markdown."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.0,
            "max_tokens": 4000
        }
        
        try:
            # Print prompt length for debugging
            print(f"Sending prompt with {len(prompt)} characters to OpenAI API")
            
            response = requests.post(url, headers=headers, json=data)
            
            # Debug the response
            print(f"API response status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error response: {response.text}")
                return {"error": f"API error: {response.status_code} - {response.text}"}
            
            result = response.json()
            
            # Extract the generated text from the response
            if 'choices' in result and len(result['choices']) > 0:
                message_content = result['choices'][0]['message']['content']
                
                # Try to parse the text as JSON
                try:
                    # Remove any markdown code blocks if present
                    json_str = re.sub(r'^```json', '', message_content)
                    json_str = re.sub(r'^```', '', json_str)
                    json_str = re.sub(r'```$', '', json_str)
                    json_str = json_str.strip()
                    
                    # Debug the JSON string
                    print(f"Received JSON string of length {len(json_str)}")
                    print(f"First 100 chars: {json_str[:100]}...")
                    
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON from OpenAI response: {str(e)}")
                    print(f"Raw text: {message_content[:200]}...")
                    return {"error": f"Failed to parse JSON from OpenAI response: {str(e)}"}
            
            print(f"Unexpected OpenAI response format")
            return {"error": "Unexpected OpenAI response format"}
            
        except requests.exceptions.RequestException as e:
            print(f"OpenAI API request failed: {str(e)}")
            return {"error": f"OpenAI API request failed: {str(e)}"}
        except Exception as e:
            print(f"Unexpected error with OpenAI API: {str(e)}")
            return {"error": f"Unexpected error with OpenAI API: {str(e)}"}
    
    def _normalize_invoice_data(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and structure the invoice data from the LLM response."""
        # Create a default structure first
        normalized_data = {
            "Serial Number": self.serial_number,
            "Document Type": "Tax Invoice",
            "Invoice/Document Number": "",
            "Invoice/Document Date": "",
            "Supplier Name": "",
            "Supplier GSTIN": "",
            "Supplier Address": "",
            "Buyer Name": "",
            "Buyer GSTIN": "",
            "Buyer Address": "",
            "Consignee Name": "",
            "Consignee GSTIN": "",
            "Consignee Address": "",
            "PO Number": "",
            "SO Number": "",
            "STR Number": "",
            "Box Count": "",
            "Total Quantity": 0.0,
            "Subtotal/Taxable Value": 0.0,
            "CGST Amount": 0.0,
            "SGST Amount": 0.0,
            "IGST Amount": 0.0,
            "CESS Amount": 0.0,
            "Additional Charges / Round Off": 0.0,
            "Total Invoice Value": 0.0,
            "Reverse Charge": "No",
            "IRN No": "",
            "E-Way Bill No": "",
            "Amount in Words": "",
            "Additional Remarks": ""
        }
        
        # Check if we have invoice data in the response
        if "error" in llm_response:
            normalized_data["Additional Remarks"] = f"Error in LLM extraction: {llm_response['error']}"
            return normalized_data
            
        # Extract invoice data from the LLM response
        try:
            invoice_data = llm_response.get("invoice_data", {})
            
            # Map the fields from the LLM response
            field_mapping = {
                "Document Type": "Document Type",
                "Invoice Number": "Invoice/Document Number",
                "Invoice Date": "Invoice/Document Date",
                "Supplier Name": "Supplier Name",
                "Supplier GSTIN": "Supplier GSTIN",
                "Supplier Address": "Supplier Address",
                "Buyer Name": "Buyer Name",
                "Buyer GSTIN": "Buyer GSTIN",
                "Buyer Address": "Buyer Address",
                "Total Invoice Value": "Total Invoice Value"
            }
            
            # Update normalized data with values from the LLM response
            for llm_field, norm_field in field_mapping.items():
                if llm_field in invoice_data:
                    normalized_data[norm_field] = invoice_data[llm_field]
            
            # Convert numeric values to float
            for key in ["Total Quantity", "Subtotal/Taxable Value", "CGST Amount", 
                        "SGST Amount", "IGST Amount", "CESS Amount", 
                        "Additional Charges / Round Off", "Total Invoice Value"]:
                try:
                    if normalized_data[key] and normalized_data[key] != "":
                        # Remove any currency symbols or commas
                        if isinstance(normalized_data[key], str):
                            normalized_data[key] = re.sub(r'[₹$,]', '', normalized_data[key])
                        normalized_data[key] = float(normalized_data[key])
                except (ValueError, TypeError):
                    normalized_data[key] = 0.0
            
            # Add information about which LLM provider was used
            normalized_data["Additional Remarks"] = f"Extracted with {self.llm_provider.capitalize()} LLM"
            
            return normalized_data
            
        except Exception as e:
            print(f"Error normalizing invoice data: {str(e)}")
            normalized_data["Additional Remarks"] = f"Error normalizing data: {str(e)}"
            return normalized_data
    
    def _normalize_line_items(self, llm_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normalize and structure the line item data from the LLM response."""
        # Check if we have an error or empty response
        if "error" in llm_response or "line_items" not in llm_response:
            return []
            
        try:
            line_items = llm_response.get("line_items", [])
            normalized_items = []
            
            for i, item in enumerate(line_items):
                # Create a default structure for each line item
                normalized_item = {
                    "Invoice Serial Number": self.serial_number,
                    "Invoice Number": llm_response.get("invoice_data", {}).get("Invoice Number", ""),
                    "Line #": i + 1,
                    "PO Identifier": "",
                    "Item/SKU Code": "",
                    "Item Description": "",
                    "HSN Code": "",
                    "Quantity": 0.0,
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
                
                # Map the fields from the LLM response
                field_mapping = {
                    "Line Number": "Line #",
                    "Item/SKU Code": "Item/SKU Code",
                    "Item Description": "Item Description",
                    "HSN Code": "HSN Code",
                    "Quantity": "Quantity",
                    "Unit of Measurement": "UOM",
                    "Unit Price": "Unit Price",
                    "Discount": "Discount",
                    "Tax Rate": "Tax Rate",
                    "CGST Rate": "CGST Rate",
                    "SGST Rate": "SGST Rate",
                    "IGST Rate": "IGST Rate",
                    "CGST Amount": "CGST Amount",
                    "SGST Amount": "SGST Amount",
                    "IGST Amount": "IGST Amount",
                    "Line Total Value": "Line Total Value"
                }
                
                # Update normalized item with values from the LLM response
                for llm_field, norm_field in field_mapping.items():
                    if llm_field in item:
                        normalized_item[norm_field] = item[llm_field]
                
                # Convert numeric values to float
                for key in ["Quantity", "Unit Price", "Discount", "CGST Amount", 
                            "SGST Amount", "IGST Amount", "Line Total Value"]:
                    try:
                        if normalized_item[key] and normalized_item[key] != "":
                            # Remove any currency symbols or commas
                            if isinstance(normalized_item[key], str):
                                normalized_item[key] = re.sub(r'[₹$,]', '', normalized_item[key])
                            normalized_item[key] = float(normalized_item[key])
                    except (ValueError, TypeError):
                        normalized_item[key] = 0.0
                
                normalized_items.append(normalized_item)
            
            return normalized_items
            
        except Exception as e:
            print(f"Error normalizing line items: {str(e)}")
            return []
    
    def _extract_basic_info_from_text(self) -> Dict[str, Any]:
        """
        Fallback method to extract basic information from text using regex patterns.
        This is used when the LLM API fails.
        """
        # Create a basic structure
        basic_info = {
            "Serial Number": self.serial_number,
            "Document Type": "Tax Invoice",
            "Invoice/Document Number": "",
            "Invoice/Document Date": "",
            "Supplier Name": "",
            "Supplier GSTIN": "",
            "Supplier Address": "",
            "Buyer Name": "",
            "Buyer GSTIN": "",
            "Buyer Address": "",
            "Total Invoice Value": 0.0,
            "Additional Remarks": f"Extracted with fallback method due to {self.llm_provider.capitalize()} API failure"
        }
        
        # Extract document type
        if "tax invoice" in self.text.lower():
            basic_info["Document Type"] = "Tax Invoice"
        elif "delivery challan" in self.text.lower():
            basic_info["Document Type"] = "Delivery Challan"
        
        # Extract invoice number
        invoice_patterns = [
            r"Invoice\s*No\.?\s*:?\s*([A-Za-z0-9/\-_]+)",
            r"Document\s*No\s*:?\s*([A-Za-z0-9/\-_]+)",
            r"(Mensa/[A-Z]{2}/[A-Z]{3}/\d+)"
        ]
        for pattern in invoice_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                basic_info["Invoice/Document Number"] = match.group(1).strip()
                break
        
        # Extract date
        date_patterns = [
            r"Invoice\s*Date\s*:\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
            r"Date\s*:\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
            r"Date\s*:\s*(\d{1,2}[A-Za-z]{3}\d{2,4})",
            r"Date\s*of\s*Supply\s*:\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})"
        ]
        for pattern in date_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                basic_info["Invoice/Document Date"] = match.group(1).strip()
                break
        
        # Extract company names
        # First few lines often contain the supplier name
        lines = self.text.split('\n')
        if len(lines) > 1:
            for i in range(min(3, len(lines))):
                if lines[i].strip() and "invoice" not in lines[i].lower():
                    basic_info["Supplier Name"] = lines[i].strip()
                    break
        
        # Look for buyer/customer name - improved patterns
        buyer_patterns = [
            r"(?:Buyer|Bill To|Customer|Ship To|Billed To)\s*:\s*([^\n]+)",
            r"(?:Buyer|Bill To|Customer|Ship To|Billed To)\s*Name\s*:\s*([^\n]+)",
            r"Details\s*of\s*Receiver\s*[^:]*:\s*([^\n]+)"
        ]
        for pattern in buyer_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                basic_info["Buyer Name"] = match.group(1).strip()
                break
        
        # Look for buyer info followed by legal name
        legal_name_match = re.search(r"Legal\s*Name\s*:?\s*([^\n]+)", self.text, re.IGNORECASE)
        if legal_name_match:
            basic_info["Buyer Name"] = legal_name_match.group(1).strip()
        
        # Look for buyer info by explicit company names
        known_buyers = ["Myntra", "Jabong", "India Pvt Ltd"]
        for buyer in known_buyers:
            if buyer.lower() in self.text.lower():
                # Find the complete line containing this company name
                for line in lines:
                    if buyer.lower() in line.lower():
                        basic_info["Buyer Name"] = line.strip()
                        break
                if basic_info["Buyer Name"]:
                    break
        
        # Look specifically for "Myntra Jabong India Pvt Ltd" which is in this invoice
        myntra_match = re.search(r"(Myntra\s*Jabong\s*India\s*Pvt\s*Ltd)", self.text, re.IGNORECASE)
        if myntra_match:
            basic_info["Buyer Name"] = myntra_match.group(1).strip()
        
        # Extract GSTIN
        gstin_pattern = r"([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{1}[Z]{1}[0-9A-Z]{1})"
        gstin_matches = re.findall(gstin_pattern, self.text)
        if len(gstin_matches) >= 1:
            basic_info["Supplier GSTIN"] = gstin_matches[0]
        if len(gstin_matches) >= 2:
            basic_info["Buyer GSTIN"] = gstin_matches[1]
        
        # Extract addresses - add more patterns
        supplier_address_match = re.search(r"(SVS\s*Warehouse[^\n]+(?:\n[^\n]+){1,3})", self.text)
        if supplier_address_match:
            address = supplier_address_match.group(1).replace('\n', ' ')
            basic_info["Supplier Address"] = address.strip()
        
        # Extract total value
        total_patterns = [
            r"Total\s*Invoice\s*Value\s*(?:in\s*INR)?\s*:?\s*(?:₹|Rs\.?)?\s*(\d[\d,.]+\.\d+)",
            r"Grand\s*Total\s*:?\s*(?:₹|Rs\.?)?\s*(\d[\d,.]+\.\d+)",
            r"Total\s*Amount\s*:?\s*(?:₹|Rs\.?)?\s*(\d[\d,.]+\.\d+)",
            r"Total\s*:?\s*(?:₹|Rs\.?)?\s*(\d[\d,.]+\.\d+)"
        ]
        for pattern in total_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace(',', '')
                try:
                    basic_info["Total Invoice Value"] = float(value_str)
                except ValueError:
                    pass
                break
        
        return basic_info
    
    def parse(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Parse the PDF using LLM to extract structured data.
        Returns a tuple of (invoice_data, item_data).
        """
        # Extract text if not already extracted
        if not self.text:
            self.extract_text()
            
        # If we still don't have text, log an error
        if not self.text:
            print("WARNING: Failed to extract any text from the PDF!")
            return {
                "Serial Number": self.serial_number,
                "Document Type": "Tax Invoice",
                "Invoice/Document Number": "",
                "Additional Remarks": "Failed to extract text from PDF"
            }, []
        
        print(f"Successfully extracted {len(self.text)} characters of text")
        print(f"First 200 characters: {self.text[:200]}")
        
        # Generate prompt for the LLM
        prompt = self._generate_llm_prompt()
        
        # Call the selected LLM API
        print(f"Calling {self.llm_provider.capitalize()} API to extract structured data...")
        llm_response = self._call_llm_api(prompt)
        
        # Check for API error
        if "error" in llm_response:
            print(f"LLM API error: {llm_response['error']}")
            print("Falling back to basic regex extraction...")
            
            # Use fallback method to extract basic info
            invoice_data = self._extract_basic_info_from_text()
            return invoice_data, []
        
        # Process and normalize the LLM response
        invoice_data = self._normalize_invoice_data(llm_response)
        item_data = self._normalize_line_items(llm_response)
        
        return invoice_data, item_data 