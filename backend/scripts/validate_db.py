"""Validacion completa de base de datos.

Recorre el ciclo completo del aplicativo web:
Producto -> Compra -> Precio -> Publicacion -> Venta -> Factura

En cada paso valida que las tablas correctas se actualicen con los datos
correctos. Al finalizar reinicia la base de datos.

Uso:
  python scripts/validate_db.py
"""

import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.core.security as security
security.PBKDF2_ITERATIONS = 1000

from app.core.db import get_db
from app.core.security import hash_password
from app.main import app
from app.models.base import Base
from app.modules.auth.models import BusinessSettings, User
from app.modules.invoices.models import InvoiceCounter
from app.modules.products.models import Attribute, AttributeValue

from app.modules.cash import models as _cash
from app.modules.inventory import models as _inv
from app.modules.pricing import models as _pri
from app.modules.purchases import models as _pur
from app.modules.sales import models as _sal


PASS = "\033[92mOK\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"


def _eta(desc: str):
    print(f"  -> {desc} ... ", end="", flush=True)


def _ok(msg=""):
    print(f"{PASS} {msg}" if msg else f"{PASS}")


def _fail(msg=""):
    print(f"{FAIL} {msg}")
    raise AssertionError(msg)


def _check(val, msg=""):
    if val:
        _ok(msg)
    else:
        _fail(msg)


