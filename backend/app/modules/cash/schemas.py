from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CashOpenRequest(BaseModel):
    opening_amount: Decimal = Field(ge=0, description="Base de caja con la que abre el turno")


class CashCloseRequest(BaseModel):
    closing_amount: Decimal = Field(ge=0, description="Efectivo contado al cerrar")
    notes: str | None = None


class SessionTotals(BaseModel):
    sales_count: int
    total_sold: Decimal
    by_payment_method: dict[str, Decimal]


class CashSessionOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    status: str
    opening_amount: Decimal
    closing_amount: Decimal | None
    expected_cash: Decimal | None
    difference: Decimal | None
    notes: str | None
    opened_at: datetime
    closed_at: datetime | None
    totals: SessionTotals | None = None


class CashSessionPage(BaseModel):
    items: list[CashSessionOut]
    total: int
    page: int
    page_size: int
