import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PageHeader } from "../../components/layout";
import {
  Badge,
  Button,
  Card,
  GoBack,
  Input,
  Label,
  Modal,
  Spinner,
  Td,
  Th,
  useToast,
} from "../../components/ui";
import { api, errorMessage } from "../../lib/api";
import { money, pct, qty } from "../../lib/money";
import { buildCombos, VariantComboBuilder } from "./VariantComboBuilder";
import type { ProductDetail, Variant } from "./types";

export function ProductDetailPage() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [addOpen, setAddOpen] = useState(false);
  const [combos, setCombos] = useState<Record<number, number[]>>({});
  const [barcodeVariant, setBarcodeVariant] = useState<Variant | null>(null);
  const [barcode, setBarcode] = useState("");

  const { data: product, isLoading } = useQuery({
    queryKey: ["product", id],
    queryFn: () => api<ProductDetail>(`/products/${id}`),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["product", id] });
    queryClient.invalidateQueries({ queryKey: ["products"] });
  };

  const toggleProduct = useMutation({
    mutationFn: () =>
      api(`/products/${id}`, { method: "PATCH", body: { is_active: !product?.is_active } }),
    onSuccess: invalidate,
    onError: (err) => toast.error(errorMessage(err)),
  });

  const toggleVariant = useMutation({
    mutationFn: (variant: { id: number; is_active: boolean }) =>
      api(`/variants/${variant.id}`, { method: "PATCH", body: { is_active: !variant.is_active } }),
    onSuccess: invalidate,
    onError: (err) => toast.error(errorMessage(err)),
  });

  const saveBarcode = useMutation({
    mutationFn: () =>
      api(`/variants/${barcodeVariant!.id}`, { method: "PATCH", body: { barcode } }),
    onSuccess: () => {
      invalidate();
      toast.success("Código de barras guardado");
      setBarcodeVariant(null);
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const addVariants = useMutation({
    mutationFn: () =>
      api(`/products/${id}/variants`, {
        method: "POST",
        body: { variant_combos: buildCombos(combos) },
      }),
    onSuccess: () => {
      invalidate();
      toast.success("Variantes agregadas");
      setAddOpen(false);
      setCombos({});
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  if (isLoading || !product) return <Spinner />;

  return (
    <div>
      <PageHeader
        title={<><GoBack fallback="/products" /> {product.name}</>}
        actions={
          <>
            {!product.is_bulk && (
              <Button variant="secondary" onClick={() => setAddOpen(true)}>
                + Agregar variantes
              </Button>
            )}
            <Button
              variant={product.is_active ? "danger" : "primary"}
              onClick={() => toggleProduct.mutate()}
            >
              {product.is_active ? "Desactivar producto" : "Activar producto"}
            </Button>
          </>
        }
      />

      {product.photo_path && (
        <div className="mb-4 overflow-hidden rounded-xl border border-slate-200">
          <img
            src={`/photos/${product.photo_path}`}
            alt={product.name}
            className="mx-auto max-h-64 object-contain"
          />
        </div>
      )}

      <Card className="mb-4 grid grid-cols-2 gap-4 p-4 text-sm sm:grid-cols-4">
        <div>
          <p className="text-slate-500">SKU base</p>
          <p className="font-mono font-medium">{product.base_sku}</p>
        </div>
        <div>
          <p className="text-slate-500">Categoría</p>
          <p className="font-medium">{product.category_name ?? "—"}</p>
        </div>
        <div>
          <p className="text-slate-500">Unidad</p>
          <p className="font-medium capitalize">{product.unit_of_measure}</p>
          <p className="text-xs text-slate-400">
            {product.is_bulk ? "A granel (las variantes pueden tener su propia unidad)" : "Por unidad"}
          </p>
        </div>
        <div>
          <p className="text-slate-500">IVA</p>
          <p className="font-medium">{pct(product.tax_rate)}</p>
        </div>
        {product.description && (
          <div className="col-span-full">
            <p className="text-slate-500">Descripción</p>
            <p>{product.description}</p>
          </div>
        )}
      </Card>

      <Card>
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="font-semibold text-slate-800">Variantes ({product.variants.length})</h2>
        </div>
        <div className="overflow-x-auto">
        <table className="w-full min-w-[650px]">
          <thead className="border-b border-slate-200">
            <tr>
              <Th>SKU</Th>
              <Th>Atributos</Th>
              <Th className="text-right">Precio</Th>
              <Th>Estado precio</Th>
              <Th className="text-right">Stock</Th>
              <Th>Estado</Th>
              <Th className="text-right">Acciones</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {product.variants.map((variant) => (
              <tr key={variant.id}>
                <Td className="font-mono text-xs whitespace-nowrap">
                  {variant.sku}
                  {variant.barcode && (
                    <span className="block text-slate-400">▮ {variant.barcode}</span>
                  )}
                </Td>
                <Td className="whitespace-nowrap">
                  {variant.attributes.length === 0
                    ? "—"
                    : variant.attributes.map((a) => (
                        <span key={a.attribute_id} className="mr-2">
                          <span className="text-slate-400">{a.attribute_name}:</span> {a.value}
                        </span>
                      ))}
                </Td>
                <Td className="text-right whitespace-nowrap">
                  {money(variant.price)}
                  {variant.unit_of_measure !== "unidad" && variant.price_per_lb && (
                    <span className="block text-xs text-slate-400">
                      {money(variant.price_per_lb)}/lb
                    </span>
                  )}
                </Td>
                <Td className="whitespace-nowrap">
                  {variant.price_status === "publicado" ? (
                    <Badge color="green">Publicado</Badge>
                  ) : (
                    <Badge color="yellow">Borrador</Badge>
                  )}
                </Td>
                <Td className="text-right whitespace-nowrap">
                  {variant.stock === null ? "0" : qty(variant.stock)}
                  {variant.unit_of_measure !== "unidad" && <span className="text-xs text-slate-400"> {variant.unit_of_measure}</span>}
                </Td>
                <Td className="whitespace-nowrap">
                  <Badge color={variant.is_active ? "green" : "red"}>
                    {variant.is_active ? "Activa" : "Inactiva"}
                  </Badge>
                </Td>
                <Td className="text-right whitespace-nowrap">
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setBarcodeVariant(variant);
                        setBarcode(variant.barcode ?? "");
                      }}
                    >
                      Código barras
                    </Button>
                    <Button variant="secondary" onClick={() => toggleVariant.mutate(variant)}>
                      {variant.is_active ? "Desactivar" : "Activar"}
                    </Button>
                  </div>
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
        <div className="border-t border-slate-200 px-4 py-3 text-sm text-slate-500">
          Configura los precios en{" "}
          <Link to="/pricing" className="text-indigo-600 hover:underline">
            Precios
          </Link>{" "}
          y registra entradas en{" "}
          <Link to="/purchases/new" className="text-indigo-600 hover:underline">
            Compras
          </Link>
          .
        </div>
      </Card>

      <Modal
        open={barcodeVariant !== null}
        onClose={() => setBarcodeVariant(null)}
        title={`Código de barras · ${barcodeVariant?.sku ?? ""}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            saveBarcode.mutate();
          }}
          className="space-y-4"
        >
          <div>
            <Label htmlFor="bc-input">Código (escanéalo con el lector o escríbelo)</Label>
            <Input
              id="bc-input"
              value={barcode}
              onChange={(e) => setBarcode(e.target.value)}
              placeholder="Ej. 7701234567890"
              autoFocus
            />
            <p className="mt-1 text-xs text-slate-500">
              Déjalo vacío y guarda para quitar el código. En el punto de venta, escanear este
              código agrega el producto directo al carrito.
            </p>
          </div>
          <Button type="submit" className="w-full" disabled={saveBarcode.isPending}>
            Guardar
          </Button>
        </form>
      </Modal>

      <Modal open={addOpen} onClose={() => setAddOpen(false)} title="Agregar variantes" wide>
        <div className="space-y-4">
          <VariantComboBuilder selected={combos} onChange={setCombos} />
          <Button
            className="w-full"
            disabled={buildCombos(combos).length === 0 || addVariants.isPending}
            onClick={() => addVariants.mutate()}
          >
            {addVariants.isPending ? "Agregando…" : "Agregar combinaciones"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
