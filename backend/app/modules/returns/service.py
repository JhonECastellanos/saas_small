from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.money import D, KG_PER_LB, q2, q3
from app.modules.auth.models import User
from app.modules.inventory.service import apply_movement
from app.modules.products.models import Product, Variant
from app.modules.returns.models import SaleReturn, SaleReturnItem
from app.modules.returns.schemas import ReturnCreate, ReturnItemOut, ReturnOut
from app.modules.sales.models import Sale, SaleItem


def create_return(db: Session, invoice_id: int, data: ReturnCreate, user: User) -> ReturnOut:
    from app.modules.invoices.models import Invoice

    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Factura no encontrada")

    sale = db.scalar(
        select(Sale)
        .options(selectinload(Sale.items))
        .where(Sale.id == invoice.sale_id)
    )
    if sale is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venta no encontrada")
    if sale.status == "anulada":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "No se puede devolver una venta anulada"
        )

    sale_items_by_id: dict[int, SaleItem] = {si.id: si for si in sale.items}
    return_results: list[dict] = []
    total_amount = Decimal("0")

    for item in data.items:
        sale_item = sale_items_by_id.get(item.sale_item_id)
        if sale_item is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Ítem {item.sale_item_id} no pertenece a esta venta",
            )
        if D(item.quantity) > sale_item.quantity:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Cantidad devuelta excede la vendida para el ítem {item.sale_item_id}",
            )

        variant = db.get(Variant, sale_item.variant_id)
        if variant is None:
            continue
        delta = q3(D(item.quantity))
        if variant.unit_of_measure in ("kg", "lb") and sale_item.unit_snapshot == "lb":
            delta = q3(D(item.quantity) * KG_PER_LB)

        apply_movement(
            db,
            variant_id=sale_item.variant_id,
            delta=delta,
            movement_type="ajuste",
            user_id=user.id,
            reference_type="sale",
            reference_id=sale.id,
            notes=f"Devolución de factura #{invoice_id}",
        )

        line_total = q2(D(item.quantity) * sale_item.unit_price_snapshot)
        total_amount += line_total
        return_results.append(
            {
                "sale_item_id": sale_item.id,
                "description": sale_item.description_snapshot,
                "quantity": D(item.quantity),
                "unit_price": sale_item.unit_price_snapshot,
                "line_total": line_total,
            }
        )

    ret = SaleReturn(
        sale_id=sale.id,
        user_id=user.id,
        total_amount=q2(total_amount),
        reason=data.reason,
    )
    db.add(ret)
    db.flush()

    out_items = []
    for ri in return_results:
        ritem = SaleReturnItem(
            return_id=ret.id,
            sale_item_id=ri["sale_item_id"],
            quantity=ri["quantity"],
            unit_price=ri["unit_price"],
            line_total=ri["line_total"],
        )
        db.add(ritem)
        db.flush()
        out_items.append(
            ReturnItemOut(
                id=ritem.id,
                sale_item_id=ri["sale_item_id"],
                description=ri["description"],
                quantity=ri["quantity"],
                unit_price=ri["unit_price"],
                line_total=ri["line_total"],
            )
        )

    db.commit()
    return ReturnOut(
        id=ret.id,
        sale_id=sale.id,
        total_amount=ret.total_amount,
        reason=ret.reason,
        created_at=ret.created_at,
        items=out_items,
    )
