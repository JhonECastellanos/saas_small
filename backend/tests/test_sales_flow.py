from decimal import Decimal

from tests.helpers import get_stock, sellable_product


def _sell(client, headers, items, payment="efectivo"):
    return client.post(
        "/api/v1/sales", json={"payment_method": payment, "items": items}, headers=headers
    )


def test_full_sale_flow(client, admin_headers, seller_headers, seed_base):
    product = sellable_product(
        client, admin_headers, name="Gorra", stock_qty=10, cost=5000, price=10000, tax_rate="0.19"
    )
    variant_id = product["variants"][0]["id"]

    resp = _sell(client, seller_headers, [{"variant_id": variant_id, "quantity": 3, "unit": "unidad"}])
    assert resp.status_code == 201, resp.text
    sale = resp.json()

    # Totales con IVA 19% sobre base 30.000
    assert Decimal(sale["subtotal"]) == Decimal("30000.00")
    assert Decimal(sale["tax_amount"]) == Decimal("5700.00")
    assert Decimal(sale["total"]) == Decimal("35700.00")
    assert sale["invoice_number"] == "FV-000001"

    # Snapshots en la línea
    item = sale["items"][0]
    assert item["sku"] == "GORRA-001"
    assert Decimal(item["unit_price"]) == Decimal("10000.00")
    assert Decimal(item["tax_rate"]) == Decimal("0.19")

    # Stock descontado y kardex con salida
    stock = get_stock(client, admin_headers, sku="GORRA")
    assert Decimal(stock[0]["quantity"]) == Decimal("7")
    movements = client.get(
        "/api/v1/inventory/movements",
        headers=admin_headers,
        params={"variant_id": variant_id, "movement_type": "salida_venta"},
    ).json()["items"]
    assert len(movements) == 1
    assert Decimal(movements[0]["quantity"]) == Decimal("-3")
    assert Decimal(movements[0]["balance_after"]) == Decimal("7")

    # Consecutivo de factura
    resp2 = _sell(client, seller_headers, [{"variant_id": variant_id, "quantity": 1, "unit": "unidad"}])
    assert resp2.json()["invoice_number"] == "FV-000002"


def test_oversell_rolls_back_everything(client, admin_headers, seller_headers, seed_base):
    product = sellable_product(client, admin_headers, name="Gorra", stock_qty=5)
    variant_id = product["variants"][0]["id"]

    resp = _sell(client, seller_headers, [{"variant_id": variant_id, "quantity": 100, "unit": "unidad"}])
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["sku"] == "GORRA-001"
    assert Decimal(detail["available"]) == Decimal("5")

    # Nada cambió: ni stock, ni movimientos de venta, ni facturas
    stock = get_stock(client, admin_headers, sku="GORRA")
    assert Decimal(stock[0]["quantity"]) == Decimal("5")
    movements = client.get(
        "/api/v1/inventory/movements",
        headers=admin_headers,
        params={"variant_id": variant_id, "movement_type": "salida_venta"},
    ).json()["items"]
    assert movements == []
    invoices = client.get("/api/v1/invoices", headers=admin_headers).json()
    assert invoices["total"] == 0


def test_multiline_sale_fails_atomically(client, admin_headers, seller_headers, seed_base):
    """Si la segunda línea no tiene stock, la primera tampoco debe descontarse."""
    p1 = sellable_product(client, admin_headers, name="Gorra", stock_qty=10)
    p2 = sellable_product(client, admin_headers, name="Bufanda", stock_qty=1)
    v1, v2 = p1["variants"][0]["id"], p2["variants"][0]["id"]

    resp = _sell(
        client,
        seller_headers,
        [
            {"variant_id": v1, "quantity": 2, "unit": "unidad"},
            {"variant_id": v2, "quantity": 5, "unit": "unidad"},
        ],
    )
    assert resp.status_code == 409
    assert Decimal(get_stock(client, admin_headers, sku="GORRA")[0]["quantity"]) == Decimal("10")
    assert Decimal(get_stock(client, admin_headers, sku="BUFANDA")[0]["quantity"]) == Decimal("1")


