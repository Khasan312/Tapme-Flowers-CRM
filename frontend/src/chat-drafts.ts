import { useCallback, useEffect, useState } from "react";
import { newUuid } from "./uuid";
import type { ChatReply } from "./chat-types";

function savedReply(value: unknown): ChatReply | null {
  if (!value || typeof value !== "object") return null;
  const row = value as Record<string, unknown>;
  if (
    typeof row.id !== "string" ||
    !/^[1-9][0-9]*$/.test(row.id) ||
    !["in", "out"].includes(String(row.direction)) ||
    !["text", "sender", "kind", "media_name"].every(
      (key) => typeof row[key] === "string",
    )
  )
    return null;
  return value as ChatReply;
}

const prefix = "tapme-chat-draft:";
export function clearChatDrafts() {
  try {
    for (const key of Object.keys(sessionStorage))
      if (key.startsWith(prefix) || key.startsWith("tapme-chat-navigation:"))
        sessionStorage.removeItem(key);
  } catch {
    /* Browser storage may be disabled. */
  }
}
export function useChatDraft(
  userId: string,
  businessId: string,
  chatId: string,
) {
  const key = `${prefix}${userId}:${businessId}:${chatId}`;
  const [draft, setStoredDraft] = useState(() => {
    try {
      const stored = JSON.parse(sessionStorage.getItem(key) || "null");
      if (
        typeof stored?.text === "string" &&
        typeof stored?.requestId === "string"
      )
        return {
          text: stored.text as string,
          requestId: stored.requestId as string,
          replyTo: savedReply(stored.replyTo),
        };
    } catch {
      /* Start with an empty draft. */
    }
    return {
      text: "",
      requestId: newUuid(),
      replyTo: null as ChatReply | null,
    };
  });
  const setDraft = useCallback(
    (next: { text: string; requestId: string; replyTo?: ChatReply | null }) => {
      setStoredDraft((current) => ({ ...current, ...next }));
    },
    [],
  );
  useEffect(() => {
    try {
      sessionStorage.setItem(key, JSON.stringify(draft));
    } catch {
      /* Keep the live draft even without storage. */
    }
  }, [key, draft]);
  return [draft, setDraft] as const;
}
