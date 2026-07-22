"use client";
import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { SuporteDashboardOut, SuporteFiltrosState } from "@/lib/types";

export function useSuporteDashboard(filters: SuporteFiltrosState) {
  const [data, setData] = useState<SuporteDashboardOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- padrao de loading state para fetch: precisa voltar a "true" a cada refetch (mudanca de filtro), nao so na 1a montagem.
    setLoading(true);
    apiGet<SuporteDashboardOut>("/api/suporte/dashboard", {
      start: filters.start,
      end: filters.end,
      categoria: filters.categoria,
      tipo_erro: filters.tipoErro,
    })
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setError(null);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filters.start, filters.end, filters.categoria, filters.tipoErro]);

  return { data, loading, error };
}
