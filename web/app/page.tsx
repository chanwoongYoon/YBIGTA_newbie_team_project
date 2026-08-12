"use client";

import { useState } from "react";
import { ChatMessage, Conversation } from "@/lib/types";
import Sidebar from "@/components/Sidebar";
import MobileHeader from "@/components/MobileHeader";
import ChatWindow from "@/components/ChatWindow";
import ChatInput from "@/components/ChatInput";

const CONVERSATIONS: Conversation[] = [
  { id: "c1", title: "요즘 리뷰에서 자주 나오는 키워드는?" },
  { id: "c2", title: "별점 추이 분석" },
  { id: "c3", title: "긍정/부정 리뷰 비율" },
];

const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "agent",
  text: "안녕하세요! 👋 《불편한 편의점》 리뷰 데이터를 실시간으로 모아 분석해드려요. 무엇이 궁금하세요?",
  suggestions: ["요즘 리뷰에서 자주 나오는 키워드가 뭐야?"],
};

let messageId = 1;
function nextId() {
  messageId += 1;
  return `m${messageId}`;
}

export default function HomePage() {
  const [activeConversation, setActiveConversation] = useState(CONVERSATIONS[0].id);
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSend(text: string) {
    const userMessage: ChatMessage = { id: nextId(), role: "user", text };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      if (!res.ok) throw new Error("request failed");

      const data = await res.json();
      const agentMessage: ChatMessage = {
        id: nextId(),
        role: "agent",
        text: data.text,
        mcpCall: data.mcpCall,
        data: data.data,
        suggestions: data.suggestions,
      };
      setMessages((prev) => [...prev, agentMessage]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: "agent",
          text: "죄송해요, 답변을 가져오는 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleNewConversation() {
    setMessages([WELCOME_MESSAGE]);
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface p-4 sm:p-8">
      <div className="flex h-[85vh] w-full max-w-4xl overflow-hidden rounded-xl2 bg-white shadow-panel">
        <Sidebar
          conversations={CONVERSATIONS}
          activeId={activeConversation}
          onSelect={setActiveConversation}
          onNewConversation={handleNewConversation}
          bookTitle="불편한 편의점"
          collectedCount={342}
        />

        <div className="flex min-w-0 flex-1 flex-col bg-surface/40">
          <MobileHeader />
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onSuggestionSelect={handleSend}
          />
          <ChatInput onSend={handleSend} disabled={isLoading} />
        </div>
      </div>
    </main>
  );
}
