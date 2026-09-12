import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Label,
  Modal,
  Pagination,
  Spinner,
  Td,
  Th,
  useToast,
} from "../../components/ui";
import { api, errorMessage } from "../../lib/api";
import { qty } from "../../lib/money";
import type { Page } from "../products/types";

export interface StockItem {
  variant_id: number;
  sku: string;
  product_id: number;
  product_name: string;
  variant_label: string;
  unit_of_measure: string;
  is_bulk: boolean;
  quantity: string;
  low_stock_threshold: string;
  is_low: boolean;
}

export function StockPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [lowOnly, setLowOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [adjusting, setAdjusting] = useState<StockItem | null>(null);
  const [adjustForm, setAdjustForm] = useState({ delta: "", notes: "" });
  const [thresholdItem, setThresholdItem] = useState<StockItem | null>(null);
  const [threshold, setThreshold] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["stock", search, lowOnly, page],
    queryFn: () =>
      api<Page<StockItem>>("/inventory/stock", {
        params: { q: search, low_stock_only: lowOnly, page, page_size: 50 },
      }),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["stock"] });

  const adjust = useMutation({
    mutationFn: () =>
      api("/inventory/adjustments", {
        method: "POST",
        body: {
          variant_id: adjusting!.variant_id,
          quantity_delta: Number(adjustForm.delta),
          notes: adjustForm.notes,
        },
      }),
    onSuccess: () => {
      invalidate();
      toast.success("Ajuste registrado en el kardex");
      setAdjusting(null);
      setAdjustForm({ delta: "", notes: "" });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const saveThreshold = useMutation({
    mutationFn: () =>
      api(`/inventory/stock/${thresholdItem!.variant_id}/threshold`, {
        method: "PATCH",
        body: { low_stock_threshold: threshold === "" ? null : Number(threshold) },
      }),
    onSuccess: () => {
      invalidate();
      toast.success("Umbral actualizado");
      setThresholdItem(null);
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <div>
      <PageHeader
        title="Inventario"
        actions={
          <Link to="/inventory/kardex">
            <Button variant="secondary">Ver kardex</Button>
          </Link>
        }
      />

      <Card className="mb-4 flex flex-wrap items-center gap-3 p-3">
        <Input
          placeholder="Buscar por producto o SKU…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="max-w-xs"
        />
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={lowOnly}
            onChange={(e) => {
              setLowOnly(e.target.checked);
              setPage(1);
            }}
            className="h-4 w-4 rounded border-slate-300 text-indigo-600"
          />
          Solo stock bajo
        </label>
      </Card>

      <Card>
        {isLoading ? (
          <Spinner />
        ) : data && data.items.length === 0 ? (
          <EmptyState message="Sin registros de inventario. El stock aparece al registrar compras." />
        ) : (
          <>
            <div className="overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead className="border-b border-slate-200">
                <tr>
                  <Th>Producto</Th>
                  <Th>SKU</Th>
                  <Th className="text-right">Stock</Th>
                  <Th className="text-right">Umbral</Th>
                  <Th>Alerta</Th>
                  <Th className="text-right">Acciones</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data?.items.map((item) => (
                  <tr key={item.variant_id} className={item.is_low ? "bg-red-50/50" : ""}>
                    <Td className="font-medium whitespace-nowrap">
                      {item.product_name}
                      {item.variant_label && (
                        <span className="text-slate-400"> · {item.variant_label}</span>
                      )}
                    </Td>
                    <Td className="font-mono text-xs whitespace-nowrap">{item.sku}</Td>
                    <Td className="text-right font-semibold whitespace-nowrap">
                      {qty(item.quantity)}
                      {item.is_bulk && <span className="text-xs text-slate-400"> kg</span>}
                    </Td>
                    <Td className="text-right text-slate-500 whitespace-nowrap">{qty(item.low_stock_threshold)}</Td>
                    <Td className="whitespace-nowrap">
                      {item.is_low ? <Badge color="red">Stock bajo</Badge> : <Badge color="green">OK</Badge>}
                    </Td>
                    <Td className="text-right whitespace-nowrap">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="secondary"
                          onClick={() => {
                            setThresholdItem(item);
                            setThreshold(item.low_stock_threshold);
                          }}
                        >
                          Umbral
                        </Button>
                        <Button variant="secondary" onClick={() => setAdjusting(item)}>
                          Ajustar
                        </Button>
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
        open={adjusting !== null}
        onClose={() => setAdjusting(null)}
        title={`Ajustar stock · ${adjusting?.sku ?? ""}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            adjust.mutate();
          }}
          className="space-y-4"
        >
          <p className="text-sm text-slate-600">
            Stock actual: <strong>{qty(adjusting?.quantity ?? 0)}</strong>
            {adjusting?.is_bulk ? " kg" : ""}
          </p>
          <div>
            <Label htmlFor="adj-delta">Cantidad (positiva suma, negativa resta)</Label>
            <Input
              id="adj-delta"
              type="number"
              step={adjusting?.is_bulk ? "0.001" : "1"}
              value={adjustForm.delta}
              onChange={(e) => setAdjustForm({ ...adjustForm, delta: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="adj-notes">Motivo (obligatorio)</Label>
            <Input
              id="adj-notes"
              value={adjustForm.notes}
              onChange={(e) => setAdjustForm({ ...adjustForm, notes: e.target.value })}
              required
              minLength={3}
              placeholder="Ej. conteo físico, merma, daño…"
            />
          </div>
          <Button type="submit" className="w-full" disabled={adjust.isPending}>
            Registrar ajuste
          </Button>
        </form>
      </Modal>

      <Modal
        open={thresholdItem !== null}
        onClose={() => setThresholdItem(null)}
        title={`Umbral de alerta · ${thresholdItem?.sku ?? ""}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            saveThreshold.mutate();
          }}
          className="space-y-4"
        >
          <div>
            <Label htmlFor="th-value">Alertar cuando el stock sea ≤</Label>
            <Input
              id="th-value"
              type="number"
              min="0"
              step={thresholdItem?.is_bulk ? "0.001" : "1"}
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
            />
            <p className="mt-1 text-xs text-slate-500">
              Vacío = usar el umbral general configurado en el negocio.
            </p>
          </div>
          <Button type="submit" className="w-full" disabled={saveThreshold.isPending}>
            Guardar
          </Button>
        </form>
      </Modal>
    </div>
  );
}
