import { Instagram, MessageCircle, MessagesSquare } from "lucide-react";
import type { ChatChannel } from "./chat-types";
import "./chat-channels.css";

export function ChatChannelPicker({
  value,
  unread,
  select,
  placement,
}: {
  value: ChatChannel | null;
  unread: number;
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
        const count = channel === "whatsapp" ? unread : 0;
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

export function InstagramChats() {
  return (
    <section className="instagram-workspace" aria-label="Переписка в Instagram">
      <aside className="instagram-list">
        <header>
          <span className="instagram-brand">
            <Instagram size={20} />
            Instagram
          </span>
          <span className="instagram-status">Не подключён</span>
        </header>
        <div className="instagram-list-empty">
          <MessagesSquare size={26} />
          <strong>Сообщения Direct</strong>
          <p>Здесь появятся переписки с клиентами из Instagram.</p>
        </div>
      </aside>
      <div className="instagram-welcome">
        <span className="instagram-logo">
          <Instagram size={38} strokeWidth={1.6} />
        </span>
        <span className="instagram-eyebrow">
          Новый канал для вашего магазина
        </span>
        <h2>Ваш Instagram — рядом</h2>
        <p>
          Подключение пока не настроено. После подключения профессионального
          аккаунта вы сможете читать Direct и отвечать клиентам здесь.
        </p>
        <details className="instagram-setup">
          <summary>Что нужно для подключения?</summary>
          <ol>
            <li>
              Профессиональный аккаунт магазина в Instagram: «Бизнес» или
              «Автор».
            </li>
            <li>Настройка интеграции Meta и разрешений на переписку.</li>
            <li>Проверка входящего сообщения и ответа из CRM.</li>
          </ol>
          <p>
            Интеграцию Instagram ещё предстоит подключить. Добавлять сообщения
            вручную не нужно.
          </p>
        </details>
      </div>
    </section>
  );
}
