// Server-only orchestration: user question -> LLM decides MCP tool -> MCP Server
// -> DB -> result back to LLM -> final natural-language answer.
// Per assignment spec: the LLM must never receive raw DB/SQL access, only
// MCP tool calls, and this whole flow must run server-side (never in the browser).
import OpenAI from "openai";
import { AgentPayload, ChatMessage } from "./types";
import { callMcpTool, isMcpConfigured, listMcpTools } from "./mcpClient";
import { pickMockTool } from "./mockTools";

const SUGGESTIONS = ["별점 추이 보기", "긍정 리뷰 비율"];

function toChatMessage(
  text: string,
  toolName: string | undefined,
  data: AgentPayload | undefined
): Omit<ChatMessage, "id" | "role"> {
  return {
    text,
    mcpCall: toolName ? { tool: toolName } : undefined,
    data,
    suggestions: SUGGESTIONS,
  };
}

async function runWithMcp(userMessage: string) {
  const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  const tools = await listMcpTools();

  const openAiTools = tools.map((t) => ({
    type: "function" as const,
    function: {
      name: t.name,
      description: t.description,
      parameters: t.parameters,
    },
  }));

  const first = await client.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      {
        role: "system",
        content:
          "당신은 『불편한 편의점』 리뷰 데이터를 분석해주는 에이전트입니다. " +
          "질문에 답하려면 반드시 제공된 MCP tool을 호출해 실제 DB 데이터를 조회한 뒤 " +
          "그 결과를 바탕으로 답하세요. 스스로 알고 있는 지식으로 추측해 답하지 마세요.",
      },
      { role: "user", content: userMessage },
    ],
    tools: openAiTools,
    tool_choice: "auto",
  });

  const choice = first.choices[0];
  const toolCall = choice.message.tool_calls?.[0];

  if (!toolCall) {
    return toChatMessage(choice.message.content ?? "", undefined, undefined);
  }

  const args = JSON.parse(toolCall.function.arguments || "{}");
  const { result } = await callMcpTool(toolCall.function.name, args);

  const second = await client.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      {
        role: "system",
        content: "MCP tool 결과를 바탕으로 사용자 질문에 간결하게 답하세요.",
      },
      { role: "user", content: userMessage },
      {
        role: "assistant",
        content: null,
        tool_calls: [toolCall],
      },
      {
        role: "tool",
        tool_call_id: toolCall.id,
        content: JSON.stringify(result),
      },
    ],
  });

  const answer = second.choices[0].message.content ?? "";
  return toChatMessage(answer, toolCall.function.name, result as AgentPayload);
}

async function runWithMock(userMessage: string) {
  const tool = pickMockTool(userMessage);
  const data = tool.run({});
  const text = `${data.title ?? "요청하신 분석 결과예요"} 💬`;
  return toChatMessage(text, tool.name, data);
}

export async function runAgent(userMessage: string) {
  if (isMcpConfigured() && process.env.OPENAI_API_KEY) {
    return runWithMcp(userMessage);
  }
  // MCP Server / LLM key not wired up yet - dev-only mock so the UI stays demoable.
  return runWithMock(userMessage);
}
