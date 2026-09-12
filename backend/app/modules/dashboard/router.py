from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_admin
from app.core.security import decode_access_token
from app.core.ws_manager import manager
from app.modules.inventory.service import list_stock
from app.modules.purchases.models import Purchase
from app.modules.purchases.service import list_purchases
from app.modules.returns.models import SaleReturn
from app.modules.sales.models import Sale

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", dependencies=[Depends(require_admin)])
def summary(db: Session = Depends(get_db)):
    today = date.today()
    current_month = today.month
    current_year = today.year

    sales_today = db.execute(
        select(func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0)).where(
            func.date(Sale.created_at) == today.isoformat(), Sale.status == "completada"
        )
    ).one()

    returns_today = db.scalar(
        select(func.coalesce(func.sum(SaleReturn.total_amount), 0)).where(
            func.date(SaleReturn.created_at) == today.isoformat(),
        )
    ) or 0

    sales_month = db.scalar(
        select(func.coalesce(func.sum(Sale.total), 0)).where(
            func.extract("month", Sale.created_at) == current_month,
            func.extract("year", Sale.created_at) == current_year,
            Sale.status == "completada",
        )
    ) or 0

    returns_month = db.scalar(
        select(func.coalesce(func.sum(SaleReturn.total_amount), 0)).where(
            func.extract("month", SaleReturn.created_at) == current_month,
            func.extract("year", SaleReturn.created_at) == current_year,
        )
    ) or 0

    sales_year = db.scalar(
        select(func.coalesce(func.sum(Sale.total), 0)).where(
            func.extract("year", Sale.created_at) == current_year,
            Sale.status == "completada",
        )
    ) or 0

    returns_year = db.scalar(
        select(func.coalesce(func.sum(SaleReturn.total_amount), 0)).where(
            func.extract("year", SaleReturn.created_at) == current_year,
        )
    ) or 0

    purchases_month = db.scalar(
        select(func.coalesce(func.sum(Purchase.total_cost), 0)).where(
            func.extract("month", Purchase.purchase_date) == current_month,
            func.extract("year", Purchase.purchase_date) == current_year,
            Purchase.status == "completada",
        )
    ) or 0

    purchases_year = db.scalar(
        select(func.coalesce(func.sum(Purchase.total_cost), 0)).where(
            func.extract("year", Purchase.purchase_date) == current_year,
            Purchase.status == "completada",
        )
    ) or 0

    low_stock = list_stock(db, low_stock_only=True, page=1, page_size=10)
    recent_purchases = list_purchases(db, page=1, page_size=5)
    return {
        "sales_today_count": sales_today[0],
        "sales_today_total": str(max(sales_today[1] - returns_today, 0)),
        "sales_month_total": str(max(sales_month - returns_month, 0)),
        "sales_year_total": str(max(sales_year - returns_year, 0)),
        "purchases_month_total": str(purchases_month),
        "purchases_year_total": str(purchases_year),
        "low_stock_count": low_stock.total,
        "low_stock_items": low_stock.items,
        "recent_purchases": recent_purchases.items,
    }


@router.websocket("/ws")
async def dashboard_ws(ws: WebSocket, token: str = Query(default="")):
    payload = decode_access_token(token)
    if payload is None:
        await ws.close(code=4001)
        return
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
