def test_login_ok(client, seed_base):
    resp = client.post(
        "/api/v1/auth/login", json={"email": "admin@test.co", "password": "admin123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["role"] == "admin"


def test_login_wrong_password(client, seed_base):
    resp = client.post(
        "/api/v1/auth/login", json={"email": "admin@test.co", "password": "incorrecta"}
    )
    assert resp.status_code == 401


def test_protected_route_requires_token(client, seed_base):
    assert client.get("/api/v1/products").status_code == 401


def test_seller_cannot_access_admin_endpoints(client, seller_headers):
    assert client.get("/api/v1/users", headers=seller_headers).status_code == 403
    assert client.get("/api/v1/purchases", headers=seller_headers).status_code == 403
    assert client.get("/api/v1/pricing", headers=seller_headers).status_code == 403


def test_deactivated_user_is_rejected(client, admin_headers, seed_base, db_session):
    seller = seed_base["seller"]
    resp = client.patch(
        f"/api/v1/users/{seller.id}", json={"is_active": False}, headers=admin_headers
    )
    assert resp.status_code == 200
    login = client.post(
        "/api/v1/auth/login", json={"email": "vendedor@test.co", "password": "vende123"}
    )
    assert login.status_code == 401
