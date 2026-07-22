import { NextResponse } from "next/server";

import { runPythonCli } from "@/lib/pythonBridge";
import type { SuporteFiltrosOut } from "@/lib/types";

export async function GET() {
  const data = await runPythonCli<SuporteFiltrosOut>("suporte-filtros");
  return NextResponse.json(data);
}
