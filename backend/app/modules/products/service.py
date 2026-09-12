import os
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.auth.service import get_business_settings
from app.modules.products import sku as sku_gen
from app.modules.products.models import (
    Attribute,
    AttributeValue,
    Category,
    Product,
    Variant,
    VariantAttributeValue,
)
from app.modules.pricing.models import VariantPrice
from app.modules.products.schemas import (
    AttributeCreate,
    AttributeValueCreate,
    CategoryCreate,
    ProductCreate,
    ProductDetail,
    ProductListItem,
    ProductPage,
    ProductUpdate,
    VariantAttributeOut,
    VariantCombosCreate,
    VariantComboSpec,
    VariantOut,
)

# ---------- Categorías ----------


def list_categories(db: Session) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)))


def create_category(db: Session, data: CategoryCreate) -> Category:
    if db.scalar(select(Category).where(Category.name == data.name.strip())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe esa categoría")
    category = Category(name=data.name.strip())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


# ---------- Atributos dinámicos ----------


def list_attributes(db: Session) -> list[Attribute]:
    return list(
        db.scalars(
            select(Attribute)
            .options(selectinload(Attribute.values))
            .order_by(Attribute.sort_order, Attribute.id)
        )
    )


def create_attribute(db: Session, data: AttributeCreate) -> Attribute:
    exists = db.scalar(
        select(Attribute).where(
            (Attribute.name == data.name.strip()) | (Attribute.code == data.code.strip().upper())
        )
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un atributo con ese nombre o código")
    attr = Attribute(
        name=data.name.strip(), code=data.code.strip().upper(), sort_order=data.sort_order
    )
    db.add(attr)
    db.commit()
    db.refresh(attr)
    return attr


def add_attribute_value(db: Session, attribute_id: int, data: AttributeValueCreate) -> Attribute:
    attr = db.get(Attribute, attribute_id)
    if attr is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Atributo no encontrado")
    duplicate = db.scalar(
        select(AttributeValue).where(
            AttributeValue.attribute_id == attribute_id,
            (AttributeValue.value == data.value.strip())
            | (AttributeValue.code == data.code.strip().upper()),
        )
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese valor o código ya existe en el atributo")
    db.add(
        AttributeValue(
            attribute_id=attribute_id, value=data.value.strip(), code=data.code.strip().upper()
        )
    )
    db.commit()
    db.refresh(attr)
    return attr


# ---------- Productos y variantes ----------


def _load_combo_values(db: Session, combo: list[int]) -> list[AttributeValue]:
    """Valida y carga los valores de una combinación, ordenados para el SKU."""
    if not combo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Combinación de variante vacía")
    values = list(
        db.scalars(
            select(AttributeValue)
            .options(selectinload(AttributeValue.attribute))
            .where(AttributeValue.id.in_(combo))
        )
    )
    if len(values) != len(set(combo)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Valor de atributo inexistente")
    seen_attrs = set()
    for v in values:
        if v.attribute_id in seen_attrs:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Una variante no puede tener dos valores del mismo atributo",
            )
        seen_attrs.add(v.attribute_id)
    values.sort(key=lambda v: (v.attribute.sort_order, v.attribute.id))
    return values


def _signature(combo: list[int]) -> str:
    return "-".join(str(i) for i in sorted(combo))


def _create_variant(
    db: Session, product: Product, combo: list[int], unit_of_measure: str | None = None
) -> Variant:
    if combo:
        values = _load_combo_values(db, combo)
        signature = _signature(combo)
        variant_sku = product.base_sku + "".join(f"-{v.code}" for v in values)
    else:
        values, signature, variant_sku = [], "", product.base_sku

    duplicate = db.scalar(
        select(Variant).where(
            Variant.product_id == product.id, Variant.attributes_signature == signature
        )
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, f"La combinación ya existe ({duplicate.sku})")

    variant = Variant(
        product_id=product.id,
        sku=variant_sku,
        attributes_signature=signature,
        unit_of_measure=unit_of_measure or product.unit_of_measure,
    )
    db.add(variant)
    db.flush()
    for v in values:
        db.add(
            VariantAttributeValue(
                variant_id=variant.id, attribute_id=v.attribute_id, attribute_value_id=v.id
            )
        )
    db.add(VariantPrice(variant_id=variant.id))
    return variant


def create_product(db: Session, data: ProductCreate) -> Product:
    settings = get_business_settings(db)
    tax_rate = data.tax_rate if data.tax_rate is not None else settings.default_tax_rate
    product = Product(
        name=data.name.strip(),
        description=data.description,
        category_id=data.category_id,
        base_sku=sku_gen.next_base_sku(db, data.name),
        unit_of_measure=data.unit_of_measure,
        is_bulk=data.unit_of_measure in ("kg", "lb"),
        tax_rate=tax_rate,
    )
    db.add(product)
    db.flush()

    combos = data.variant_combos or [VariantComboSpec(attribute_value_ids=[])]
    for combo in combos:
        _create_variant(db, product, combo.attribute_value_ids, combo.unit_of_measure or None)

    db.commit()
    db.refresh(product)
    return product


def add_variants(db: Session, product_id: int, combos: list[dict]) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    for combo in combos:
        attr_ids = combo.get("attribute_value_ids", [])
        unit = combo.get("unit_of_measure") or None
        _create_variant(db, product, attr_ids, unit)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, data: ProductUpdate) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def update_variant(
    db: Session, variant_id: int, is_active: bool | None = None, barcode: str | None = None
) -> Variant:
    variant = db.get(Variant, variant_id)
    if variant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    if is_active is not None:
        variant.is_active = is_active
    if barcode is not None:
        code = barcode.strip() or None
        if code:
            duplicate = db.scalar(
                select(Variant).where(Variant.barcode == code, Variant.id != variant_id)
            )
            if duplicate:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"Ese código de barras ya está asignado a {duplicate.sku}",
                )
        variant.barcode = code
    db.commit()
    db.refresh(variant)
    return variant


def delete_product(db: Session, product_id: int) -> None:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    product.is_active = False
    for v in product.variants:
        v.is_active = False
    db.commit()


def upload_product_photo(db: Session, product_id: int, file: UploadFile) -> None:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    photo_dir = Path(os.environ.get("PRODUCT_PHOTO_DIR", "/app/product_photos"))
    photo_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix if file.filename else ".jpg"
    filename = f"{product.base_sku}{ext}"
    filepath = photo_dir / filename
    content = file.read()
    filepath.write_bytes(content)
    product.photo_path = str(filename)
    db.commit()


def list_products(
    db: Session,
    q: str | None = None,
    category_id: int | None = None,
    include_inactive: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> ProductPage:
    query = select(Product)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(Product.name.ilike(pattern) | Product.base_sku.ilike(pattern))
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    if not include_inactive:
        query = query.where(Product.is_active.is_(True))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    products = list(
        db.scalars(
            query.options(selectinload(Product.category), selectinload(Product.variants))
            .order_by(Product.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    items = [
        ProductListItem(
            id=p.id,
            name=p.name,
            base_sku=p.base_sku,
            category_id=p.category_id,
            category_name=p.category.name if p.category else None,
            unit_of_measure=p.unit_of_measure,
            is_bulk=p.is_bulk,
            tax_rate=p.tax_rate,
            is_active=p.is_active,
            photo_path=p.photo_path,
            variant_count=len(p.variants),
        )
        for p in products
    ]
    return ProductPage(items=items, total=total, page=page, page_size=page_size)


def variant_to_out(db: Session, variant: Variant) -> VariantOut:
    # Imports locales para evitar ciclos entre módulos.
    from app.modules.inventory.models import Stock
    from app.modules.pricing.models import VariantPrice

    attrs = [
        VariantAttributeOut(
            attribute_id=vav.attribute_id,
            attribute_name=vav.attribute.name,
            value_id=vav.value.id,
            value=vav.value.value,
            code=vav.value.code,
        )
        for vav in sorted(
            variant.attribute_values, key=lambda x: (x.attribute.sort_order, x.attribute_id)
        )
    ]
    price = db.scalar(select(VariantPrice).where(VariantPrice.variant_id == variant.id))
    stock = db.get(Stock, variant.id)
    return VariantOut(
        id=variant.id,
        sku=variant.sku,
        barcode=variant.barcode,
        is_active=variant.is_active,
        unit_of_measure=variant.unit_of_measure,
        attributes=attrs,
        price=price.price if price else None,
        price_per_lb=price.price_per_lb if price else None,
        price_status=price.status if price else None,
        stock=stock.quantity if stock else None,
    )


def get_product_detail(db: Session, product_id: int) -> ProductDetail:
    product = db.scalar(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.variants)
            .selectinload(Variant.attribute_values)
            .selectinload(VariantAttributeValue.value),
            selectinload(Product.variants)
            .selectinload(Variant.attribute_values)
            .selectinload(VariantAttributeValue.attribute),
        )
        .where(Product.id == product_id)
    )
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return ProductDetail(
        id=product.id,
        name=product.name,
        description=product.description,
        base_sku=product.base_sku,
        category_id=product.category_id,
        category_name=product.category.name if product.category else None,
        unit_of_measure=product.unit_of_measure,
        is_bulk=product.is_bulk,
        tax_rate=product.tax_rate,
        is_active=product.is_active,
        photo_path=product.photo_path,
        variants=[variant_to_out(db, v) for v in sorted(product.variants, key=lambda v: v.sku)],
    )
