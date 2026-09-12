from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPK, TimestampMixin


class VariantPrice(Base, TimestampMixin):
    __tablename__ = "variant_prices"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_price_non_negative"),
        CheckConstraint("status IN ('borrador','publicado')", name="ck_price_status"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id"), unique=True, nullable=False)
    # Precio por unidad, o por kg (unidad canónica) si el producto es a granel.
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    # Solo granel: precio por libra, editable (se sugiere el derivado del kg).
    price_per_lb: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    cost_reference: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    margin_percent: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="borrador")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    variant = relationship("Variant")
