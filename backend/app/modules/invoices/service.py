import re
from collections import defaultdict
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.auth.models import User
from app.modules.invoices.models import Invoice
from app.modules.invoices.schemas import (
    InvoiceDetail,
    InvoiceLineOut,
    InvoiceListItem,
    InvoicePage,
    TaxBreakdownItem,
)
from app.modules.sales.models import Sale


def _number(invoice: Invoice) -> str:
    return f"{invoice.invoice_prefix}-{invoice.invoice_number:06d}"


def list_invoices(
    db: Session,
    user: User,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> InvoicePage:
    query = select(Invoice, Sale).join(Sale, Invoice.sale_id == Sale.id)
    if user.role != "admin":
        query = query.where(Sale.user_id == user.id)
    if q:
        # Busca por número de factura en toda la base: "FV-000012", "12" o "fv12"
        digits = re.sub(r"\D", "", q)
        if digits:
            query = query.where(Invoice.invoice_number == int(digits))
        else:
            query = query.where(Invoice.invoice_prefix.ilike(f"%{q.strip()}%"))
    if date_from:
        query = query.where(func.date(Invoice.issued_at) >= date_from)
    if date_to:
        query = query.where(func.date(Invoice.issued_at) <= date_to)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.options(selectinload(Sale.user))
        .order_by(Invoice.invoice_number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = [
        InvoiceListItem(
            id=inv.id,
            number=_number(inv),
            sale_id=sale.id,
            sale_status=sale.status,
            seller_name=sale.user.full_name,
            total=sale.total,
            issued_at=inv.issued_at,
        )
        for inv, sale in rows
    ]
    return InvoicePage(items=items, total=total, page=page, page_size=page_size)


def get_invoice(db: Session, invoice_id: int, user: User) -> InvoiceDetail:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Factura no encontrada")
    sale = db.scalar(
        select(Sale)
        .options(selectinload(Sale.items), selectinload(Sale.user))
        .where(Sale.id == invoice.sale_id)
    )
    if user.role != "admin" and sale.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo puedes ver tus propias facturas")

    breakdown: dict[Decimal, dict[str, Decimal]] = defaultdict(
        lambda: {"base": Decimal("0"), "tax": Decimal("0")}
    )
    for item in sale.items:
        breakdown[item.tax_rate_snapshot]["base"] += item.line_total
        breakdown[item.tax_rate_snapshot]["tax"] += item.tax_amount

    return InvoiceDetail(
        id=invoice.id,
        number=_number(invoice),
        sale_id=sale.id,
        sale_status=sale.status,
        business_name=invoice.business_name,
        business_tax_id=invoice.business_tax_id,
        business_address=invoice.business_address,
        business_phone=invoice.business_phone,
        currency=invoice.currency,
        seller_name=sale.user.full_name,
        payment_method=sale.payment_method,
        customer_name=sale.customer_name,
        customer_id_number=sale.customer_id_number,
        issued_at=invoice.issued_at,
        items=[
            InvoiceLineOut(
                id=i.id,
                description=i.description_snapshot,
                sku=i.sku_snapshot,
                quantity=i.quantity,
                unit=i.unit_snapshot,
                unit_price=i.unit_price_snapshot,
                discount_pct=i.discount_pct,
                tax_rate=i.tax_rate_snapshot,
                tax_amount=i.tax_amount,
                line_total=i.line_total,
            )
            for i in sale.items
        ],
        subtotal=sale.subtotal,
        discount_amount=sale.discount_amount,
        tax_amount=sale.tax_amount,
        total=sale.total,
        tax_breakdown=[
            TaxBreakdownItem(tax_rate=rate, base=vals["base"], tax=vals["tax"])
            for rate, vals in sorted(breakdown.items())
        ],
    )
