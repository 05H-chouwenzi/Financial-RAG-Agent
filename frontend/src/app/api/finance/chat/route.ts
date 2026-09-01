import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// Financial-RAG-Agent 后端地址（可在 .env 中用 FINANCE_BACKEND_URL 覆盖）
const BACKEND_URL = process.env.FINANCE_BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const question = (body.question || "").trim();
    if (!question) {
      return NextResponse.json({ error: "请输入问题" }, { status: 400 });
    }
    const res = await fetch(BACKEND_URL + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: body.top_k || 5 }),
      signal: AbortSignal.timeout(90000),
    });
    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json(
        { error: "后端调用失败(" + res.status + "): " + text.slice(0, 200) },
        { status: 502 }
      );
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "后端不可用";
    return NextResponse.json({ error: "后端不可用: " + msg }, { status: 502 });
  }
}
