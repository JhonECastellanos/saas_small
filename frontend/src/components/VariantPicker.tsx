import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../lib/api";
import type { Page, ProductDetail, ProductListItem, Variant } from "../features/products/types";
import { Input, Spinner } from "./ui";

export interface PickedVariant {
  variant: Variant;
  product: ProductDetail;
}

/** Busca un producto por nombre/SKU y permite elegir una de sus variantes. */
export function VariantPicker({ onPick }: { onPick: (picked: PickedVariant) => void }) {
  const [search, setSearch] = useState("");
  const [productId, setProductId] = useState<number | null>(null);

  const { data: results, isFetching } = useQuery({
    queryKey: ["variant-picker", search],
    queryFn: () =>
      api<Page<ProductListItem>>("/products", { params: { q: search, page_size: 8 } }),
    enabled: search.trim().length >= 1,
  });

  const { data: product } = useQuery({
    queryKey: ["product", String(productId)],
    queryFn: () => api<ProductDetail>(`/products/${productId}`),
    enabled: productId !== null,
  });

  return (
    <div className="space-y-2">
      <Input
        placeholder="Buscar producto por nombre o SKU…"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setProductId(null);
        }}
        autoFocus
      />
      {isFetching && <Spinner />}
      {!productId && results && search.trim() && (
        <div className="max-h-48 divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-200">
          {results.items.length === 0 && (
            <p className="p-3 text-sm text-slate-500">Sin resultados</p>
          )}
          {results.items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setProductId(item.id)}
              className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-indigo-50"
            >
              <span>
                {item.name}
                <span className="ml-2 font-mono text-xs text-slate-400">{item.base_sku}</span>
              </span>
              <span className="text-xs text-slate-400">
                {item.variant_count} variante{item.variant_count === 1 ? "" : "s"}
              </span>
            </button>
          ))}
        </div>
      )}
      {product && (
        <div className="max-h-48 divide-y divide-slate-100 overflow-y-auto rounded-lg border border-indigo-200">
          {product.variants
            .filter((v) => v.is_active)
            .map((variant) => (
              <button
                key={variant.id}
                type="button"
                onClick={() => onPick({ variant, product })}
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-indigo-50"
              >
                <span>
                  <span className="font-mono text-xs">{variant.sku}</span>
                  {variant.attributes.length > 0 && (
                    <span className="ml-2 text-slate-500">
                      {variant.attributes.map((a) => a.value).join(" / ")}
                    </span>
                  )}
                </span>
                <span className="text-xs text-slate-400">
                  Stock: {variant.stock ?? "0"}
                  {product.is_bulk ? " kg" : ""}
                </span>
              </button>
            ))}
        </div>
      )}
    </div>
  );
}
