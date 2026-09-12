from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class StockItem(BaseModel):
    variant_id: int
    sku: str
    product_id: int
    product_name: str
    variant_label: str
    unit_of_measure: str
    is_bulk: bool
    quantity: Decimal
    low_stock_threshold: Decimal
    is_low: bool


class StockPage(BaseModel):
    items: list[StockItem]
    total: int
    page: int
    page_size: int


class ThresholdUpdate(BaseModel):
    low_stock_threshold: Decimal | None = Field(default=None, ge=0)


class AdjustmentCreate(BaseModel):
    variant_id: int
    quantity_delta: Decimal = Field(description="Positivo suma, negativo resta")
    notes: str = Field(min_length=3, description="Motivo del ajuste (obligatorio)")


class MovementOut(BaseModel):
    id: int
    variant_id: int
    sku: str
    product_name: str
    movement_type: str
    quantity: Decimal
    balance_after: Decimal
    unit_cost: Decimal | None
    reference_type: str | None
    reference_id: int | None
    notes: str | None
    created_by: int
    created_at: datetime


class MovementPage(BaseModel):
    items: list[MovementOut]
    total: int
    page: int
    page_size: int
