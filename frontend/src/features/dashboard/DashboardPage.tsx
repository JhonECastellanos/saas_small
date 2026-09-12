import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout";
import { Badge, Card, CardSkeleton, Skeleton, Spinner, TableSkeleton, Td, Th } from "../../components/ui";
import { api } from "../../lib/api";
import { formatDateOnly, money, qty } from "../../lib/money";

interface Summary {
  sales_today_count: number;
  sales_today_total: string;
  sales_month_total: string;
  sales_year_total: string;
  purchases_month_total: string;
  purchases_year_total: string;
  low_stock_count: number;
  low_stock_items: {
    variant_id: number;
    sku: string;
    product_name: string;
    variant_label: string;
    quantity: string;
    low_stock_threshold: string;
    unit_of_measure: string;
  }[];
  recent_purchases: {
    id: number;
    supplier_name: string;
    purchase_date: string;
    total_cost: string;
    item_count: number;
  }[];
}

function Stat({ label, value, accent, index = 0 }: { label: string; value: string; accent?: boolean; index?: number }) {
  return (
    <Card className="animate-fade-in p-5" style={{ animationDelay: `${index * 80}ms` }}>
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${accent ? "text-indigo-600" : "text-slate-900"}`}>
        {value}
      </p>
    </Card>
  );
}

export function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api<Summary>("/dashboard/summary"),
  });

  if (isLoading || !data) {
    return (
      <div>
        <PageHeader title="Dashboard" />
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
          {Array.from({ length: 7 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card className="p-4"><TableSkeleton rows={4} /></Card>
          <Card className="p-4"><TableSkeleton rows={4} /></Card>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Dashboard" />
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
        <Stat index={0} label="Ventas de hoy" value={String(data.sales_today_count)} />
        <Stat index={1} label="Total vendido hoy" value={money(data.sales_today_total)} accent />
        <Stat index={2} label="Stock bajo" value={String(data.low_stock_count)} />
        <Stat index={3} label="Ventas del mes" value={money(data.sales_month_total)} accent />
        <Stat index={4} label="Ventas del año" value={money(data.sales_year_total)} accent />
        <Stat index={5} label="Compras del mes" value={money(data.purchases_month_total)} />
        <Stat index={6} label="Compras del año" value={money(data.purchases_year_total)} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <h2 className="font-semibold text-slate-800">Stock bajo</h2>
            <Link to="/inventory" className="text-sm text-indigo-600 hover:underline">
              Ver inventario
            </Link>
          </div>
          {data.low_stock_items.length === 0 ? (
            <p className="p-6 text-center text-sm text-slate-500">Sin alertas de stock</p>
          ) : (
            <table className="w-full">
              <thead>
                <tr>
                  <Th>Producto</Th>
                  <Th>SKU</Th>
                  <Th className="text-right">Stock</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.low_stock_items.map((item) => (
                  <tr key={item.variant_id}>
                    <Td>
                      {item.product_name}
                      {item.variant_label && (
                        <span className="text-slate-400"> · {item.variant_label}</span>
                      )}
                    </Td>
                    <Td className="font-mono text-xs">{item.sku}</Td>
                    <Td className="text-right">
                      <Badge color="red">
                        {qty(item.quantity)} {item.unit_of_measure !== "unidad" && "kg"}
                      </Badge>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card>
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <h2 className="font-semibold text-slate-800">Últimas compras</h2>
            <Link to="/purchases" className="text-sm text-indigo-600 hover:underline">
              Ver compras
            </Link>
          </div>
          {data.recent_purchases.length === 0 ? (
            <p className="p-6 text-center text-sm text-slate-500">Aún no hay compras</p>
          ) : (
            <table className="w-full">
              <thead>
                <tr>
                  <Th>Proveedor</Th>
                  <Th>Fecha</Th>
                  <Th className="text-right">Total</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.recent_purchases.map((purchase) => (
                  <tr key={purchase.id}>
                    <Td>{purchase.supplier_name}</Td>
                    <Td>{formatDateOnly(purchase.purchase_date)}</Td>
                    <Td className="text-right font-medium">{money(purchase.total_cost)}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}
