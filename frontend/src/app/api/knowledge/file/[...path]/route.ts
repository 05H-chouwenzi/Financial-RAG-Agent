import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.FINANCE_BACKEND_URL || "http://127.0.0.1:8000";

interface Ctx {
  params: Promise<{ path: string[] }>;
}

export async function GET(_request: NextRequest, ctx: Ctx) {
  try {
    const { path } = await ctx.params;
    const rel = path.join("/");
    const res = await fetch(BACKEND_URL + "/api/knowledge/file/" + rel, {
      cache: "no-store",
      signal: AbortSignal.timeout(60000),
    });
    if (!res.ok) return new NextResponse("文件不存在", { status: 404 });
    const buf = await res.arrayBuffer();
    const filename = rel.split("/").pop() || "report.pdf";
    return new NextResponse(buf, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `inline; filename*=UTF-8''${encodeURIComponent(filename)}`,
      },
    });
  } catch {
    return new NextResponse("文件不可用", { status: 502 });
  }
}
