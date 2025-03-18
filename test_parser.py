#!/usr/bin/env python
"""
Test script for the PDF invoice parser.
This script will parse a sample invoice PDF and save the extracted data to CSV files.
"""

import os
import sys
from pdf_parser import InvoiceParser
from utils import save_to_csv, save_items_to_csv, ensure_directories

def main():
    """Main function to test the PDF parser."""
    # Ensure output directory exists
    ensure_directories()
    
    # Get the sample PDF path
    sample_pdf = "invoices/input/Mensa_KA_BLR_830 (1).pdf"
    if not os.path.exists(sample_pdf):
        print(f"Error: Sample PDF not found at {sample_pdf}")
        sys.exit(1)
    
    print(f"Parsing sample invoice: {sample_pdf}")
    
    # Initialize parser and parse PDF
    parser = InvoiceParser(sample_pdf)
    invoice_data, item_data = parser.parse()
    
    # Save data to CSV files
    invoice_csv = "output/test_invoice_level.csv"
    item_csv = "output/test_item_level.csv"
    
    save_to_csv(invoice_data, invoice_csv)
    save_items_to_csv(item_data, item_csv)
    
    print(f"Invoice-level data saved to: {invoice_csv}")
    print(f"Item-level data saved to: {item_csv}")
    print(f"Found {len(item_data)} line items")
    
    # Print some sample data
    print("\nInvoice Summary:")
    print(f"Document Type: {invoice_data['Document Type']}")
    print(f"Invoice Number: {invoice_data['Invoice/Document Number']}")
    print(f"Invoice Date: {invoice_data['Invoice/Document Date']}")
    print(f"Supplier: {invoice_data['Supplier Name']}")
    print(f"Buyer: {invoice_data['Buyer Name']}")
    print(f"Total Value: {invoice_data['Total Invoice Value']}")
    
    if item_data:
        print("\nFirst Item:")
        first_item = item_data[0]
        print(f"SKU: {first_item['Item/SKU Code']}")
        print(f"Quantity: {first_item['Quantity']}")
        print(f"Unit Price: {first_item['Unit Price']}")
        print(f"Tax Rate: {first_item['Tax Rate']}")
        print(f"Line Total: {first_item['Line Total Value']}")

if __name__ == "__main__":
    main() 