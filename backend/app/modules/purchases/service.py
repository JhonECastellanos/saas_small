from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.money import D, KG_PER_LB, q2, q3
from app.modules.inventory.service import apply_movement, variant_label
from app.modules.pricing.models import VariantPrice
from app.modules.products.models import Product, Variant, VariantAttributeValue
from app.modules.purchases.models import Purchase, PurchaseItem, Supplier
from app.modules.purchases.schemas import (
    PurchaseCreate,
    PurchaseItemOut,
    PurchaseListItem,
    PurchaseOut,
    PurchasePage,
    SupplierCreate,
    SupplierUpdate,
)

# ---------- Proveedores ----------


def list_suppliers(db: Session, include_inactive: bool = False) -> list[Supplier]:
    query = select(Supplier).order_by(Supplier.name)
    if not include_inactive:
        query = query.where(Supplier.is_active.is_(True))
    return list(db.scalars(query))


def create_supplier(db: Session, data: SupplierCreate) -> Supplier:
    if db.scalar(select(Supplier).where(Supplier.name == data.name.strip())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un proveedor con ese nombre")
    supplier = Supplier(
        name=data.name.strip(), tax_id=data.tax_id, phone=data.phone, email=data.email
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def update_supplier(db: Session, supplier_id: int, data: SupplierUpdate) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proveedor no encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier


# ---------- Compras ----------


def _canonical_quantities(
    variant: Variant, unit: str, quantity: Decimal, unit_cost: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    """Convierte a unidad canónica. Devuelve (cantidad, costo_unitario, total_línea)."""
    quantity = D(quantity)
    unit_cost = D(unit_cost)
    line_total = q2(quantity * unit_cost)
    var_bulk = variant.unit_of_measure in ("kg", "lb")

    if not var_bulk:
        if unit != "unidad":
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"La variante '{variant.sku}' se compra por unidad",
            )
        return q3(quantity), q2(unit_cost), line_total

    if unit not in ("kg", "lb"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"El producto a granel '{product.name}' se compra en kg o lb",
        )
    if unit == "kg":
        return q3(quantity), q2(unit_cost), line_total
    # lb -> kg. El costo canónico se deriva del total para que las cifras cuadren.
    qty_kg = q3(quantity * KG_PER_LB)
    if qty_kg == 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Cantidad demasiado pequeña")
    cost_per_kg = q2(line_total / qty_kg)
    return qty_kg, cost_per_kg, line_total


def create_purchase(db: Session, data: PurchaseCreate, user_id: int) -> Purchase:
    supplier = db.get(Supplier, data.supplier_id)
    if supplier is None or not supplier.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proveedor no encontrado o inactivo")

    purchase = Purchase(
        supplier_id=data.supplier_id,
        purchase_date=data.purchase_date,
        notes=data.notes,
        total_cost=Decimal("0"),
        created_by=user_id,
    )
    db.add(purchase)
    db.flush()

    total = Decimal("0")
    for item in data.items:
        variant = db.get(Variant, item.variant_id)
        if variant is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"Variante {item.variant_id} no encontrada"
            )
        qty, cost, line_total = _canonical_quantities(
            variant, item.unit, item.quantity, item.unit_cost
        )
        total += line_total
        db.add(
            PurchaseItem(
                purchase_id=purchase.id,
                variant_id=variant.id,
                quantity=qty,
                unit_cost=cost,
                input_unit=item.unit,
                input_quantity=q3(D(item.quantity)),
                line_total=line_total,
            )
        )
        apply_movement(
            db,
            variant_id=variant.id,
            delta=qty,
            movement_type="entrada_compra",
            user_id=user_id,
            unit_cost=cost,
            reference_type="purchase",
            reference_id=purchase.id,
        )

        if cost > 0:
            vp = db.scalar(select(VariantPrice).where(VariantPrice.variant_id == variant.id))
            if vp is None:
                vp = VariantPrice(
                    variant_id=variant.id,
                    price=q2(cost),
                    status="publicado",
                    published_at=datetime.now(timezone.utc),
                )
                db.add(vp)
            elif (vp.price is None or D(vp.price) <= 0) and vp.status == "borrador":
                vp.price = q2(cost)
                vp.status = "publicado"
                vp.published_at = datetime.now(timezone.utc)

    purchase.total_cost = q2(total)
    db.commit()
    db.refresh(purchase)
    return purchase


def last_unit_cost(db: Session, variant_id: int) -> Decimal | None:
    """Último costo canónico de compra de una variante (para margen y utilidad).

    Ignora compras anuladas.
    """
    return db.scalar(
        select(PurchaseItem.unit_cost)
        .join(Purchase, PurchaseItem.purchase_id == Purchase.id)
        .where(PurchaseItem.variant_id == variant_id, Purchase.status == "completada")
        .order_by(PurchaseItem.id.desc())
        .limit(1)
    )


def _purchase_to_out(db: Session, purchase: Purchase) -> PurchaseOut:
    items = []
    for item in purchase.items:
        variant = item.variant
        items.append(
            PurchaseItemOut(
                id=item.id,
                variant_id=item.variant_id,
                sku=variant.sku,
                product_name=variant.product.name,
                variant_label=variant_label(variant),
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                input_unit=item.input_unit,
                input_quantity=item.input_quantity,
                line_total=item.line_total,
            )
        )
    return PurchaseOut(
        id=purchase.id,
        supplier_id=purchase.supplier_id,
        supplier_name=purchase.supplier.name,
        purchase_date=purchase.purchase_date,
        status=purchase.status,
        notes=purchase.notes,
        total_cost=purchase.total_cost,
        created_at=purchase.created_at,
        items=items,
    )


def get_purchase(db: Session, purchase_id: int) -> PurchaseOut:
    purchase = db.scalar(
        select(Purchase)
        .options(
            selectinload(Purchase.supplier),
            selectinload(Purchase.items)
            .selectinload(PurchaseItem.variant)
            .selectinload(Variant.product),
            selectinload(Purchase.items)
            .selectinload(PurchaseItem.variant)
            .selectinload(Variant.attribute_values)
            .selectinload(VariantAttributeValue.value),
            selectinload(Purchase.items)
            .selectinload(PurchaseItem.variant)
            .selectinload(Variant.attribute_values)
            .selectinload(VariantAttributeValue.attribute),
        )
        .where(Purchase.id == purchase_id)
    )
    if purchase is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compra no encontrada")
    return _purchase_to_out(db, purchase)


def list_purchases(
    db: Session,
    supplier_id: int | None = None,
    variant_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PurchasePage:
    query = select(Purchase).join(Supplier, Purchase.supplier_id == Supplier.id)
    if supplier_id is not None:
        query = query.where(Purchase.supplier_id == supplier_id)
    if variant_id is not None:
        query = query.where(
            Purchase.id.in_(
                select(PurchaseItem.purchase_id).where(PurchaseItem.variant_id == variant_id)
            )
        )
    if date_from:
        query = query.where(Purchase.purchase_date >= date_from)
    if date_to:
        query = query.where(Purchase.purchase_date <= date_to)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    purchases = list(
        db.scalars(
            query.options(selectinload(Purchase.supplier), selectinload(Purchase.items))
            .order_by(Purchase.purchase_date.desc(), Purchase.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    items = [
        PurchaseListItem(
            id=p.id,
            supplier_name=p.supplier.name,
            purchase_date=p.purchase_date,
            status=p.status,
            total_cost=p.total_cost,
            item_count=len(p.items),
            created_at=p.created_at,
        )
        for p in purchases
    ]
    return PurchasePage(items=items, total=total, page=page, page_size=page_size)


def void_purchase(db: Session, purchase_id: int, user_id: int) -> PurchaseOut:
    """Anula una compra revirtiendo sus entradas de stock.

    Falla con 409 si parte de la mercancía ya se vendió (el stock no alcanza
    para revertir): primero habría que ajustar o anular las ventas implicadas.
    """
    purchase = db.scalar(
        select(Purchase).options(selectinload(Purchase.items)).where(Purchase.id == purchase_id)
    )
    if purchase is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compra no encontrada")
    if purchase.status == "anulada":
        raise HTTPException(status.HTTP_409_CONFLICT, "La compra ya está anulada")

    from app.modules.inventory.service import InsufficientStockError

    try:
        for item in purchase.items:
            apply_movement(
                db,
                variant_id=item.variant_id,
                delta=-item.quantity,
                movement_type="ajuste",
                user_id=user_id,
                reference_type="purchase",
                reference_id=purchase.id,
                notes=f"Anulación de compra #{purchase.id}",
            )
    except InsufficientStockError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede anular: parte de la mercancía ya se vendió "
            f"(variante {exc.variant_id} sin stock suficiente para revertir)",
        ) from None

    purchase.status = "anulada"
    db.commit()
    return get_purchase(db, purchase.id)
