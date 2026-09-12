import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PageHeader } from "../../components/layout";
import {
  Button,
  Card,
  GoBack,
  Input,
  Label,
  Select,
  Td,
  Th,
  useToast,
} from "../../components/ui";
import { VariantPicker } from "../../components/VariantPicker";
import { api, errorMessage } from "../../lib/api";
import { money } from "../../lib/money";
import type { Supplier } from "./SuppliersPage";

interface Line {
  variant_id: number;
  sku: string;
  label: string;
  is_bulk: boolean;
  quantity: string;
  unit: "unidad" | "kg" | "lb";
  unit_cost: string;
}

export function PurchaseFormPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [supplierId, setSupplierId] = useState("");
  const [purchaseDate, setPurchaseDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<Line[]>([]);

  const { data: suppliers } = useQuery({
    queryKey: ["suppliers"],
    queryFn: () => api<Supplier[]>("/suppliers"),
  });

  const save = useMutation({
    mutationFn: () =>
      api("/purchases", {
        method: "POST",
        body: {
          supplier_id: Number(supplierId),
          purchase_date: purchaseDate,
          notes: notes || null,
          items: lines.map((line) => ({
            variant_id: line.variant_id,
            quantity: Number(line.quantity),
            unit: line.unit,
            unit_cost: Number(line.unit_cost),
          })),
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["purchases"] });
      queryClient.invalidateQueries({ queryKey: ["stock"] });
      queryClient.invalidateQueries({ queryKey: ["pricing"] });
      toast.success("Compra registrada y stock actualizado");
      navigate("/purchases");
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const total = lines.reduce(
    (acc, line) => acc + (Number(line.quantity) || 0) * (Number(line.unit_cost) || 0),
    0,
  );
  const valid =
    supplierId &&
    lines.length > 0 &&
    lines.every((l) => Number(l.quantity) > 0 && Number(l.unit_cost) >= 0);

  function updateLine(index: number, patch: Partial<Line>) {
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  }

  return (
    <div>
      <PageHeader title={<><GoBack fallback="/purchases" /> Registrar compra</>} />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="p-4 lg:col-span-1">
          <div className="space-y-4">
            <div>
              <Label htmlFor="pc-supplier">Proveedor</Label>
              <Select
                id="pc-supplier"
                value={supplierId}
                onChange={(e) => setSupplierId(e.target.value)}
              >
                <option value="">Selecciona…</option>
                {suppliers?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </Select>
              <p className="mt-1 text-xs text-slate-500">
                ¿No está?{" "}
                <Link to="/purchases/suppliers" className="text-indigo-600 hover:underline">
                  Crear proveedor
                </Link>
              </p>
            </div>
            <div>
              <Label htmlFor="pc-date">Fecha de compra</Label>
              <Input
                id="pc-date"
                type="date"
                value={purchaseDate}
                onChange={(e) => setPurchaseDate(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="pc-notes">Notas</Label>
              <Input id="pc-notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
            <div>
              <Label>Agregar producto</Label>
              <VariantPicker
                onPick={({ variant, product }) => {
                  if (lines.some((l) => l.variant_id === variant.id)) {
                    toast.error("Esa variante ya está en la compra");
                    return;
                  }
                  setLines((prev) => [
                    ...prev,
                    {
                      variant_id: variant.id,
                      sku: variant.sku,
                      label:
                        product.name +
                        (variant.attributes.length
                          ? ` · ${variant.attributes.map((a) => a.value).join(" / ")}`
                          : ""),
                      is_bulk: product.is_bulk,
                      quantity: "",
                      unit: product.is_bulk ? "kg" : "unidad",
                      unit_cost: "",
                    },
                  ]);
                }}
              />
            </div>
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <div className="border-b border-slate-200 px-4 py-3">
            <h2 className="font-semibold text-slate-800">Ítems de la compra</h2>
          </div>
          {lines.length === 0 ? (
            <p className="p-8 text-center text-sm text-slate-500">
              Busca un producto a la izquierda para agregarlo.
            </p>
          ) : (
            <table className="w-full">
              <thead className="border-b border-slate-200">
                <tr>
                  <Th>Producto</Th>
                  <Th>Cantidad</Th>
                  <Th>Unidad</Th>
                  <Th>Costo unitario</Th>
                  <Th className="text-right">Subtotal</Th>
                  <Th />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {lines.map((line, index) => (
                  <tr key={line.variant_id}>
                    <Td>
                      {line.label}
                      <span className="block font-mono text-xs text-slate-400">{line.sku}</span>
                    </Td>
                    <Td>
                      <Input
                        type="number"
                        min="0"
                        step={line.is_bulk ? "0.001" : "1"}
                        value={line.quantity}
                        onChange={(e) => updateLine(index, { quantity: e.target.value })}
                        className="w-24"
                      />
                    </Td>
                    <Td>
                      {line.is_bulk ? (
                        <Select
                          value={line.unit}
                          onChange={(e) =>
                            updateLine(index, { unit: e.target.value as Line["unit"] })
                          }
                          className="w-20"
                        >
                          <option value="kg">kg</option>
                          <option value="lb">lb</option>
                        </Select>
                      ) : (
                        "unidad"
                      )}
                    </Td>
                    <Td>
                      <Input
                        type="number"
                        min="0"
                        step="0.01"
                        value={line.unit_cost}
                        onChange={(e) => updateLine(index, { unit_cost: e.target.value })}
                        className="w-28"
                        placeholder={line.is_bulk ? `$ por ${line.unit}` : "$"}
                      />
                    </Td>
                    <Td className="text-right">
                      {money((Number(line.quantity) || 0) * (Number(line.unit_cost) || 0))}
                    </Td>
                    <Td className="text-right">
                      <Button
                        variant="ghost"
                        onClick={() => setLines((prev) => prev.filter((_, i) => i !== index))}
                        aria-label="Quitar"
                      >
                        ✕
                      </Button>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3">
            <p className="text-lg font-semibold text-slate-800">Total: {money(total)}</p>
            <Button disabled={!valid || save.isPending} onClick={() => save.mutate()}>
              {save.isPending ? "Guardando…" : "Confirmar compra"}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
