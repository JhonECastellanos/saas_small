"""Seed inicial: admin, configuración del negocio, contador de facturas y atributos base.

Uso:
  python scripts/seed.py                       # contra DATABASE_URL (SQLite local por defecto)
  DATABASE_URL=postgresql://... python scripts/seed.py   # contra Supabase (usar URL DIRECTA 5432)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.base import Base  # noqa: E402

# Importar todos los modelos para registrarlos en Base.metadata
from app.modules.auth.models import BusinessSettings, User  # noqa: E402
from app.modules.cash import models as _cash  # noqa: E402, F401
from app.modules.inventory import models as _inv  # noqa: E402, F401
from app.modules.invoices.models import InvoiceCounter  # noqa: E402
from app.modules.pricing import models as _pri  # noqa: E402, F401
from app.modules.products.models import Attribute, AttributeValue  # noqa: E402
from app.modules.purchases import models as _pur  # noqa: E402, F401
from app.modules.sales import models as _sal  # noqa: E402, F401
from app.modules.returns import models as _ret  # noqa: E402, F401

ADMIN_EMAIL = os.environ.get("SEED_ADMIN_EMAIL", "admin@negocio.com")
ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "admin123")

BASE_ATTRIBUTES = {
    ("Color", "COL"): [("Rojo", "ROJ"), ("Azul", "AZU"), ("Negro", "NEG"), ("Blanco", "BLA")],
    ("Talla", "TAL"): [("XS", "XS"), ("S", "S"), ("M", "M"), ("L", "L"), ("XL", "XL")],
    ("Sabor", "SAB"): [("Vainilla", "VAI"), ("Chocolate", "CHO"), ("Fresa", "FRE")],
}


def run() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == ADMIN_EMAIL)) is None:
            db.add(
                User(
                    email=ADMIN_EMAIL,
                    password_hash=hash_password(ADMIN_PASSWORD),
                    full_name="Administrador",
                    role="admin",
                )
            )
            print(f"Admin creado: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        if db.get(BusinessSettings, 1) is None:
            db.add(BusinessSettings(id=1))
            print("Configuración de negocio creada (edítala en el panel admin)")
        if db.get(InvoiceCounter, 1) is None:
            db.add(InvoiceCounter(id=1, last_number=0))
            print("Contador de facturas inicializado")
        for order, ((name, code), values) in enumerate(BASE_ATTRIBUTES.items()):
            attr = db.scalar(select(Attribute).where(Attribute.name == name))
            if attr is None:
                attr = Attribute(name=name, code=code, sort_order=order)
                db.add(attr)
                db.flush()
                for value, vcode in values:
                    db.add(AttributeValue(attribute_id=attr.id, value=value, code=vcode))
                print(f"Atributo creado: {name} ({len(values)} valores)")
        db.commit()
        print("Seed completado.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
