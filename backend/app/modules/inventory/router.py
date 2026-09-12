from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_admin
from app.core.ws_manager import manager
from app.modules.auth.models import User
from app.modules.inventory import service
from app.modules.inventory.schemas import (
    AdjustmentCreate,
    MovementPage,
    StockPage,
    ThresholdUpdate,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/stock", response_model=StockPage, dependencies=[Depends(get_current_user)])
def list_stock(
    q: str | None = None,
    low_stock_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return service.list_stock(db, q, low_stock_only, page, page_size)


@router.get("/stock/low", response_model=StockPage, dependencies=[Depends(get_current_user)])
def low_stock(db: Session = Depends(get_db)):
    return service.list_stock(db, low_stock_only=True, page=1, page_size=100)


@router.patch("/stock/{variant_id}/threshold", dependencies=[Depends(require_admin)])
def set_threshold(variant_id: int, data: ThresholdUpdate, db: Session = Depends(get_db)):
    service.set_threshold(db, variant_id, data.low_stock_threshold)
    return {"ok": True}


@router.post("/adjustments", status_code=201)
async def create_adjustment(
    data: AdjustmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    balance = service.create_adjustment(db, data, user.id)
    await manager.broadcast({"type": "inventory_updated", "payload": {"variant_id": data.variant_id}})
    return {"variant_id": data.variant_id, "balance_after": str(balance)}


@router.get("/movements", response_model=MovementPage, dependencies=[Depends(require_admin)])
def list_movements(
    variant_id: int | None = None,
    movement_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return service.list_movements(db, variant_id, movement_type, date_from, date_to, page, page_size)
