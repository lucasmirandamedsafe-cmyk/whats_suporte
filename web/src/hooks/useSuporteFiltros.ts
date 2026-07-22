"use client";
import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { SuporteFiltrosOut } from "@/lib/types";

export function useSuporteFiltros() {
  const [data, setData] = useState<SuporteFiltrosOut | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    apiGet<SuporteFiltrosOut>("/api/suporte/filtros").then((d) => {
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
