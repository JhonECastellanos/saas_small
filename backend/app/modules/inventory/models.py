from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPK


class Stock(Base):
    __tablename__ = "stock"
    __table_args__ = (CheckConstraint("quantity >= 0", name="ck_stock_non_negative"),)

    variant_id: Mapped[int] = mapped_column(
        ForeignKey("variants.id"), primary_key=True, autoincrement=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=Decimal("0"))
    low_stock_threshold: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    variant = relationship("Variant")


class InventoryMovement(Base):
    """Kardex append-only: nunca se actualiza ni borra un movimiento."""

    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('entrada_compra','salida_venta','ajuste')", name="ck_movement_type"
        ),
        Index("ix_movements_variant_created", "variant_id", "created_at"),
        Index("ix_movements_reference", "reference_type", "reference_id"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)  # con signo
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    reference_type: Mapped[str | None] = mapped_column(String(20))
    reference_id: Mapped[int | None] = mapped_column(BigInteger)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    variant = relationship("Variant")
