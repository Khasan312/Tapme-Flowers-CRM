import { useEffect, useRef } from "react";
import type { ChatChannel } from "./chat-types";
import type { WorkspaceRoute } from "./navigation";

type ChannelHistory = {
  channel: ChatChannel;
  whatsapp: string | null;
  instagram: string | null;
};
const emptyHistory = (): ChannelHistory => ({
  channel: "whatsapp",
  whatsapp: null,
  instagram: null,
});
const isChatId = (value: unknown): value is string =>
  typeof value === "string" &&
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);

export function useChatChannelNavigation(
  userId: string,
  route: WorkspaceRoute,
) {
  const memory = useRef(new Map<string, ChannelHistory>());
  const key =
    userId && route.businessId
      ? `tapme-chat-navigation:${userId}:${route.businessId}`
      : "";

  function read(): ChannelHistory {
    if (!key) return emptyHistory();
    const cached = memory.current.get(key);
    if (cached) return cached;
    try {
      const stored = JSON.parse(sessionStorage.getItem(key) || "null");
      return {
        channel: stored?.channel === "instagram" ? "instagram" : "whatsapp",
        whatsapp: isChatId(stored?.whatsapp) ? stored.whatsapp : null,
        instagram: isChatId(stored?.instagram) ? stored.instagram : null,
      };
    } catch {
      return emptyHistory();
    }
  }

  function remember() {
    const saved = read();
    if (!key || route.view !== "chats") return saved;
    const next = {
      ...saved,
      channel: route.chatChannel,
      [route.chatChannel]: route.chatId,
    };
    memory.current.set(key, next);
    try {
      sessionStorage.setItem(key, JSON.stringify(next));
    } catch {
      // Keep the selection in memory when browser storage is unavailable.
    }
    return next;
  }

  useEffect(() => {
    memory.current.clear();
  }, [userId]);
  useEffect(() => {
    remember();
  }, [key, route.view, route.chatChannel, route.chatId]);

  return (channel?: ChatChannel): WorkspaceRoute => {
    const saved = remember();
    const next = channel ?? saved.channel;
    return {
      ...route,
      view: "chats",
      chatChannel: next,
      chatId: saved[next],
      orderId: null,
      customerId: null,
    };
  };
}
