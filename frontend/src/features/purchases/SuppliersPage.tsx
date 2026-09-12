import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader } from "../../components/layout";
import {
  Badge,
  Button,
  Card,
  EmptyState,
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

export interface Supplier {
  id: number;
  name: string;
  tax_id: string | null;
  phone: string | null;
  email: string | null;
  is_active: boolean;
}

const emptyForm = { name: "", tax_id: "", phone: "", email: "" };

export function SuppliersPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Supplier | null>(null);
  const [form, setForm] = useState(emptyForm);

  const { data: suppliers, isLoading } = useQuery({
    queryKey: ["suppliers", "all"],
    queryFn: () => api<Supplier[]>("/suppliers", { params: { include_inactive: true } }),
  });

  const save = useMutation({
    mutationFn: () => {
      const body = {
        name: form.name,
        tax_id: form.tax_id || null,
        phone: form.phone || null,
        email: form.email || null,
      };
      return editing
        ? api(`/suppliers/${editing.id}`, { method: "PATCH", body })
        : api("/suppliers", { method: "POST", body });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      toast.success("Proveedor guardado");
      setModalOpen(false);
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const toggleActive = useMutation({
    mutationFn: (supplier: Supplier) =>
      api(`/suppliers/${supplier.id}`, {
        method: "PATCH",
        body: { is_active: !supplier.is_active },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["suppliers"] }),
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <div>
      <PageHeader
        title={<><GoBack fallback="/purchases" /> Proveedores</>}
        actions={
          <Button
            onClick={() => {
              setEditing(null);
              setForm(emptyForm);
              setModalOpen(true);
            }}
          >
            + Nuevo proveedor
          </Button>
        }
      />
      <Card>
        {isLoading ? (
          <Spinner />
        ) : suppliers && suppliers.length === 0 ? (
          <EmptyState message="Sin proveedores registrados." />
        ) : (
          <table className="w-full">
            <thead className="border-b border-slate-200">
              <tr>
                <Th>Nombre</Th>
                <Th>NIT</Th>
                <Th>Teléfono</Th>
                <Th>Correo</Th>
                <Th>Estado</Th>
                <Th className="text-right">Acciones</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {suppliers?.map((supplier) => (
                <tr key={supplier.id}>
                  <Td className="font-medium">{supplier.name}</Td>
                  <Td>{supplier.tax_id ?? "—"}</Td>
                  <Td>{supplier.phone ?? "—"}</Td>
                  <Td>{supplier.email ?? "—"}</Td>
                  <Td>
                    <Badge color={supplier.is_active ? "green" : "red"}>
                      {supplier.is_active ? "Activo" : "Inactivo"}
                    </Badge>
                  </Td>
                  <Td className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="secondary"
                        onClick={() => {
                          setEditing(supplier);
                          setForm({
                            name: supplier.name,
                            tax_id: supplier.tax_id ?? "",
                            phone: supplier.phone ?? "",
                            email: supplier.email ?? "",
                          });
                          setModalOpen(true);
                        }}
                      >
                        Editar
                      </Button>
                      <Button
                        variant={supplier.is_active ? "danger" : "secondary"}
                        onClick={() => toggleActive.mutate(supplier)}
                      >
                        {supplier.is_active ? "Desactivar" : "Activar"}
                      </Button>
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? "Editar proveedor" : "Nuevo proveedor"}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
          className="space-y-4"
        >
          <div>
            <Label htmlFor="s-name">Nombre</Label>
            <Input
              id="s-name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="s-nit">NIT</Label>
            <Input
              id="s-nit"
              value={form.tax_id}
              onChange={(e) => setForm({ ...form, tax_id: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="s-phone">Teléfono</Label>
            <Input
              id="s-phone"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="s-email">Correo</Label>
            <Input
              id="s-email"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <Button type="submit" className="w-full" disabled={save.isPending}>
            Guardar
          </Button>
        </form>
      </Modal>
    </div>
  );
}
