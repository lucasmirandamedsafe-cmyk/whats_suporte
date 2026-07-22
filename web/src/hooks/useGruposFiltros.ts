"use client";
import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { GruposFiltrosOut } from "@/lib/types";

export function useGruposFiltros() {
  const [data, setData] = useState<GruposFiltrosOut | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    apiGet<GruposFiltrosOut>("/api/grupos/filtros").then((d) => {
      if (!cancelled) {
        setData(d);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return { data, loading };
}
