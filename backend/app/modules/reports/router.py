from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_admin
from app.core.money import q2
from app.modules.products.models import Product, Variant
from app.modules.sales.models import Sale, SaleItem

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_admin)])


def _sales_in_range(date_from: str | None, date_to: str | None):
    conditions = [Sale.status == "completada"]
    if date_from:
        conditions.append(func.date(Sale.created_at) >= date_from)
    if date_to:
        conditions.append(func.date(Sale.created_at) <= date_to)
    return conditions


@router.get("/sales")
def sales_report(
    date_from: str | None = None,
    date_to: str | None = None,
    top: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Resumen de ventas del periodo: totales, por día, por método de pago,
    productos más vendidos y utilidad estimada (precio - último costo al vender)."""
    conditions = _sales_in_range(date_from, date_to)

    totals = db.execute(
        select(
            func.count(Sale.id),
            func.coalesce(func.sum(Sale.subtotal), 0),
            func.coalesce(func.sum(Sale.discount_amount), 0),
            func.coalesce(func.sum(Sale.tax_amount), 0),
            func.coalesce(func.sum(Sale.total), 0),
        ).where(*conditions)
    ).one()

    by_day = db.execute(
        select(
            func.date(Sale.created_at).label("day"),
            func.count(Sale.id),
            func.coalesce(func.sum(Sale.total), 0),
        )
        .where(*conditions)
        .group_by("day")
        .order_by("day")
    ).all()

    by_payment = db.execute(
        select(Sale.payment_method, func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0))
        .where(*conditions)
        .group_by(Sale.payment_method)
    ).all()

    # Top productos con utilidad: ingresos - (costo snapshot × cantidad canónica no aplica
    # aquí: el costo es por unidad vendida en su unidad canónica; para líneas en lb el
    # costo snapshot es por kg, así que se usa el costo prorrateado guardado al vender).
    line_cost = SaleItem.unit_cost_snapshot * SaleItem.quantity
    top_products = db.execute(
        select(
            Product.id,
            Product.name,
            Variant.sku,
            func.coalesce(func.sum(SaleItem.quantity), 0).label("units"),
            func.coalesce(func.sum(SaleItem.line_total), 0).label("revenue"),
            func.coalesce(func.sum(line_cost), 0).label("cost"),
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .join(Variant, SaleItem.variant_id == Variant.id)
        .join(Product, Variant.product_id == Product.id)
        .where(*conditions)
        .group_by(Product.id, Product.name, Variant.sku)
        .order_by(func.sum(SaleItem.line_total).desc())
        .limit(top)
    ).all()

    def profit_row(revenue, cost) -> dict:
        revenue_d = q2(revenue)
        cost_d = q2(cost) if cost is not None else None
        return {
            "revenue": str(revenue_d),
            "cost": str(cost_d) if cost_d is not None else None,
            "profit": str(q2(revenue_d - cost_d)) if cost_d is not None else None,
        }

    total_revenue = q2(totals[1])
    total_cost = db.scalar(
        select(func.coalesce(func.sum(line_cost), 0))
        .select_from(SaleItem)
        .join(Sale, SaleItem.sale_id == Sale.id)
        .where(*conditions, SaleItem.unit_cost_snapshot.is_not(None))
    ) or Decimal("0")

    return {
        "totals": {
            "sales_count": totals[0],
            "subtotal": str(q2(totals[1])),
            "discount": str(q2(totals[2])),
            "tax": str(q2(totals[3])),
            "total": str(q2(totals[4])),
            "estimated_cost": str(q2(total_cost)),
            "estimated_profit": str(q2(total_revenue - q2(total_cost))),
        },
        "by_day": [
            {"day": str(day), "count": count, "total": str(q2(total))}
            for day, count, total in by_day
        ],
        "by_payment_method": [
            {"method": method, "count": count, "total": str(q2(total))}
            for method, count, total in by_payment
        ],
        "top_products": [
            {
                "product_id": product_id,
                "name": name,
                "sku": sku,
                "units": str(units),
                **profit_row(revenue, cost),
            }
            for product_id, name, sku, units, revenue, cost in top_products
        ],
    }
