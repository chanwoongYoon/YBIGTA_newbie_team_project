import { ChatMessage } from "@/lib/types";
import McpBadge from "./McpBadge";

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl bg-brand px-4 py-3 text-sm text-white shadow-card sm:max-w-[70%]">
          {message.text}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-start gap-1.5">
      {message.mcpCall && <McpBadge tool={message.mcpCall.tool} />}

      <div className="max-w-[90%] rounded-2xl bg-white px-4 py-3 text-sm text-gray-800 shadow-card sm:max-w-[75%]">
        <p>{message.text}</p>

        {message.data?.rows && message.data.rows.length > 0 && (
          <div className="mt-3 space-y-1.5">
            {message.data.rows.map((row, i) => (
              <div
                key={row.label}
                className="flex items-center justify-between gap-4 text-sm"
              >
                <span className="flex items-center gap-2 text-gray-700">
                  <span className="text-xs text-muted">{i + 1}</span>
                  {row.label}
                </span>
                <span className="font-semibold text-brand">{row.value}</span>
              </div>
            ))}
          </div>
        )}

        {message.data?.caption && (
          <p className="mt-3 border-t border-black/5 pt-2 text-xs text-muted">
            {message.data.caption}
          </p>
        )}
      </div>
    </div>
  );
}
