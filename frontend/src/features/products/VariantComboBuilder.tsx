import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import type { Attribute } from "./types";

/** Selector de valores por atributo; genera el producto cartesiano de combinaciones. */
export function VariantComboBuilder({
  selected,
  onChange,
}: {
  selected: Record<number, number[]>; // attribute_id -> value_ids
  onChange: (selected: Record<number, number[]>) => void;
}) {
  const { data: attributes } = useQuery({
    queryKey: ["attributes"],
    queryFn: () => api<Attribute[]>("/attributes"),
  });

  function toggle(attributeId: number, valueId: number) {
    const current = selected[attributeId] ?? [];
    const next = current.includes(valueId)
      ? current.filter((id) => id !== valueId)
      : [...current, valueId];
    onChange({ ...selected, [attributeId]: next });
  }

  const comboCount = Object.values(selected)
    .filter((ids) => ids.length > 0)
    .reduce((acc, ids) => acc * ids.length, 1);
  const hasSelection = Object.values(selected).some((ids) => ids.length > 0);

  return (
    <div className="space-y-3">
      {attributes?.map((attribute) => (
        <div key={attribute.id}>
          <p className="mb-1 text-sm font-medium text-slate-700">{attribute.name}</p>
          <div className="flex flex-wrap gap-1.5">
            {attribute.values.map((value) => {
              const active = (selected[attribute.id] ?? []).includes(value.id);
              return (
                <button
                  key={value.id}
                  type="button"
                  onClick={() => toggle(attribute.id, value.id)}
                  className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                    active
                      ? "border-indigo-600 bg-indigo-600 text-white"
                      : "border-slate-300 bg-white text-slate-600 hover:border-indigo-400"
                  }`}
                >
                  {value.value}
                </button>
              );
            })}
            {attribute.values.length === 0 && (
              <span className="text-xs text-slate-400">Sin valores definidos</span>
            )}
          </div>
        </div>
      ))}
      <p className="text-xs text-slate-500">
        {hasSelection
          ? `Se crearán ${comboCount} variante${comboCount === 1 ? "" : "s"} (una por combinación).`
          : "Sin atributos seleccionados: se crea una única variante estándar."}{" "}
        <Link to="/products/attributes" className="text-indigo-600 hover:underline">
          Gestionar atributos
        </Link>
      </p>
    </div>
  );
}

/** Producto cartesiano: {color:[1,2], talla:[3]} -> [{attribute_value_ids:[1,3]}, {attribute_value_ids:[2,3]}] */
export function buildCombos(selected: Record<number, number[]>): { attribute_value_ids: number[] }[] {
  const groups = Object.values(selected).filter((ids) => ids.length > 0);
  if (groups.length === 0) return [];
  return groups.reduce<number[][]>(
    (acc, ids) => acc.flatMap((combo) => ids.map((id) => [...combo, id])),
    [[]],
  ).map((ids) => ({ attribute_value_ids: ids }));
}
