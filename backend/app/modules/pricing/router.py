from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_admin
from app.modules.pricing import service
from app.modules.pricing.schemas import PricePage, PriceUpdate

router = APIRouter(prefix="/pricing", tags=["pricing"], dependencies=[Depends(require_admin)])


@router.get("", response_model=PricePage)
def pricing_overview(
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return service.pricing_overview(db, q, page, page_size)


@router.put("/variants/{variant_id}")
def upsert_price(variant_id: int, data: PriceUpdate, db: Session = Depends(get_db)):
    price = service.upsert_price(db, variant_id, data)
    return {
        "variant_id": variant_id,
        "price": str(price.price),
        "price_per_lb": str(price.price_per_lb) if price.price_per_lb is not None else None,
        "margin_percent": str(price.margin_percent) if price.margin_percent is not None else None,
        "status": price.status,
    }


@router.post("/variants/{variant_id}/publish")
def publish(variant_id: int, db: Session = Depends(get_db)):
    price = service.publish(db, variant_id, True)
    return {"variant_id": variant_id, "status": price.status}


@router.post("/variants/{variant_id}/unpublish")
def unpublish(variant_id: int, db: Session = Depends(get_db)):
    price = service.publish(db, variant_id, False)
    return {"variant_id": variant_id, "status": price.status}
