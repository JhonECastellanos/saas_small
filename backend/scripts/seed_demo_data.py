"""Datos de ejemplo para validar el Dashboard.

Crea un proveedor, productos con variantes, precios publicados,
compras y ventas con fechas en el mes/año actual.

Uso:
  python scripts/seed_demo_data.py
"""

import os
import sys
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.base import Base

from app.modules.auth.models import BusinessSettings, User
from app.modules.cash.models import CashSession
from app.modules.inventory import models as _inv
from app.modules.invoices.models import Invoice, InvoiceCounter
from app.modules.returns.models import SaleReturn, SaleReturnItem
from app.modules.pricing.models import VariantPrice
from app.modules.products.models import Attribute, AttributeValue, Product, Variant, VariantAttributeValue
from app.modules.purchases.models import Purchase, PurchaseItem, Supplier
from app.modules.sales.models import Sale, SaleItem

from app.core.db import SessionLocal
from app.core.money import D, q2, q3
from app.modules.inventory.service import apply_movement


def run() -> None:
    db = SessionLocal()
    try:
        from app.core.security import hash_password
        from app.modules.auth.models import User

        admin = db.query(User).filter(User.email == "admin@negocio.com").first()
        if not admin:
            admin = User(
                email="admin@negocio.com",
                password_hash=hash_password("admin123"),
                full_name="Administrador",
                role="admin",
            )
            db.add(admin)
            db.flush()

        seller = db.query(User).filter(User.email == "vendedor1@negocio.com").first()
        if not seller:
            seller = User(
                email="vendedor1@negocio.com",
                password_hash=hash_password("vendedor123"),
                full_name="Vendedor Uno",
                role="vendedor",
            )
            db.add(seller)
            db.flush()

        if db.query(InvoiceCounter).filter(InvoiceCounter.id == 1).first() is None:
            db.add(InvoiceCounter(id=1, last_number=0))
            db.flush()

        from app.modules.auth.models import BusinessSettings
        if db.query(BusinessSettings).filter(BusinessSettings.id == 1).first() is None:
            db.add(BusinessSettings(id=1))
            db.flush()

        supplier, _ = _first_or_create(
            db, Supplier, Supplier.name == "Distribuidora Mayorista S.A.S.",
            name="Distribuidora Mayorista S.A.S.",
            tax_id="900.123.456-7", phone="+57 601 234 5678",
            email="ventas@distribuidora.com", is_active=True,
        )

        attrs = {}
        for attr in db.query(Attribute).all():
            values = db.query(AttributeValue).filter(
                AttributeValue.attribute_id == attr.id
            ).all()
            attrs[attr.name.lower()] = {v.value: v for v in values}

        COLOR = attrs.get("color", {})
        TALLA = attrs.get("talla", {})

        today = date.today()

        # --- Producto 1: Camisa Polo (con variantes) ---
        camisa = _create_product(db, "Camisa Polo", "POLO", "unidad", False, D("0.19"))
        camisa_variants = []
        if COLOR and TALLA:
            for cname in ("Rojo", "Azul"):
                for tname in ("M", "L"):
                    color = COLOR[cname]
                    talla = TALLA[tname]
                    sig = f"{color.code}-{talla.code}"
                    sku = f"{camisa.base_sku}-{sig}"
                    v = Variant(
                        product_id=camisa.id, sku=sku,
                        attributes_signature=sig, is_active=True,
                    )
                    db.add(v)
                    db.flush()
                    db.add(VariantAttributeValue(
                        variant_id=v.id, attribute_id=color.attribute_id,
                        attribute_value_id=color.id,
                    ))
                    db.add(VariantAttributeValue(
                        variant_id=v.id, attribute_id=talla.attribute_id,
                        attribute_value_id=talla.id,
                    ))
                    camisa_variants.append(v)
        else:
            v = Variant(
                product_id=camisa.id, sku="POLO-001-DEF",
                attributes_signature="DEF", is_active=True,
            )
            db.add(v)
            db.flush()
            camisa_variants.append(v)

        for v in camisa_variants:
            _create_price(db, v, D("35000"), None, D("15000"))

        # --- Producto 2: Arroz (granel) ---
        arroz = _create_product(db, "Arroz", "ARROZ", "kg", True, D("0.05"))
        v_arroz = Variant(
            product_id=arroz.id, sku="ARROZ-001-DEF",
            attributes_signature="DEF", is_active=True,
        )
        db.add(v_arroz)
        db.flush()
        arroz_per_lb = q2(D("6500") / D("2.20462"))
        _create_price(db, v_arroz, D("6500"), arroz_per_lb, D("4000"))

        # --- Producto 3: Aceite Vegetal ---
        aceite = _create_product(db, "Aceite Vegetal", "ACEITE", "unidad", False, D("0.19"))
        v_aceite = Variant(
            product_id=aceite.id, sku="ACEITE-001-DEF",
            attributes_signature="DEF", is_active=True,
        )
        db.add(v_aceite)
        db.flush()
        _create_price(db, v_aceite, D("25000"), None, D("12000"))

        db.flush()

        # --- Compra 1: Camisas (30 unds, hace 3 días) ---
        qty_camisa = D("30")
        camisa_cost = D("15000")
        camisa_total = q2(qty_camisa * camisa_cost)
        _do_purchase(db, camisa, camisa_variants, qty_camisa, camisa_cost,
                     camisa_total, supplier.id, admin.id, today - timedelta(days=3))

        # --- Compra 2: Arroz (50 kg, hace 2 días) ---
        qty_arroz = D("50")
        arroz_cost = D("4000")
        arroz_total = q2(qty_arroz * arroz_cost)
        _do_purchase(db, arroz, [v_arroz], qty_arroz, arroz_cost,
                     arroz_total, supplier.id, admin.id, today - timedelta(days=2))

        # --- Compra 3: Aceite (20 unds, hace 5 días) ---
        qty_aceite = D("20")
        aceite_cost = D("12000")
        aceite_total = q2(qty_aceite * aceite_cost)
        _do_purchase(db, aceite, [v_aceite], qty_aceite, aceite_cost,
                     aceite_total, supplier.id, admin.id, today - timedelta(days=5))

        # --- Ventas ---
        _do_sale(db, camisa, camisa_variants[:2], [D("2"), D("1")],
                 D("35000"), D("0.19"), "unidad", admin.id, today - timedelta(days=1))
        _do_sale(db, arroz, [v_arroz], [D("3")],
                 D("6500"), D("0.05"), "kg", admin.id, today - timedelta(days=1))
        _do_sale(db, aceite, [v_aceite], [D("5")],
                 D("25000"), D("0.19"), "unidad", admin.id, today)

        db.commit()

        _print_summary(db, today)

    finally:
        db.close()


