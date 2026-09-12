import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader } from "../../components/layout";
import {
  Badge,
  Button,
  Card,
  Input,
  Label,
  Modal,
  Select,
  Spinner,
  Td,
  Th,
  useToast,
} from "../../components/ui";
import { api, errorMessage } from "../../lib/api";
import type { User } from "../../lib/auth";

export function UsersPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [form, setForm] = useState({ email: "", full_name: "", password: "", role: "vendedor" });

  const { data: users, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => api<User[]>("/users"),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editing) {
        const body: Record<string, unknown> = { full_name: form.full_name, role: form.role };
        if (form.password) body.password = form.password;
        return api(`/users/${editing.id}`, { method: "PATCH", body });
      }
      return api("/users", { method: "POST", body: form });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success(editing ? "Usuario actualizado" : "Usuario creado");
      setModalOpen(false);
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const toggleActive = useMutation({
    mutationFn: (user: User) =>
      api(`/users/${user.id}`, { method: "PATCH", body: { is_active: !user.is_active } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
    onError: (err) => toast.error(errorMessage(err)),
  });

  function openCreate() {
    setEditing(null);
    setForm({ email: "", full_name: "", password: "", role: "vendedor" });
    setModalOpen(true);
  }

  function openEdit(user: User) {
    setEditing(user);
    setForm({ email: user.email, full_name: user.full_name, password: "", role: user.role });
    setModalOpen(true);
  }

  return (
    <div>
      <PageHeader
        title="Usuarios"
        actions={<Button onClick={openCreate}>+ Nuevo usuario</Button>}
      />
      <Card>
        {isLoading ? (
          <Spinner />
        ) : (
          <table className="w-full">
            <thead className="border-b border-slate-200">
              <tr>
                <Th>Nombre</Th>
                <Th>Correo</Th>
                <Th>Rol</Th>
                <Th>Estado</Th>
                <Th className="text-right">Acciones</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users?.map((user) => (
                <tr key={user.id}>
                  <Td className="font-medium">{user.full_name}</Td>
                  <Td>{user.email}</Td>
                  <Td>
                    <Badge color={user.role === "admin" ? "indigo" : "gray"}>
                      {user.role === "admin" ? "Administrador" : "Vendedor"}
                    </Badge>
                  </Td>
                  <Td>
                    <Badge color={user.is_active ? "green" : "red"}>
                      {user.is_active ? "Activo" : "Inactivo"}
                    </Badge>
                  </Td>
                  <Td className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="secondary" onClick={() => openEdit(user)}>
                        Editar
                      </Button>
                      <Button
                        variant={user.is_active ? "danger" : "secondary"}
                        onClick={() => toggleActive.mutate(user)}
                      >
                        {user.is_active ? "Desactivar" : "Activar"}
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
        title={editing ? "Editar usuario" : "Nuevo usuario"}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            saveMutation.mutate();
          }}
          className="space-y-4"
        >
          {!editing && (
            <div>
              <Label htmlFor="u-email">Correo</Label>
              <Input
                id="u-email"
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
              />
            </div>
          )}
          <div>
            <Label htmlFor="u-name">Nombre completo</Label>
            <Input
              id="u-name"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="u-pass">
              {editing ? "Nueva contraseña (dejar vacío para no cambiar)" : "Contraseña"}
            </Label>
            <Input
              id="u-pass"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required={!editing}
              minLength={6}
            />
          </div>
          <div>
            <Label htmlFor="u-role">Rol</Label>
            <Select
              id="u-role"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
            >
              <option value="vendedor">Vendedor</option>
              <option value="admin">Administrador</option>
            </Select>
          </div>
          <Button type="submit" className="w-full" disabled={saveMutation.isPending}>
            {saveMutation.isPending ? "Guardando…" : "Guardar"}
          </Button>
        </form>
      </Modal>
    </div>
  );
}
