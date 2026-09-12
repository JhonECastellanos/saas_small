from decimal import Decimal

from tests.helpers import create_product, create_purchase, create_supplier, get_stock


def test_purchase_updates_stock_and_kardex(client, admin_headers, seed_base):
    product = create_product(client, admin_headers, name="Gorra")
    variant_id = product["variants"][0]["id"]
    supplier = create_supplier(client, admin_headers)

    create_purchase(
        client,
        admin_headers,
        supplier["id"],
        [{"variant_id": variant_id, "quantity": 10, "unit": "unidad", "unit_cost": 5000}],
    )

    stock = get_stock(client, admin_headers, sku="GORRA")
    assert Decimal(stock[0]["quantity"]) == Decimal("10")

    movements = client.get(
        "/api/v1/inventory/movements",
        headers=admin_headers,
        params={"variant_id": variant_id},
    ).json()["items"]
    assert len(movements) == 1
    assert movements[0]["movement_type"] == "entrada_compra"
    assert Decimal(movements[0]["balance_after"]) == Decimal("10")
    assert Decimal(movements[0]["unit_cost"]) == Decimal("5000.00")


def test_purchase_in_lb_converts_to_kg(client, admin_headers, seed_base):
    product = create_product(client, admin_headers, name="Arroz", unit="kg")
    variant_id = product["variants"][0]["id"]
    supplier = create_supplier(client, admin_headers)

    # 10 lb = 4.536 kg (10 * 0.45359237, redondeado a 3 decimales)
    create_purchase(
        client,
        admin_headers,
        supplier["id"],
        [{"variant_id": variant_id, "quantity": 10, "unit": "lb", "unit_cost": 2000}],
    )
    stock = get_stock(client, admin_headers, sku="ARROZ")
    assert Decimal(stock[0]["quantity"]) == Decimal("4.536")


def test_adjustment_requires_note_and_moves_stock(client, admin_headers, seed_base):
    product = create_product(client, admin_headers, name="Gorra")
    variant_id = product["variants"][0]["id"]
    supplier = create_supplier(client, admin_headers)
    create_purchase(
        client,
        admin_headers,
        supplier["id"],
        [{"variant_id": variant_id, "quantity": 10, "unit": "unidad", "unit_cost": 5000}],
    )

    no_note = client.post(
        "/api/v1/inventory/adjustments",
        json={"variant_id": variant_id, "quantity_delta": -2, "notes": ""},
        headers=admin_headers,
    )
    assert no_note.status_code == 422

    resp = client.post(
        "/api/v1/inventory/adjustments",
        json={"variant_id": variant_id, "quantity_delta": -2, "notes": "Merma por daño"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert Decimal(resp.json()["balance_after"]) == Decimal("8")

    negative = client.post(
        "/api/v1/inventory/adjustments",
        json={"variant_id": variant_id, "quantity_delta": -100, "notes": "imposible"},
        headers=admin_headers,
    )
    assert negative.status_code == 409


def test_purchase_history_filters(client, admin_headers, seed_base):
    product = create_product(client, admin_headers, name="Gorra")
    variant_id = product["variants"][0]["id"]
    s1 = create_supplier(client, admin_headers, name="Proveedor A")
    s2 = create_supplier(client, admin_headers, name="Proveedor B")
    create_purchase(
        client,
        admin_headers,
        s1["id"],
        [{"variant_id": variant_id, "quantity": 5, "unit": "unidad", "unit_cost": 100}],
        purchase_date="2026-07-01",
    )
    create_purchase(
        client,
        admin_headers,
        s2["id"],
        [{"variant_id": variant_id, "quantity": 3, "unit": "unidad", "unit_cost": 120}],
        purchase_date="2026-07-15",
    )

    by_supplier = client.get(
        "/api/v1/purchases", headers=admin_headers, params={"supplier_id": s1["id"]}
    ).json()
    assert by_supplier["total"] == 1
    assert by_supplier["items"][0]["supplier_name"] == "Proveedor A"

    by_date = client.get(
        "/api/v1/purchases", headers=admin_headers, params={"date_from": "2026-07-10"}
    ).json()
    assert by_date["total"] == 1
    assert by_date["items"][0]["supplier_name"] == "Proveedor B"