def _first_or_create(db, model, condition, **kwargs):
    obj = db.query(model).filter(condition).first()
    if obj:
        return obj, False
    obj = model(**kwargs)
    db.add(obj)
    db.flush()
    return obj, True


def _create_product(db, name, base_sku, unit, is_bulk, tax_rate):
    from app.modules.products.models import SkuCounter
    existing = db.query(Product).filter(Product.base_sku == base_sku).first()
    if existing:
        return existing
    product = Product(
        name=name, base_sku=base_sku,
        unit_of_measure=unit, is_bulk=is_bulk,
        tax_rate=tax_rate, is_active=True,
    )
    db.add(product)
    db.flush()
    if db.query(SkuCounter).filter(SkuCounter.prefix == base_sku).first() is None:
        from sqlalchemy import insert
        db.execute(insert(SkuCounter).values(prefix=base_sku, last_number=1))
    return product


def _create_price(db, variant, price, price_per_lb, cost_ref):
    existing = db.query(VariantPrice).filter(
        VariantPrice.variant_id == variant.id
    ).first()
    if existing:
        return existing
    vp = VariantPrice(
        variant_id=variant.id, price=price,
        price_per_lb=price_per_lb, cost_reference=cost_ref,
        status="publicado",
    )
    db.add(vp)
    return vp


def _do_purchase(db, product, variants, total_qty, cost, total,
                 supplier_id, user_id, pdate):
    purchase = Purchase(
        supplier_id=supplier_id, purchase_date=pdate,
        status="completada", total_cost=total, created_by=user_id,
    )
    db.add(purchase)
    db.flush()

    per_v = q3(total_qty / D(len(variants)))
    per_line = q2(per_v * cost)
    for v in variants:
        db.add(PurchaseItem(
            purchase_id=purchase.id, variant_id=v.id,
            quantity=per_v, unit_cost=cost,
            input_unit=product.unit_of_measure if not product.is_bulk else "kg",
            input_quantity=per_v, line_total=per_line,
        ))
        apply_movement(db, variant_id=v.id, delta=per_v,
                       movement_type="entrada_compra", user_id=user_id,
                       unit_cost=cost, reference_type="purchase",
                       reference_id=purchase.id)
    print(f"  Compra: {product.name} x {total_qty} = ${total:,.0f} ({pdate})")


