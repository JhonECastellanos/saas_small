import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
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
import { money, pct } from "../../lib/money";
import type { Page } from "../products/types";

interface PriceItem {
  variant_id: number;
  sku: string;
  product_name: string;
  variant_label: string;
  unit_of_measure: string;
  is_bulk: boolean;
  price: string | null;
  price_per_lb: string | null;
  suggested_price_per_lb: string | null;
  margin_percent: string | null;
  last_cost: string | null;
  status: string;
  tax_rate: string;
}

export function PricingPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<PriceItem | null>(null);
  const [form, setForm] = useState({ mode: "price", price: "", margin: "", price_per_lb: "" });

  const { data, isLoading } = useQuery({
    queryKey: ["pricing", search, page],
    queryFn: () =>
      api<Page<PriceItem>>("/pricing", { params: { q: search, page, page_size: 50 } }),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["pricing"] });
    queryClient.invalidateQueries({ queryKey: ["products"] });
    queryClient.invalidateQueries({ queryKey: ["catalog"] });
  };

  const savePrice = useMutation({
    mutationFn: () => {
      const body: Record<string, unknown> = {};
      if (form.mode === "margin" && form.margin !== "") {
        body.margin_percent = Number(form.margin);
      } else if (form.price !== "") {
        body.price = Number(form.price);
      }
      if (editing?.is_bulk && form.price_per_lb !== "") {
        body.price_per_lb = Number(form.price_per_lb);
      }
      return api(`/pricing/variants/${editing!.variant_id}`, { method: "PUT", body });
    },
    onSuccess: () => {
      invalidate();
      toast.success("Precio guardado");
      setEditing(null);
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const togglePublish = useMutation({
    mutationFn: (item: PriceItem) =>
      api(
        `/pricing/variants/${item.variant_id}/${item.status === "publicado" ? "unpublish" : "publish"}`,
        { method: "POST" },
      ),
    onSuccess: (_, item) => {
      invalidate();
      toast.success(
        item.status === "publicado" ? "Precio pasado a borrador" : "Precio publicado: ya se puede vender",
      );
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  function openEdit(item: PriceItem) {
    setEditing(item);
    setForm({
      mode: item.margin_percent ? "margin" : "price",
      price: item.price ?? "",
      margin: item.margin_percent ?? "",
      price_per_lb: item.price_per_lb ?? "",
    });
  }

  return (
    <div>
      <PageHeader title="Precios" />
      <p className="mb-4 text-sm text-slate-500">
        Una variante solo aparece en el punto de venta cuando su precio está{" "}
        <Badge color="green">Publicado</Badge>. Mientras esté en borrador, no se puede vender.
      </p>

      <Card className="mb-4 p-3">
        <Input
          placeholder="Buscar por producto o SKU…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="max-w-xs"
        />
      </Card>

      <Card>
        {isLoading ? (
          <Spinner />
        ) : data && data.items.length === 0 ? (
          <EmptyState message="No hay variantes. Crea productos primero." />
        ) : (
          <>
            <div className="overflow-x-auto">
            <table className="w-full min-w-[650px]">
              <thead className="border-b border-slate-200">
                <tr>
                  <Th>Producto</Th>
                  <Th>SKU</Th>
                  <Th className="text-right">Último costo</Th>
                  <Th className="text-right">Precio</Th>
                  <Th>IVA</Th>
                  <Th>Estado</Th>
                  <Th className="text-right">Acciones</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data?.items.map((item) => (
                  <tr key={item.variant_id} className="hover:bg-slate-50">
                    <Td className="font-medium whitespace-nowrap">
                      {item.product_name}
                      {item.variant_label && (
                        <span className="text-slate-400"> · {item.variant_label}</span>
                      )}
                    </Td>
                    <Td className="font-mono text-xs whitespace-nowrap">{item.sku}</Td>
                    <Td className="text-right whitespace-nowrap">
                      {money(item.last_cost)}
                      {item.is_bulk && item.last_cost && (
                        <span className="text-xs text-slate-400">/kg</span>
                      )}
                    </Td>
                    <Td className="text-right whitespace-nowrap">
                      {money(item.price)}
                      {item.is_bulk && (
                        <span className="block text-xs text-slate-400">
                          {item.price && "por kg"}
                          {item.price_per_lb && ` · ${money(item.price_per_lb)}/lb`}
                        </span>
                      )}
                      {item.margin_percent && (
                        <span className="block text-xs text-emerald-600">
                          margen {item.margin_percent}%
                        </span>
                      )}
                    </Td>
                    <Td className="whitespace-nowrap">{pct(item.tax_rate)}</Td>
                    <Td className="whitespace-nowrap">
                      <Badge color={item.status === "publicado" ? "green" : "yellow"}>
                        {item.status === "publicado" ? "Publicado" : "Borrador"}
                      </Badge>
                    </Td>
                    <Td className="text-right whitespace-nowrap">
                      <div className="flex justify-end gap-2">
                        <Button variant="secondary" onClick={() => openEdit(item)}>
                          Editar
                        </Button>
                        <Button
                          variant={item.status === "publicado" ? "ghost" : "primary"}
                          disabled={item.status !== "publicado" && !item.price}
                          onClick={() => togglePublish.mutate(item)}
                        >
                          {item.status === "publicado" ? "Despublicar" : "Publicar"}
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
        open={editing !== null}
        onClose={() => setEditing(null)}
        title={`Precio · ${editing?.sku ?? ""}`}
      >
        {editing && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              savePrice.mutate();
            }}
            className="space-y-4"
          >
            <div className="flex gap-2">
              <Button
                type="button"
                variant={form.mode === "price" ? "primary" : "secondary"}
                onClick={() => setForm({ ...form, mode: "price" })}
              >
                Precio directo
              </Button>
              <Button
                type="button"
                variant={form.mode === "margin" ? "primary" : "secondary"}
                onClick={() => setForm({ ...form, mode: "margin" })}
                disabled={!editing.last_cost}
                title={!editing.last_cost ? "Requiere costo de compra registrado" : undefined}
              >
                Por margen
              </Button>
            </div>
            {form.mode === "price" ? (
              <div>
                <Label htmlFor="pr-price">
                  Precio de venta {editing.is_bulk ? "por kg" : "por unidad"} (COP)
                </Label>
                <Input
                  id="pr-price"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.price}
                  onChange={(e) => setForm({ ...form, price: e.target.value })}
                  required
                />
              </div>
            ) : (
              <div>
                <Label htmlFor="pr-margin">
                  Margen % sobre el último costo ({money(editing.last_cost)})
                </Label>
                <Input
                  id="pr-margin"
                  type="number"
                  min="0"
                  step="0.1"
                  value={form.margin}
                  onChange={(e) => setForm({ ...form, margin: e.target.value })}
                  required
                />
                {form.margin && editing.last_cost && (
                  <p className="mt-1 text-xs text-slate-500">
                    Precio resultante:{" "}
                    {money(Number(editing.last_cost) * (1 + Number(form.margin) / 100))}
                  </p>
                )}
              </div>
            )}
            {editing.is_bulk && (
              <div>
                <Label htmlFor="pr-lb">Precio por libra (COP)</Label>
                <Input
                  id="pr-lb"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.price_per_lb}
                  onChange={(e) => setForm({ ...form, price_per_lb: e.target.value })}
                  placeholder={
                    editing.suggested_price_per_lb
                      ? `Sugerido: ${editing.suggested_price_per_lb}`
                      : "Se sugiere automáticamente"
                  }
                />
                <p className="mt-1 text-xs text-slate-500">
                  Puedes redondearlo a un precio comercial (ej. $5.000/lb).
                </p>
              </div>
            )}
            <Button type="submit" className="w-full" disabled={savePrice.isPending}>
              Guardar precio
            </Button>
          </form>
        )}
      </Modal>
    </div>
  );
}
