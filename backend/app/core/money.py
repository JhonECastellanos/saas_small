"""Única fuente de verdad para Decimal, redondeo y conversión kg/lb.

Reglas:
- Dinero: 2 decimales, ROUND_HALF_UP, siempre Decimal (jamás float).
- Cantidades: 3 decimales.
- El stock de productos a granel se guarda SIEMPRE en la unidad canónica (kg).
- Factor exacto kg/lb para inventario; los precios por lb son editables
  (se sugiere el derivado, pero el comerciante puede redondearlo).
"""

from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")
THREE_PLACES = Decimal("0.001")

KG_PER_LB = Decimal("0.45359237")
LB_PER_KG = Decimal("2.20462262")


def D(value) -> Decimal:
    """Convierte con seguridad a Decimal (vía str para evitar ruido binario de float)."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def q2(value) -> Decimal:
    return D(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def q3(value) -> Decimal:
    return D(value).quantize(THREE_PLACES, rounding=ROUND_HALF_UP)


def lb_to_kg(qty_lb) -> Decimal:
    return q3(D(qty_lb) * KG_PER_LB)


def kg_to_lb(qty_kg) -> Decimal:
    return q3(D(qty_kg) * LB_PER_KG)


def suggested_price_per_lb(price_per_kg) -> Decimal:
    return q2(D(price_per_kg) * KG_PER_LB)
