import { Instagram, MessageCircle } from "lucide-react";
import type { ChatChannel } from "./chat-types";
import "./chat-channels.css";
export { InstagramChats } from "./instagram-chats";

export function ChatChannelPicker({
  value,
  unread,
  instagramUnread = 0,
  select,
  placement,
}: {
  value: ChatChannel | null;
  unread: number;
  instagramUnread?: number;
  select: (channel: ChatChannel) => void;
  placement: "sidebar" | "mobile";
}) {
  return (
    <div
      className={`chat-channel-picker is-${placement}`}
      role="group"
      aria-label="Каналы чатов"
    >
      {(["whatsapp", "instagram"] as const).map((channel) => {
        const name = channel === "whatsapp" ? "WhatsApp" : "Instagram";
        const Icon = channel === "whatsapp" ? MessageCircle : Instagram;
        const count = channel === "whatsapp" ? unread : instagramUnread;
        return (
          <button
            key={channel}
            type="button"
            data-channel={channel}
            aria-label={name}
            aria-pressed={value === channel}
            aria-description={
              count ? `${count} непрочитанных сообщений` : undefined
            }
            onClick={() => select(channel)}
          >
            <Icon size={16} />
            <span>{name}</span>
            {count > 0 && (
              <span className="chat-channel-count" aria-hidden="true">
                {count > 99 ? "99+" : count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
