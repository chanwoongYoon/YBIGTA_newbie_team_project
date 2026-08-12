export default function McpBadge({ tool }: { tool: string }) {
  return (
    <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-brand-light px-3 py-1 text-xs font-medium text-brand-dark">
      <span className="h-1.5 w-1.5 rounded-full bg-brand" />
      MCP · {tool}() 호출됨
    </span>
  );
}
