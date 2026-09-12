from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.money import D, KG_PER_LB, q2, q3
from app.modules.auth.models import User
from app.modules.auth.service import get_business_settings
from app.modules.inventory.models import Stock
from app.modules.inventory.service import (
    InsufficientStockError,
    apply_movement,
    variant_label,
)
from app.modules.invoices.models import Invoice, InvoiceCounter
from app.modules.pricing.models import VariantPrice
from app.modules.products.models import Product, Variant, VariantAttributeValue
from app.modules.purchases.service import last_unit_cost
from app.modules.sales.models import Sale, SaleItem
from app.modules.sales.schemas import (
    CatalogItem,
    SaleCreate,
    SaleItemOut,
    SaleListItem,
    SaleOut,
    SalePage,
)

# ---------- Catálogo POS ----------


def catalog(db: Session, q: str | None = None, limit: int = 30) -> list[CatalogItem]:
    query = (
        select(Variant, Product, VariantPrice, Stock)
        .join(Product, Variant.product_id == Product.id)
        .join(VariantPrice, VariantPrice.variant_id == Variant.id)
        .outerjoin(Stock, Stock.variant_id == Variant.id)
        .where(
            Variant.is_active.is_(True),
            Product.is_active.is_(True),
            VariantPrice.status == "publicado",
        )
    )
    if q:
        term = q.strip()
        pattern = f"%{term}%"
        query = query.where(
            Product.name.ilike(pattern)
            | Variant.sku.ilike(pattern)
            | (Variant.barcode == term)
        )
    rows = db.execute(
        query.options(
            selectinload(Variant.attribute_values).selectinload(VariantAttributeValue.value),
            selectinload(Variant.attribute_values).selectinload(VariantAttributeValue.attribute),
        )
        .order_by(Product.name, Variant.sku)
        .limit(limit)
    ).all()
    return [
        CatalogItem(
            variant_id=variant.id,
            sku=variant.sku,
            barcode=variant.barcode,
            product_id=product.id,
            product_name=product.name,
            variant_label=variant_label(variant),
            unit_of_measure=variant.unit_of_measure,
            is_bulk=variant.unit_of_measure in ("kg", "lb"),
            price=price.price,
            price_per_lb=price.price_per_lb,
            tax_rate=product.tax_rate,
            stock=stock.quantity if stock else Decimal("0"),
        )
        for variant, product, price, stock in rows
    ]


# ---------- Venta (transacción integradora) ----------


def _next_invoice_number(db: Session) -> int:
    """Incremento atómico del consecutivo dentro de la transacción de la venta."""
    stmt = (
        update(InvoiceCounter)
        .where(InvoiceCounter.id == 1)
        .values(last_number=InvoiceCounter.last_number + 1)
        .returning(InvoiceCounter.last_number)
    )
    number = db.execute(stmt).scalar()
    if number is None:
        db.add(InvoiceCounter(id=1, last_number=0))
        db.flush()
        number = db.execute(stmt).scalar()
    return number


def create_sale(db: Session, data: SaleCreate, user: User) -> SaleOut:
    from app.modules.cash.service import get_open_session

    settings = get_business_settings(db)
    open_session = get_open_session(db, user.id)

    sale = Sale(
        user_id=user.id,
        cash_session_id=open_session.id if open_session else None,
        payment_method=data.payment_method,
        customer_name=(data.customer_name or "").strip() or None,
        customer_id_number=(data.customer_id_number or "").strip() or None,
        subtotal=Decimal("0"),
        discount_amount=Decimal("0"),
        tax_amount=Decimal("0"),
        total=Decimal("0"),
    )
    db.add(sale)
    db.flush()

    subtotal = Decimal("0")
    discount_total = Decimal("0")
    tax_total = Decimal("0")
    for index, item in enumerate(data.items):
        variant = db.get(Variant, item.variant_id)
        if variant is None or not variant.is_active:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"Línea {index + 1}: variante no disponible"
            )
        product = db.get(Product, variant.product_id)
        if not product.is_active:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"Línea {index + 1}: producto inactivo"
            )
        price = db.scalar(select(VariantPrice).where(VariantPrice.variant_id == variant.id))
        if price is None or price.status != "publicado":
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Línea {index + 1}: '{product.name}' no tiene precio publicado",
            )

        qty = q3(D(item.quantity))
        var_unit = variant.unit_of_measure
        var_bulk = var_unit in ("kg", "lb")
        if var_bulk:
            if item.unit not in ("kg", "lb"):
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    f"Línea {index + 1}: esta variante se vende en kg o lb",
                )
            if item.unit == "lb":
                if price.price_per_lb is None:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        f"Línea {index + 1}: '{product.name}' no tiene precio por libra",
                    )
                unit_price = price.price_per_lb
                canonical_delta = q3(qty * KG_PER_LB)
            else:
                unit_price = price.price
                canonical_delta = qty
        else:
            if item.unit != "unidad":
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    f"Línea {index + 1}: esta variante se vende por unidad",
                )
            if qty != qty.to_integral_value():
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    f"Línea {index + 1}: la cantidad debe ser entera para productos por unidad",
                )
            unit_price = price.price
            canonical_delta = qty

        gross = q2(qty * D(unit_price))
        discount_pct = q2(D(item.discount_pct))
        line_base = q2(gross * (Decimal("1") - discount_pct / Decimal("100")))
        line_tax = q2(line_base * D(product.tax_rate))
        subtotal += line_base
        discount_total += gross - line_base
        tax_total += line_tax

        cost = last_unit_cost(db, variant.id)
        if cost is not None and var_bulk and item.unit == "lb":
            cost = q2(D(cost) * KG_PER_LB)

        label = variant_label(variant)
        description = f"{product.name} {label}".strip()
        db.add(
            SaleItem(
                sale_id=sale.id,
                variant_id=variant.id,
                sku_snapshot=variant.sku,
                description_snapshot=description,
                quantity=qty,
                unit_snapshot=item.unit,
                unit_price_snapshot=D(unit_price),
                discount_pct=discount_pct,
                unit_cost_snapshot=cost,
                tax_rate_snapshot=product.tax_rate,
                tax_amount=line_tax,
                line_total=line_base,
            )
        )
        try:
            apply_movement(
                db,
                variant_id=variant.id,
                delta=-canonical_delta,
                movement_type="salida_venta",
                user_id=user.id,
                reference_type="sale",
                reference_id=sale.id,
            )
        except InsufficientStockError:
            db.rollback()
            stock = db.get(Stock, variant.id)
            available = stock.quantity if stock else Decimal("0")
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                {
                    "message": f"Stock insuficiente para '{description}'",
                    "line": index + 1,
                    "variant_id": variant.id,
                    "sku": variant.sku,
                    "available": str(available),
                    "requested": str(canonical_delta),
                },
            ) from None

    sale.subtotal = q2(subtotal)
    sale.discount_amount = q2(discount_total)
    sale.tax_amount = q2(tax_total)
    sale.total = q2(subtotal + tax_total)

    number = _next_invoice_number(db)
    invoice = Invoice(
        sale_id=sale.id,
        invoice_prefix=settings.invoice_prefix,
        invoice_number=number,
        business_name=settings.business_name,
        business_tax_id=settings.tax_id,
        business_address=settings.address,
        business_phone=settings.phone,
        currency=settings.currency,
        issued_at=datetime.now(timezone.utc),
    )
    db.add(invoice)
    db.commit()
    return get_sale(db, sale.id, user)


