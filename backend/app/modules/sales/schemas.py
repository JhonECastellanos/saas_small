from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CatalogItem(BaseModel):
    variant_id: int
    sku: str
    barcode: str | None
    product_id: int
    product_name: str
    variant_label: str
    unit_of_measure: str
    is_bulk: bool
    price: Decimal
    price_per_lb: Decimal | None
    tax_rate: Decimal
    stock: Decimal


class SaleItemCreate(BaseModel):
    variant_id: int
    quantity: Decimal = Field(gt=0)
    unit: str = Field(pattern="^(unidad|kg|lb)$")
    discount_pct: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class SaleCreate(BaseModel):
    payment_method: str = Field(pattern="^(efectivo|transferencia|tarjeta)$")
    customer_name: str | None = Field(default=None, max_length=150)
    customer_id_number: str | None = Field(default=None, max_length=30)
    items: list[SaleItemCreate] = Field(min_length=1)


class SaleItemOut(BaseModel):
    id: int
    variant_id: int
    sku: str
    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    discount_pct: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    line_total: Decimal


class SaleOut(BaseModel):
    id: int
    status: str
    seller_name: str
    payment_method: str
    customer_name: str | None
    customer_id_number: str | None
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total: Decimal
    created_at: datetime
    invoice_id: int | None
    invoice_number: str | None
    items: list[SaleItemOut]


class SaleListItem(BaseModel):
    id: int
    status: str
    seller_name: str
    payment_method: str
    total: Decimal
    created_at: datetime
    invoice_id: int | None
    invoice_number: str | None


class SalePage(BaseModel):
    items: list[SaleListItem]
    total: int
    page: int
    page_size: int
