from pydantic import BaseModel, Field
from typing import List, Optional


class InvoiceItemLevel(BaseModel):
    """Model for invoice item-level data"""
    invoice_serial_number: str = Field(alias="Invoice Serial Number")
    invoice_number: str = Field(alias="Invoice Number")
    line_number: int = Field(alias="Line #")
    po_identifier: Optional[str] = Field(default="", alias="PO Identifier")
    item_sku_code: Optional[str] = Field(default="", alias="Item/SKU Code")
    item_description: Optional[str] = Field(default="", alias="Item Description")
    hsn_code: Optional[str] = Field(default="", alias="HSN Code")
    quantity: float = Field(alias="Quantity")
    uom: Optional[str] = Field(default="", alias="UOM")
    unit_price: float = Field(alias="Unit Price")
    discount: Optional[float] = Field(default=0.0, alias="Discount")
    tax_rate: Optional[str] = Field(default="", alias="Tax Rate")
    cgst_rate: Optional[str] = Field(default="", alias="CGST Rate")
    sgst_rate: Optional[str] = Field(default="", alias="SGST Rate")
    igst_rate: Optional[str] = Field(default="", alias="IGST Rate")
    cgst_amount: Optional[float] = Field(default=0.0, alias="CGST Amount")
    sgst_amount: Optional[float] = Field(default=0.0, alias="SGST Amount")
    igst_amount: Optional[float] = Field(default=0.0, alias="IGST Amount")
    line_total_value: float = Field(alias="Line Total Value")


class InvoiceLevel(BaseModel):
    """Model for invoice-level data"""
    serial_number: str = Field(alias="Serial Number")
    document_type: str = Field(alias="Document Type")
    invoice_document_number: str = Field(alias="Invoice/Document Number")
    invoice_document_date: str = Field(alias="Invoice/Document Date")
    supplier_name: str = Field(alias="Supplier Name")
    supplier_gstin: str = Field(alias="Supplier GSTIN")
    supplier_address: str = Field(alias="Supplier Address")
    buyer_name: str = Field(alias="Buyer Name")
    buyer_gstin: str = Field(alias="Buyer GSTIN")
    buyer_address: str = Field(alias="Buyer Address")
    consignee_name: Optional[str] = Field(default="", alias="Consignee Name")
    consignee_gstin: Optional[str] = Field(default="", alias="Consignee GSTIN")
    consignee_address: Optional[str] = Field(default="", alias="Consignee Address")
    po_number: Optional[str] = Field(default="", alias="PO Number")
    so_number: Optional[str] = Field(default="", alias="SO Number")
    str_number: Optional[str] = Field(default="", alias="STR Number")
    box_count: Optional[str] = Field(default="", alias="Box Count")
    total_quantity: Optional[float] = Field(default=0.0, alias="Total Quantity")
    subtotal_taxable_value: float = Field(alias="Subtotal/Taxable Value")
    cgst_amount: Optional[float] = Field(default=0.0, alias="CGST Amount")
    sgst_amount: Optional[float] = Field(default=0.0, alias="SGST Amount")
    igst_amount: Optional[float] = Field(default=0.0, alias="IGST Amount")
    cess_amount: Optional[float] = Field(default=0.0, alias="CESS Amount")
    additional_charges: Optional[float] = Field(default=0.0, alias="Additional Charges / Round Off")
    total_invoice_value: float = Field(alias="Total Invoice Value")
    reverse_charge: Optional[str] = Field(default="No", alias="Reverse Charge")
    irn_no: Optional[str] = Field(default="", alias="IRN No")
    eway_bill_no: Optional[str] = Field(default="", alias="E-Way Bill No")
    amount_in_words: Optional[str] = Field(default="", alias="Amount in Words")
    additional_remarks: Optional[str] = Field(default="", alias="Additional Remarks")


class ParsingResponse(BaseModel):
    """Response model for parsing result"""
    status: str
    invoice_csv_url: str
    item_csv_url: str
    message: str 