import { useEffect, useState } from "react";
import { newUuid } from "./uuid";

const prefix = "tapme-chat-draft:";
export function clearChatDrafts() {
  try {
    for (const key of Object.keys(sessionStorage))
      if (key.startsWith(prefix)) sessionStorage.removeItem(key);
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
  const [draft, setDraft] = useState(() => {
    try {
      const stored = JSON.parse(sessionStorage.getItem(key) || "null");
      if (
        typeof stored?.text === "string" &&
        typeof stored?.requestId === "string"
      )
        return {
          text: stored.text as string,
          requestId: stored.requestId as string,
        };
    } catch {
      /* Start with an empty draft. */
    }
    return { text: "", requestId: newUuid() };
  });
  useEffect(() => {
    try {
      sessionStorage.setItem(key, JSON.stringify(draft));
    } catch {
      /* Keep the live draft even without storage. */
    }
  }, [key, draft]);
  return [draft, setDraft] as const;
}
