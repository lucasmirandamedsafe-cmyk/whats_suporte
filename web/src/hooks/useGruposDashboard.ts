"use client";
import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { GruposDashboardOut, GruposFiltrosState } from "@/lib/types";

export function useGruposDashboard(filters: GruposFiltrosState) {
  const [data, setData] = useState<GruposDashboardOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const areasKey = (filters.areas ?? []).slice().sort().join(",");

  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- padrao de loading state para fetch: precisa voltar a "true" a cada refetch (mudanca de filtro), nao so na 1a montagem.
    setLoading(true);
    apiGet<GruposDashboardOut>("/api/grupos/dashboard", {
      areas: filters.areas,
      start: filters.start,
      end: filters.end,
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [areasKey, filters.start, filters.end]);

  return { data, loading, error };
}
