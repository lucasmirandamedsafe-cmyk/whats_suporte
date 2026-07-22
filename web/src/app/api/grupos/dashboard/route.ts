import { NextRequest, NextResponse } from "next/server";

import { appendParam, runPythonCli } from "@/lib/pythonBridge";
import type { GruposDashboardOut } from "@/lib/types";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;

  const args: string[] = [];
  appendParam(args, "--areas", params.getAll("areas"));
  appendParam(args, "--start", params.get("start"));
  appendParam(args, "--end", params.get("end"));

  const data = await runPythonCli<GruposDashboardOut>("grupos-dashboard", args);
  return NextResponse.json(data);
}
