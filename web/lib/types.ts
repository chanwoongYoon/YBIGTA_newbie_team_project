export type Role = "user" | "agent";

export interface StatRow {
  label: string;
  value: string;
}

export interface McpCall {
  tool: string;
}

export interface AgentPayload {
  title?: string;
  rows?: StatRow[];
  caption?: string;
}

export interface ChatMessage {
  id: string;
  role: Role;
  text: string;
  mcpCall?: McpCall;
  data?: AgentPayload;
  suggestions?: string[];
}

export interface Conversation {
  id: string;
  title: string;
}
