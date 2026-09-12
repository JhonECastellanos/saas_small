import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Badge, Button, Card, Input, Label, Modal, Select, useToast } from "../../components/ui";
import { api, errorMessage } from "../../lib/api";
import { money, qty as fmtQty } from "../../lib/money";

interface CatalogItem {
  variant_id: number;
  sku: string;
  barcode: string | null;
  product_name: string;
  variant_label: string;
  unit_of_measure: string;
  is_bulk: boolean;
  price: string;
  price_per_lb: string | null;
  tax_rate: string;
  stock: string;
}

interface CartLine {
  item: CatalogItem;
  quantity: string;
  unit: "unidad" | "kg" | "lb";
  discount: string;
}

interface SaleResult {
  id: number;
  invoice_id: number;
  invoice_number: string;
  total: string;
}

function lineTotals(line: CartLine) {
  const quantity = Number(line.quantity) || 0;
  const unitPrice =
    line.unit === "lb" && line.item.price_per_lb
      ? Number(line.item.price_per_lb)
      : Number(line.item.price);
  const discountPct = Math.min(100, Math.max(0, Number(line.discount) || 0));
  const gross = quantity * unitPrice;
  const base = gross * (1 - discountPct / 100);
  const tax = base * Number(line.item.tax_rate);
  return { gross, base, tax, discount: gross - base, total: base + tax, unitPrice };
}

interface Category {
  id: number;
  name: string;
}

interface ProductCreated {
  id: number;
  name: string;
  base_sku: string;
}

