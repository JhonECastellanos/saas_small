import pytest
from fastapi.testclient import TestClient

import app.core.security as security

# pbkdf2 con 600k iteraciones es correcto en producción pero lentísimo para
# cientos de logins de prueba; en tests basta con que el formato sea el mismo.
security.PBKDF2_ITERATIONS = 1000
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_db
from app.core.security import hash_password
from app.main import app
from app.models.base import Base
from app.modules.auth.models import BusinessSettings, User
from app.modules.invoices.models import InvoiceCounter
from app.modules.products.models import Attribute, AttributeValue

# Importar todos los modelos para registrar las tablas
from app.modules.cash import models as _cash  # noqa: F401
from app.modules.inventory import models as _inv  # noqa: F401
from app.modules.pricing import models as _pri  # noqa: F401
from app.modules.purchases import models as _pur  # noqa: F401
from app.modules.sales import models as _sal  # noqa: F401


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seed_base(db_session):
    """Usuarios, configuración, contador de facturas y atributos color/talla."""
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
    db_session.add_all(
        [admin, seller, BusinessSettings(id=1), InvoiceCounter(id=1, last_number=0)]
    )
    db_session.flush()

    color = Attribute(name="Color", code="COL", sort_order=0)
    talla = Attribute(name="Talla", code="TAL", sort_order=1)
    db_session.add_all([color, talla])
    db_session.flush()
    values = {}
    for value, code, attr in [
        ("Rojo", "ROJ", color),
        ("Azul", "AZU", color),
        ("M", "M", talla),
        ("L", "L", talla),
    ]:
        av = AttributeValue(attribute_id=attr.id, value=value, code=code)
        db_session.add(av)
        db_session.flush()
        values[value] = av.id
    db_session.commit()
    return {"admin": admin, "seller": seller, "values": values}


def _login(client, email, password):
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def admin_headers(client, seed_base):
    token = _login(client, "admin@test.co", "admin123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def seller_headers(client, seed_base):
    token = _login(client, "vendedor@test.co", "vende123")
    return {"Authorization": f"Bearer {token}"}
