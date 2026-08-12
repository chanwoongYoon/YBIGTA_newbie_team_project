// Local fallback used only when MCP_SERVER_URL / MCP_AUTH_TOKEN are not set yet
// (e.g. while the MCP Server teammate is still building it). Lets the UI/agent
// flow be demoed end-to-end before the real MCP Server is deployed.
// Swap this out once isMcpConfigured() is true - see lib/llm.ts.
import { AgentPayload } from "./types";

export interface MockToolDef {
  name: string;
  description: string;
  run: (args: Record<string, unknown>) => AgentPayload;
}

export const MOCK_TOOLS: MockToolDef[] = [
  {
    name: "get_keyword_stats",
    description:
      "최근 N일간 리뷰에서 가장 많이 언급된 키워드 상위 K개를 집계합니다.",
    run: () => ({
      title: "최근 7일 리뷰에서 많이 언급된 키워드 TOP 3",
      rows: [
        { label: "따뜻하다", value: "128회" },
        { label: "힐링", value: "94회" },
        { label: "캐릭터", value: "71회" },
      ],
      caption: "분석 대상: 최근 7일 수집 리뷰 342건 · 실시간 업데이트",
    }),
  },
  {
    name: "get_rating_trend",
    description: "기간별 평균 별점 추이를 조회합니다.",
    run: () => ({
      title: "최근 4주 평균 별점 추이",
      rows: [
        { label: "1주 전", value: "4.3점" },
        { label: "2주 전", value: "4.1점" },
        { label: "3주 전", value: "4.4점" },
        { label: "4주 전", value: "4.2점" },
      ],
      caption: "분석 대상: 최근 4주 수집 리뷰 · 실시간 업데이트",
    }),
  },
  {
    name: "get_sentiment_ratio",
    description: "긍정/부정 리뷰 비율을 집계합니다.",
    run: () => ({
      title: "긍정 / 부정 리뷰 비율",
      rows: [
        { label: "긍정", value: "92.7%" },
        { label: "부정", value: "7.3%" },
      ],
      caption: "분석 대상: 최근 7일 수집 리뷰 342건 · 실시간 업데이트",
    }),
  },
];

export function pickMockTool(userMessage: string): MockToolDef {
  const text = userMessage.toLowerCase();
  if (text.includes("별점") || text.includes("추이")) {
    return MOCK_TOOLS[1];
  }
  if (text.includes("긍정") || text.includes("부정") || text.includes("비율")) {
    return MOCK_TOOLS[2];
  }
  return MOCK_TOOLS[0];
}
