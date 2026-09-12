from decimal import Decimal

from tests.helpers import (
    create_product,
    create_purchase,
    create_supplier,
    get_stock,
    sellable_product,
)


def _sell(client, headers, items, payment="efectivo", **extra):
    return client.post(
        "/api/v1/sales",
        json={"payment_method": payment, "items": items, **extra},
        headers=headers,
    )


# ---------- Descuentos y cliente en la factura ----------


def test_sale_with_discount_and_customer(client, admin_headers, seller_headers, seed_base):
    product = sellable_product(
        client, admin_headers, name="Gorra", stock_qty=10, price=10000, tax_rate="0.19"
    )
    variant_id = product["variants"][0]["id"]

    resp = _sell(
        client,
        seller_headers,
        [{"variant_id": variant_id, "quantity": 2, "unit": "unidad", "discount_pct": 10}],
        customer_name="Carlos Pérez",
        customer_id_number="1032456789",
    )
    assert resp.status_code == 201, resp.text
    sale = resp.json()
    # 2 × 10.000 = 20.000, con 10% de descuento = 18.000; IVA 19% = 3.420
    assert Decimal(sale["subtotal"]) == Decimal("18000.00")
    assert Decimal(sale["discount_amount"]) == Decimal("2000.00")
    assert Decimal(sale["tax_amount"]) == Decimal("3420.00")
    assert Decimal(sale["total"]) == Decimal("21420.00")
    assert sale["customer_name"] == "Carlos Pérez"

    invoice = client.get(f"/api/v1/invoices/{sale['invoice_id']}", headers=seller_headers).json()
    assert invoice["customer_name"] == "Carlos Pérez"
    assert invoice["customer_id_number"] == "1032456789"
    assert Decimal(invoice["discount_amount"]) == Decimal("2000.00")
    assert Decimal(invoice["items"][0]["discount_pct"]) == Decimal("10.00")


def test_discount_over_100_rejected(client, admin_headers, seller_headers, seed_base):
    product = sellable_product(client, admin_headers, name="Gorra", stock_qty=5)
    resp = _sell(
        client,
        seller_headers,
        [
            {
                "variant_id": product["variants"][0]["id"],
                "quantity": 1,
                "unit": "unidad",
                "discount_pct": 150,
            }
        ],
    )
    assert resp.status_code == 422


# ---------- Anulación de compras ----------


