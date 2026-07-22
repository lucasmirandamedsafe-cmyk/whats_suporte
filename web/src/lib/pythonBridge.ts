import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

// web/ e' uma subpasta do repo - a raiz (onde o pacote Python `api` e
// `pipeline` vivem) e' o pai desta pasta. Assume-se que o Next.js foi
// iniciado com `cd web && npm run dev`, conforme documentado no README.
const REPO_ROOT = path.resolve(process.cwd(), "..");

/**
 * Roda `python -m api.cli <command> [...args]` a partir da raiz do repo e
 * devolve o JSON impresso no stdout. Um processo Python por chamada - sem
 * servidor de longa duracao, sem cache: le data/whatsapp.db e calcula via
 * pipeline/metrics.py (a mesma logica que o Streamlit usava) a cada request.
 */
export async function runPythonCli<T>(command: string, args: string[] = []): Promise<T> {
  const { stdout } = await execFileAsync("python", ["-m", "api.cli", command, ...args], {
    cwd: REPO_ROOT,
    encoding: "utf8",
    maxBuffer: 20 * 1024 * 1024,
  });
  return JSON.parse(stdout) as T;
}

export function appendParam(args: string[], flag: string, value: string | string[] | null | undefined) {
  if (value === null || value === undefined || value === "") return;
  if (Array.isArray(value)) {
    for (const v of value) args.push(flag, v);
  } else {
    args.push(flag, value);
  }
}
