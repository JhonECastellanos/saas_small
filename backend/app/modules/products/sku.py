"""Generación de SKU: prefijo derivado del nombre + contador atómico en BD."""

import re
import unicodedata

from sqlalchemy import insert, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.products.models import SkuCounter


def derive_prefix(name: str) -> str:
    """'Camisa manga larga' -> 'CAMISA'. Sin tildes, solo A-Z0-9, máx 12 chars."""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    first_word = normalized.strip().split()[0] if normalized.strip() else "PROD"
    prefix = re.sub(r"[^A-Za-z0-9]", "", first_word).upper()[:12]
    return prefix or "PROD"


def next_number(db: Session, prefix: str) -> int:
    """Incremento atómico serverless-safe: UPDATE ... RETURNING dentro de la
    transacción actual; el row-lock serializa generaciones concurrentes."""
    stmt = (
        update(SkuCounter)
        .where(SkuCounter.prefix == prefix)
        .values(last_number=SkuCounter.last_number + 1)
        .returning(SkuCounter.last_number)
    )
    number = db.execute(stmt).scalar()
    if number is None:
        try:
            with db.begin_nested():
                db.execute(insert(SkuCounter).values(prefix=prefix, last_number=0))
        except IntegrityError:
            pass  # otra transacción lo creó primero; el UPDATE siguiente funciona
        number = db.execute(stmt).scalar()
    return number


def next_base_sku(db: Session, name: str) -> str:
    prefix = derive_prefix(name)
    return f"{prefix}-{next_number(db, prefix):03d}"
