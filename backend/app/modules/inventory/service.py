from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.money import D, q3
from app.modules.auth.service import get_business_settings
from app.modules.inventory.models import InventoryMovement, Stock
from app.modules.inventory.schemas import (
    AdjustmentCreate,
    MovementOut,
    MovementPage,
    StockItem,
    StockPage,
)
from app.modules.products.models import Product, Variant, VariantAttributeValue


class InsufficientStockError(Exception):
    def __init__(self, variant_id: int, requested: Decimal):
        self.variant_id = variant_id
        self.requested = requested
        super().__init__(f"Stock insuficiente para variante {variant_id}")


def ensure_stock_row(db: Session, variant_id: int) -> None:
    if db.get(Stock, variant_id) is None:
        db.execute(insert(Stock).values(variant_id=variant_id, quantity=Decimal("0")))


def apply_movement(
    db: Session,
    *,
    variant_id: int,
    delta: Decimal,
    movement_type: str,
    user_id: int,
    unit_cost: Decimal | None = None,
    reference_type: str | None = None,
    reference_id: int | None = None,
    notes: str | None = None,
) -> Decimal:
    """Aplica un movimiento de stock de forma atómica dentro de la transacción actual.

    El UPDATE condicional (quantity + delta >= 0) evita la sobreventa sin
    read-modify-write: dos ventas concurrentes se serializan en el row-lock y
    la que exceda el stock simplemente no coincide con el WHERE (rowcount 0).
    NO hace commit — el llamador decide el límite de la transacción.
    """
    delta = q3(D(delta))
    ensure_stock_row(db, variant_id)
    stmt = (
        update(Stock)
        .where(Stock.variant_id == variant_id, Stock.quantity + delta >= 0)
        .values(quantity=Stock.quantity + delta)
        .returning(Stock.quantity)
    )
    new_balance = db.execute(stmt).scalar()
    if new_balance is None:
        raise InsufficientStockError(variant_id, -delta)
    db.add(
        InventoryMovement(
            variant_id=variant_id,
            movement_type=movement_type,
            quantity=delta,
            balance_after=new_balance,
            unit_cost=unit_cost,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            created_by=user_id,
        )
    )
    return new_balance


def variant_label(variant: Variant) -> str:
    values = sorted(
        variant.attribute_values, key=lambda x: (x.attribute.sort_order, x.attribute_id)
    )
    if not values:
        return ""
    return " / ".join(v.value.value for v in values)


def create_adjustment(db: Session, data: AdjustmentCreate, user_id: int) -> Decimal:
    variant = db.get(Variant, data.variant_id)
    if variant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    if D(data.quantity_delta) == 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El ajuste no puede ser cero")
    try:
        balance = apply_movement(
            db,
            variant_id=data.variant_id,
            delta=D(data.quantity_delta),
            movement_type="ajuste",
            user_id=user_id,
            reference_type="manual",
            notes=data.notes,
        )
    except InsufficientStockError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "El ajuste dejaría el stock en negativo"
        ) from None
    db.commit()
    return balance


def list_stock(
    db: Session,
    q: str | None = None,
    low_stock_only: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> StockPage:
    settings = get_business_settings(db)
    default_threshold = settings.default_low_stock_threshold

    query = (
        select(Stock, Variant, Product)
        .join(Variant, Stock.variant_id == Variant.id)
        .join(Product, Variant.product_id == Product.id)
    )
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(Product.name.ilike(pattern) | Variant.sku.ilike(pattern))
    if low_stock_only:
        query = query.where(
            Stock.quantity <= func.coalesce(Stock.low_stock_threshold, default_threshold)
        )
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
    for stock, variant, product in rows:
        threshold = stock.low_stock_threshold if stock.low_stock_threshold is not None else default_threshold
        items.append(
            StockItem(
                variant_id=variant.id,
                sku=variant.sku,
                product_id=product.id,
                product_name=product.name,
                variant_label=variant_label(variant),
                unit_of_measure=variant.unit_of_measure,
                is_bulk=variant.unit_of_measure in ("kg", "lb"),
                quantity=stock.quantity,
                low_stock_threshold=threshold,
                is_low=stock.quantity <= threshold,
            )
        )
    return StockPage(items=items, total=total, page=page, page_size=page_size)


def set_threshold(db: Session, variant_id: int, threshold: Decimal | None) -> None:
    ensure_stock_row(db, variant_id)
    stock = db.get(Stock, variant_id)
    stock.low_stock_threshold = threshold
    db.commit()


def list_movements(
    db: Session,
    variant_id: int | None = None,
    movement_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> MovementPage:
    query = (
        select(InventoryMovement, Variant, Product)
        .join(Variant, InventoryMovement.variant_id == Variant.id)
        .join(Product, Variant.product_id == Product.id)
    )
    if variant_id is not None:
        query = query.where(InventoryMovement.variant_id == variant_id)
    if movement_type:
        query = query.where(InventoryMovement.movement_type == movement_type)
    if date_from:
        query = query.where(func.date(InventoryMovement.created_at) >= date_from)
    if date_to:
        query = query.where(func.date(InventoryMovement.created_at) <= date_to)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(InventoryMovement.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        MovementOut(
            id=m.id,
            variant_id=m.variant_id,
            sku=v.sku,
            product_name=p.name,
            movement_type=m.movement_type,
            quantity=m.quantity,
            balance_after=m.balance_after,
            unit_cost=m.unit_cost,
            reference_type=m.reference_type,
            reference_id=m.reference_id,
            notes=m.notes,
            created_by=m.created_by,
            created_at=m.created_at,
        )
        for m, v, p in rows
    ]
    return MovementPage(items=items, total=total, page=page, page_size=page_size)