def _do_sale(db, product, variants, qties, price, tax_rate, unit,
             user_id, sdate):
    from datetime import datetime, timezone

    total_q = sum(qties)
    subtotal = q2(D(total_q) * price)
    tax_amt = q2(subtotal * tax_rate)
    total = q2(subtotal + tax_amt)
    now = datetime.now(timezone.utc)

    result = db.execute(
        Sale.__table__.insert().returning(Sale.__table__.c.id).values(
            user_id=user_id, status="completada",
            payment_method="efectivo",
            subtotal=subtotal, discount_amount=D("0"),
            tax_amount=tax_amt, total=total,
            created_at=now, updated_at=now,
        )
    )
    sale_id = result.scalar_one()

    for v, qty in zip(variants, qties):
        dqty = D(qty)
        line_total = q2(dqty * price)
        line_tax = q2(line_total * tax_rate)
        unit_cost = D("15000") if product.base_sku == "POLO" else D("4000") if product.base_sku == "ARROZ" else D("12000")
        db.execute(
            SaleItem.__table__.insert().values(
                sale_id=sale_id, variant_id=v.id,
                sku_snapshot=v.sku,
                description_snapshot=f"{product.name} {v.sku}",
                quantity=dqty, unit_snapshot=unit,
                unit_price_snapshot=price,
                discount_pct=D("0"),
                unit_cost_snapshot=unit_cost,
                tax_rate_snapshot=tax_rate,
                tax_amount=line_tax, line_total=line_total,
            )
        )
        apply_movement(db, variant_id=v.id, delta=-dqty,
                       movement_type="salida_venta", user_id=user_id,
                       reference_type="sale", reference_id=sale_id)

    counter = db.query(InvoiceCounter).filter(InvoiceCounter.id == 1).first()
    if counter:
        counter.last_number += 1
        num = counter.last_number
    else:
        num = 1
    db.add(Invoice(
        sale_id=sale_id, invoice_prefix="FV",
        invoice_number=num,
        business_name="Mi Negocio", business_tax_id="123.456.789-0",
        business_address="Calle 123", business_phone="555-0000",
        currency="COP", issued_at=now,
    ))
    print(f"  Venta: {product.name} x {total_q} = ${total:,.0f} ({sdate})")


def _print_summary(db, today):
    from app.modules.sales.models import Sale as SaleModel
    from app.modules.purchases.models import Purchase as PurchaseModel
    from sqlalchemy import func, select

    cm = today.month
    cy = today.year

    s_month = db.scalar(
        select(func.coalesce(func.sum(SaleModel.total), 0)).where(
            func.extract("month", SaleModel.created_at) == cm,
            func.extract("year", SaleModel.created_at) == cy,
            SaleModel.status == "completada",
        )
    ) or 0
    s_year = db.scalar(
        select(func.coalesce(func.sum(SaleModel.total), 0)).where(
            func.extract("year", SaleModel.created_at) == cy,
            SaleModel.status == "completada",
        )
    ) or 0
    p_month = db.scalar(
        select(func.coalesce(func.sum(PurchaseModel.total_cost), 0)).where(
            func.extract("month", PurchaseModel.purchase_date) == cm,
            func.extract("year", PurchaseModel.purchase_date) == cy,
            PurchaseModel.status == "completada",
        )
    ) or 0
    p_year = db.scalar(
        select(func.coalesce(func.sum(PurchaseModel.total_cost), 0)).where(
            func.extract("year", PurchaseModel.purchase_date) == cy,
            PurchaseModel.status == "completada",
        )
    ) or 0

    print("\n" + "=" * 50)
    print("RESUMEN DE DATOS DE EJEMPLO")
    print("=" * 50)
    print(f" Ventas del mes:     ${s_month:>10,.2f}")
    print(f" Ventas del año:     ${s_year:>10,.2f}")
    print(f" Compras del mes:    ${p_month:>10,.2f}")
    print(f" Compras del año:    ${p_year:>10,.2f}")
    print("=" * 50)
    print(" Ve al Dashboard en http://localhost:3000")
    print()


if __name__ == "__main__":
    run()
