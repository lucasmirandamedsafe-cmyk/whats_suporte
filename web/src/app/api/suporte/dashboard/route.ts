import { NextRequest, NextResponse } from "next/server";

import { appendParam, runPythonCli } from "@/lib/pythonBridge";
import type { SuporteDashboardOut } from "@/lib/types";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;

  const args: string[] = [];
  appendParam(args, "--start", params.get("start"));
  appendParam(args, "--end", params.get("end"));
  appendParam(args, "--categoria", params.get("categoria"));
  appendParam(args, "--tipo-erro", params.get("tipo_erro"));

  const data = await runPythonCli<SuporteDashboardOut>("suporte-dashboard", args);
  return NextResponse.json(data);
}
