"""Configuración de Alembic.

Orden de resolución de la URL de base de datos:
  1. DIRECT_DATABASE_URL  (conexión directa a Supabase, puerto 5432 — recomendada
     para DDL; nunca migrar a través del pooler transaction-mode)
  2. DATABASE_URL
  3. SQLite local de desarrollo
"""

import os
import sys

from alembic import context
from sqlalchemy import create_engine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.base import Base  # noqa: E402

# Importar todos los modelos para que Alembic vea el esquema completo
from app.modules.auth import models as _auth  # noqa: E402, F401
from app.modules.cash import models as _cash  # noqa: E402, F401
from app.modules.inventory import models as _inv  # noqa: E402, F401
from app.modules.invoices import models as _invo  # noqa: E402, F401
from app.modules.pricing import models as _pri  # noqa: E402, F401
from app.modules.products import models as _pro  # noqa: E402, F401
from app.modules.purchases import models as _pur  # noqa: E402, F401
from app.modules.sales import models as _sal  # noqa: E402, F401
from app.modules.returns import models as _ret  # noqa: E402, F401

target_metadata = Base.metadata


def _database_url() -> str:
    url = (
        os.environ.get("DIRECT_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or "sqlite:///./dev.db"
    )
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_database_url())
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # necesario para ALTER TABLE en SQLite
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
