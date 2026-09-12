import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.modules.auth.router import router as auth_router
from app.modules.cash.router import router as cash_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.inventory.router import router as inventory_router
from app.modules.invoices.router import router as invoices_router
from app.modules.pricing.router import router as pricing_router
from app.modules.products.router import router as products_router
from app.modules.returns.router import router as returns_router
from app.modules.purchases.router import router as purchases_router
from app.modules.reports.router import router as reports_router
from app.modules.sales.router import router as sales_router

settings = get_settings()

# En producción no se permite arrancar con el secreto de desarrollo:
# un despliegue sin JWT_SECRET configurado sería un hueco de seguridad silencioso.
if settings.ENV == "production" and settings.JWT_SECRET == "dev-secret-no-usar-en-produccion":
    raise RuntimeError(
        "JWT_SECRET no está configurado. Define la variable de entorno antes de desplegar."
    )

# Monitoreo de errores opcional: se activa solo si SENTRY_DSN está definido.
_sentry_dsn = os.environ.get("SENTRY_DSN")
if _sentry_dsn:
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=_sentry_dsn, environment=settings.ENV, traces_sample_rate=0.1)
    except ImportError:
        pass

app = FastAPI(
    title="Gestión Comercial API",
    version="2.0.0",
    docs_url="/api/docs" if settings.ENV != "production" else None,
    openapi_url="/api/openapi.json" if settings.ENV != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

API_PREFIX = "/api/v1"
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(products_router, prefix=API_PREFIX)
app.include_router(purchases_router, prefix=API_PREFIX)
app.include_router(pricing_router, prefix=API_PREFIX)
app.include_router(inventory_router, prefix=API_PREFIX)
app.include_router(sales_router, prefix=API_PREFIX)
app.include_router(invoices_router, prefix=API_PREFIX)
app.include_router(cash_router, prefix=API_PREFIX)
app.include_router(reports_router, prefix=API_PREFIX)
app.include_router(dashboard_router, prefix=API_PREFIX)
app.include_router(returns_router, prefix=API_PREFIX)

# Servir fotos de productos
_photo_dir = os.environ.get("PRODUCT_PHOTO_DIR", "/app/product_photos")
Path(_photo_dir).mkdir(parents=True, exist_ok=True)
app.mount("/photos", StaticFiles(directory=_photo_dir), name="photos")


@app.get("/api/health")
def health():
    return {"status": "ok", "env": settings.ENV}
