from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_admin
from app.modules.auth.models import User
from app.modules.returns import service
from app.modules.returns.schemas import ReturnCreate, ReturnOut

router = APIRouter(prefix="/invoices", tags=["returns"])


@router.post("/{invoice_id}/return", response_model=ReturnOut, dependencies=[Depends(require_admin)])
def return_invoice(
    invoice_id: int,
    data: ReturnCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    return service.create_return(db, invoice_id, data, user)
