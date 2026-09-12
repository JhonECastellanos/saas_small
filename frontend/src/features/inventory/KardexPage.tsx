import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader } from "../../components/layout";
import {
  Badge,
  Card,
  EmptyState,
  GoBack,
  Input,
  Pagination,
  Select,
  Spinner,
  Td,
  Th,
} from "../../components/ui";
import { api } from "../../lib/api";
import { formatDate, money, qty } from "../../lib/money";
import type { Page } from "../products/types";

interface Movement {
  id: number;
  variant_id: number;
  sku: string;
  product_name: string;
  movement_type: string;
  quantity: string;
  balance_after: string;
  unit_cost: string | null;
  reference_type: string | null;
  reference_id: number | null;
  notes: string | null;
  created_at: string;
}

const typeLabels: Record<string, { label: string; color: string }> = {
  entrada_compra: { label: "Entrada compra", color: "green" },
  salida_venta: { label: "Salida venta", color: "indigo" },
  ajuste: { label: "Ajuste", color: "yellow" },
};

export function KardexPage() {
  const [filters, setFilters] = useState({ movement_type: "", date_from: "", date_to: "" });
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["movements", filters, page],
    queryFn: () =>
      api<Page<Movement>>("/inventory/movements", {
        params: { ...filters, page, page_size: 50 },
      }),
  });

  return (
    <div>
      <PageHeader title={<><GoBack fallback="/inventory" /> Kardex de inventario</>} />
      <Card className="mb-4 flex flex-wrap gap-3 p-3">
        <Select
          value={filters.movement_type}
          onChange={(e) => {
            setFilters({ ...filters, movement_type: e.target.value });
            setPage(1);
          }}
          className="max-w-48"
        >
          <option value="">Todos los movimientos</option>
          <option value="entrada_compra">Entradas por compra</option>
          <option value="salida_venta">Salidas por venta</option>
          <option value="ajuste">Ajustes</option>
        </Select>
        <Input
          type="date"
          value={filters.date_from}
          onChange={(e) => {
            setFilters({ ...filters, date_from: e.target.value });
            setPage(1);
          }}
          className="max-w-40"
        />
        <Input
          type="date"
          value={filters.date_to}
          onChange={(e) => {
            setFilters({ ...filters, date_to: e.target.value });
            setPage(1);
          }}
          className="max-w-40"
        />
      </Card>

      <Card>
        {isLoading ? (
          <Spinner />
        ) : data && data.items.length === 0 ? (
          <EmptyState message="Sin movimientos con esos filtros." />
        ) : (
          <>
            <table className="w-full">
              <thead className="border-b border-slate-200">
                <tr>
                  <Th>Fecha</Th>
                  <Th>Producto</Th>
                  <Th>Tipo</Th>
                  <Th className="text-right">Cantidad</Th>
                  <Th className="text-right">Saldo</Th>
                  <Th className="text-right">Costo</Th>
                  <Th>Referencia</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data?.items.map((movement) => {
                  const type = typeLabels[movement.movement_type] ?? {
                    label: movement.movement_type,
                    color: "gray",
                  };
                  const isNegative = Number(movement.quantity) < 0;
                  return (
                    <tr key={movement.id}>
                      <Td className="whitespace-nowrap text-xs">{formatDate(movement.created_at)}</Td>
                      <Td>
                        {movement.product_name}
                        <span className="block font-mono text-xs text-slate-400">{movement.sku}</span>
                      </Td>
                      <Td>
                        <Badge color={type.color}>{type.label}</Badge>
                      </Td>
                      <Td
                        className={`text-right font-medium ${isNegative ? "text-red-600" : "text-emerald-600"}`}
                      >
                        {isNegative ? "" : "+"}
                        {qty(movement.quantity)}
                      </Td>
                      <Td className="text-right font-semibold">{qty(movement.balance_after)}</Td>
                      <Td className="text-right">{money(movement.unit_cost)}</Td>
                      <Td className="text-xs text-slate-500">
                        {movement.reference_type === "purchase" && `Compra #${movement.reference_id}`}
                        {movement.reference_type === "sale" && `Venta #${movement.reference_id}`}
                        {movement.reference_type === "manual" && "Manual"}
                        {movement.notes && <span className="block">{movement.notes}</span>}
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {data && (
              <Pagination page={page} pageSize={data.page_size} total={data.total} onPage={setPage} />
            )}
          </>
        )}
      </Card>
    </div>
  );
}
