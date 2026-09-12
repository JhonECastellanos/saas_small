from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ReturnItemInput(BaseModel):
    sale_item_id: int
    quantity: Decimal = Field(gt=0)


class ReturnCreate(BaseModel):
    items: list[ReturnItemInput] = Field(min_length=1)
    reason: str | None = None


class ReturnItemOut(BaseModel):
    id: int
    sale_item_id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class ReturnOut(BaseModel):
    id: int
    sale_id: int
    total_amount: Decimal
    reason: str | None
    created_at: datetime
    items: list[ReturnItemOut]
