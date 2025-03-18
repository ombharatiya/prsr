import os
import csv
import pandas as pd
from typing import Dict, List, Any


def ensure_directories():
    """Ensure all required directories exist."""
    os.makedirs("temp", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    

def save_to_csv(data: Dict[str, Any], filepath: str, headers: List[str] = None):
    """
    Save dictionary data to a CSV file.
    
    Args:
        data: Dictionary containing data to save
        filepath: Path to save the CSV file
        headers: Optional list of headers. If None, uses data keys as headers.
    """
    headers = headers or list(data.keys())
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerow(data)


def save_items_to_csv(items: List[Dict[str, Any]], filepath: str, headers: List[str] = None):
    """
    Save a list of dictionaries to a CSV file.
    
    Args:
        items: List of dictionaries containing data to save
        filepath: Path to save the CSV file
        headers: Optional list of headers. If None, uses keys from first item as headers.
    """
    if not items:
        # Create empty file with headers
        headers = headers or ["Invoice Serial Number", "Invoice Number", "Line #", "PO Identifier",
                             "Item/SKU Code", "Item Description", "HSN Code", "Quantity", "UOM",
                             "Unit Price", "Discount", "Tax Rate", "CGST Rate", "SGST Rate",
                             "IGST Rate", "CGST Amount", "SGST Amount", "IGST Amount", "Line Total Value"]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
        return
    
    headers = headers or list(items[0].keys())
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(items)


def save_dataframe_to_csv(df: pd.DataFrame, filepath: str):
    """
    Save a pandas DataFrame to a CSV file.
    
    Args:
        df: DataFrame to save
        filepath: Path to save the CSV file
    """
    df.to_csv(filepath, index=False, encoding='utf-8')


def get_csv_headers(csv_path: str) -> List[str]:
    """
    Get headers from a CSV file.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        List of column headers
    """
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader)
    return headers 