from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.money import q2
from app.modules.auth.models import User
from app.modules.cash.models import CashSession
from app.modules.cash.schemas import (
    CashCloseRequest,
    CashOpenRequest,
    CashSessionOut,
    CashSessionPage,
    SessionTotals,
)
from app.modules.sales.models import Sale


def _session_totals(db: Session, session: CashSession) -> SessionTotals:
    """Ventas completadas registradas dentro del turno."""
    rows = db.execute(
        select(Sale.payment_method, func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0))
        .where(Sale.cash_session_id == session.id, Sale.status == "completada")
        .group_by(Sale.payment_method)
    ).all()
    by_method: dict[str, Decimal] = {}
    count = 0
    total = Decimal("0")
    for method, method_count, method_total in rows:
        by_method[method] = q2(method_total)
        count += method_count
        total += Decimal(str(method_total))
    return SessionTotals(sales_count=count, total_sold=q2(total), by_payment_method=by_method)


def _to_out(db: Session, session: CashSession, with_totals: bool = True) -> CashSessionOut:
    return CashSessionOut(
        id=session.id,
        user_id=session.user_id,
        user_name=session.user.full_name,
        status=session.status,
        opening_amount=session.opening_amount,
        closing_amount=session.closing_amount,
        expected_cash=session.expected_cash,
        difference=session.difference,
        notes=session.notes,
        opened_at=session.opened_at,
        closed_at=session.closed_at,
        totals=_session_totals(db, session) if with_totals else None,
    )


def get_open_session(db: Session, user_id: int) -> CashSession | None:
    return db.scalar(
        select(CashSession)
        .options(selectinload(CashSession.user))
        .where(CashSession.user_id == user_id, CashSession.status == "abierta")
    )


def open_session(db: Session, data: CashOpenRequest, user: User) -> CashSessionOut:
    if get_open_session(db, user.id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya tienes un turno de caja abierto")
    session = CashSession(user_id=user.id, opening_amount=q2(data.opening_amount))
    db.add(session)
    db.commit()
    db.refresh(session)
    return _to_out(db, session)


def close_session(db: Session, data: CashCloseRequest, user: User) -> CashSessionOut:
    session = get_open_session(db, user.id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No tienes un turno de caja abierto")
    session.closed_at = datetime.now(timezone.utc)
    totals = _session_totals(db, session)
    cash_sales = totals.by_payment_method.get("efectivo", Decimal("0"))
    session.expected_cash = q2(session.opening_amount + cash_sales)
    session.closing_amount = q2(data.closing_amount)
    session.difference = q2(session.closing_amount - session.expected_cash)
    session.notes = data.notes
    session.status = "cerrada"
    db.commit()
    db.refresh(session)
    return _to_out(db, session)


def current_session(db: Session, user: User) -> CashSessionOut | None:
    session = get_open_session(db, user.id)
    return _to_out(db, session) if session else None


def list_sessions(db: Session, user: User, page: int = 1, page_size: int = 20) -> CashSessionPage:
    query = select(CashSession)
    if user.role != "admin":
        query = query.where(CashSession.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    sessions = list(
        db.scalars(
            query.options(selectinload(CashSession.user))
            .order_by(CashSession.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return CashSessionPage(
        items=[_to_out(db, s) for s in sessions], total=total, page=page, page_size=page_size
    )
