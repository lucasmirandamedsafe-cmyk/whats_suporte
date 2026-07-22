import { NextResponse } from "next/server";

import { runPythonCli } from "@/lib/pythonBridge";
import type { GruposFiltrosOut } from "@/lib/types";

export async function GET() {
  const data = await runPythonCli<GruposFiltrosOut>("grupos-filtros");
  return NextResponse.json(data);
}
