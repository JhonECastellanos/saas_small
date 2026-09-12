"""Helpers de caja negra sobre la API para armar escenarios de prueba."""


def create_product(client, headers, name="Camisa", unit="unidad", combos=None, tax_rate=None):
    payload = {"name": name, "unit_of_measure": unit, "variant_combos": combos or []}
    if tax_rate is not None:
        payload["tax_rate"] = tax_rate
    resp = client.post("/api/v1/products", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_supplier(client, headers, name="Proveedor Uno"):
    resp = client.post("/api/v1/suppliers", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_purchase(client, headers, supplier_id, items, purchase_date="2026-07-01"):
    resp = client.post(
        "/api/v1/purchases",
        json={"supplier_id": supplier_id, "purchase_date": purchase_date, "items": items},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def set_price(client, headers, variant_id, price=None, margin=None, price_per_lb=None):
    payload = {}
    if price is not None:
        payload["price"] = price
    if margin is not None:
        payload["margin_percent"] = margin
    if price_per_lb is not None:
        payload["price_per_lb"] = price_per_lb
    resp = client.put(f"/api/v1/pricing/variants/{variant_id}", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def publish_price(client, headers, variant_id):
    resp = client.post(f"/api/v1/pricing/variants/{variant_id}/publish", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def get_stock(client, headers, sku=None):
    resp = client.get("/api/v1/inventory/stock", headers=headers, params={"q": sku or ""})
    assert resp.status_code == 200, resp.text
    return resp.json()["items"]


def sellable_product(
    client,
    headers,
    name="Camisa",
    unit="unidad",
    combos=None,
    stock_qty=10,
    cost=5000,
    price=10000,
    tax_rate=None,
    price_per_lb=None,
):
    """Producto listo para vender: creado + compra + precio publicado."""
    product = create_product(client, headers, name=name, unit=unit, combos=combos, tax_rate=tax_rate)
    supplier = create_supplier(client, headers, name=f"Prov {name}")
    purchase_unit = "unidad" if unit == "unidad" else "kg"
    for variant in product["variants"]:
        create_purchase(
            client,
            headers,
            supplier["id"],
            [
                {
                    "variant_id": variant["id"],
                    "quantity": stock_qty,
                    "unit": purchase_unit,
                    "unit_cost": cost,
                }
            ],
        )
        set_price(client, headers, variant["id"], price=price, price_per_lb=price_per_lb)
        publish_price(client, headers, variant["id"])
    resp = client.get(f"/api/v1/products/{product['id']}", headers=headers)
    return resp.json()
