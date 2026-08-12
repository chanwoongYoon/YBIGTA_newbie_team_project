"use client";

import { useEffect, useRef } from "react";
import { ChatMessage } from "@/lib/types";
import MessageBubble from "./MessageBubble";
import SuggestedChips from "./SuggestedChips";

export default function ChatWindow({
  messages,
  isLoading,
  onSuggestionSelect,
}: {
  messages: ChatMessage[];
  isLoading: boolean;
  onSuggestionSelect: (text: string) => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const lastAgentMessage = [...messages].reverse().find((m) => m.role === "agent");

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}

      {isLoading && (
        <div className="flex items-center gap-1.5 rounded-2xl bg-white px-4 py-3 text-sm text-muted shadow-card w-fit">
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand [animation-delay:-0.2s]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand [animation-delay:-0.1s]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand" />
        </div>
      )}

      {!isLoading && lastAgentMessage?.suggestions && (
        <SuggestedChips
          suggestions={lastAgentMessage.suggestions}
          onSelect={onSuggestionSelect}
        />
      )}

      <div ref={bottomRef} />
    </div>
  );
}
