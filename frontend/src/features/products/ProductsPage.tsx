import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout";
import {
  Badge,
  Button,
  Card,
  ConfirmModal,
  EmptyState,
  Input,
  Label,
  Modal,
  Pagination,
  Select,
  Spinner,
  Td,
  Th,
  useToast,
} from "../../components/ui";
import { api, errorMessage } from "../../lib/api";
import { pct } from "../../lib/money";
import { buildCombos, VariantComboBuilder } from "./VariantComboBuilder";
import type { Category, Page, ProductDetail, ProductListItem } from "./types";

const emptyForm = {
  name: "",
  description: "",
  category_id: "",
  unit_of_measure: "unidad",
  tax_rate: "",
};

export function ProductsPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<ProductListItem | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [createPhoto, setCreatePhoto] = useState<File | null>(null);
  const [combos, setCombos] = useState<Record<number, number[]>>({});
  const [newCategory, setNewCategory] = useState("");
  const [confirming, setConfirming] = useState<ProductListItem | null>(null);

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => api<Category[]>("/categories"),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["products", { search, categoryFilter, page }],
    queryFn: () =>
      api<Page<ProductListItem>>("/products", {
        params: {
          q: search,
          category_id: categoryFilter,
          page,
          page_size: 20,
          include_inactive: true,
        },
      }),
  });

  const createCategory = useMutation({
    mutationFn: () => api("/categories", { method: "POST", body: { name: newCategory } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      setNewCategory("");
      toast.success("Categoría creada");
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const saveProduct = useMutation({
    mutationFn: async () => {
      const body = {
        name: form.name,
        description: form.description || null,
        category_id: form.category_id ? Number(form.category_id) : null,
        unit_of_measure: form.unit_of_measure,
        tax_rate: form.tax_rate === "" ? null : Number(form.tax_rate) / 100,
        variant_combos: form.unit_of_measure === "unidad" ? buildCombos(combos) : [],
      };
      if (editingProduct) {
        return api<ProductDetail>(`/products/${editingProduct.id}`, { method: "PATCH", body });
      }
      const product = await api<ProductDetail>("/products", { method: "POST", body });
      if (createPhoto) {
        const fd = new FormData();
        fd.append("file", createPhoto);
        await api(`/products/${product.id}/photo`, { method: "POST", body: fd, formData: true });
      }
      return product;
    },
    onSuccess: (product) => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      toast.success(editingProduct ? `Producto actualizado: ${product.name}` : `Producto creado: ${product.base_sku}`);
      closeModal();
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const toggleActive = useMutation({
    mutationFn: (product: ProductListItem) =>
      api(`/products/${product.id}`, { method: "PATCH", body: { is_active: !product.is_active } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      toast.success("Estado del producto actualizado");
      setConfirming(null);
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  function openEdit(product: ProductListItem) {
    setEditingProduct(product);
    setForm({
      name: product.name,
      description: "",
      category_id: product.category_id?.toString() ?? "",
      unit_of_measure: product.is_bulk ? product.unit_of_measure : "unidad",
      tax_rate: (Number(product.tax_rate) * 100).toString(),
    });
    setCombos({});
    setCreatePhoto(null);
    setModalOpen(true);
  }

  function closeModal() {
    setModalOpen(false);
    setEditingProduct(null);
    setForm(emptyForm);
    setCombos({});
    setCreatePhoto(null);
  }

  return (
    <div>
      <PageHeader
        title="Productos"
        actions={
          <>
            <Link to="/products/attributes">
              <Button variant="secondary">Atributos</Button>
            </Link>
            <Button onClick={() => { setEditingProduct(null); setForm(emptyForm); setCombos({}); setCreatePhoto(null); setModalOpen(true); }}>+ Nuevo producto</Button>
          </>
        }
      />

      <Card className="mb-4 flex flex-wrap gap-3 p-3">
        <Input
          placeholder="Buscar por nombre o SKU…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="max-w-xs"
        />
        <Select
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
          className="max-w-48"
        >
          <option value="">Todas las categorías</option>
          {categories?.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </Select>
      </Card>

      <Card>
        {isLoading ? (
          <Spinner />
        ) : data && data.items.length === 0 ? (
          <EmptyState message="No hay productos. Crea el primero con el botón de arriba." />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px]">
              <thead className="border-b border-slate-200">
                  <tr>
                    <Th className="w-12">Foto</Th>
                    <Th>Producto</Th>
                    <Th>SKU</Th>
                  <Th>Categoría</Th>
                  <Th>Unidad</Th>
                  <Th>IVA</Th>
                  <Th className="text-center">Variantes</Th>
                  <Th>Estado</Th>
                  <Th className="text-right">Acciones</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data?.items.map((product) => (
                  <tr key={product.id} className="hover:bg-slate-50 cursor-pointer" onDoubleClick={() => openEdit(product)}>
                    <Td className="w-12">
                      {product.photo_path && (
                        <img src={`/photos/${product.photo_path}`} alt="" className="h-10 w-10 rounded-lg object-cover" />
                      )}
                    </Td>
                    <Td className="font-medium whitespace-nowrap">
                      <Link to={`/products/${product.id}`} className="text-indigo-700 hover:underline">
                        {product.name}
                      </Link>
                    </Td>
                    <Td className="font-mono text-xs whitespace-nowrap">{product.base_sku}</Td>
                    <Td className="whitespace-nowrap">{product.category_name ?? "—"}</Td>
                    <Td className="whitespace-nowrap">
                      {product.is_bulk ? (
                        <Badge color="yellow">granel ({product.unit_of_measure})</Badge>
                      ) : (
                        "unidad"
                      )}
                    </Td>
                    <Td className="whitespace-nowrap">{pct(product.tax_rate)}</Td>
                    <Td className="text-center whitespace-nowrap">{product.variant_count}</Td>
                    <Td className="whitespace-nowrap">
                      <Badge color={product.is_active ? "green" : "red"}>
                        {product.is_active ? "Activo" : "Inactivo"}
                      </Badge>
                    </Td>
                    <Td className="text-right whitespace-nowrap">
                      <Button variant="secondary" onClick={() => openEdit(product)} title="Editar producto">
                        Editar
                      </Button>
                      <Button
                        variant="ghost"
                        className="ml-1 text-slate-400 hover:text-red-600 hover:bg-red-50"
                        onClick={() => setConfirming(product)}
                        title={product.is_active ? "Desactivar producto" : "Eliminar producto"}
                      >
                        🗑
                      </Button>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
            {data && (
              <Pagination page={page} pageSize={data.page_size} total={data.total} onPage={setPage} />
            )}
          </>
        )}
      </Card>

      <Modal open={modalOpen} onClose={closeModal} title={editingProduct ? "Editar producto" : "Nuevo producto"} wide>
        <form onSubmit={(e) => { e.preventDefault(); saveProduct.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="p-name">Nombre</Label>
              <Input id="p-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required minLength={2} />
              <p className="mt-1 text-xs text-slate-500">El SKU se genera automáticamente (ej. CAMISA-001).</p>
            </div>
            <div>
              <Label htmlFor="p-unit">Unidad de medida</Label>
              <Select id="p-unit" value={form.unit_of_measure} onChange={(e) => setForm({ ...form, unit_of_measure: e.target.value })}>
                <option value="unidad">Por unidad</option>
                <option value="kg">A granel — kilo (kg)</option>
                <option value="lb">A granel — libra (lb)</option>
              </Select>
              {form.unit_of_measure !== "unidad" && (
                <p className="mt-1 text-xs text-slate-500">El stock se lleva en kg; podrás definir precio por kg y por lb.</p>
              )}
            </div>
            <div>
              <Label htmlFor="p-cat">Categoría</Label>
              <div className="flex gap-2">
                <Select id="p-cat" value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
                  <option value="">Sin categoría</option>
                  {categories?.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </Select>
              </div>
              <div className="mt-2 flex gap-2">
                <Input placeholder="Nueva categoría…" value={newCategory} onChange={(e) => setNewCategory(e.target.value)} />
                <Button type="button" variant="secondary" disabled={!newCategory.trim() || createCategory.isPending} onClick={() => createCategory.mutate()}>
                  Crear
                </Button>
              </div>
            </div>
            <div>
              <Label htmlFor="p-tax">IVA % (vacío = predeterminado del negocio)</Label>
              <Input id="p-tax" type="number" min={0} max={100} step="0.1" placeholder="Ej. 19" value={form.tax_rate} onChange={(e) => setForm({ ...form, tax_rate: e.target.value })} />
            </div>
            <div className="sm:col-span-2">
              <Label htmlFor="p-desc">Descripción</Label>
              <Input id="p-desc" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            {!editingProduct && (
              <div className="sm:col-span-2">
                <Label htmlFor="p-photo">Foto del producto</Label>
                <Input
                  id="p-photo"
                  type="file"
                  accept="image/*"
                  capture="environment"
                  ref={fileRef as React.RefObject<HTMLInputElement>}
                  onChange={(e) => setCreatePhoto(e.target.files?.[0] ?? null)}
                />
                {createPhoto && <p className="mt-1 text-xs text-emerald-600">{createPhoto.name} seleccionado</p>}
                <p className="mt-1 text-xs text-slate-400">Opcional. Se puede agregar después desde la página del producto.</p>
              </div>
            )}
          </div>

          {form.unit_of_measure === "unidad" && (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="mb-2 text-sm font-semibold text-slate-700">Variantes (color, talla, sabor…)</p>
              <VariantComboBuilder selected={combos} onChange={setCombos} />
            </div>
          )}

          <Button type="submit" className="w-full" disabled={saveProduct.isPending}>
            {saveProduct.isPending ? "Guardando…" : editingProduct ? "Guardar cambios" : "Crear producto"}
          </Button>
        </form>
      </Modal>

      <ConfirmModal
        open={confirming !== null}
        onClose={() => setConfirming(null)}
        title="Confirmar"
        message={
          confirming?.is_active
            ? `¿Desactivar "${confirming?.name}"? Dejará de aparecer en el punto de venta.`
            : `¿Eliminar "${confirming?.name}"? Esta acción no se puede deshacer.`
        }
        confirmLabel={confirming?.is_active ? "Desactivar" : "Eliminar"}
        danger={!confirming?.is_active}
        loading={toggleActive.isPending}
        onConfirm={() => confirming && toggleActive.mutate(confirming)}
      />
    </div>
  );
}
