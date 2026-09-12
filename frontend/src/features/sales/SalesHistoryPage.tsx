import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout";
import {
  Badge,
  Button,
  Card,
  ConfirmModal,
  EmptyState,
  Input,
  Pagination,
  Spinner,
  Td,
  Th,
  useToast,
} from "../../components/ui";
import { api, errorMessage } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { formatDate, money } from "../../lib/money";
import type { Page } from "../products/types";

interface SaleListItem {
  id: number;
  status: string;
  seller_name: string;
  payment_method: string;
  total: string;
  created_at: string;
  invoice_id: number | null;
  invoice_number: string | null;
}

const paymentLabels: Record<string, string> = {
  efectivo: "💵 Efectivo",
  transferencia: "📲 Transferencia",
  tarjeta: "💳 Tarjeta",
};

export function SalesHistoryPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [filters, setFilters] = useState({ date_from: "", date_to: "" });
  const [page, setPage] = useState(1);
  const [confirmVoid, setConfirmVoid] = useState<{ id: number; invoice: string } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["sales", filters, page],
    queryFn: () =>
      api<Page<SaleListItem>>("/sales", { params: { ...filters, page, page_size: 20 } }),
  });

  const voidSale = useMutation({
    mutationFn: (saleId: number) => api(`/sales/${saleId}/void`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      queryClient.invalidateQueries({ queryKey: ["stock"] });
      queryClient.invalidateQueries({ queryKey: ["catalog"] });
      toast.success("Venta anulada y stock repuesto");
      setConfirmVoid(null);
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <div>
      <PageHeader title={user?.role === "admin" ? "Ventas" : "Mis ventas"} />
      <Card className="mb-4 flex flex-wrap gap-3 p-3">
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
          <EmptyState message="Sin ventas registradas." />
        ) : (
          <>
            <table className="w-full">
              <thead className="border-b border-slate-200">
                <tr>
                  <Th>Factura</Th>
                  <Th>Fecha</Th>
                  {user?.role === "admin" && <Th>Vendedor</Th>}
                  <Th>Pago</Th>
                  <Th className="text-right">Total</Th>
                  <Th>Estado</Th>
                  <Th className="text-right">Acciones</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data?.items.map((sale) => (
                  <tr key={sale.id} className={sale.status === "anulada" ? "opacity-60" : ""}>
                    <Td className="font-mono text-xs font-medium">{sale.invoice_number ?? "—"}</Td>
                    <Td className="text-xs">{formatDate(sale.created_at)}</Td>
                    {user?.role === "admin" && <Td>{sale.seller_name}</Td>}
                    <Td className="text-xs">{paymentLabels[sale.payment_method]}</Td>
                    <Td className="text-right font-semibold">{money(sale.total)}</Td>
                    <Td>
                      <Badge color={sale.status === "completada" ? "green" : "red"}>
                        {sale.status === "completada" ? "Completada" : "Anulada"}
                      </Badge>
                    </Td>
                    <Td className="text-right">
                      <div className="flex justify-end gap-2">
                        {sale.invoice_id && (
                          <Link to={`/invoices/${sale.invoice_id}/print`}>
                            <Button variant="secondary">🧾 Factura</Button>
                          </Link>
                        )}
                        {user?.role === "admin" && sale.status === "completada" && (
                          <Button
                            variant="danger"
                            onClick={() => setConfirmVoid({ id: sale.id, invoice: sale.invoice_number ?? "" })}
                          >
                            Anular
                          </Button>
                        )}
                      </div>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data && (
              <Pagination page={page} pageSize={data.page_size} total={data.total} onPage={setPage} />
            )}
          </>
        )}
      </Card>

      <ConfirmModal
        open={confirmVoid !== null}
        onClose={() => setConfirmVoid(null)}
        title="Anular venta"
        message={`¿Anular la venta ${confirmVoid?.invoice}? Se repone el stock.`}
        confirmLabel="Anular"
        danger
        loading={voidSale.isPending}
        onConfirm={() => confirmVoid && voidSale.mutate(confirmVoid.id)}
      />
    </div>
  );
}
