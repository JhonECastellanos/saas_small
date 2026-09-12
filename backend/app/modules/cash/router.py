from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import User
from app.modules.cash import service
from app.modules.cash.schemas import (
    CashCloseRequest,
    CashOpenRequest,
    CashSessionOut,
    CashSessionPage,
)

router = APIRouter(prefix="/cash", tags=["cash"])


@router.get("/current", response_model=CashSessionOut | None)
def current_session(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.current_session(db, user)


@router.post("/open", response_model=CashSessionOut, status_code=201)
def open_session(
    data: CashOpenRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return service.open_session(db, data, user)


@router.post("/close", response_model=CashSessionOut)
def close_session(
    data: CashCloseRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return service.close_session(db, data, user)


@router.get("/sessions", response_model=CashSessionPage)
def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.list_sessions(db, user, page, page_size)
