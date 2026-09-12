from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.money import D, q2, suggested_price_per_lb
from app.modules.inventory.service import variant_label
from app.modules.pricing.models import VariantPrice
from app.modules.pricing.schemas import PriceItem, PricePage, PriceUpdate
from app.modules.products.models import Product, Variant, VariantAttributeValue
from app.modules.purchases.service import last_unit_cost


def _get_or_create(db: Session, variant_id: int) -> VariantPrice:
    price = db.scalar(select(VariantPrice).where(VariantPrice.variant_id == variant_id))
    if price is None:
        price = VariantPrice(variant_id=variant_id)
        db.add(price)
        db.flush()
    return price


def upsert_price(db: Session, variant_id: int, data: PriceUpdate) -> VariantPrice:
    variant = db.get(Variant, variant_id)
    if variant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    product = db.get(Product, variant.product_id)
    price = _get_or_create(db, variant_id)

    if data.margin_percent is not None:
        cost = last_unit_cost(db, variant_id)
        if cost is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "No hay costo de compra registrado; registra una compra o define el precio manualmente",
            )
        price.margin_percent = q2(D(data.margin_percent))
        price.price = q2(D(cost) * (Decimal("1") + D(data.margin_percent) / Decimal("100")))
        price.cost_reference = cost
    elif data.price is not None:
        price.price = q2(D(data.price))
        price.margin_percent = None

    var_bulk = variant.unit_of_measure in ("kg", "lb")
    if var_bulk:
        if data.price_per_lb is not None:
            price.price_per_lb = q2(D(data.price_per_lb))
        elif price.price_per_lb is None and price.price:
            price.price_per_lb = suggested_price_per_lb(price.price)
    else:
        price.price_per_lb = None

    db.commit()
    db.refresh(price)
    return price


def publish(db: Session, variant_id: int, publish_it: bool) -> VariantPrice:
    price = db.scalar(select(VariantPrice).where(VariantPrice.variant_id == variant_id))
    if publish_it:
        if price is None or price.price is None or D(price.price) <= 0:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Define un precio mayor que cero antes de publicar",
            )
        price.status = "publicado"
        price.published_at = datetime.now(timezone.utc)
        price.cost_reference = last_unit_cost(db, variant_id) or price.cost_reference
    else:
        if price is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "La variante no tiene precio")
        price.status = "borrador"
    db.commit()
    db.refresh(price)
    return price


def pricing_overview(
    db: Session, q: str | None = None, page: int = 1, page_size: int = 50
) -> PricePage:
    query = (
        select(Variant, Product, VariantPrice)
        .join(Product, Variant.product_id == Product.id)
        .outerjoin(VariantPrice, VariantPrice.variant_id == Variant.id)
        .where(Variant.is_active.is_(True), Product.is_active.is_(True))
    )
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(Product.name.ilike(pattern) | Variant.sku.ilike(pattern))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.options(
            selectinload(Variant.attribute_values).selectinload(VariantAttributeValue.value),
            selectinload(Variant.attribute_values).selectinload(VariantAttributeValue.attribute),
        )
        .order_by(Product.name, Variant.sku)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = []
    for variant, product, price in rows:
        items.append(
            PriceItem(
                variant_id=variant.id,
                sku=variant.sku,
                product_id=product.id,
                product_name=product.name,
                variant_label=variant_label(variant),
                unit_of_measure=variant.unit_of_measure,
                is_bulk=variant.unit_of_measure in ("kg", "lb"),
                price=price.price if price else None,
                price_per_lb=price.price_per_lb if price else None,
                suggested_price_per_lb=(
                    suggested_price_per_lb(price.price) if price and variant.unit_of_measure in ("kg", "lb") else None
                ),
                margin_percent=price.margin_percent if price else None,
                last_cost=last_unit_cost(db, variant.id),
                status=price.status if price else "borrador",
                tax_rate=product.tax_rate,
            )
        )
    return PricePage(items=items, total=total, page=page, page_size=page_size)