def test_void_purchase_restores_stock(client, admin_headers, seed_base):
    product = create_product(client, admin_headers, name="Gorra")
    variant_id = product["variants"][0]["id"]
    supplier = create_supplier(client, admin_headers)
    purchase = create_purchase(
        client,
        admin_headers,
        supplier["id"],
        [{"variant_id": variant_id, "quantity": 10, "unit": "unidad", "unit_cost": 5000}],
    )
    assert purchase["status"] == "completada"

    resp = client.post(f"/api/v1/purchases/{purchase['id']}/void", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "anulada"
    assert Decimal(get_stock(client, admin_headers, sku="GORRA")[0]["quantity"]) == Decimal("0")

    # Doble anulación rechazada
    assert (
        client.post(f"/api/v1/purchases/{purchase['id']}/void", headers=admin_headers).status_code
        == 409
    )


def test_void_purchase_blocked_if_stock_sold(client, admin_headers, seller_headers, seed_base):
    product = sellable_product(client, admin_headers, name="Gorra", stock_qty=10)
    variant_id = product["variants"][0]["id"]
    _sell(client, seller_headers, [{"variant_id": variant_id, "quantity": 8, "unit": "unidad"}])

    purchases = client.get("/api/v1/purchases", headers=admin_headers).json()["items"]
    resp = client.post(f"/api/v1/purchases/{purchases[0]['id']}/void", headers=admin_headers)
    assert resp.status_code == 409  # ya se vendieron 8 de las 10; no se puede revertir


# ---------- Reportes ----------


def test_sales_report_totals_and_profit(client, admin_headers, seller_headers, seed_base):
    product = sellable_product(
        client, admin_headers, name="Gorra", stock_qty=10, cost=5000, price=10000, tax_rate="0"
    )
    variant_id = product["variants"][0]["id"]
    _sell(client, seller_headers, [{"variant_id": variant_id, "quantity": 3, "unit": "unidad"}])
    _sell(
        client,
        seller_headers,
        [{"variant_id": variant_id, "quantity": 1, "unit": "unidad"}],
        payment="tarjeta",
    )

    report = client.get("/api/v1/reports/sales", headers=admin_headers).json()
    assert report["totals"]["sales_count"] == 2
    assert Decimal(report["totals"]["total"]) == Decimal("40000.00")
    # Utilidad: 40.000 ingresos - 20.000 costo (4 × 5.000)
    assert Decimal(report["totals"]["estimated_cost"]) == Decimal("20000.00")
    assert Decimal(report["totals"]["estimated_profit"]) == Decimal("20000.00")

    methods = {m["method"]: m["count"] for m in report["by_payment_method"]}
    assert methods == {"efectivo": 1, "tarjeta": 1}

    top = report["top_products"][0]
    assert top["sku"] == "GORRA-001"
    assert Decimal(top["profit"]) == Decimal("20000.00")

    # Solo admin
    assert client.get("/api/v1/reports/sales", headers=seller_headers).status_code == 403


# ---------- Cierre de caja ----------


def test_cash_session_cycle(client, admin_headers, seller_headers, seed_base):
    product = sellable_product(
        client, admin_headers, name="Gorra", stock_qty=10, price=10000, tax_rate="0.19"
    )

    opened = client.post(
        "/api/v1/cash/open", json={"opening_amount": 50000}, headers=seller_headers
    )
    assert opened.status_code == 201

    # No se puede abrir dos veces
    assert (
        client.post(
            "/api/v1/cash/open", json={"opening_amount": 1}, headers=seller_headers
        ).status_code
        == 409
    )

    _sell(
        client,
        seller_headers,
        [{"variant_id": product["variants"][0]["id"], "quantity": 2, "unit": "unidad"}],
    )

    current = client.get("/api/v1/cash/current", headers=seller_headers).json()
    assert current["totals"]["sales_count"] == 1

    closed = client.post(
        "/api/v1/cash/close",
        json={"closing_amount": 73000, "notes": "cierre del día"},
        headers=seller_headers,
    ).json()
    # Esperado: 50.000 base + 23.800 venta en efectivo (IVA 19% incluido en total)
    assert Decimal(closed["expected_cash"]) == Decimal("73800.00")
    assert Decimal(closed["difference"]) == Decimal("-800.00")
    assert closed["status"] == "cerrada"

    assert client.get("/api/v1/cash/current", headers=seller_headers).json() is None


# ---------- Código de barras ----------


def test_barcode_assignment_and_catalog_search(client, admin_headers, seed_base):
    product = sellable_product(client, admin_headers, name="Gorra", stock_qty=5, price=10000)
    variant_id = product["variants"][0]["id"]

    resp = client.patch(
        f"/api/v1/variants/{variant_id}", json={"barcode": "7701234567890"}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["barcode"] == "7701234567890"

    # Búsqueda exacta por código de barras en el catálogo del POS
    catalog = client.get(
        "/api/v1/sales/catalog", headers=admin_headers, params={"q": "7701234567890"}
    ).json()
    assert len(catalog) == 1
    assert catalog[0]["sku"] == "GORRA-001"

    # Código duplicado en otra variante → 409
    other = sellable_product(client, admin_headers, name="Bufanda", stock_qty=5)
    dup = client.patch(
        f"/api/v1/variants/{other['variants'][0]['id']}",
        json={"barcode": "7701234567890"},
        headers=admin_headers,
    )
    assert dup.status_code == 409


# ---------- Búsqueda de facturas en servidor ----------


def test_invoice_search_by_number(client, admin_headers, seller_headers, seed_base):
    product = sellable_product(client, admin_headers, name="Gorra", stock_qty=10)
    variant_id = product["variants"][0]["id"]
    for _ in range(3):
        _sell(client, seller_headers, [{"variant_id": variant_id, "quantity": 1, "unit": "unidad"}])

    result = client.get(
        "/api/v1/invoices", headers=admin_headers, params={"q": "FV-000002"}
    ).json()
    assert result["total"] == 1
    assert result["items"][0]["number"] == "FV-000002"

    # También con solo el número
    result = client.get("/api/v1/invoices", headers=admin_headers, params={"q": "3"}).json()
    assert result["total"] == 1
    assert result["items"][0]["number"] == "FV-000003"
