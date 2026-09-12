from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.modules.auth.models import User
from app.modules.invoices import service
from app.modules.invoices.schemas import InvoiceDetail, InvoicePage

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=InvoicePage)
def list_invoices(
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.list_invoices(db, user, q, date_from, date_to, page, page_size)


@router.get("/{invoice_id}", response_model=InvoiceDetail)
def get_invoice(
    invoice_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return service.get_invoice(db, invoice_id, user)
