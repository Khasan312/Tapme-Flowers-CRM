import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { CheckSquare, Copy, Reply } from "lucide-react";
import type { ChatMessage, ChatReply } from "./chat-types";
import "./chat-message-actions.css";

export function messageText(
  message: Pick<ChatReply, "text" | "kind" | "media_name">,
) {
  const attachment =
    message.media_name ||
    (
      {
        image: "Фото",
        document: "Документ",
        audio: "Аудио",
        video: "Видео",
        sticker: "Стикер",
      } as Record<string, string>
    )[message.kind];
  return (
    [attachment ? `[${attachment}]` : "", message.text]
      .filter(Boolean)
      .join("\n") || "Сообщение без текста"
  );
}

export async function copyMessageText(text: string) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
  } catch {
    /* Local HTTP and browser permissions may require the selection fallback. */
  }
  const active = document.activeElement as HTMLElement | null;
  const input = document.createElement("textarea");
  input.value = text;
  input.readOnly = true;
  input.style.cssText =
    "position:fixed;left:0;top:0;opacity:0;pointer-events:none;font-size:16px";
  document.body.append(input);
  try {
    input.focus({ preventScroll: true });
    input.select();
    if (!document.execCommand("copy")) throw new Error("Clipboard unavailable");
  } finally {
    input.remove();
    active?.focus({ preventScroll: true });
  }
}

export type MessageMenuTarget = {
  message: ChatMessage;
  trigger: HTMLElement;
  x: number;
  y: number;
};

export function MessageBubble({
  message,
  className,
  selecting,
  selected,
  toggle,
  menu,
  children,
}: {
  message: ChatMessage;
  className: string;
  selecting: boolean;
  selected: boolean;
  toggle: () => void;
  menu: (target: MessageMenuTarget) => void;
  children: ReactNode;
}) {
  const press = useRef<{ timer: number; x: number; y: number } | null>(null);
  const held = useRef(false);
  const moved = useRef(false);
  function cancel() {
    if (press.current) window.clearTimeout(press.current.timer);
    press.current = null;
  }
  useEffect(() => cancel, []);
  function open(trigger: HTMLElement, x: number, y: number) {
    menu({ message, trigger, x, y });
  }
  return (
    <article
      className={`${className} chat-action-bubble ${selecting ? "is-selecting" : ""} ${selected ? "is-selected" : ""}`}
      tabIndex={0}
      data-message-id={message.id}
      aria-label={`${message.direction === "system" ? "Системное" : message.direction === "out" ? "Исходящее" : "Входящее"} сообщение`}
      aria-haspopup="menu"
      onContextMenu={(event) => {
        event.preventDefault();
        cancel();
        if (!moved.current) {
          held.current = true;
          open(event.currentTarget, event.clientX, event.clientY);
        }
      }}
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget) return;
        if (
          event.key === "ContextMenu" ||
          (event.shiftKey && event.key === "F10")
        ) {
          event.preventDefault();
          const box = event.currentTarget.getBoundingClientRect();
          open(event.currentTarget, box.left + 16, box.bottom);
        } else if (selecting && ["Enter", " "].includes(event.key)) {
          event.preventDefault();
          toggle();
        }
      }}
      onClickCapture={(event) => {
        if (held.current || moved.current) {
          event.preventDefault();
          event.stopPropagation();
          held.current = moved.current = false;
          return;
        }
        if (
          selecting &&
          !(event.target as HTMLElement).closest(".chat-message-select")
        ) {
          event.preventDefault();
          event.stopPropagation();
          toggle();
        }
      }}
      onPointerDown={(event) => {
        cancel();
        held.current = moved.current = false;
        if (
          event.pointerType !== "touch" ||
          !event.isPrimary ||
          (event.target as HTMLElement).closest("button,input,a,audio")
        )
          return;
        const trigger = event.currentTarget,
          x = event.clientX,
          y = event.clientY;
        press.current = {
          x,
          y,
          timer: window.setTimeout(() => {
            press.current = null;
            held.current = true;
            open(trigger, x, y);
          }, 550),
        };
      }}
      onPointerMove={(event) => {
        if (
          press.current &&
          Math.hypot(
            event.clientX - press.current.x,
            event.clientY - press.current.y,
          ) > 10
        ) {
          moved.current = true;
          cancel();
        }
      }}
      onPointerUp={cancel}
      onPointerLeave={cancel}
      onPointerCancel={() => {
        moved.current = true;
        cancel();
      }}
    >
      {selecting && (
        <input
          className="chat-message-select"
          type="checkbox"
          aria-label={`Выбрать сообщение ${message.id}`}
          checked={selected}
          onChange={toggle}
        />
      )}
      {children}
    </article>
  );
}

