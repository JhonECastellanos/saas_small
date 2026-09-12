from tests.helpers import create_product


def test_product_with_variant_matrix(client, admin_headers, seed_base):
    v = seed_base["values"]
    combos = [
        {"attribute_value_ids": [v["Rojo"], v["M"]]},
        {"attribute_value_ids": [v["Rojo"], v["L"]]},
        {"attribute_value_ids": [v["Azul"], v["M"]]},
        {"attribute_value_ids": [v["Azul"], v["L"]]},
    ]
    product = create_product(client, admin_headers, name="Camisa", combos=combos)
    assert product["base_sku"] == "CAMISA-001"
    skus = sorted(variant["sku"] for variant in product["variants"])
    assert skus == [
        "CAMISA-001-AZU-L",
        "CAMISA-001-AZU-M",
        "CAMISA-001-ROJ-L",
        "CAMISA-001-ROJ-M",
    ]
    assert len(product["variants"]) == 4


def test_duplicate_combo_rejected(client, admin_headers, seed_base):
    v = seed_base["values"]
    product = create_product(client, admin_headers, name="Camisa", combos=[{"attribute_value_ids": [v["Rojo"], v["M"]]}])
    resp = client.post(
        f"/api/v1/products/{product['id']}/variants",
        json={"variant_combos": [{"attribute_value_ids": [v["M"], v["Rojo"]]}]},  # mismo combo en otro orden
        headers=admin_headers,
    )
    assert resp.status_code == 409


def test_sku_counter_increments_per_prefix(client, admin_headers, seed_base):
    p1 = create_product(client, admin_headers, name="Camisa polo")
    p2 = create_product(client, admin_headers, name="Camisa manga larga")
    p3 = create_product(client, admin_headers, name="Pantalón")
    assert p1["base_sku"] == "CAMISA-001"
    assert p2["base_sku"] == "CAMISA-002"
    assert p3["base_sku"] == "PANTALON-001"


def test_bulk_product_gets_default_variant(client, admin_headers, seed_base):
    product = create_product(client, admin_headers, name="Arroz", unit="kg")
    assert product["is_bulk"] is True
    assert len(product["variants"]) == 1
    assert product["variants"][0]["sku"] == "ARROZ-001"
    assert product["variants"][0]["attributes"] == []


def test_two_values_of_same_attribute_rejected(client, admin_headers, seed_base):
    v = seed_base["values"]
    resp = client.post(
        "/api/v1/products",
        json={"name": "Camisa", "variant_combos": [{"attribute_value_ids": [v["Rojo"], v["Azul"]]}]},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_seller_cannot_create_product(client, seller_headers):
    resp = client.post("/api/v1/products", json={"name": "Hack"}, headers=seller_headers)
    assert resp.status_code == 403
