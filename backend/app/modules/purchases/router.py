from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_admin
from app.core.ws_manager import manager
from app.modules.auth.models import User
from app.modules.purchases import service
from app.modules.purchases.schemas import (
    PurchaseCreate,
    PurchaseOut,
    PurchasePage,
    SupplierCreate,
    SupplierOut,
    SupplierUpdate,
)

router = APIRouter(tags=["purchases"], dependencies=[Depends(require_admin)])


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(include_inactive: bool = False, db: Session = Depends(get_db)):
    return service.list_suppliers(db, include_inactive)


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db)):
    return service.create_supplier(db, data)


@router.patch("/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: int, data: SupplierUpdate, db: Session = Depends(get_db)):
    return service.update_supplier(db, supplier_id, data)


@router.post("/purchases", response_model=PurchaseOut, status_code=201)
async def create_purchase(
    data: PurchaseCreate, db: Session = Depends(get_db), user: User = Depends(require_admin)
):
    purchase = service.create_purchase(db, data, user.id)
    result = service.get_purchase(db, purchase.id)
    await manager.broadcast({"type": "purchase_created", "payload": {"id": purchase.id}})
    await manager.broadcast({"type": "dashboard_update"})
    return result


@router.get("/purchases", response_model=PurchasePage)
def list_purchases(
    supplier_id: int | None = None,
    variant_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.list_purchases(db, supplier_id, variant_id, date_from, date_to, page, page_size)


@router.get("/purchases/{purchase_id}", response_model=PurchaseOut)
def get_purchase(purchase_id: int, db: Session = Depends(get_db)):
    return service.get_purchase(db, purchase_id)


@router.post("/purchases/{purchase_id}/void", response_model=PurchaseOut)
async def void_purchase(
    purchase_id: int, db: Session = Depends(get_db), user: User = Depends(require_admin)
):
    result = service.void_purchase(db, purchase_id, user.id)
    await manager.broadcast({"type": "inventory_updated", "payload": {"purchase_id": purchase_id}})
    await manager.broadcast({"type": "dashboard_update"})
    return result
