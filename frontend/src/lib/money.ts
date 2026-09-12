const copFormatter = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

const copWithCents = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** Formatea un monto (string decimal del backend) como COP: $12.500 */
export function money(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "number" ? value : parseFloat(value);
  if (Number.isNaN(num)) return "—";
  // Sin decimales si es entero (uso normal en COP); con centavos si los hay
  return Number.isInteger(num) ? copFormatter.format(num) : copWithCents.format(num);
}

/** Formatea cantidades: enteros sin decimales, granel con hasta 3 decimales. */
export function qty(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "number" ? value : parseFloat(value);
  if (Number.isNaN(num)) return "—";
  return new Intl.NumberFormat("es-CO", { maximumFractionDigits: 3 }).format(num);
}

export function pct(rate: string | number): string {
  const num = typeof rate === "number" ? rate : parseFloat(rate);
  return `${(num * 100).toFixed(num * 100 % 1 === 0 ? 0 : 1)}%`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("es-CO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDateOnly(iso: string): string {
  // Fechas sin hora (purchase_date) vienen como YYYY-MM-DD
  const [y, m, d] = iso.split("T")[0].split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("es-CO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}
