import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.FINANCE_BACKEND_URL || "http://127.0.0.1:8000";

export async function GET() {
  try {
    const res = await fetch(BACKEND_URL + "/api/knowledge/files", {
      cache: "no-store",
      signal: AbortSignal.timeout(30000),
    });
    if (!res.ok) return NextResponse.json({ files: [], error: "后端不可用" }, { status: 502 });
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ files: [], error: "后端不可用" }, { status: 502 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const form = await request.formData();
    const res = await fetch(BACKEND_URL + "/api/knowledge/upload", {
      method: "POST",
      body: form,
      signal: AbortSignal.timeout(120000),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { error: "上传失败(" + res.status + "): " + (data.message || "") },
        { status: 502 }
      );
    }
    return NextResponse.json(data);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "后端不可用";
    return NextResponse.json({ error: "上传失败: " + msg }, { status: 502 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const file = request.nextUrl.searchParams.get("file") || "";
    const res = await fetch(BACKEND_URL + "/api/knowledge/files?file=" + encodeURIComponent(file), {
      method: "DELETE",
      signal: AbortSignal.timeout(30000),
    });
    if (!res.ok) return NextResponse.json({ error: "删除失败" }, { status: 502 });
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ error: "删除失败" }, { status: 502 });
  }
}
