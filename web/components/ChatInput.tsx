"use client";

import { FormEvent, useState } from "react";
import { SendIcon } from "./icons";

export default function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled?: boolean;
}) {
  const [value, setValue] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-2 border-t border-black/5 p-4"
    >
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="질문을 입력하세요..."
        disabled={disabled}
        className="flex-1 rounded-full bg-surface px-4 py-2.5 text-sm text-gray-800 outline-none placeholder:text-muted focus:ring-2 focus:ring-brand/30"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand text-white transition hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-40"
        aria-label="전송"
      >
        <SendIcon />
      </button>
    </form>
  );
}
