import { createBrowserRouter } from "react-router-dom";
import { AppShell, ProtectedRoute } from "./components/layout";
import { LoginPage } from "./features/auth/LoginPage";
import { UsersPage } from "./features/auth/UsersPage";
import { CashPage } from "./features/cash/CashPage";
import { DashboardPage } from "./features/dashboard/DashboardPage";
import { ReportsPage } from "./features/reports/ReportsPage";
import { KardexPage } from "./features/inventory/KardexPage";
import { StockPage } from "./features/inventory/StockPage";
import { InvoicePrintPage } from "./features/invoices/InvoicePrintPage";
import { InvoicesPage } from "./features/invoices/InvoicesPage";
import { PricingPage } from "./features/pricing/PricingPage";
import { AttributesPage } from "./features/products/AttributesPage";
import { ProductDetailPage } from "./features/products/ProductDetailPage";
import { ProductsPage } from "./features/products/ProductsPage";
import { PurchaseFormPage } from "./features/purchases/PurchaseFormPage";
import { PurchasesPage } from "./features/purchases/PurchasesPage";
import { SuppliersPage } from "./features/purchases/SuppliersPage";
import { PosPage } from "./features/sales/PosPage";
import { SalesHistoryPage } from "./features/sales/SalesHistoryPage";
import { SettingsPage } from "./features/settings/SettingsPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/pos", element: <PosPage /> },
          { path: "/sales", element: <SalesHistoryPage /> },
          { path: "/invoices", element: <InvoicesPage /> },
          { path: "/cash", element: <CashPage /> },
          {
            element: <ProtectedRoute adminOnly />,
            children: [
              { path: "/", element: <DashboardPage /> },
              { path: "/products", element: <ProductsPage /> },
              { path: "/products/:id", element: <ProductDetailPage /> },
              { path: "/products/attributes", element: <AttributesPage /> },
              { path: "/purchases", element: <PurchasesPage /> },
              { path: "/purchases/new", element: <PurchaseFormPage /> },
              { path: "/purchases/suppliers", element: <SuppliersPage /> },
              { path: "/pricing", element: <PricingPage /> },
              { path: "/inventory", element: <StockPage /> },
              { path: "/inventory/kardex", element: <KardexPage /> },
              { path: "/reports", element: <ReportsPage /> },
              { path: "/users", element: <UsersPage /> },
              { path: "/settings", element: <SettingsPage /> },
            ],
          },
        ],
      },
      // La factura imprimible va fuera del AppShell (página limpia para imprimir)
      { path: "/invoices/:id/print", element: <InvoicePrintPage /> },
    ],
  },
]);
