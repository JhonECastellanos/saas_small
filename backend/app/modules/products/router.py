from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_admin
from app.core.ws_manager import manager
from app.modules.products import service
from app.modules.products.schemas import (
    AttributeCreate,
    AttributeOut,
    AttributeValueCreate,
    CategoryCreate,
    CategoryOut,
    ProductCreate,
    ProductDetail,
    ProductPage,
    ProductUpdate,
    VariantCombosCreate,
    VariantUpdate,
)

router = APIRouter(tags=["products"])


@router.get("/categories", response_model=list[CategoryOut], dependencies=[Depends(get_current_user)])
def list_categories(db: Session = Depends(get_db)):
    return service.list_categories(db)


@router.post(
    "/categories", response_model=CategoryOut, status_code=201, dependencies=[Depends(require_admin)]
)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    return service.create_category(db, data)


@router.get("/attributes", response_model=list[AttributeOut], dependencies=[Depends(get_current_user)])
def list_attributes(db: Session = Depends(get_db)):
    return service.list_attributes(db)


@router.post(
    "/attributes", response_model=AttributeOut, status_code=201, dependencies=[Depends(require_admin)]
)
def create_attribute(data: AttributeCreate, db: Session = Depends(get_db)):
    return service.create_attribute(db, data)


@router.post(
    "/attributes/{attribute_id}/values",
    response_model=AttributeOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def add_attribute_value(attribute_id: int, data: AttributeValueCreate, db: Session = Depends(get_db)):
    return service.add_attribute_value(db, attribute_id, data)


@router.get("/products", response_model=ProductPage, dependencies=[Depends(get_current_user)])
def list_products(
    q: str | None = None,
    category_id: int | None = None,
    include_inactive: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.list_products(db, q, category_id, include_inactive, page, page_size)


@router.post("/products", response_model=ProductDetail, status_code=201, dependencies=[Depends(require_admin)])
async def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    product = service.create_product(db, data)
    result = service.get_product_detail(db, product.id)
    await manager.broadcast({"type": "product_created", "payload": {"id": product.id}})
    return result


@router.get("/products/{product_id}", response_model=ProductDetail, dependencies=[Depends(get_current_user)])
def get_product(product_id: int, db: Session = Depends(get_db)):
    return service.get_product_detail(db, product_id)


@router.patch("/products/{product_id}", response_model=ProductDetail, dependencies=[Depends(require_admin)])
async def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    service.update_product(db, product_id, data)
    result = service.get_product_detail(db, product_id)
    await manager.broadcast({"type": "product_updated", "payload": {"id": product_id}})
    return result


@router.delete("/products/{product_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    service.delete_product(db, product_id)
    await manager.broadcast({"type": "product_deleted", "payload": {"id": product_id}})


@router.post(
    "/products/{product_id}/photo",
    response_model=ProductDetail,
    dependencies=[Depends(require_admin)],
)
def upload_product_photo(product_id: int, file: UploadFile, db: Session = Depends(get_db)):
    service.upload_product_photo(db, product_id, file)
    return service.get_product_detail(db, product_id)


@router.post(
    "/products/{product_id}/variants",
    response_model=ProductDetail,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
async def add_variants(product_id: int, data: VariantCombosCreate, db: Session = Depends(get_db)):
    service.add_variants(db, product_id, [c.model_dump() for c in data.variant_combos])
    result = service.get_product_detail(db, product_id)
    await manager.broadcast({"type": "product_updated", "payload": {"id": product_id}})
    return result


@router.patch("/variants/{variant_id}", dependencies=[Depends(require_admin)])
def update_variant(variant_id: int, data: VariantUpdate, db: Session = Depends(get_db)):
    variant = service.update_variant(db, variant_id, data.is_active, data.barcode)
    return {
        "id": variant.id,
        "sku": variant.sku,
        "is_active": variant.is_active,
        "barcode": variant.barcode,
    }
