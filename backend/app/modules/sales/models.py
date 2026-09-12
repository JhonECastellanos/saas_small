from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPK, TimestampMixin


class Sale(Base, TimestampMixin):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("status IN ('completada','anulada')", name="ck_sales_status"),
        CheckConstraint(
            "payment_method IN ('efectivo','transferencia','tarjeta')", name="ck_sales_payment"
        ),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="completada")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(15), nullable=False)
    # Datos opcionales del cliente para la factura
    customer_name: Mapped[str | None] = mapped_column(String(150))
    customer_id_number: Mapped[str | None] = mapped_column(String(30))
    # Turno de caja en que se hizo la venta (si el vendedor tenía uno abierto)
    cash_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("cash_sessions.id"), index=True
    )

    items: Mapped[list["SaleItem"]] = relationship(back_populates="sale")
    user = relationship("User")


class SaleItem(Base):
    """Snapshot inmutable: la factura histórica no depende de precios vivos."""

    __tablename__ = "sale_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_sale_item_qty_positive"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id"), nullable=False)
    sku_snapshot: Mapped[str] = mapped_column(String(60), nullable=False)
    description_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    # Cantidad en la unidad en que se vendió (unit_snapshot: unidad/kg/lb).
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_snapshot: Mapped[str] = mapped_column(String(10), nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0")
    )
    # Último costo de compra al momento de vender (para reportes de utilidad)
    unit_cost_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    tax_rate_snapshot: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    sale: Mapped[Sale] = relationship(back_populates="items")
    variant = relationship("Variant")
