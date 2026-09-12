from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_admin
from app.core.ws_manager import manager
from app.modules.auth.models import User
from app.modules.sales import service
from app.modules.sales.schemas import CatalogItem, SaleCreate, SaleOut, SalePage

router = APIRouter(prefix="/sales", tags=["sales"])


@router.get("/catalog", response_model=list[CatalogItem])
def catalog(
    q: str | None = None,
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return service.catalog(db, q, limit)


@router.post("", response_model=SaleOut, status_code=201)
async def create_sale(
    data: SaleCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    result = service.create_sale(db, data, user)
    variant_ids = [item.variant_id for item in data.items]
    await manager.broadcast({"type": "sale_created", "payload": {"id": result.id, "variant_ids": variant_ids}})
    await manager.broadcast({"type": "dashboard_update"})
    return result


@router.get("", response_model=SalePage)
def list_sales(
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.list_sales(db, user, date_from, date_to, page, page_size)


@router.get("/{sale_id}", response_model=SaleOut)
def get_sale(sale_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.get_sale(db, sale_id, user)


@router.post("/{sale_id}/void", response_model=SaleOut)
async def void_sale(sale_id: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    result = service.void_sale(db, sale_id, user)
    await manager.broadcast({"type": "inventory_updated", "payload": {"sale_id": sale_id}})
    await manager.broadcast({"type": "dashboard_update"})
    return result