export function PosPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const searchRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState("");
  const [cart, setCart] = useState<CartLine[]>([]);
  const [payment, setPayment] = useState("efectivo");
  const [customerName, setCustomerName] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({ name: "", category_id: "", unit_of_measure: "unidad", tax_rate: "" });
  const [createPhoto, setCreatePhoto] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: results, isFetching } = useQuery({
    queryKey: ["catalog", search],
    queryFn: () => api<CatalogItem[]>("/sales/catalog", { params: { q: search, limit: 20 } }),
  });

  const totals = useMemo(() => {
    let base = 0;
    let tax = 0;
    let discount = 0;
    for (const line of cart) {
      const t = lineTotals(line);
      base += t.base;
      tax += t.tax;
      discount += t.discount;
    }
    return { base, tax, discount, total: base + tax };
  }, [cart]);

  const checkout = useMutation({
    mutationFn: () =>
      api<SaleResult>("/sales", {
        method: "POST",
        body: {
          payment_method: payment,
          customer_name: customerName.trim() || null,
          customer_id_number: customerId.trim() || null,
          items: cart.map((line) => ({
            variant_id: line.item.variant_id,
            quantity: Number(line.quantity),
            unit: line.unit,
            discount_pct: Math.min(100, Math.max(0, Number(line.discount) || 0)),
          })),
        },
      }),
    onSuccess: (sale) => {
      queryClient.invalidateQueries({ queryKey: ["catalog"] });
      queryClient.invalidateQueries({ queryKey: ["stock"] });
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      setCart([]);
      setCustomerName("");
      setCustomerId("");
      toast.success(`Venta registrada · Factura ${sale.invoice_number}`);
      navigate(`/invoices/${sale.invoice_id}/print`);
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  function addToCart(item: CatalogItem) {
    setCart((prev) => {
      const existing = prev.find((l) => l.item.variant_id === item.variant_id);
      if (existing) {
        if (!item.is_bulk) {
          return prev.map((l) =>
            l.item.variant_id === item.variant_id
              ? { ...l, quantity: String((Number(l.quantity) || 0) + 1) }
              : l,
          );
        }
        return prev;
      }
      return [
        ...prev,
        {
          item,
          quantity: item.is_bulk ? "" : "1",
          unit: item.is_bulk ? "kg" : "unidad",
          discount: "",
        },
      ];
    });
    searchRef.current?.focus();
    searchRef.current?.select();
  }

  /** Lector de código de barras: escanea (escribe + Enter) y agrega directo. */
  function onSearchEnter(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key !== "Enter" || !search.trim() || !results) return;
    e.preventDefault();
    const term = search.trim();
    const exact = results.find(
      (r) => r.barcode === term || r.sku.toUpperCase() === term.toUpperCase(),
    );
    const target = exact ?? (results.length === 1 ? results[0] : undefined);
    if (target && Number(target.stock) > 0) {
      addToCart(target);
      setSearch("");
    }
  }

  function updateLine(variantId: number, patch: Partial<CartLine>) {
    setCart((prev) =>
      prev.map((line) => (line.item.variant_id === variantId ? { ...line, ...patch } : line)),
    );
  }

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => api<Category[]>("/categories"),
  });

  const createProduct = useMutation({
    mutationFn: () =>
      api<ProductCreated>("/products", {
        method: "POST",
        body: {
          name: createForm.name,
          category_id: createForm.category_id ? Number(createForm.category_id) : null,
          unit_of_measure: createForm.unit_of_measure,
          tax_rate: createForm.tax_rate ? Number(createForm.tax_rate) : null,
        },
      }),
    onSuccess: async (product) => {
      if (createPhoto) {
        const formData = new FormData();
        formData.append("file", createPhoto);
        try {
          await api(`/products/${product.id}/photo`, { method: "POST", body: formData, formData: true });
        } catch {
          toast.error("Producto creado, pero falló la subida de la foto");
        }
      }
      queryClient.invalidateQueries({ queryKey: ["catalog"] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
      toast.success(`Producto "${product.name}" creado`);
      setShowCreateModal(false);
      setCreateForm({ name: "", category_id: "", unit_of_measure: "unidad", tax_rate: "" });
      setCreatePhoto(null);
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const cartValid = cart.length > 0 && cart.every((line) => Number(line.quantity) > 0);

  return (
    <div className="grid h-[calc(100vh-3rem)] grid-cols-1 gap-4 lg:grid-cols-5">
      {/* Buscador y resultados */}
      <div className="flex min-h-0 flex-col lg:col-span-3">
        <div className="mb-3 flex items-center gap-2">
          <Input
            ref={searchRef}
            placeholder="🔍 Buscar por nombre, código o escanear código de barras…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={onSearchEnter}
            className="flex-1 py-3 text-base shadow"
            autoFocus
          />
          <Button variant="secondary" onClick={() => setShowCreateModal(true)} className="shrink-0">
            + Producto
          </Button>
        </div>
        <Card className="min-h-0 flex-1 overflow-y-auto">
          {isFetching && results === undefined ? (
            <p className="p-6 text-center text-sm text-slate-500">Cargando catálogo…</p>
          ) : results && results.length === 0 ? (
            <p className="p-6 text-center text-sm text-slate-500">
              {search
                ? "Sin resultados. Verifica que el producto tenga precio publicado."
                : "No hay productos publicados para la venta."}
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-2 p-3 sm:grid-cols-2 xl:grid-cols-3">
              {results?.map((item) => {
                const outOfStock = Number(item.stock) <= 0;
                return (
                  <button
                    key={item.variant_id}
                    onClick={() => !outOfStock && addToCart(item)}
                    disabled={outOfStock}
                    className={`rounded-xl border p-3 text-left transition-all ${
                      outOfStock
                        ? "cursor-not-allowed border-slate-200 bg-slate-50 opacity-60"
                        : "border-slate-200 bg-white hover:border-indigo-400 hover:shadow-md active:scale-[0.98]"
                    }`}
                  >
                    <p className="font-medium leading-tight text-slate-800">{item.product_name}</p>
                    {item.variant_label && (
                      <p className="text-xs text-slate-500">{item.variant_label}</p>
                    )}
                    <p className="mt-1 font-mono text-[10px] text-slate-400">
                      {item.sku}
                      {item.barcode && ` · ${item.barcode}`}
                    </p>
                    <div className="mt-2 flex items-center justify-between">
                      <span className="font-bold text-indigo-700">
                        {money(item.price)}
                        {item.is_bulk && <span className="text-xs font-normal">/kg</span>}
                      </span>
                      <Badge
                        color={outOfStock ? "red" : Number(item.stock) <= 5 ? "yellow" : "green"}
                      >
                        {outOfStock ? "Agotado" : `${fmtQty(item.stock)}${item.is_bulk ? " kg" : ""}`}
                      </Badge>
                    </div>
                    {item.is_bulk && item.price_per_lb && (
                      <p className="text-xs text-slate-400">{money(item.price_per_lb)}/lb</p>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </Card>
      </div>

      {/* Carrito */}
      <Card className="flex min-h-0 flex-col lg:col-span-2">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="font-semibold text-slate-800">🛒 Carrito ({cart.length})</h2>
          {cart.length > 0 && (
            <Button variant="ghost" onClick={() => setCart([])}>
              Vaciar
            </Button>
          )}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {cart.length === 0 ? (
            <p className="p-6 text-center text-sm text-slate-500">
              Toca un producto o escanea su código para agregarlo.
            </p>
          ) : (
            <div className="divide-y divide-slate-100">
              {cart.map((line) => {
                const t = lineTotals(line);
                return (
                  <div key={line.item.variant_id} className="p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-slate-800">
                          {line.item.product_name}
                          {line.item.variant_label && (
                            <span className="text-slate-400"> · {line.item.variant_label}</span>
                          )}
                        </p>
                        <p className="text-xs text-slate-400">
                          {money(t.unitPrice)} / {line.unit}
                        </p>
                      </div>
                      <button
                        onClick={() =>
                          setCart((prev) =>
                            prev.filter((l) => l.item.variant_id !== line.item.variant_id),
                          )
                        }
                        className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600"
                        aria-label="Quitar del carrito"
                      >
                        ✕
                      </button>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      {!line.item.is_bulk ? (
                        <div className="flex shrink-0 items-center rounded-lg border border-slate-300">
                          <button
                            className="px-2.5 py-1 text-slate-600 hover:bg-slate-100"
                            onClick={() =>
                              updateLine(line.item.variant_id, {
                                quantity: String(Math.max(1, Number(line.quantity) - 1)),
                              })
                            }
                          >
                            −
                          </button>
                          <span className="w-8 text-center text-sm font-medium">
                            {line.quantity}
                          </span>
                          <button
                            className="px-2.5 py-1 text-slate-600 hover:bg-slate-100"
                            onClick={() =>
                              updateLine(line.item.variant_id, {
                                quantity: String(Number(line.quantity) + 1),
                              })
                            }
                          >
                            +
                          </button>
                        </div>
                      ) : (
                        <div className="flex shrink-0 items-center gap-1.5">
                          <Input
                            type="number"
                            min="0"
                            step="0.001"
                            value={line.quantity}
                            onChange={(e) =>
                              updateLine(line.item.variant_id, { quantity: e.target.value })
                            }
                            className="w-20 sm:w-24"
                            placeholder="Peso"
                            autoFocus
                          />
                          <Select
                            value={line.unit}
                            onChange={(e) =>
                              updateLine(line.item.variant_id, {
                                unit: e.target.value as CartLine["unit"],
                              })
                            }
                            className="w-16 sm:w-20"
                          >
                            <option value="kg">kg</option>
                            {line.item.price_per_lb && <option value="lb">lb</option>}
                          </Select>
                        </div>
                      )}
                      <div className="flex shrink-0 items-center gap-1">
                        <Input
                          type="number"
                          min="0"
                          max="100"
                          step="0.5"
                          value={line.discount}
                          onChange={(e) =>
                            updateLine(line.item.variant_id, { discount: e.target.value })
                          }
                          className="w-14 sm:w-16"
                          placeholder="0"
                          aria-label="Descuento %"
                        />
                        <span className="whitespace-nowrap text-xs text-slate-400">% desc</span>
                      </div>
                      <span className="ml-auto text-sm font-semibold text-slate-800">
                        {money(t.base)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
        <div className="border-t border-slate-200 p-4">
          <div className="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <Input
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              placeholder="Cliente (opcional)"
              aria-label="Nombre del cliente"
            />
            <Input
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              placeholder="Cédula / NIT (opcional)"
              aria-label="Documento del cliente"
            />
          </div>
          <div className="mb-3 space-y-1 text-sm">
            {totals.discount > 0 && (
              <div className="flex justify-between text-emerald-700">
                <span>Descuento</span>
                <span>−{money(totals.discount)}</span>
              </div>
            )}
            <div className="flex justify-between text-slate-600">
              <span>Subtotal</span>
              <span>{money(totals.base)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>IVA</span>
              <span>{money(totals.tax)}</span>
            </div>
            <div className="flex justify-between text-lg font-bold text-slate-900">
              <span>Total</span>
              <span>{money(totals.total)}</span>
            </div>
          </div>
          <div className="mb-3">
            <Select value={payment} onChange={(e) => setPayment(e.target.value)}>
              <option value="efectivo">💵 Efectivo</option>
              <option value="transferencia">📲 Transferencia</option>
              <option value="tarjeta">💳 Tarjeta</option>
            </Select>
          </div>
          <Button
            className="w-full py-3 text-base"
            disabled={!cartValid || checkout.isPending}
            onClick={() => checkout.mutate()}
          >
            {checkout.isPending ? "Procesando…" : `Cobrar ${money(totals.total)}`}
          </Button>
          <p className="mt-2 text-center text-xs text-slate-400">
            El total definitivo lo calcula el servidor al confirmar.
          </p>
        </div>
      </Card>

      <Modal
        open={showCreateModal}
        onClose={() => { setShowCreateModal(false); setCreatePhoto(null); }}
        title="Nuevo producto rápido"
      >
        <form
          onSubmit={(e) => { e.preventDefault(); createProduct.mutate(); }}
          className="space-y-4"
        >
          <div>
            <Label htmlFor="cp-name">Nombre del producto</Label>
            <Input
              id="cp-name"
              value={createForm.name}
              onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="cp-cat">Categoría</Label>
            <Select
              id="cp-cat"
              value={createForm.category_id}
              onChange={(e) => setCreateForm({ ...createForm, category_id: e.target.value })}
            >
              <option value="">Sin categoría</option>
              {categories?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </Select>
          </div>
          <div>
            <Label htmlFor="cp-unit">Unidad de medida</Label>
            <Select
              id="cp-unit"
              value={createForm.unit_of_measure}
              onChange={(e) => setCreateForm({ ...createForm, unit_of_measure: e.target.value })}
            >
              <option value="unidad">Unidad</option>
              <option value="kg">Kilogramo</option>
              <option value="lb">Libra</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="cp-tax">Tasa de IVA (0.0 – 1.0, opcional)</Label>
            <Input
              id="cp-tax"
              type="number"
              min="0"
              max="1"
              step="0.01"
              value={createForm.tax_rate}
              onChange={(e) => setCreateForm({ ...createForm, tax_rate: e.target.value })}
              placeholder="Ej: 0.19"
            />
          </div>
          <div>
            <Label htmlFor="cp-photo">Foto del producto (obligatorio)</Label>
            <Input
              id="cp-photo"
              type="file"
              accept="image/*"
              capture="environment"
              ref={fileRef as React.RefObject<HTMLInputElement>}
              onChange={(e) => setCreatePhoto(e.target.files?.[0] ?? null)}
              required
            />
            {createPhoto && (
              <p className="mt-1 text-xs text-emerald-600">{createPhoto.name} seleccionado</p>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              type="button"
              className="flex-1"
              onClick={() => { setShowCreateModal(false); setCreatePhoto(null); }}
            >
              Cancelar
            </Button>
            <Button type="submit" className="flex-1" disabled={createProduct.isPending}>
              {createProduct.isPending ? "Creando…" : "Crear producto"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