# ---------- Consultas ----------


def _sale_to_out(sale: Sale, invoice: Invoice | None) -> SaleOut:
    return SaleOut(
        id=sale.id,
        status=sale.status,
        seller_name=sale.user.full_name,
        payment_method=sale.payment_method,
        customer_name=sale.customer_name,
        customer_id_number=sale.customer_id_number,
        subtotal=sale.subtotal,
        discount_amount=sale.discount_amount,
        tax_amount=sale.tax_amount,
        total=sale.total,
        created_at=sale.created_at,
        invoice_id=invoice.id if invoice else None,
        invoice_number=f"{invoice.invoice_prefix}-{invoice.invoice_number:06d}" if invoice else None,
        items=[
            SaleItemOut(
                id=i.id,
                variant_id=i.variant_id,
                sku=i.sku_snapshot,
                description=i.description_snapshot,
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
    )


def get_sale(db: Session, sale_id: int, user: User) -> SaleOut:
    sale = db.scalar(
        select(Sale)
        .options(selectinload(Sale.items), selectinload(Sale.user))
        .where(Sale.id == sale_id)
    )
    if sale is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venta no encontrada")
    if user.role != "admin" and sale.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo puedes ver tus propias ventas")
    invoice = db.scalar(select(Invoice).where(Invoice.sale_id == sale.id))
    return _sale_to_out(sale, invoice)


def list_sales(
    db: Session,
    user: User,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> SalePage:
    query = select(Sale)
    if user.role != "admin":
        query = query.where(Sale.user_id == user.id)
    if date_from:
        query = query.where(func.date(Sale.created_at) >= date_from)
    if date_to:
        query = query.where(func.date(Sale.created_at) <= date_to)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    sales = list(
        db.scalars(
            query.options(selectinload(Sale.user))
            .order_by(Sale.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    invoices = {
        inv.sale_id: inv
        for inv in db.scalars(select(Invoice).where(Invoice.sale_id.in_([s.id for s in sales])))
    }
    items = [
        SaleListItem(
            id=s.id,
            status=s.status,
            seller_name=s.user.full_name,
            payment_method=s.payment_method,
            total=s.total,
            created_at=s.created_at,
            invoice_id=invoices[s.id].id if s.id in invoices else None,
            invoice_number=(
                f"{invoices[s.id].invoice_prefix}-{invoices[s.id].invoice_number:06d}"
                if s.id in invoices
                else None
            ),
        )
        for s in sales
    ]
    return SalePage(items=items, total=total, page=page, page_size=page_size)


def void_sale(db: Session, sale_id: int, user: User) -> SaleOut:
    sale = db.scalar(
        select(Sale).options(selectinload(Sale.items)).where(Sale.id == sale_id)
    )
    if sale is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venta no encontrada")
    if sale.status == "anulada":
        raise HTTPException(status.HTTP_409_CONFLICT, "La venta ya está anulada")

    for item in sale.items:
        variant = db.get(Variant, item.variant_id)
        if variant.unit_of_measure in ("kg", "lb") and item.unit_snapshot == "lb":
            delta = q3(D(item.quantity) * KG_PER_LB)
        else:
            delta = q3(D(item.quantity))
        apply_movement(
            db,
            variant_id=item.variant_id,
            delta=delta,
            movement_type="ajuste",
            user_id=user.id,
            reference_type="sale",
            reference_id=sale.id,
            notes=f"Anulación de venta #{sale.id}",
        )
    sale.status = "anulada"
    db.commit()
    return get_sale(db, sale.id, user)