def test_bulk_sale_in_lb_discounts_kg(client, admin_headers, seller_headers, seed_base):
    product = sellable_product(
        client,
        admin_headers,
        name="Arroz",
        unit="kg",
        stock_qty=10,  # 10 kg
        cost=2000,
        price=11000,  # por kg
        price_per_lb=5000,
    )
    variant_id = product["variants"][0]["id"]

    # Venta de 2.5 lb a $5.000/lb = $12.500; descuenta 1.134 kg
    resp = _sell(client, seller_headers, [{"variant_id": variant_id, "quantity": 2.5, "unit": "lb"}])
    assert resp.status_code == 201, resp.text
    sale = resp.json()
    assert Decimal(sale["subtotal"]) == Decimal("12500.00")

    stock = get_stock(client, admin_headers, sku="ARROZ")
    assert Decimal(stock[0]["quantity"]) == Decimal("8.866")  # 10 - 1.134

    # Venta en kg con decimales: 0.250 kg a $11.000/kg = $2.750
    resp2 = _sell(client, seller_headers, [{"variant_id": variant_id, "quantity": 0.25, "unit": "kg"}])
    assert Decimal(resp2.json()["subtotal"]) == Decimal("2750.00")
    stock = get_stock(client, admin_headers, sku="ARROZ")
    assert Decimal(stock[0]["quantity"]) == Decimal("8.616")


def test_fractional_quantity_rejected_for_unit_products(client, admin_headers, seller_headers, seed_base):
    product = sellable_product(client, admin_headers, name="Gorra", stock_qty=10)
    variant_id = product["variants"][0]["id"]
    resp = _sell(client, seller_headers, [{"variant_id": variant_id, "quantity": 1.5, "unit": "unidad"}])
    assert resp.status_code == 422


def test_seller_only_sees_own_sales(client, admin_headers, seller_headers, seed_base):
    product = sellable_product(client, admin_headers, name="Gorra", stock_qty=10)
    variant_id = product["variants"][0]["id"]
    _sell(client, seller_headers, [{"variant_id": variant_id, "quantity": 1, "unit": "unidad"}])
    _sell(client, admin_headers, [{"variant_id": variant_id, "quantity": 1, "unit": "unidad"}])

    seller_sales = client.get("/api/v1/sales", headers=seller_headers).json()
    admin_sales = client.get("/api/v1/sales", headers=admin_headers).json()
    assert seller_sales["total"] == 1
    assert admin_sales["total"] == 2

    admin_sale_id = next(
        s["id"] for s in admin_sales["items"] if s["seller_name"] == "Admin Test"
    )
    assert client.get(f"/api/v1/sales/{admin_sale_id}", headers=seller_headers).status_code == 403


def test_void_sale_restores_stock_admin_only(client, admin_headers, seller_headers, seed_base):
    product = sellable_product(client, admin_headers, name="Gorra", stock_qty=10)
    variant_id = product["variants"][0]["id"]
    sale = _sell(client, seller_headers, [{"variant_id": variant_id, "quantity": 4, "unit": "unidad"}]).json()

    assert (
        client.post(f"/api/v1/sales/{sale['id']}/void", headers=seller_headers).status_code == 403
    )

    resp = client.post(f"/api/v1/sales/{sale['id']}/void", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "anulada"
    stock = get_stock(client, admin_headers, sku="GORRA")
    assert Decimal(stock[0]["quantity"]) == Decimal("10")

    # No se puede anular dos veces
    assert client.post(f"/api/v1/sales/{sale['id']}/void", headers=admin_headers).status_code == 409


def test_invoice_detail_has_business_snapshot_and_breakdown(
    client, admin_headers, seller_headers, seed_base
):
    exempt = sellable_product(client, admin_headers, name="Panela", stock_qty=10, tax_rate="0")
    taxed = sellable_product(client, admin_headers, name="Gorra", stock_qty=10, tax_rate="0.19")

    sale = _sell(
        client,
        seller_headers,
        [
            {"variant_id": exempt["variants"][0]["id"], "quantity": 1, "unit": "unidad"},
            {"variant_id": taxed["variants"][0]["id"], "quantity": 1, "unit": "unidad"},
        ],
    ).json()

    invoice = client.get(f"/api/v1/invoices/{sale['invoice_id']}", headers=seller_headers).json()
    assert invoice["number"] == sale["invoice_number"]
    assert invoice["business_name"]  # snapshot presente
    assert len(invoice["items"]) == 2
    rates = {item["tax_rate"] for item in invoice["tax_breakdown"]}
    assert len(rates) == 2  # desglose por tasa (0% y 19%)
    assert Decimal(invoice["total"]) == Decimal(sale["total"])
