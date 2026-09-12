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
  Modal,
  Pagination,
  Select,
  Spinner,
  Td,
  Th,
  useToast,
} from "../../components/ui";
import { api, errorMessage } from "../../lib/api";
import { formatDateOnly, money, qty } from "../../lib/money";
import type { Page } from "../products/types";
import type { Supplier } from "./SuppliersPage";

interface PurchaseListItem {
  id: number;
  supplier_name: string;
  purchase_date: string;
  status: string;
  total_cost: string;
  item_count: number;
  created_at: string;
}

interface PurchaseDetail {
  id: number;
  supplier_name: string;
  purchase_date: string;
  notes: string | null;
  total_cost: string;
  items: {
    id: number;
    sku: string;
    product_name: string;
    variant_label: string;
    input_quantity: string;
    input_unit: string;
    quantity: string;
    unit_cost: string;
    line_total: string;
  }[];
}

export function PurchasesPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [filters, setFilters] = useState({ supplier_id: "", date_from: "", date_to: "" });
  const [page, setPage] = useState(1);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [confirmVoid, setConfirmVoid] = useState<number | null>(null);

  const voidPurchase = useMutation({
    mutationFn: (purchaseId: number) =>
      api(`/purchases/${purchaseId}/void`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchases"] });
      queryClient.invalidateQueries({ queryKey: ["stock"] });
      toast.success("Compra anulada y stock revertido");
      setConfirmVoid(null);
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const { data: suppliers } = useQuery({
    queryKey: ["suppliers"],
    queryFn: () => api<Supplier[]>("/suppliers"),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["purchases", filters, page],
    queryFn: () =>
      api<Page<PurchaseListItem>>("/purchases", { params: { ...filters, page, page_size: 20 } }),
  });

  const { data: detail } = useQuery({
    queryKey: ["purchase", detailId],
    queryFn: () => api<PurchaseDetail>(`/purchases/${detailId}`),
    enabled: detailId !== null,
  });

  return (
    <div>
      <PageHeader
        title="Compras"
        actions={
          <>
            <Link to="/purchases/suppliers">
              <Button variant="secondary">Proveedores</Button>
            </Link>
            <Link to="/purchases/new">
              <Button>+ Registrar compra</Button>
            </Link>
          </>
        }
      />

      <Card className="mb-4 flex flex-wrap items-end gap-3 p-3">
        <div className="w-56">
          <Select
            value={filters.supplier_id}
            onChange={(e) => {
              setFilters({ ...filters, supplier_id: e.target.value });
              setPage(1);
            }}
          >
            <option value="">Todos los proveedores</option>
            {suppliers?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </div>
        <Input
          type="date"
          value={filters.date_from}
          onChange={(e) => {
            setFilters({ ...filters, date_from: e.target.value });
            setPage(1);
          }}
          className="max-w-40"
          aria-label="Desde"
        />
        <Input
          type="date"
          value={filters.date_to}
          onChange={(e) => {
            setFilters({ ...filters, date_to: e.target.value });
            setPage(1);
          }}
          className="max-w-40"
          aria-label="Hasta"
        />
      </Card>

      <Card>
        {isLoading ? (
          <Spinner />
        ) : data && data.items.length === 0 ? (
          <EmptyState message="No hay compras con esos filtros." />
        ) : (
          <>
            <div className="overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead className="border-b border-slate-200">
                <tr>
                  <Th>#</Th>
                  <Th>Proveedor</Th>
                  <Th>Fecha</Th>
                  <Th>Estado</Th>
                  <Th className="text-center">Ítems</Th>
                  <Th className="text-right">Total</Th>
                  <Th />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data?.items.map((purchase) => (
                  <tr
                    key={purchase.id}
                    className={purchase.status === "anulada" ? "opacity-60" : "hover:bg-slate-50"}
                  >
                    <Td className="whitespace-nowrap">{purchase.id}</Td>
                    <Td className="font-medium whitespace-nowrap">{purchase.supplier_name}</Td>
                    <Td className="whitespace-nowrap">{formatDateOnly(purchase.purchase_date)}</Td>
                    <Td className="whitespace-nowrap">
                      <Badge color={purchase.status === "completada" ? "green" : "red"}>
                        {purchase.status === "completada" ? "Completada" : "Anulada"}
                      </Badge>
                    </Td>
                    <Td className="text-center whitespace-nowrap">{purchase.item_count}</Td>
                    <Td className="text-right font-medium whitespace-nowrap">{money(purchase.total_cost)}</Td>
                    <Td className="text-right whitespace-nowrap">
                      <div className="flex justify-end gap-2">
                        <Button variant="secondary" onClick={() => setDetailId(purchase.id)}>
                          Ver detalle
                        </Button>
                        {purchase.status === "completada" && (
                          <Button
                            variant="danger"
                            onClick={() => setConfirmVoid(purchase.id)}
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
            </div>
            {data && (
              <Pagination page={page} pageSize={data.page_size} total={data.total} onPage={setPage} />
            )}
          </>
        )}
      </Card>

      <Modal
        open={detailId !== null}
        onClose={() => setDetailId(null)}
        title={`Compra #${detailId ?? ""}`}
        wide
      >
        {!detail ? (
          <Spinner />
        ) : (
          <div>
            <p className="mb-3 text-sm text-slate-600">
              <strong>{detail.supplier_name}</strong> · {formatDateOnly(detail.purchase_date)}
              {detail.notes && <span className="block text-slate-400">{detail.notes}</span>}
            </p>
            <div className="overflow-x-auto">
            <table className="w-full min-w-[450px]">
              <thead className="border-b border-slate-200">
                <tr>
                  <Th>Producto</Th>
                  <Th className="text-right">Cantidad</Th>
                  <Th className="text-right">Costo unit.</Th>
                  <Th className="text-right">Total</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {detail.items.map((item) => (
                  <tr key={item.id}>
                    <Td className="whitespace-nowrap">
                      {item.product_name}
                      {item.variant_label && (
                        <span className="text-slate-400"> · {item.variant_label}</span>
                      )}
                      <span className="block font-mono text-xs text-slate-400">{item.sku}</span>
                    </Td>
                    <Td className="text-right whitespace-nowrap">
                      {qty(item.input_quantity)} {item.input_unit}
                      {item.input_unit === "lb" && (
                        <span className="block text-xs text-slate-400">
                          = {qty(item.quantity)} kg
                        </span>
                      )}
                    </Td>
                    <Td className="text-right whitespace-nowrap">{money(item.unit_cost)}</Td>
                    <Td className="text-right whitespace-nowrap">{money(item.line_total)}</Td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-slate-200">
                  <td colSpan={3} className="px-4 py-2.5 text-sm font-semibold text-slate-700 whitespace-nowrap">
                    Total
                  </td>
                  <td className="px-4 py-2.5 text-right text-sm font-semibold text-slate-700 whitespace-nowrap">
                    {money(detail.total_cost)}
                  </td>
                </tr>
              </tfoot>
            </table>
            </div>
          </div>
        )}
      </Modal>

      <ConfirmModal
        open={confirmVoid !== null}
        onClose={() => setConfirmVoid(null)}
        title="Anular compra"
        message={`¿Anular la compra #${confirmVoid}? Se descuenta del inventario lo que entró con ella.`}
        confirmLabel="Anular"
        danger
        loading={voidPurchase.isPending}
        onConfirm={() => confirmVoid && voidPurchase.mutate(confirmVoid)}
      />
    </div>
  );
}
