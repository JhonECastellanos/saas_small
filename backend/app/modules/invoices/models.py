from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPK


class InvoiceCounter(Base):
    """Consecutivo sin huecos: fila única incrementada con UPDATE ... RETURNING
    dentro de la misma transacción de la venta (el row-lock serializa)."""

    __tablename__ = "invoice_counters"
    __table_args__ = (CheckConstraint("id = 1", name="ck_invoice_counter_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1, autoincrement=False)
    last_number: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("invoice_prefix", "invoice_number", name="uq_invoice_number"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), unique=True, nullable=False)
    invoice_prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    invoice_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Snapshot del negocio al momento de emitir (la factura no cambia después).
    business_name: Mapped[str] = mapped_column(String(150), nullable=False)
    business_tax_id: Mapped[str | None] = mapped_column(String(30))
    business_address: Mapped[str | None] = mapped_column(Text)
    business_phone: Mapped[str | None] = mapped_column(String(30))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="COP")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    sale = relationship("Sale")
