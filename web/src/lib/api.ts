// As rotas /api/* sao do proprio Next.js (web/src/app/api/**/route.ts), que
// chamam Python via subprocess (ver lib/pythonBridge.ts) - por isso aqui basta
// um caminho relativo, sempre same-origin, sem precisar de base URL/CORS.

type ParamValue = string | string[] | undefined;

export async function apiGet<T>(path: string, params?: Record<string, ParamValue>): Promise<T> {
  const searchParams = new URLSearchParams();
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === "") continue;
      if (Array.isArray(value)) {
        for (const v of value) searchParams.append(key, v);
      } else {
        searchParams.set(key, value);
      }
    }
  }

  const query = searchParams.toString();
  const url = query ? `${path}?${query}` : path;

  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Erro ao chamar ${path}: HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}
