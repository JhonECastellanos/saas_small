from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SupplierCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    tax_id: str | None = None
    phone: str | None = None
    email: str | None = None


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    tax_id: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool | None = None


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    tax_id: str | None
    phone: str | None
    email: str | None
    is_active: bool


class PurchaseItemCreate(BaseModel):
    variant_id: int
    quantity: Decimal = Field(gt=0)
    unit: str = Field(pattern="^(unidad|kg|lb)$", description="Unidad en que se digita la compra")
    unit_cost: Decimal = Field(ge=0, description="Costo por la unidad digitada")


class PurchaseCreate(BaseModel):
    supplier_id: int
    purchase_date: date
    notes: str | None = None
    items: list[PurchaseItemCreate] = Field(min_length=1)


class PurchaseItemOut(BaseModel):
    id: int
    variant_id: int
    sku: str
    product_name: str
    variant_label: str
    quantity: Decimal
    unit_cost: Decimal
    input_unit: str
    input_quantity: Decimal
    line_total: Decimal


class PurchaseOut(BaseModel):
    id: int
    supplier_id: int
    supplier_name: str
    purchase_date: date
    status: str
    notes: str | None
    total_cost: Decimal
    created_at: datetime
    items: list[PurchaseItemOut]


class PurchaseListItem(BaseModel):
    id: int
    supplier_name: str
    purchase_date: date
    status: str
    total_cost: Decimal
    item_count: int
    created_at: datetime


class PurchasePage(BaseModel):
    items: list[PurchaseListItem]
    total: int
    page: int
    page_size: int
