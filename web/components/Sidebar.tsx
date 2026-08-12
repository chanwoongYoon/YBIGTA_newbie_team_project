"use client";

import { Conversation } from "@/lib/types";
import { AgentAvatar, PlusIcon } from "./icons";

interface SidebarProps {
  conversations: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  onNewConversation: () => void;
  bookTitle: string;
  collectedCount: number;
}

export default function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNewConversation,
  bookTitle,
  collectedCount,
}: SidebarProps) {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-black/5 bg-white/70 md:flex">
      <div className="flex items-center gap-2 px-5 pt-5">
        <AgentAvatar />
        <span className="text-sm font-semibold text-gray-900">리뷰 분석</span>
      </div>

      <div className="px-4 pt-4">
        <button
          onClick={onNewConversation}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-brand px-3 py-2 text-sm font-medium text-white transition hover:bg-brand-dark"
        >
          <PlusIcon />
          새 대화
        </button>
      </div>

      <div className="mt-5 flex-1 overflow-y-auto px-4">
        <p className="px-1 pb-2 text-xs font-medium text-muted">최근 대화</p>
        <ul className="space-y-1">
          {conversations.map((c) => {
            const active = c.id === activeId;
            return (
              <li key={c.id}>
                <button
                  onClick={() => onSelect(c.id)}
                  className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition ${
                    active
                      ? "bg-brand-light font-medium text-brand-dark"
                      : "text-gray-600 hover:bg-black/5"
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                      active ? "bg-brand" : "bg-gray-300"
                    }`}
                  />
                  <span className="truncate">{c.title}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="flex items-center gap-2 border-t border-black/5 px-5 py-4">
        <span className="text-lg">📖</span>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-gray-900">{bookTitle}</p>
          <p className="truncate text-xs text-muted">
            실시간 리뷰 {collectedCount}건 수집 중
          </p>
        </div>
      </div>
    </aside>
  );
}
