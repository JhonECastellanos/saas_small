from decimal import Decimal

from tests.helpers import (
    create_product,
    create_purchase,
    create_supplier,
    publish_price,
    set_price,
)


def _catalog_skus(client, headers):
    resp = client.get("/api/v1/sales/catalog", headers=headers)
    assert resp.status_code == 200
    return [item["sku"] for item in resp.json()]


def test_unpriced_variant_not_in_catalog(client, admin_headers, seed_base):
    create_product(client, admin_headers, name="Gorra")
    assert _catalog_skus(client, admin_headers) == []


def test_margin_computes_price_from_last_cost(client, admin_headers, seed_base):
    product = create_product(client, admin_headers, name="Gorra")
    variant_id = product["variants"][0]["id"]
    supplier = create_supplier(client, admin_headers)
    create_purchase(
        client,
        admin_headers,
        supplier["id"],
        [{"variant_id": variant_id, "quantity": 10, "unit": "unidad", "unit_cost": 5000}],
    )
    result = set_price(client, admin_headers, variant_id, margin=30)
    assert Decimal(result["price"]) == Decimal("6500.00")


def test_margin_without_cost_rejected(client, admin_headers, seed_base):
    product = create_product(client, admin_headers, name="Gorra")
    variant_id = product["variants"][0]["id"]
    resp = client.put(
        f"/api/v1/pricing/variants/{variant_id}",
        json={"margin_percent": 30},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_publish_requires_positive_price(client, admin_headers, seed_base):
    product = create_product(client, admin_headers, name="Gorra")
    variant_id = product["variants"][0]["id"]
    resp = client.post(f"/api/v1/pricing/variants/{variant_id}/publish", headers=admin_headers)
    assert resp.status_code == 422


def test_publish_and_unpublish_control_catalog(client, admin_headers, seed_base):
    product = create_product(client, admin_headers, name="Gorra")
    variant_id = product["variants"][0]["id"]
    set_price(client, admin_headers, variant_id, price=10000)
    publish_price(client, admin_headers, variant_id)
    assert "GORRA-001" in _catalog_skus(client, admin_headers)

    client.post(f"/api/v1/pricing/variants/{variant_id}/unpublish", headers=admin_headers)
    assert "GORRA-001" not in _catalog_skus(client, admin_headers)

    sale = client.post(
        "/api/v1/sales",
        json={
            "payment_method": "efectivo",
            "items": [{"variant_id": variant_id, "quantity": 1, "unit": "unidad"}],
        },
        headers=admin_headers,
    )
    assert sale.status_code == 422


def test_bulk_price_suggests_per_lb(client, admin_headers, seed_base):
    product = create_product(client, admin_headers, name="Arroz", unit="kg")
    variant_id = product["variants"][0]["id"]
    result = set_price(client, admin_headers, variant_id, price=11000)
    # 11000 * 0.45359237 = 4989.52 sugerido, editable después
    assert Decimal(result["price_per_lb"]) == Decimal("4989.52")

    result = set_price(client, admin_headers, variant_id, price_per_lb=5000)
    assert Decimal(result["price_per_lb"]) == Decimal("5000.00")
