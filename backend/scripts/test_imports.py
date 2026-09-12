import sys
sys.path.insert(0, ".")

from app.models.base import Base
from app.modules.cash.models import CashSession
from app.modules.sales.models import Sale, SaleItem
from app.modules.pricing.models import VariantPrice
from app.modules.products.models import Product, Variant, Attribute, AttributeValue
from app.modules.purchases.models import Purchase, PurchaseItem, Supplier
from app.modules.invoices.models import Invoice, InvoiceCounter
from app.modules.auth.models import User, BusinessSettings
from app.modules.inventory.models import Stock, InventoryMovement

print("All models imported OK")
print("Total tables:", len(Base.metadata.tables))
print("Tables:", sorted(Base.metadata.tables.keys()))
print("cash_sessions:", "cash_sessions" in Base.metadata.tables)

from sqlalchemy import create_engine
engine = create_engine("sqlite://")
Base.metadata.create_all(engine)
print("create_all OK")
