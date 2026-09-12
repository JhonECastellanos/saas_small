import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { PageHeader } from "../../components/layout";
import { Button, Card, Input, Label, Spinner, useToast } from "../../components/ui";
import { api, errorMessage } from "../../lib/api";

interface BusinessSettings {
  business_name: string;
  tax_id: string | null;
  address: string | null;
  phone: string | null;
  default_tax_rate: string;
  invoice_prefix: string;
  default_low_stock_threshold: string;
  currency: string;
}

export function SettingsPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({
    business_name: "",
    tax_id: "",
    address: "",
    phone: "",
    default_tax_rate: "",
    invoice_prefix: "",
    default_low_stock_threshold: "",
  });

  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api<BusinessSettings>("/settings/business"),
  });

  useEffect(() => {
    if (data) {
      setForm({
        business_name: data.business_name,
        tax_id: data.tax_id ?? "",
        address: data.address ?? "",
        phone: data.phone ?? "",
        default_tax_rate: String(Number(data.default_tax_rate) * 100),
        invoice_prefix: data.invoice_prefix,
        default_low_stock_threshold: data.default_low_stock_threshold,
      });
    }
  }, [data]);

  const save = useMutation({
    mutationFn: () =>
      api("/settings/business", {
        method: "PUT",
        body: {
          business_name: form.business_name,
          tax_id: form.tax_id || null,
          address: form.address || null,
          phone: form.phone || null,
          default_tax_rate: Number(form.default_tax_rate) / 100,
          invoice_prefix: form.invoice_prefix,
          default_low_stock_threshold: Number(form.default_low_stock_threshold),
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      toast.success("Configuración guardada");
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  if (isLoading) return <Spinner />;

  return (
    <div className="max-w-2xl">
      <PageHeader title="Configuración del negocio" />
      <Card className="p-5">
        <p className="mb-4 text-sm text-slate-500">
          Estos datos aparecen en las facturas. Cada factura guarda una copia al momento de
          emitirse, así que los cambios solo afectan facturas futuras.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
          className="grid grid-cols-1 gap-4 sm:grid-cols-2"
        >
          <div className="sm:col-span-2">
            <Label htmlFor="b-name">Nombre del negocio</Label>
            <Input
              id="b-name"
              value={form.business_name}
              onChange={(e) => setForm({ ...form, business_name: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="b-nit">NIT</Label>
            <Input
              id="b-nit"
              value={form.tax_id}
              onChange={(e) => setForm({ ...form, tax_id: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="b-phone">Teléfono</Label>
            <Input
              id="b-phone"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </div>
          <div className="sm:col-span-2">
            <Label htmlFor="b-address">Dirección</Label>
            <Input
              id="b-address"
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="b-tax">IVA predeterminado % (productos nuevos)</Label>
            <Input
              id="b-tax"
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={form.default_tax_rate}
              onChange={(e) => setForm({ ...form, default_tax_rate: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="b-prefix">Prefijo de factura</Label>
            <Input
              id="b-prefix"
              value={form.invoice_prefix}
              onChange={(e) => setForm({ ...form, invoice_prefix: e.target.value.toUpperCase() })}
              maxLength={10}
              required
            />
          </div>
          <div>
            <Label htmlFor="b-threshold">Umbral general de stock bajo</Label>
            <Input
              id="b-threshold"
              type="number"
              min="0"
              step="0.001"
              value={form.default_low_stock_threshold}
              onChange={(e) =>
                setForm({ ...form, default_low_stock_threshold: e.target.value })
              }
            />
          </div>
          <div className="sm:col-span-2">
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? "Guardando…" : "Guardar configuración"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
