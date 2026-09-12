from decimal import Decimal

from pydantic import BaseModel, Field


class PriceUpdate(BaseModel):
    price: Decimal | None = Field(default=None, ge=0, description="Precio por unidad o por kg")
    margin_percent: Decimal | None = Field(
        default=None, ge=0, description="Si se envía, el precio se calcula desde el último costo"
    )
    price_per_lb: Decimal | None = Field(default=None, ge=0, description="Solo productos a granel")


class PriceItem(BaseModel):
    variant_id: int
    sku: str
    product_id: int
    product_name: str
    variant_label: str
    unit_of_measure: str
    is_bulk: bool
    price: Decimal | None
    price_per_lb: Decimal | None
    suggested_price_per_lb: Decimal | None
    margin_percent: Decimal | None
    last_cost: Decimal | None
    status: str
    tax_rate: Decimal


class PricePage(BaseModel):
    items: list[PriceItem]
    total: int
    page: int
    page_size: int
