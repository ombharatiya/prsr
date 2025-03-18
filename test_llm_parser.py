#!/usr/bin/env python
"""
Test script for the LLM-based PDF invoice parser using either Google's Gemini API or OpenAI's API.
This script will parse a sample invoice PDF and save the extracted data to CSV files.
"""

import os
import sys
import argparse
from llm_pdf_parser import LLMPDFParser
from utils import save_to_csv, save_items_to_csv, ensure_directories

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Parse a PDF invoice using LLM.")
    parser.add_argument("--provider", "-p", choices=["google", "openai"], default="google",
                        help="LLM provider to use (default: google)")
    parser.add_argument("--input", "-i", default="MyTest/input/Mensa_KA_BLR_830 (1).pdf",
                        help="Path to the input PDF file")
    parser.add_argument("--output-dir", "-o", default="MyTest/output",
                        help="Directory to save output CSV files")
    return parser.parse_args()

def main():
    """Main function to test the LLM PDF parser."""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Set the LLM provider
    llm_provider = args.provider
    print(f"Using {llm_provider.capitalize()} as the LLM provider")
    
    # Set API keys based on provider
    api_key = None
    openai_api_key = None
    
    if llm_provider == "google":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("Error: GOOGLE_API_KEY environment variable not set.")
            print("Please set it with: export GOOGLE_API_KEY=your_api_key")
            sys.exit(1)
    elif llm_provider == "openai":
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            print("Error: OPENAI_API_KEY environment variable not set.")
            print("Please set it with: export OPENAI_API_KEY=your_api_key")
            sys.exit(1)
    
    # Ensure output directories exist
    ensure_directories()
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Get the sample PDF path
    sample_pdf = args.input
    if not os.path.exists(sample_pdf):
        print(f"Error: Sample PDF not found at {sample_pdf}")
        sys.exit(1)
    
    print(f"Parsing sample invoice: {sample_pdf}")
    
    # Initialize parser and parse PDF with the specified provider
    parser = LLMPDFParser(
        pdf_path=sample_pdf,
        api_key=api_key,
        llm_provider=llm_provider,
        openai_api_key=openai_api_key
    )
    invoice_data, item_data = parser.parse()
    
    # Print the raw text extracted for debugging
    print("\nExtracted text sample (first 500 chars):")
    print(parser.text[:500])
    print("..." if len(parser.text) > 500 else "")
    
    # Save data to CSV files
    provider_prefix = "google" if llm_provider == "google" else "openai"
    invoice_csv = f"{args.output_dir}/{provider_prefix}_invoice_level.csv"
    item_csv = f"{args.output_dir}/{provider_prefix}_item_level.csv"
    
    save_to_csv(invoice_data, invoice_csv)
    save_items_to_csv(item_data, item_csv)
    
    print(f"\nInvoice-level data saved to: {invoice_csv}")
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