export function MessageActionsMenu({
  target,
  close,
  reply,
  copy,
  select,
  canReply,
  replyReason,
}: {
  target: MessageMenuTarget;
  close: () => void;
  reply: () => void;
  copy: () => Promise<boolean>;
  select: () => void;
  canReply: boolean;
  replyReason: string;
}) {
  const node = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ left: target.x, top: target.y });
  const [copying, setCopying] = useState(false);
  useLayoutEffect(() => {
    const box = node.current!.getBoundingClientRect();
    setPosition({
      left: Math.max(8, Math.min(target.x, window.innerWidth - box.width - 8)),
      top: Math.max(8, Math.min(target.y, window.innerHeight - box.height - 8)),
    });
    node.current
      ?.querySelector<HTMLButtonElement>("button:not(:disabled)")
      ?.focus({ preventScroll: true });
  }, [target]);
  useEffect(() => {
    function outside(event: Event) {
      if (!node.current?.contains(event.target as Node)) close();
    }
    document.addEventListener("pointerdown", outside);
    document.addEventListener("scroll", outside, true);
    window.addEventListener("resize", close);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("scroll", outside, true);
      window.removeEventListener("resize", close);
    };
  }, [close]);
  function restore() {
    target.trigger.focus({ preventScroll: true });
    close();
  }
  return createPortal(
    <div
      ref={node}
      className="chat-context-menu chat-message-menu"
      role="menu"
      aria-label="Действия с сообщением"
      style={position}
      onContextMenu={(e) => e.preventDefault()}
      onKeyDown={(event) => {
        if (event.key === "Escape" || event.key === "Tab") {
          event.stopPropagation();
          if (event.key === "Escape") event.preventDefault();
          restore();
        } else if (
          ["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)
        ) {
          event.preventDefault();
          const items = [
            ...node.current!.querySelectorAll<HTMLButtonElement>(
              "button:not(:disabled)",
            ),
          ];
          const index = items.indexOf(
            document.activeElement as HTMLButtonElement,
          );
          items[
            event.key === "Home"
              ? 0
              : event.key === "End"
                ? items.length - 1
                : (index +
                    (event.key === "ArrowDown" ? 1 : -1) +
                    items.length) %
                  items.length
          ]?.focus();
        }
      }}
    >
      <button
        type="button"
        role="menuitem"
        disabled={!canReply || copying}
        title={canReply ? undefined : replyReason}
        onClick={() => {
          close();
          reply();
        }}
      >
        <Reply size={17} />
        Ответить
      </button>
      <button
        type="button"
        role="menuitem"
        disabled={copying}
        onClick={async () => {
          setCopying(true);
          if (await copy()) restore();
          else setCopying(false);
        }}
      >
        <Copy size={17} />
        {copying ? "Копируем…" : "Скопировать"}
      </button>
      <button
        type="button"
        role="menuitem"
        disabled={copying}
        onClick={() => {
          restore();
          select();
        }}
      >
        <CheckSquare size={17} />
        Выбрать
      </button>
    </div>,
    document.body,
  );
}
