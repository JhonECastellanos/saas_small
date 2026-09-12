import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader } from "../../components/layout";
import {
  Badge,
  Button,
  Card,
  GoBack,
  Input,
  Label,
  Modal,
  useToast,
} from "../../components/ui";
import { api, errorMessage } from "../../lib/api";
import type { Attribute } from "./types";

export function AttributesPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [attrModal, setAttrModal] = useState(false);
  const [valueModal, setValueModal] = useState<Attribute | null>(null);
  const [attrForm, setAttrForm] = useState({ name: "", code: "" });
  const [valueForm, setValueForm] = useState({ value: "", code: "" });

  const { data: attributes } = useQuery({
    queryKey: ["attributes"],
    queryFn: () => api<Attribute[]>("/attributes"),
  });

  const createAttribute = useMutation({
    mutationFn: () => api("/attributes", { method: "POST", body: attrForm }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["attributes"] });
      toast.success("Atributo creado");
      setAttrModal(false);
      setAttrForm({ name: "", code: "" });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const addValue = useMutation({
    mutationFn: () =>
      api(`/attributes/${valueModal!.id}/values`, { method: "POST", body: valueForm }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["attributes"] });
      toast.success("Valor agregado");
      setValueModal(null);
      setValueForm({ value: "", code: "" });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <div>
      <PageHeader
        title={<><GoBack fallback="/products" /> Atributos de variantes</>}
        actions={<Button onClick={() => setAttrModal(true)}>+ Nuevo atributo</Button>}
      />
      <p className="mb-4 text-sm text-slate-500">
        Los atributos (color, talla, sabor…) son dinámicos: puedes crear nuevos tipos sin tocar la
        base de datos. El código corto se usa para armar el SKU de cada variante.
      </p>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {attributes?.map((attribute) => (
          <Card key={attribute.id} className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="font-semibold text-slate-800">{attribute.name}</h2>
                <p className="font-mono text-xs text-slate-400">{attribute.code}</p>
              </div>
              <Button variant="secondary" onClick={() => setValueModal(attribute)}>
                + Valor
              </Button>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {attribute.values.map((value) => (
                <Badge key={value.id} color="indigo">
                  {value.value} <span className="ml-1 opacity-60">({value.code})</span>
                </Badge>
              ))}
              {attribute.values.length === 0 && (
                <p className="text-xs text-slate-400">Sin valores aún</p>
              )}
            </div>
          </Card>
        ))}
      </div>

      <Modal open={attrModal} onClose={() => setAttrModal(false)} title="Nuevo atributo">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createAttribute.mutate();
          }}
          className="space-y-4"
        >
          <div>
            <Label htmlFor="a-name">Nombre (ej. Material)</Label>
            <Input
              id="a-name"
              value={attrForm.name}
              onChange={(e) => setAttrForm({ ...attrForm, name: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="a-code">Código corto para SKU (ej. MAT)</Label>
            <Input
              id="a-code"
              value={attrForm.code}
              onChange={(e) => setAttrForm({ ...attrForm, code: e.target.value.toUpperCase() })}
              required
              maxLength={10}
            />
          </div>
          <Button type="submit" className="w-full" disabled={createAttribute.isPending}>
            Crear atributo
          </Button>
        </form>
      </Modal>

      <Modal
        open={valueModal !== null}
        onClose={() => setValueModal(null)}
        title={`Nuevo valor de ${valueModal?.name ?? ""}`}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            addValue.mutate();
          }}
          className="space-y-4"
        >
          <div>
            <Label htmlFor="v-value">Valor (ej. Verde)</Label>
            <Input
              id="v-value"
              value={valueForm.value}
              onChange={(e) => setValueForm({ ...valueForm, value: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="v-code">Código corto para SKU (ej. VER)</Label>
            <Input
              id="v-code"
              value={valueForm.code}
              onChange={(e) => setValueForm({ ...valueForm, code: e.target.value.toUpperCase() })}
              required
              maxLength={10}
            />
          </div>
          <Button type="submit" className="w-full" disabled={addValue.isPending}>
            Agregar valor
          </Button>
        </form>
      </Modal>
    </div>
  );
}
