import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader } from "../../components/layout";
import { Card, Input, Spinner, Td, Th } from "../../components/ui";
import { api } from "../../lib/api";
import { money, qty } from "../../lib/money";

interface SalesReport {
  totals: {
    sales_count: number;
    subtotal: string;
    discount: string;
    tax: string;
    total: string;
    estimated_cost: string;
    estimated_profit: string;
  };
  by_day: { day: string; count: number; total: string }[];
  by_payment_method: { method: string; count: number; total: string }[];
  top_products: {
    product_id: number;
    name: string;
    sku: string;
    units: string;
    revenue: string;
    cost: string | null;
    profit: string | null;
  }[];
}

const methodLabels: Record<string, string> = {
  efectivo: "💵 Efectivo",
  transferencia: "📲 Transferencia",
  tarjeta: "💳 Tarjeta",
};

function firstDayOfMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <Card className="p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-1 text-xl font-bold ${accent ?? "text-slate-900"}`}>{value}</p>
    </Card>
  );
}

export function ReportsPage() {
  const [dateFrom, setDateFrom] = useState(firstDayOfMonth);
  const [dateTo, setDateTo] = useState(today);

  const { data, isLoading } = useQuery({
    queryKey: ["reports", dateFrom, dateTo],
    queryFn: () =>
      api<SalesReport>("/reports/sales", {
        params: { date_from: dateFrom, date_to: dateTo, top: 15 },
      }),
  });

  return (
    <div>
      <PageHeader title="Reportes de ventas" />
      <Card className="mb-4 flex flex-wrap items-center gap-3 p-3">
        <label className="text-sm text-slate-600">Desde</label>
        <Input
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          className="max-w-40"
        />
        <label className="text-sm text-slate-600">Hasta</label>
        <Input
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          className="max-w-40"
        />
      </Card>

      {isLoading || !data ? (
        <Spinner />
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Stat label="Ventas" value={String(data.totals.sales_count)} />
            <Stat label="Total vendido" value={money(data.totals.total)} accent="text-indigo-600" />
            <Stat label="Descuentos" value={money(data.totals.discount)} />
            <Stat label="Costo estimado" value={money(data.totals.estimated_cost)} />
            <Stat
              label="Utilidad estimada"
              value={money(data.totals.estimated_profit)}
              accent="text-emerald-600"
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <div className="border-b border-slate-200 px-4 py-3">
                <h2 className="font-semibold text-slate-800">Ventas por día</h2>
              </div>
              {data.by_day.length === 0 ? (
                <p className="p-6 text-center text-sm text-slate-500">Sin ventas en el periodo.</p>
              ) : (
                <div className="overflow-x-auto">
                <table className="w-full min-w-[350px]">
                  <thead>
                    <tr>
                      <Th>Día</Th>
                      <Th className="text-right">Ventas</Th>
                      <Th className="text-right">Total</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.by_day.map((row) => (
                      <tr key={row.day}>
                        <Td className="whitespace-nowrap">{row.day}</Td>
                        <Td className="text-right whitespace-nowrap">{row.count}</Td>
                        <Td className="text-right font-medium whitespace-nowrap">{money(row.total)}</Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              )}
            </Card>

            <Card>
              <div className="border-b border-slate-200 px-4 py-3">
                <h2 className="font-semibold text-slate-800">Por método de pago</h2>
              </div>
              {data.by_payment_method.length === 0 ? (
                <p className="p-6 text-center text-sm text-slate-500">Sin ventas en el periodo.</p>
              ) : (
                <div className="overflow-x-auto">
                <table className="w-full min-w-[350px]">
                  <thead>
                    <tr>
                      <Th>Método</Th>
                      <Th className="text-right">Ventas</Th>
                      <Th className="text-right">Total</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.by_payment_method.map((row) => (
                      <tr key={row.method}>
                        <Td className="whitespace-nowrap">{methodLabels[row.method] ?? row.method}</Td>
                        <Td className="text-right whitespace-nowrap">{row.count}</Td>
                        <Td className="text-right font-medium whitespace-nowrap">{money(row.total)}</Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              )}
            </Card>

            <Card className="lg:col-span-2">
              <div className="border-b border-slate-200 px-4 py-3">
                <h2 className="font-semibold text-slate-800">Productos más vendidos</h2>
              </div>
              {data.top_products.length === 0 ? (
                <p className="p-6 text-center text-sm text-slate-500">Sin ventas en el periodo.</p>
              ) : (
                <div className="overflow-x-auto">
                <table className="w-full min-w-[550px]">
                  <thead>
                    <tr>
                      <Th>Producto</Th>
                      <Th>SKU</Th>
                      <Th className="text-right">Cantidad</Th>
                      <Th className="text-right">Ingresos</Th>
                      <Th className="text-right">Costo</Th>
                      <Th className="text-right">Utilidad</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.top_products.map((row) => (
                      <tr key={row.sku}>
                        <Td className="font-medium whitespace-nowrap">{row.name}</Td>
                        <Td className="font-mono text-xs whitespace-nowrap">{row.sku}</Td>
                        <Td className="text-right whitespace-nowrap">{qty(row.units)}</Td>
                        <Td className="text-right whitespace-nowrap">{money(row.revenue)}</Td>
                        <Td className="text-right text-slate-500 whitespace-nowrap">{money(row.cost)}</Td>
                        <Td className="text-right font-medium text-emerald-700 whitespace-nowrap">
                          {money(row.profit)}
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              )}
              <p className="border-t border-slate-100 px-4 py-2 text-xs text-slate-400">
                La utilidad se estima con el último costo de compra vigente al momento de cada
                venta.
              </p>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
