import { NextRequest, NextResponse } from "next/server";

import { appendParam, runPythonCliBinary } from "@/lib/pythonBridge";

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;

  const args: string[] = [];
  appendParam(args, "--start", params.get("start"));
  appendParam(args, "--end", params.get("end"));
  appendParam(args, "--categoria", params.get("categoria"));
  appendParam(args, "--tipo-erro", params.get("tipo_erro"));

  const pdf = await runPythonCliBinary("suporte-relatorio-pdf", args);
  return new NextResponse(new Uint8Array(pdf), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="relatorio-suporte-${new Date().toISOString().slice(0, 10)}.pdf"`,
    },
  });
}
