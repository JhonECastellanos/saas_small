import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/layout";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Pagination,
  Spinner,
  Td,
  Th,
} from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { formatDate, money } from "../../lib/money";
import type { Page } from "../products/types";

interface InvoiceListItem {
  id: number;
  number: string;
  sale_id: number;
  sale_status: string;
  seller_name: string;
  total: string;
  issued_at: string;
}

export function InvoicesPage() {
  const { user } = useAuth();
  const [filters, setFilters] = useState({ q: "", date_from: "", date_to: "" });
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["invoices", filters, page],
    queryFn: () =>
      api<Page<InvoiceListItem>>("/invoices", { params: { ...filters, page, page_size: 20 } }),
  });

  return (
    <div>
      <PageHeader title={user?.role === "admin" ? "Facturas" : "Mis facturas"} />
      <Card className="mb-4 flex flex-wrap gap-3 p-3">
        <Input
          placeholder="Buscar por número (ej. FV-000012)…"
          value={filters.q}
          onChange={(e) => {
            setFilters({ ...filters, q: e.target.value });
            setPage(1);
          }}
          className="max-w-xs"
        />
        <Input
          type="date"
          value={filters.date_from}
          onChange={(e) => {
            setFilters({ ...filters, date_from: e.target.value });
            setPage(1);
          }}
          className="max-w-40"
        />
        <Input
          type="date"
          value={filters.date_to}
          onChange={(e) => {
            setFilters({ ...filters, date_to: e.target.value });
            setPage(1);
          }}
          className="max-w-40"
        />
      </Card>
      <Card>
        {isLoading ? (
          <Spinner />
        ) : data && data.items.length === 0 ? (
          <EmptyState message="Sin facturas emitidas." />
        ) : (
          <>
            <div className="overflow-x-auto">
            <table className="w-full min-w-[500px]">
              <thead className="border-b border-slate-200">
                <tr>
                  <Th>Número</Th>
                  <Th>Fecha</Th>
                  {user?.role === "admin" && <Th>Vendedor</Th>}
                  <Th className="text-right">Total</Th>
                  <Th>Estado</Th>
                  <Th className="text-right">Acciones</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data?.items.map((invoice) => (
                  <tr key={invoice.id}>
                    <Td className="font-mono text-xs font-medium whitespace-nowrap">{invoice.number}</Td>
                    <Td className="text-xs whitespace-nowrap">{formatDate(invoice.issued_at)}</Td>
                    {user?.role === "admin" && <Td className="whitespace-nowrap">{invoice.seller_name}</Td>}
                    <Td className="text-right font-semibold whitespace-nowrap">{money(invoice.total)}</Td>
                    <Td className="whitespace-nowrap">
                      <Badge color={invoice.sale_status === "completada" ? "green" : "red"}>
                        {invoice.sale_status === "completada" ? "Vigente" : "Anulada"}
                      </Badge>
                    </Td>
                    <Td className="text-right whitespace-nowrap">
                      <Link to={`/invoices/${invoice.id}/print`}>
                        <Button variant="secondary">Ver / Imprimir</Button>
                      </Link>
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
    </div>
  );
}
