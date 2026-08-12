// Server-only. Never import this from a Client Component.
// Talks to the MCP Server over HTTP using MCP_SERVER_URL / MCP_AUTH_TOKEN,
// both of which live only in the Vercel server environment (never NEXT_PUBLIC_*).

export interface McpToolSchema {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface McpToolResult {
  tool: string;
  result: unknown;
}

function getConfig() {
  const baseUrl = process.env.MCP_SERVER_URL;
  const token = process.env.MCP_AUTH_TOKEN;
  return { baseUrl, token };
}

export function isMcpConfigured(): boolean {
  const { baseUrl, token } = getConfig();
  return Boolean(baseUrl && token);
}

export async function listMcpTools(): Promise<McpToolSchema[]> {
  const { baseUrl, token } = getConfig();
  if (!baseUrl || !token) {
    throw new Error("MCP_SERVER_URL / MCP_AUTH_TOKEN is not configured");
  }

  const res = await fetch(`${baseUrl}/tools`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Failed to list MCP tools: ${res.status}`);
  }

  return res.json();
}

export async function callMcpTool(
  name: string,
  args: Record<string, unknown>
): Promise<McpToolResult> {
  const { baseUrl, token } = getConfig();
  if (!baseUrl || !token) {
    throw new Error("MCP_SERVER_URL / MCP_AUTH_TOKEN is not configured");
  }

  const res = await fetch(`${baseUrl}/tools/${name}/call`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ arguments: args }),
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`MCP tool call failed (${name}): ${res.status}`);
  }

  const result = await res.json();
  return { tool: name, result };
}
