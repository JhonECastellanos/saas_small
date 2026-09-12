from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BigIntPK, TimestampMixin


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)


class SkuCounter(Base):
    """Contador atómico por prefijo para generar SKUs sin estado en memoria."""

    __tablename__ = "sku_counters"

    prefix: Mapped[str] = mapped_column(String(20), primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("unit_of_measure IN ('unidad','kg','lb')", name="ck_products_unit"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    base_sku: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(10), nullable=False, default="unidad")
    is_bulk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    photo_path: Mapped[str | None] = mapped_column(String(255))

    category: Mapped[Category | None] = relationship()
    variants: Mapped[list["Variant"]] = relationship(back_populates="product")


class Attribute(Base, TimestampMixin):
    """Tipo de variante dinámico: color, talla, sabor… se agregan sin tocar el esquema."""

    __tablename__ = "attributes"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    values: Mapped[list["AttributeValue"]] = relationship(
        back_populates="attribute", order_by="AttributeValue.value"
    )


class AttributeValue(Base, TimestampMixin):
    __tablename__ = "attribute_values"
    __table_args__ = (
        UniqueConstraint("attribute_id", "value", name="uq_attr_value"),
        UniqueConstraint("attribute_id", "code", name="uq_attr_code"),
        # Permite la FK compuesta desde variant_attribute_values que garantiza
        # que el valor pertenece al atributo declarado.
        UniqueConstraint("id", "attribute_id", name="uq_attrvalue_id_attr"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    attribute_id: Mapped[int] = mapped_column(ForeignKey("attributes.id"), nullable=False)
    value: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False)

    attribute: Mapped[Attribute] = relationship(back_populates="values")


class Variant(Base, TimestampMixin):
    """Unidad vendible. Todo producto tiene al menos una variante (default si no
    maneja atributos), de modo que compras/stock/ventas siempre referencian variant_id."""

    __tablename__ = "variants"
    __table_args__ = (
        UniqueConstraint("product_id", "attributes_signature", name="uq_variant_combo"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(40), unique=True)
    attributes_signature: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    unit_of_measure: Mapped[str] = mapped_column(String(10), nullable=False, default="unidad")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    product: Mapped[Product] = relationship(back_populates="variants")
    attribute_values: Mapped[list["VariantAttributeValue"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )


class VariantAttributeValue(Base):
    __tablename__ = "variant_attribute_values"
    __table_args__ = (
        ForeignKeyConstraint(
            ["attribute_value_id", "attribute_id"],
            ["attribute_values.id", "attribute_values.attribute_id"],
            name="fk_vav_value_belongs_to_attribute",
        ),
    )

    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id"), primary_key=True)
    attribute_id: Mapped[int] = mapped_column(ForeignKey("attributes.id"), primary_key=True)
    attribute_value_id: Mapped[int] = mapped_column(nullable=False)

    variant: Mapped[Variant] = relationship(back_populates="attribute_values")
    attribute: Mapped[Attribute] = relationship()
    value: Mapped[AttributeValue] = relationship(
        foreign_keys=[attribute_value_id],
        primaryjoin="VariantAttributeValue.attribute_value_id == AttributeValue.id",
        viewonly=True,
    )
