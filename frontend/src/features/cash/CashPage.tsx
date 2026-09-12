import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { PageHeader } from "../../components/layout";
import {
  Badge,
  Button,
  Card,
  Input,
  Label,
  Spinner,
  Td,
  Th,
  useToast,
} from "../../components/ui";
import { api, errorMessage } from "../../lib/api";
import { formatDate, money } from "../../lib/money";

interface SessionTotals {
  sales_count: number;
  total_sold: string;
  by_payment_method: Record<string, string>;
}

interface CashSession {
  id: number;
  user_name: string;
  status: string;
  opening_amount: string;
  closing_amount: string | null;
  expected_cash: string | null;
  difference: string | null;
  notes: string | null;
  opened_at: string;
  closed_at: string | null;
  totals: SessionTotals | null;
}

interface SessionPage {
  items: CashSession[];
  total: number;
}

const methodLabels: Record<string, string> = {
  efectivo: "💵 Efectivo",
  transferencia: "📲 Transferencia",
  tarjeta: "💳 Tarjeta",
};

export function CashPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [openingAmount, setOpeningAmount] = useState("");
  const [closingAmount, setClosingAmount] = useState("");
  const [notes, setNotes] = useState("");

  const { data: current, isLoading } = useQuery({
    queryKey: ["cash", "current"],
    queryFn: () => api<CashSession | null>("/cash/current"),
  });

  const { data: settings } = useQuery({
    queryKey: ["business-settings"],
    queryFn: () => api<{ default_opening_amount: string }>("/settings/business"),
  });

  useEffect(() => {
    if (settings && openingAmount === "") {
      const def = Number(settings.default_opening_amount);
      if (def > 0) setOpeningAmount(String(def));
    }
  }, [settings, openingAmount]);

  const { data: history } = useQuery({
    queryKey: ["cash", "history"],
    queryFn: () => api<SessionPage>("/cash/sessions", { params: { page_size: 20 } }),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["cash"] });

  const openSession = useMutation({
    mutationFn: () =>
      api("/cash/open", { method: "POST", body: { opening_amount: Number(openingAmount) } }),
    onSuccess: () => {
      invalidate();
      toast.success("Turno de caja abierto");
      setOpeningAmount("");
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const closeSession = useMutation({
    mutationFn: () =>
      api<CashSession>("/cash/close", {
        method: "POST",
        body: { closing_amount: Number(closingAmount), notes: notes || null },
      }),
    onSuccess: (session) => {
      invalidate();
      const diff = Number(session.difference);
      toast.success(
        diff === 0
          ? "Caja cerrada: cuadre exacto"
          : `Caja cerrada · diferencia ${money(session.difference)}`,
      );
      setClosingAmount("");
      setNotes("");
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  if (isLoading) return <Spinner />;

  return (
    <div>
      <PageHeader title="Caja" />

      {!current ? (
        <Card className="mb-6 max-w-md p-5">
          <h2 className="mb-3 font-semibold text-slate-800">Abrir turno</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              openSession.mutate();
            }}
            className="space-y-3"
          >
            <div>
              <Label htmlFor="cash-open">Base de caja (efectivo inicial)</Label>
              <Input
                id="cash-open"
                type="number"
                min="0"
                step="0.01"
                value={openingAmount}
                onChange={(e) => setOpeningAmount(e.target.value)}
                required
                placeholder="Ej. 50000"
              />
            </div>
            <Button type="submit" disabled={openSession.isPending}>
              Abrir caja
            </Button>
          </form>
        </Card>
      ) : (
        <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Turno abierto</h2>
              <Badge color="green">Desde {formatDate(current.opened_at)}</Badge>
            </div>
            <div className="space-y-1 text-sm text-slate-700">
              <p>
                Base inicial: <strong>{money(current.opening_amount)}</strong>
              </p>
              <p>
                Ventas del turno: <strong>{current.totals?.sales_count ?? 0}</strong> ·{" "}
                <strong>{money(current.totals?.total_sold ?? 0)}</strong>
              </p>
              {current.totals &&
                Object.entries(current.totals.by_payment_method).map(([method, total]) => (
                  <p key={method} className="text-slate-500">
                    {methodLabels[method] ?? method}: {money(total)}
                  </p>
                ))}
              <p className="pt-1 text-slate-500">
                Efectivo esperado en caja:{" "}
                <strong className="text-slate-800">
                  {money(
                    Number(current.opening_amount) +
                      Number(current.totals?.by_payment_method?.efectivo ?? 0),
                  )}
                </strong>
              </p>
            </div>
          </Card>

          <Card className="p-5">
            <h2 className="mb-3 font-semibold text-slate-800">Cerrar turno (arqueo)</h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                closeSession.mutate();
              }}
              className="space-y-3"
            >
              <div>
                <Label htmlFor="cash-close">Efectivo contado al cierre</Label>
                <Input
                  id="cash-close"
                  type="number"
                  min="0"
                  step="0.01"
                  value={closingAmount}
                  onChange={(e) => setClosingAmount(e.target.value)}
                  required
                />
              </div>
              <div>
                <Label htmlFor="cash-notes">Notas (opcional)</Label>
                <Input
                  id="cash-notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Novedades del turno…"
                />
              </div>
              <Button type="submit" variant="danger" disabled={closeSession.isPending}>
                Cerrar caja
              </Button>
            </form>
          </Card>
        </div>
      )}

      <Card>
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="font-semibold text-slate-800">Historial de turnos</h2>
        </div>
        {!history || history.items.length === 0 ? (
          <p className="p-6 text-center text-sm text-slate-500">Sin turnos registrados.</p>
        ) : (
          <table className="w-full">
            <thead className="border-b border-slate-200">
              <tr>
                <Th>Usuario</Th>
                <Th>Apertura</Th>
                <Th>Cierre</Th>
                <Th className="text-right">Base</Th>
                <Th className="text-right">Vendido</Th>
                <Th className="text-right">Esperado</Th>
                <Th className="text-right">Contado</Th>
                <Th className="text-right">Diferencia</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {history.items.map((session) => {
                const diff = session.difference === null ? null : Number(session.difference);
                return (
                  <tr key={session.id}>
                    <Td>{session.user_name}</Td>
                    <Td className="text-xs">{formatDate(session.opened_at)}</Td>
                    <Td className="text-xs">
                      {session.closed_at ? formatDate(session.closed_at) : <Badge color="green">Abierta</Badge>}
                    </Td>
                    <Td className="text-right">{money(session.opening_amount)}</Td>
                    <Td className="text-right">{money(session.totals?.total_sold ?? 0)}</Td>
                    <Td className="text-right">{money(session.expected_cash)}</Td>
                    <Td className="text-right">{money(session.closing_amount)}</Td>
                    <Td className="text-right">
                      {diff === null ? (
                        "—"
                      ) : (
                        <span
                          className={
                            diff === 0
                              ? "text-emerald-600"
                              : diff < 0
                                ? "font-medium text-red-600"
                                : "font-medium text-amber-600"
                          }
                        >
                          {money(session.difference)}
                        </span>
                      )}
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
