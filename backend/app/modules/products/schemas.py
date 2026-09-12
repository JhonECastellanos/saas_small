from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class AttributeValueCreate(BaseModel):
    value: str = Field(min_length=1, max_length=80)
    code: str = Field(min_length=1, max_length=10, description="Código corto para el SKU, ej. ROJ")


class AttributeValueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    value: str
    code: str


class AttributeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    code: str = Field(min_length=1, max_length=10)
    sort_order: int = 0


class AttributeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    sort_order: int
    values: list[AttributeValueOut]


class VariantAttributeOut(BaseModel):
    attribute_id: int
    attribute_name: str
    value_id: int
    value: str
    code: str


class VariantOut(BaseModel):
    id: int
    sku: str
    barcode: str | None = None
    is_active: bool
    unit_of_measure: str
    attributes: list[VariantAttributeOut]
    price: Decimal | None = None
    price_per_lb: Decimal | None = None
    price_status: str | None = None
    stock: Decimal | None = None


class VariantComboSpec(BaseModel):
    attribute_value_ids: list[int] = Field(default_factory=list, description="IDs de valores de atributos, ej. [id_rojo, id_M]")
    unit_of_measure: str = Field(default="", pattern="^(unidad|kg|lb)?$", description="Vacío = hereda del producto")


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    category_id: int | None = None
    unit_of_measure: str = Field(default="unidad", pattern="^(unidad|kg|lb)$")
    tax_rate: Decimal | None = Field(default=None, ge=0, le=1)
    # Cada combinación es una variante opcionalmente con su propia unidad de medida.
    # Vacío => se crea una única variante default (productos simples o a granel).
    variant_combos: list[VariantComboSpec] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    category_id: int | None = None
    tax_rate: Decimal | None = Field(default=None, ge=0, le=1)
    is_active: bool | None = None


class ProductListItem(BaseModel):
    id: int
    name: str
    base_sku: str
    category_id: int | None
    category_name: str | None
    unit_of_measure: str
    is_bulk: bool
    tax_rate: Decimal
    is_active: bool
    photo_path: str | None = None
    variant_count: int


class ProductDetail(BaseModel):
    id: int
    name: str
    description: str | None
    base_sku: str
    category_id: int | None
    category_name: str | None
    unit_of_measure: str
    is_bulk: bool
    tax_rate: Decimal
    is_active: bool
    photo_path: str | None
    variants: list[VariantOut]


class ProductPage(BaseModel):
    items: list[ProductListItem]
    total: int
    page: int
    page_size: int


class VariantCombosCreate(BaseModel):
    variant_combos: list[VariantComboSpec] = Field(min_length=1)


class VariantUpdate(BaseModel):
    is_active: bool | None = None
    barcode: str | None = Field(default=None, max_length=40)
