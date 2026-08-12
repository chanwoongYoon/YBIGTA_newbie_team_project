import { NextRequest, NextResponse } from "next/server";
import { runAgent } from "@/lib/llm";

// Server-side only. API Key / MCP token never leave this file.
// Client Components must call this route via fetch - never call the LLM or
// MCP Server directly from the browser.
export async function POST(req: NextRequest) {
  const { message } = (await req.json()) as { message?: string };

  if (!message || !message.trim()) {
    return NextResponse.json({ error: "message is required" }, { status: 400 });
  }

  try {
    const reply = await runAgent(message.trim());
    return NextResponse.json(reply);
  } catch (err) {
    console.error("[/api/chat] agent error", err);
    return NextResponse.json(
      { error: "에이전트 응답 생성 중 오류가 발생했어요." },
      { status: 500 }
    );
  }
}
