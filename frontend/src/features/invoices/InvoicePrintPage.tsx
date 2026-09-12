import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Badge, Button, Input, Modal, Spinner, useToast } from "../../components/ui";
import { api, errorMessage } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { formatDate, money, pct, qty } from "../../lib/money";

interface InvoiceDetail {
  id: number;
  number: string;
  sale_status: string;
  business_name: string;
  business_tax_id: string | null;
  business_address: string | null;
  business_phone: string | null;
  seller_name: string;
  payment_method: string;
  customer_name: string | null;
  customer_id_number: string | null;
  issued_at: string;
  items: {
    id: number;
    description: string;
    sku: string;
    quantity: string;
    unit: string;
    unit_price: string;
    discount_pct: string;
    tax_rate: string;
    line_total: string;
  }[];
  subtotal: string;
  discount_amount: string;
  tax_amount: string;
  total: string;
  tax_breakdown: { tax_rate: string; base: string; tax: string }[];
}

const paymentLabels: Record<string, string> = {
  efectivo: "Efectivo",
  transferencia: "Transferencia",
  tarjeta: "Tarjeta",
};

export function InvoicePrintPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [format, setFormat] = useState<"ticket" | "carta">("ticket");
  const [returnOpen, setReturnOpen] = useState(false);
  const [returnReason, setReturnReason] = useState("");
  const [returnQtys, setReturnQtys] = useState<Record<number, string>>({});

  const { data: invoice, isLoading } = useQuery({
    queryKey: ["invoice", id],
    queryFn: () => api<InvoiceDetail>(`/invoices/${id}`),
  });

  const doReturn = useMutation({
    mutationFn: () =>
      api(`/invoices/${id}/return`, {
        method: "POST",
        body: {
          items: Object.entries(returnQtys)
            .filter(([, q]) => Number(q) > 0)
            .map(([saleItemId, quantity]) => ({
              sale_item_id: Number(saleItemId),
              quantity: Number(quantity),
            })),
          reason: returnReason.trim() || null,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoice", id] });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setReturnOpen(false);
      setReturnQtys({});
      setReturnReason("");
      toast.success("Devolución registrada correctamente");
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  if (isLoading || !invoice) return <Spinner />;

  const isTicket = format === "ticket";

  return (
    <div className={`min-h-screen bg-slate-100 py-6 ${isTicket ? "print-ticket" : ""}`}>
      {/* Barra de acciones (no se imprime) */}
      <div className="no-print mx-auto mb-4 flex max-w-2xl flex-wrap items-center justify-between gap-3 px-4">
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate(-1)}>
            ← Volver
          </Button>
          <Button
            variant="secondary"
            onClick={() => navigate(user?.role === "admin" ? "/pos" : "/pos")}
          >
            Nueva venta
          </Button>
          {user?.role === "admin" && invoice.sale_status !== "anulada" && (
            <Button variant="danger" onClick={() => setReturnOpen(true)}>
              Devolver
            </Button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-slate-300 bg-white p-0.5">
            <button
              onClick={() => setFormat("ticket")}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                isTicket ? "bg-indigo-600 text-white" : "text-slate-600"
              }`}
            >
              Ticket 80mm
            </button>
            <button
              onClick={() => setFormat("carta")}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                !isTicket ? "bg-indigo-600 text-white" : "text-slate-600"
              }`}
            >
              Carta
            </button>
          </div>
          <Button onClick={() => window.print()}>🖨️ Imprimir</Button>
        </div>
      </div>

      {invoice.sale_status === "anulada" && (
        <div className="no-print mx-auto mb-4 max-w-2xl px-4">
          <Badge color="red">⚠️ Esta factura corresponde a una venta ANULADA</Badge>
        </div>
      )}

      {/* Factura */}
      <div
        className={`print-area mx-auto bg-white shadow-lg ${
          isTicket ? "max-w-xs p-4 font-mono text-xs" : "max-w-2xl rounded-xl p-8 text-sm"
        }`}
      >
        <div className={`text-center ${isTicket ? "" : "mb-6"}`}>
          <h1 className={`font-bold ${isTicket ? "text-sm" : "text-2xl"}`}>
            {invoice.business_name}
          </h1>
          {invoice.business_tax_id && <p>NIT: {invoice.business_tax_id}</p>}
          {invoice.business_address && <p>{invoice.business_address}</p>}
          {invoice.business_phone && <p>Tel: {invoice.business_phone}</p>}
        </div>

        <div className={isTicket ? "my-2 border-t border-dashed border-slate-400 pt-2" : "mb-4"}>
          <div className={isTicket ? "" : "flex justify-between"}>
            <p>
              <strong>Factura de venta:</strong> {invoice.number}
              {invoice.sale_status === "anulada" && <strong> (ANULADA)</strong>}
            </p>
            <p>
              <strong>Fecha:</strong> {formatDate(invoice.issued_at)}
            </p>
          </div>
          <p>
            <strong>Vendedor:</strong> {invoice.seller_name} · <strong>Pago:</strong>{" "}
            {paymentLabels[invoice.payment_method]}
          </p>
          {invoice.customer_name && (
            <p>
              <strong>Cliente:</strong> {invoice.customer_name}
              {invoice.customer_id_number && ` · ${invoice.customer_id_number}`}
            </p>
          )}
        </div>

        {isTicket ? (
          <div className="border-t border-dashed border-slate-400 pt-2">
            {invoice.items.map((item, index) => (
              <div key={index} className="mb-1.5">
                <p>{item.description}</p>
                <div className="flex justify-between">
                  <span>
                    {qty(item.quantity)} {item.unit !== "unidad" ? item.unit : "und"} ×{" "}
                    {money(item.unit_price)}
                    {Number(item.discount_pct) > 0 && ` (−${Number(item.discount_pct)}%)`}
                  </span>
                  <span>{money(item.line_total)}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <table className="mb-4 w-full border-collapse">
            <thead>
              <tr className="border-b-2 border-slate-300 text-left">
                <th className="py-2">Producto</th>
                <th className="py-2 text-right">Cant.</th>
                <th className="py-2 text-right">Precio</th>
                <th className="py-2 text-right">IVA</th>
                <th className="py-2 text-right">Subtotal</th>
              </tr>
            </thead>
            <tbody>
              {invoice.items.map((item, index) => (
                <tr key={index} className="border-b border-slate-100">
                  <td className="py-2">
                    {item.description}
                    <span className="block font-mono text-xs text-slate-400">{item.sku}</span>
                  </td>
                  <td className="py-2 text-right">
                    {qty(item.quantity)} {item.unit !== "unidad" ? item.unit : ""}
                  </td>
                  <td className="py-2 text-right">
                    {money(item.unit_price)}
                    {Number(item.discount_pct) > 0 && (
                      <span className="block text-xs text-slate-500">
                        −{Number(item.discount_pct)}%
                      </span>
                    )}
                  </td>
                  <td className="py-2 text-right">{pct(item.tax_rate)}</td>
                  <td className="py-2 text-right">{money(item.line_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div
          className={
            isTicket
              ? "mt-2 border-t border-dashed border-slate-400 pt-2"
              : "ml-auto max-w-xs space-y-1"
          }
        >
          {Number(invoice.discount_amount) > 0 && (
            <div className="flex justify-between">
              <span>Descuento</span>
              <span>−{money(invoice.discount_amount)}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span>Subtotal</span>
            <span>{money(invoice.subtotal)}</span>
          </div>
          {invoice.tax_breakdown
            .filter((b) => Number(b.tax_rate) > 0)
            .map((b) => (
              <div key={b.tax_rate} className="flex justify-between">
                <span>IVA {pct(b.tax_rate)}</span>
                <span>{money(b.tax)}</span>
              </div>
            ))}
          <div className={`flex justify-between font-bold ${isTicket ? "text-sm" : "text-lg"}`}>
            <span>TOTAL</span>
            <span>{money(invoice.total)}</span>
          </div>
        </div>

        <p className={`mt-4 text-center text-slate-500 ${isTicket ? "text-[10px]" : "text-xs"}`}>
          ¡Gracias por su compra!
        </p>
      </div>

      <Modal open={returnOpen} onClose={() => setReturnOpen(false)} title="Devolver productos" wide>
        <p className="mb-4 text-sm text-slate-600">
          Selecciona las cantidades a devolver. Stock disponible en inventario.
        </p>
        {invoice.items.map((item) => {
          const q = returnQtys[item.id] ?? "0";
          return (
            <div
              key={item.id}
              className="mb-3 flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 p-3"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-800">{item.description}</p>
                <p className="text-xs text-slate-400">
                  {money(item.unit_price)} × {qty(item.quantity)} {item.unit}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  min="0"
                  max={Number(item.quantity)}
                  step={item.unit === "unidad" ? "1" : "0.001"}
                  value={q}
                  onChange={(e) =>
                    setReturnQtys((prev) => ({
                      ...prev,
                      [item.id]: e.target.value,
                    }))
                  }
                  className="w-24"
                  aria-label={`Cantidad a devolver de ${item.description}`}
                />
                <span className="text-xs text-slate-500">/ {qty(item.quantity)}</span>
              </div>
            </div>
          );
        })}
        <Input
          value={returnReason}
          onChange={(e) => setReturnReason(e.target.value)}
          placeholder="Motivo de la devolución (opcional)"
          className="mb-4"
        />
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setReturnOpen(false)}>
            Cancelar
          </Button>
          <Button
            variant="danger"
            disabled={
              doReturn.isPending ||
              !Object.values(returnQtys).some((q) => Number(q) > 0)
            }
            onClick={() => doReturn.mutate()}
          >
            {doReturn.isPending ? "Procesando…" : "Confirmar devolución"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
