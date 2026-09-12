#!/bin/sh
set -e

echo "=== Ejecutando migraciones ==="
python -m alembic upgrade head

echo "=== Sembrando datos iniciales ==="
python scripts/seed.py

echo "=== Iniciando servidor ==="
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