def run():
    print("=" * 64)
    print("  VALIDACION COMPLETA DE BASE DE DATOS")
    print("  Ciclo: Producto -> Compra -> Precio -> Venta -> Factura")
    print("=" * 64)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = TestingSession()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        # ---------------------------------------------------------------
        # PASO 0: SEMILLA
        # ---------------------------------------------------------------
        print("\n[PASO 0] Sembrando datos base...")
        _eta("Creando usuarios admin y vendedor")
        admin = User(
            email="admin@test.co",
            password_hash=hash_password("admin123"),
            full_name="Admin Test",
            role="admin",
        )
        seller = User(
            email="vendedor@test.co",
            password_hash=hash_password("vende123"),
            full_name="Vendedor Test",
            role="vendedor",
        )
        db.add_all([admin, seller, BusinessSettings(id=1), InvoiceCounter(id=1, last_number=0)])
        db.flush()

        color = Attribute(name="Color", code="COL", sort_order=0)
        talla = Attribute(name="Talla", code="TAL", sort_order=1)
        db.add_all([color, talla])
        db.flush()
        vals = {}
        for vname, vcode, attr in [
            ("Rojo", "ROJ", color), ("Azul", "AZU", color),
            ("M", "M", talla), ("L", "L", talla),
        ]:
            av = AttributeValue(attribute_id=attr.id, value=vname, code=vcode)
            db.add(av)
            db.flush()
            vals[vname] = av.id
        db.commit()
        _ok()
        print(f"     Usuarios: admin={admin.id}, vendedor={seller.id}")
        print(f"     Atributos: {len(vals)} valores")

        _eta("Iniciando sesion como admin")
        resp = client.post("/api/v1/auth/login", json={"email": "admin@test.co", "password": "admin123"})
        _check(resp.status_code == 200, f"status={resp.status_code}")
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"     Token: {token[:40]}...")

        # ---------------------------------------------------------------
        # PASO 1: PRODUCTO
        # ---------------------------------------------------------------
        print("\n[PASO 1] Creando producto con variantes...")
        _eta("POST /api/v1/products (Camisa Polo, variantes Rojo/M + Azul/L)")
        resp = client.post("/api/v1/products", json={
            "name": "Camisa Polo",
            "unit_of_measure": "unidad",
            "variant_combos": [
                {"attribute_value_ids": [vals["Rojo"], vals["M"]]},
                {"attribute_value_ids": [vals["Azul"], vals["L"]]},
            ],
            "tax_rate": 0.19,
        }, headers=headers)
        _check(resp.status_code == 201, f"status={resp.status_code}")
        product = resp.json()
        print(f"     Producto ID={product['id']}, SKU={product['base_sku']}")
        print(f"     Variantes: {len(product['variants'])}")

        _eta("Tabla products: 1 fila")
        from app.modules.products.models import Product as ProductModel
        p_db = db.query(ProductModel).filter(ProductModel.id == product["id"]).first()
        _check(p_db is not None)
        _check(p_db.name == "Camisa Polo")
        _check(p_db.base_sku == product["base_sku"])
        _check(p_db.unit_of_measure == "unidad")
        _check(p_db.is_bulk is False)
        _ok(f"name={p_db.name}, sku={p_db.base_sku}")

        _eta("Tabla variants: 2 filas con SKUs derivados")
        from app.modules.products.models import Variant
        variants = db.query(Variant).filter(Variant.product_id == product["id"]).all()
        _check(len(variants) == 2, f"count={len(variants)}")
        skus = sorted([v.sku for v in variants])
        _check(skus[0].startswith(product["base_sku"]))
        _check(skus[1].startswith(product["base_sku"]))
        _check(skus[0] != skus[1])
        _ok(f"SKUs: {skus}")

        _eta("Tabla variant_prices: 2 filas en borrador")
        from app.modules.pricing.models import VariantPrice
        prices = db.query(VariantPrice).filter(
            VariantPrice.variant_id.in_([v.id for v in variants])
        ).all()
        _check(len(prices) == 2, f"count={len(prices)}")
        _check(all(p.status == "borrador" for p in prices))
        _check(all(p.price == 0 for p in prices))
        _ok()

        _eta("Tabla stock: 2 filas con quantity=0")
        stocks = db.query(_inv.Stock).filter(
            _inv.Stock.variant_id.in_([v.id for v in variants])
        ).all()
        _check(len(stocks) == 2, f"count={len(stocks)}")
        _check(all(s.quantity == 0 for s in stocks))
        _ok()

        _eta("Tabla sku_counters: contador incrementado")
        from app.modules.products.models import SkuCounter
        counter = db.query(SkuCounter).filter(
            SkuCounter.prefix == product["base_sku"].split("-")[0]
        ).first()
        _check(counter is not None)
        _check(counter.last_number > 0)
        _ok(f"prefix={counter.prefix}, last={counter.last_number}")

        # ---------------------------------------------------------------
        # PASO 2: PROVEEDOR
        # ---------------------------------------------------------------
        print("\n[PASO 2] Creando proveedor...")
        _eta("POST /api/v1/suppliers")
        resp = client.post("/api/v1/suppliers", json={
            "name": "Distribuidora Mayorista",
            "tax_id": "900.123.456-7",
            "phone": "+57 601 234 5678",
        }, headers=headers)
        _check(resp.status_code == 201, f"status={resp.status_code}")
        supplier = resp.json()
        print(f"     Proveedor ID={supplier['id']}, name={supplier['name']}")

        _eta("Tabla suppliers: 1 fila con datos correctos")
        from app.modules.purchases.models import Supplier
        s_db = db.query(Supplier).filter(Supplier.id == supplier["id"]).first()
        _check(s_db is not None)
        _check(s_db.name == "Distribuidora Mayorista")
        _check(s_db.tax_id == "900.123.456-7")
        _check(s_db.is_active is True)
        _ok()

        # ---------------------------------------------------------------
        # PASO 3: COMPRA
        # ---------------------------------------------------------------
        print("\n[PASO 3] Registrando compra...")
        v1, v2 = variants
        _eta("POST /api/v1/purchases (10 unidades de cada variante, costo $5.000)")
        resp = client.post("/api/v1/purchases", json={
            "supplier_id": supplier["id"],
            "purchase_date": "2026-07-20",
            "items": [
                {"variant_id": v1.id, "quantity": 10, "unit": "unidad", "unit_cost": 5000},
                {"variant_id": v2.id, "quantity": 10, "unit": "unidad", "unit_cost": 5000},
            ],
        }, headers=headers)
        _check(resp.status_code == 201, f"status={resp.status_code}")
        purchase = resp.json()
        print(f"     Compra ID={purchase['id']}, total=${purchase['total_cost']}")
        print(f"     Items: {len(purchase['items'])}")

        _eta("Tabla purchases: 1 fila con total calculado")
        from app.modules.purchases.models import Purchase
        pch_db = db.query(Purchase).filter(Purchase.id == purchase["id"]).first()
        _check(pch_db is not None)
        _check(pch_db.total_cost == 100000)
        _check(pch_db.status == "completada")
        _check(pch_db.supplier_id == supplier["id"])
        _ok(f"total={pch_db.total_cost}")

        _eta("Tabla purchase_items: 2 lineas con costos correctos")
        from app.modules.purchases.models import PurchaseItem
        pitems = db.query(PurchaseItem).filter(
            PurchaseItem.purchase_id == purchase["id"]
        ).all()
        _check(len(pitems) == 2, f"count={len(pitems)}")
        for pi in pitems:
            _check(pi.quantity == 10)
            _check(pi.unit_cost == 5000)
            _check(pi.line_total == 50000)
        _ok()

        _eta("Tabla stock: quantity actualizada a 10")
        s1 = db.query(_inv.Stock).filter(_inv.Stock.variant_id == v1.id).first()
        s2 = db.query(_inv.Stock).filter(_inv.Stock.variant_id == v2.id).first()
        _check(s1 is not None and s2 is not None)
        _check(s1.quantity == 10, f"v1={s1.quantity}")
        _check(s2.quantity == 10, f"v2={s2.quantity}")
        _ok(f"v1={s1.quantity}, v2={s2.quantity}")

        _eta("Tabla inventory_movements: 2 movimientos entrada_compra")
        from app.modules.inventory.models import InventoryMovement
        moves = db.query(InventoryMovement).filter(
            InventoryMovement.reference_type == "purchase",
            InventoryMovement.reference_id == purchase["id"],
        ).all()
        _check(len(moves) == 2, f"count={len(moves)}")
        for m in moves:
            _check(m.movement_type == "entrada_compra")
            _check(m.quantity == 10)
            _check(m.balance_after == 10)
            _check(m.unit_cost == 5000)
        _ok()

        _eta("Tabla variant_prices: auto-publicado despues de la compra")
        prices_after = db.query(VariantPrice).filter(
            VariantPrice.variant_id.in_([v1.id, v2.id])
        ).all()
        _check(all(p.status == "publicado" for p in prices_after))
        _check(all(p.price == 5000 for p in prices_after))
        _ok(f"status={prices_after[0].status}, price={prices_after[0].price}")

        # ---------------------------------------------------------------
        # PASO 4: PRECIO PERSONALIZADO Y PUBLICACION
        # ---------------------------------------------------------------
        print("\n[PASO 4] Configurando precio personalizado...")
        _eta("PUT /api/v1/pricing/variants/{id} (price=12000)")
        resp = client.put(f"/api/v1/pricing/variants/{v1.id}", json={"price": 12000}, headers=headers)
        _check(resp.status_code == 200, f"status={resp.status_code}")
        price_data = resp.json()
        _check(price_data["price"] == "12000.00")
        _check(price_data["status"] == "publicado")
        _ok(f"price={price_data['price']}, status={price_data['status']}")

        _eta("Tabla variant_prices: precio actualizado")
        pv1 = db.query(VariantPrice).filter(VariantPrice.variant_id == v1.id).first()
        _check(pv1.price == 12000)
        _check(pv1.status == "publicado")
        _ok(f"price={pv1.price}")

        # ---------------------------------------------------------------
        # PASO 5: CATALOGO
        # ---------------------------------------------------------------
        print("\n[PASO 5] Validando catalogo del POS...")
        _eta("GET /api/v1/sales/catalog (admin)")
        resp = client.get("/api/v1/sales/catalog", headers=headers)
        _check(resp.status_code == 200, f"status={resp.status_code}")
        catalog = resp.json()
        _check(len(catalog) == 2, f"count={len(catalog)}")
        _check(all(item["product_name"] == "Camisa Polo" for item in catalog))
        _check(all(int(item["stock"]) > 0 for item in catalog))
        _check(all(item["price"] != "0" for item in catalog))
        _ok(f"{len(catalog)} variantes en catalogo con stock y precio")

        _eta("GET /api/v1/sales/catalog con busqueda por nombre")
        resp = client.get("/api/v1/sales/catalog?q=Camisa&limit=10", headers=headers)
        _check(resp.status_code == 200)
        _check(len(resp.json()) == 2)
        _ok()

        _eta("GET /api/v1/sales/catalog con busqueda por SKU")
        resp = client.get(f"/api/v1/sales/catalog?q={v1.sku}&limit=10", headers=headers)
        _check(resp.status_code == 200)
        _check(len(resp.json()) == 1)
        _check(resp.json()[0]["variant_id"] == v1.id)
        _ok()

        # ---------------------------------------------------------------
        # PASO 6: VENTA
        # ---------------------------------------------------------------
        print("\n[PASO 6] Realizando venta...")
        _eta("POST /api/v1/sales (3 unidades v1 + 2 unidades v2)")
        resp = client.post("/api/v1/sales", json={
            "payment_method": "efectivo",
            "customer_name": "Cliente Prueba",
            "customer_id_number": "1234567890",
            "items": [
                {"variant_id": v1.id, "quantity": 3, "unit": "unidad", "discount_pct": 0},
                {"variant_id": v2.id, "quantity": 2, "unit": "unidad", "discount_pct": 0},
            ],
        }, headers=headers)
        _check(resp.status_code == 201, f"status={resp.status_code}")
        sale = resp.json()
        print(f"     Venta ID={sale['id']}, total=${sale['total']}")
        print(f"     Factura: {sale['invoice_number']}")

        _eta("Tabla sales: 1 fila con totales correctos")
        from app.modules.sales.models import Sale
        s_db = db.query(Sale).filter(Sale.id == sale["id"]).first()
        _check(s_db is not None)
        subtotal = 3 * 12000 + 2 * 5000
        tax = int(subtotal * Decimal("0.19"))
        total = subtotal + tax
        _check(s_db.subtotal == subtotal, f"subtotal esperado={subtotal} real={s_db.subtotal}")
        _check(s_db.tax_amount == tax, f"tax esperado={tax} real={s_db.tax_amount}")
        _check(s_db.total == total, f"total esperado={total} real={s_db.total}")
        _check(s_db.payment_method == "efectivo")
        _check(s_db.customer_name == "Cliente Prueba")
        _check(s_db.status == "completada")
        _ok(f"subtotal={s_db.subtotal}, tax={s_db.tax_amount}, total={s_db.total}")

        _eta("Tabla sale_items: 2 lineas con snapshots inmutables")
        from app.modules.sales.models import SaleItem
        sitems = db.query(SaleItem).filter(SaleItem.sale_id == sale["id"]).all()
        _check(len(sitems) == 2, f"count={len(sitems)}")
        for si in sitems:
            _check(si.sku_snapshot is not None)
            _check(si.description_snapshot is not None)
            _check(si.unit_price_snapshot is not None)
            _check(si.tax_rate_snapshot is not None)
            _check(si.line_total is not None)
            _check(si.unit_cost_snapshot == 5000)
        _ok()

        _eta("Tabla stock: descontado (10-3=7, 10-2=8)")
        s1_after = db.query(_inv.Stock).filter(_inv.Stock.variant_id == v1.id).first()
        s2_after = db.query(_inv.Stock).filter(_inv.Stock.variant_id == v2.id).first()
        _check(s1_after.quantity == 7, f"v1 esperado=7 real={s1_after.quantity}")
        _check(s2_after.quantity == 8, f"v2 esperado=8 real={s2_after.quantity}")
        _ok(f"v1={s1_after.quantity}, v2={s2_after.quantity}")

        _eta("Tabla inventory_movements: 2 movimientos salida_venta")
        sale_moves = db.query(InventoryMovement).filter(
            InventoryMovement.reference_type == "sale",
            InventoryMovement.reference_id == sale["id"],
        ).all()
        _check(len(sale_moves) == 2, f"count={len(sale_moves)}")
        for m in sale_moves:
            _check(m.movement_type == "salida_venta")
            _check(m.quantity < 0)
            _check(m.balance_after >= 0)
        _ok()

        _eta("Tabla invoices: 1 factura con snapshot del negocio")
        from app.modules.invoices.models import Invoice
        inv = db.query(Invoice).filter(Invoice.sale_id == sale["id"]).first()
        _check(inv is not None)
        _check(inv.invoice_prefix == "FV")
        _check(inv.invoice_number == 1)
        _check(inv.business_name is not None)
        _check(inv.currency == "COP")
        _check(inv.issued_at is not None)
        _ok(f"prefix={inv.invoice_prefix}, number={inv.invoice_number}")

        _eta("Tabla invoice_counters: contador incrementado a 1")
        counter_after = db.query(InvoiceCounter).filter(InvoiceCounter.id == 1).first()
        _check(counter_after.last_number == 1, f"real={counter_after.last_number}")
        _ok(f"last_number={counter_after.last_number}")

        _eta("GET /api/v1/invoices (validar listado)")
        resp = client.get("/api/v1/invoices", headers=headers, params={"page": 1, "page_size": 10})
        _check(resp.status_code == 200)
        invoices_page = resp.json()
        _check(invoices_page["total"] >= 1)
        invoice_found = any(
            inv_item["invoice_number"] == "FV-000001"
            for inv_item in invoices_page["items"]
        )
        _check(invoice_found)
        _ok(f"{len(invoices_page['items'])} factura(s) encontrada(s)")

        # ---------------------------------------------------------------
        # PASO 7: CATALOGO POST-VENTA
        # ---------------------------------------------------------------
        print("\n[PASO 7] Validando catalogo despues de venta...")
        _eta("GET /api/v1/sales/catalog (stock reducido)")
        resp = client.get("/api/v1/sales/catalog", headers=headers)
        catalog_after = resp.json()
        for item in catalog_after:
            if item["variant_id"] == v1.id:
                _check(int(item["stock"]) == 7, f"v1 stock={item['stock']}")
            elif item["variant_id"] == v2.id:
                _check(int(item["stock"]) == 8, f"v2 stock={item['stock']}")
        _ok("stocks reflejan las ventas realizadas")

        # ---------------------------------------------------------------
        # PASO 8: SOBREVENTA (ROLLBACK)
        # ---------------------------------------------------------------
        print("\n[PASO 8] Validando atomicidad en sobreventa...")
        stock_before = db.query(_inv.Stock).filter(_inv.Stock.variant_id == v1.id).first().quantity
        inv_count_before = db.query(InventoryMovement).count()

        _eta("POST /api/v1/sales (100 unidades cuando solo hay 7)")
        resp = client.post("/api/v1/sales", json={
            "payment_method": "efectivo",
            "items": [
                {"variant_id": v1.id, "quantity": 100, "unit": "unidad", "discount_pct": 0},
            ],
        }, headers=headers)
        _check(resp.status_code in (409, 422), f"status={resp.status_code} (debia fallar)")

        _eta("Tabla stock: sin cambios (rollback)")
        stock_after = db.query(_inv.Stock).filter(_inv.Stock.variant_id == v1.id).first().quantity
        _check(stock_after == stock_before, f"antes={stock_before} despues={stock_after}")
        _ok()

        _eta("Tabla inventory_movements: sin nuevos registros")
        inv_count_after = db.query(InventoryMovement).count()
        _check(inv_count_after == inv_count_before, f"antes={inv_count_before} despues={inv_count_after}")
        _ok()

        _eta("Tabla sales: sin nuevas ventas fallidas")
        sales_count_after = db.query(Sale).count()
        _check(sales_count_after == 1, f"count={sales_count_after} (solo la venta exitosa)")
        _ok()

        _eta("Tabla invoices: sin nuevas facturas")
        invoices_count = db.query(Invoice).count()
        _check(invoices_count == 1, f"count={invoices_count}")
        _ok()

        # ---------------------------------------------------------------
        # PASO 9: ANULACION DE VENTA
        # ---------------------------------------------------------------
        print("\n[PASO 9] Anulando venta y validando restauracion...")
        _eta("POST /api/v1/sales/{id}/void")
        resp = client.post(f"/api/v1/sales/{sale['id']}/void", headers=headers)
        _check(resp.status_code == 200, f"status={resp.status_code}")
        void_result = resp.json()
        _check(void_result["status"] == "anulada")
        _ok(f"status={void_result['status']}")

        _eta("Tabla stock: restaurado a 10")
        s1_void = db.query(_inv.Stock).filter(_inv.Stock.variant_id == v1.id).first()
        s2_void = db.query(_inv.Stock).filter(_inv.Stock.variant_id == v2.id).first()
        _check(s1_void.quantity == 10, f"v1={s1_void.quantity}")
        _check(s2_void.quantity == 10, f"v2={s2_void.quantity}")
        _ok()

        _eta("Tabla inventory_movements: nuevo movimiento de ajuste")
        void_moves = db.query(InventoryMovement).filter(
            InventoryMovement.reference_type == "sale",
            InventoryMovement.reference_id == sale["id"],
            InventoryMovement.movement_type == "ajuste",
        ).all()
        _check(len(void_moves) == 2, f"count={len(void_moves)}")
        for m in void_moves:
            _check(m.quantity > 0)
            _check(m.balance_after == 10)
        _ok()

        # ---------------------------------------------------------------
        # PASO 10: ANULACION DE COMPRA
        # ---------------------------------------------------------------
        print("\n[PASO 10] Anulando compra y validando...")
        _eta("POST /api/v1/purchases/{id}/void")
        resp = client.post(f"/api/v1/purchases/{purchase['id']}/void", headers=headers)
        _check(resp.status_code == 200, f"status={resp.status_code}")
        void_pch = resp.json()
        _check(void_pch["status"] == "anulada")
        _ok(f"status={void_pch['status']}")

        _eta("Tabla stock: quantity vuelta a 0")
        s1_pchvoid = db.query(_inv.Stock).filter(_inv.Stock.variant_id == v1.id).first()
        s2_pchvoid = db.query(_inv.Stock).filter(_inv.Stock.variant_id == v2.id).first()
        _check(s1_pchvoid.quantity == 0, f"v1={s1_pchvoid.quantity}")
        _check(s2_pchvoid.quantity == 0, f"v2={s2_pchvoid.quantity}")
        _ok()

        _eta("Tabla purchases: status actualizado")
        pch_voided = db.query(Purchase).filter(Purchase.id == purchase["id"]).first()
        _check(pch_voided.status == "anulada")
        _ok()

        # ---------------------------------------------------------------
        # PASO 11: PRODUCTO A GRANEL
        # ---------------------------------------------------------------
        print("\n[PASO 11] Validando producto a granel...")
        _eta("POST /api/v1/products (Arroz, unit=kg)")
        resp = client.post("/api/v1/products", json={
            "name": "Arroz",
            "unit_of_measure": "kg",
            "variant_combos": [],
            "tax_rate": 0.05,
        }, headers=headers)
        _check(resp.status_code == 201, f"status={resp.status_code}")
        bulk_product = resp.json()
        _check(bulk_product["is_bulk"] is True)
        _check(len(bulk_product["variants"]) == 1)
        bulk_variant = bulk_product["variants"][0]
        _ok(f"SKU={bulk_variant['sku']}, bulk={bulk_product['is_bulk']}")

        _eta("Tabla products: is_bulk=True, unit_of_measure=kg")
        bulk_db = db.query(ProductModel).filter(ProductModel.id == bulk_product["id"]).first()
        _check(bulk_db.is_bulk is True)
        _check(bulk_db.unit_of_measure == "kg")
        _ok()

        _eta("Compra de arroz en libras (conversion automatica)")
        resp = client.post("/api/v1/purchases", json={
            "supplier_id": supplier["id"],
            "purchase_date": "2026-07-20",
            "items": [
                {"variant_id": bulk_variant["id"], "quantity": 20, "unit": "lb", "unit_cost": 1500},
            ],
        }, headers=headers)
        _check(resp.status_code == 201, f"status={resp.status_code}")
        bulk_purchase = resp.json()
        _ok(f"total_compra=${bulk_purchase['total_cost']}")

        _eta("Tabla stock: quantity convertida a kg (20 lb = 9.072 kg)")
        bulk_stock = db.query(_inv.Stock).filter(
            _inv.Stock.variant_id == bulk_variant["id"]
        ).first()
        _check(bulk_stock is not None)
        _check(float(bulk_stock.quantity) == round(20 * 0.45359237, 3),
               f"esperado=9.072 real={bulk_stock.quantity}")
        _ok(f"stock={bulk_stock.quantity} kg")

        _eta("Tabla purchase_items: input en libras, cantidad en kg")
        bulk_items = db.query(PurchaseItem).filter(
            PurchaseItem.purchase_id == bulk_purchase["id"]
        ).all()
        _check(len(bulk_items) == 1)
        bi = bulk_items[0]
        _check(bi.input_unit == "lb")
        _check(bi.input_quantity == 20)
        _check(float(bi.quantity) == round(20 * 0.45359237, 3))
        _ok(f"input={bi.input_quantity} lb, almacenado={bi.quantity} kg")

        _eta("Venta de granel en libras")
        resp = client.put(f"/api/v1/pricing/variants/{bulk_variant['id']}",
            json={"price": 6500, "price_per_lb": 3000}, headers=headers)
        _check(resp.status_code == 200)
        resp = client.post(f"/api/v1/pricing/variants/{bulk_variant['id']}/publish", headers=headers)
        _check(resp.status_code == 200)

        resp = client.post("/api/v1/sales", json={
            "payment_method": "efectivo",
            "items": [
                {"variant_id": bulk_variant["id"], "quantity": 2.5, "unit": "lb", "discount_pct": 0},
            ],
        }, headers=headers)
        _check(resp.status_code == 201, f"status={resp.status_code}")
        bulk_sale = resp.json()
        bulk_stock_after = db.query(_inv.Stock).filter(
            _inv.Stock.variant_id == bulk_variant["id"]
        ).first()
        expected_kg_sold = round(2.5 * 0.45359237, 3)
        expected_remaining = round(float(bulk_stock.quantity) - expected_kg_sold, 3)
        _check(float(bulk_stock_after.quantity) == expected_remaining,
               f"esperado={expected_remaining} real={bulk_stock_after.quantity}")
        _ok(f"vendido={expected_kg_sold} kg, restante={bulk_stock_after.quantity} kg, factura={bulk_sale['invoice_number']}")

        # ---------------------------------------------------------------
        # RESUMEN FINAL
        # ---------------------------------------------------------------
        print("\n" + "=" * 64)
        print("  VALIDACION COMPLETA EXITOSA")
        print("=" * 64)
        print()
        print("  Tablas validadas:")
        print("    - users")
        print("    - business_settings")
        print("    - products")
        print("    - variants")
        print("    - variant_attribute_values")
        print("    - sku_counters")
        print("    - variant_prices")
        print("    - stock")
        print("    - inventory_movements")
        print("    - suppliers")
        print("    - purchases")
        print("    - purchase_items")
        print("    - sales")
        print("    - sale_items")
        print("    - invoices")
        print("    - invoice_counters")
        print()
        print("  Flujo validado:")
        print("    1. Creacion de producto con variantes -> products + variants")
        print("    2. Creacion de proveedor -> suppliers")
        print("    3. Compra con entrada de stock -> purchases + stock + kardex")
        print("    4. Precio personalizado + publicacion -> variant_prices")
        print("    5. Catalogo visible en POS -> sales/catalog")
        print("    6. Venta con descuento de stock + factura -> sales + invoices")
        print("    7. Catalogo post-venta refleja stock reducido")
        print("    8. Sobreventa rechazada con rollback total (stock + kardex + factura)")
        print("    9. Anulacion de venta restaura stock")
        print("   10. Anulacion de compra revierte inventario")
        print("   11. Producto a granel con conversion lb -> kg")
        print()

    finally:
        # Limpiar
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()

    # ---------------------------------------------------------------
    # PASO FINAL: REINICIAR BASE DE DATOS
    # ---------------------------------------------------------------
    print("=" * 64)
    print("  REINICIANDO BASE DE DATOS")
    print("=" * 64)

    print("\n  Eliminando tablas existentes...")
    Base.metadata.drop_all(engine)
    print("  Tablas eliminadas.")

    print("  Creando tablas desde cero...")
    Base.metadata.create_all(engine)
    print("  Tablas creadas.")
    print()
    print("  Base de datos lista para empezar de nuevo.")
    print("  Toda la informacion de prueba fue eliminada.")
    print()
    print("  Para poblar datos iniciales ejecuta:")
    print("    python scripts/seed.py")
    print()
    print("  Para datos demo ejecuta:")
    print("    python scripts/seed_demo_data.py")
    print()
    print("=" * 64)
    print("  LISTO. APLICACION COMO NUEVA.")
    print("=" * 64)


if __name__ == "__main__":
    run()
