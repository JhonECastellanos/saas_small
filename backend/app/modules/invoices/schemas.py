from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class InvoiceListItem(BaseModel):
    id: int
    number: str
    sale_id: int
    sale_status: str
    seller_name: str
    total: Decimal
    issued_at: datetime


class InvoicePage(BaseModel):
    items: list[InvoiceListItem]
    total: int
    page: int
    page_size: int


class InvoiceLineOut(BaseModel):
    id: int
    description: str
    sku: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    discount_pct: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    line_total: Decimal


class TaxBreakdownItem(BaseModel):
    tax_rate: Decimal
    base: Decimal
    tax: Decimal


class InvoiceDetail(BaseModel):
    id: int
    number: str
    sale_id: int
    sale_status: str
    business_name: str
    business_tax_id: str | None
    business_address: str | None
    business_phone: str | None
    currency: str
    seller_name: str
    payment_method: str
    customer_name: str | None
    customer_id_number: str | None
    issued_at: datetime
    items: list[InvoiceLineOut]
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total: Decimal
    tax_breakdown: list[TaxBreakdownItem]
