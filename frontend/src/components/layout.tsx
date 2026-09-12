import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useWebSocket } from "../hooks/useWebSocket";

const adminLinks = [
  { to: "/", label: "Dashboard", icon: "📊" },
  { to: "/pos", label: "Punto de venta", icon: "🛒" },
  { to: "/cash", label: "Caja", icon: "🗃️" },
  { to: "/products", label: "Productos", icon: "📦" },
  { to: "/purchases", label: "Compras", icon: "🚚" },
  { to: "/pricing", label: "Precios", icon: "🏷️" },
  { to: "/inventory", label: "Inventario", icon: "📋" },
  { to: "/sales", label: "Ventas", icon: "💰" },
  { to: "/invoices", label: "Facturas", icon: "🧾" },
  { to: "/reports", label: "Reportes", icon: "📈" },
  { to: "/users", label: "Usuarios", icon: "👥" },
  { to: "/settings", label: "Configuración", icon: "⚙️" },
];

const sellerLinks = [
  { to: "/pos", label: "Punto de venta", icon: "🛒" },
  { to: "/cash", label: "Caja", icon: "🗃️" },
  { to: "/sales", label: "Mis ventas", icon: "💰" },
  { to: "/invoices", label: "Mis facturas", icon: "🧾" },
];

export function ProtectedRoute({ adminOnly = false }: { adminOnly?: boolean }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== "admin") return <Navigate to="/pos" replace />;
  return <Outlet />;
}

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  useWebSocket();
  if (!user) return <Navigate to="/login" replace />;
  const links = user.role === "admin" ? adminLinks : sellerLinks;

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {/* Sidebar escritorio */}
      <aside className="no-print sticky top-0 hidden h-screen w-56 shrink-0 flex-col border-r border-slate-200 bg-white md:flex">
        <div className="flex h-14 items-center gap-2 border-b border-slate-200 px-4">
          <span className="text-xl">🏪</span>
          <span className="text-sm font-bold text-slate-800">
            Gestión Comercial
          </span>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-2">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`
              }
            >
              <span>{link.icon}</span>
              <span>{link.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-200 p-3">
          <p className="truncate text-sm font-medium text-slate-800">{user.full_name}</p>
          <p className="text-xs text-slate-500">
            {user.role === "admin" ? "Administrador" : "Vendedor"}
          </p>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="mt-2 w-full rounded-lg border border-slate-300 px-2 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
          >
            Cerrar sesión
          </button>
        </div>
      </aside>

      {/* Barra superior móvil */}
      <div className="no-print sticky top-0 z-40 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2 md:hidden">
        <div className="flex items-center gap-2">
          <span className="text-xl">🏪</span>
          <span className="text-sm font-bold text-slate-800">Gestión</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">{user.full_name}</span>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="rounded-lg border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
          >
            Salir
          </button>
        </div>
      </div>

      {/* Navegación inferior móvil */}
      <nav className="no-print fixed bottom-0 left-0 right-0 z-40 flex justify-around border-t border-slate-200 bg-white md:hidden">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 px-2 py-1.5 text-[10px] font-medium transition-colors ${
                isActive
                  ? "text-indigo-700"
                  : "text-slate-500 hover:text-slate-800"
              }`
            }
          >
            <span className="text-lg">{link.icon}</span>
            <span>{link.label}</span>
          </NavLink>
        ))}
      </nav>

      <main className="min-w-0 flex-1 p-4 pb-20 md:p-6 md:pb-6">
        <Outlet />
      </main>
    </div>
  );
}

export function PageHeader({
  title,
  actions,
}: {
  title: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
      <h1 className="flex items-center gap-2 text-xl font-bold text-slate-900">{title}</h1>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  );
}
