import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Smile, X } from "lucide-react";
import "./chat-emoji.css";

const categories = [
  {
    name: "Смайлики",
    icon: "😊",
    items: [
      ["😊", "Улыбка"],
      ["😀", "Радость"],
      ["😄", "Счастье"],
      ["😁", "Широкая улыбка"],
      ["😂", "Смех"],
      ["🤣", "Очень смешно"],
      ["😉", "Подмигивание"],
      ["🥰", "Влюблённость"],
      ["😍", "Восторг"],
      ["😘", "Поцелуй"],
      ["😎", "Круто"],
      ["🤩", "Восхищение"],
      ["🥳", "Праздник"],
      ["😇", "Ангел"],
      ["🤗", "Обнимаю"],
      ["🤔", "Думаю"],
      ["😔", "Грусть"],
      ["🥹", "Тронут до слёз"],
    ],
  },
  {
    name: "Сердца",
    icon: "❤️",
    items: [
      ["❤️", "Красное сердце"],
      ["🩷", "Розовое сердце"],
      ["🧡", "Оранжевое сердце"],
      ["💛", "Жёлтое сердце"],
      ["💚", "Зелёное сердце"],
      ["💙", "Синее сердце"],
      ["💜", "Фиолетовое сердце"],
      ["🤍", "Белое сердце"],
      ["💕", "Два сердца"],
      ["💖", "Сияющее сердце"],
      ["💝", "Сердце в подарок"],
      ["💌", "Любовное письмо"],
    ],
  },
  {
    name: "Цветы",
    icon: "💐",
    items: [
      ["💐", "Букет"],
      ["🌹", "Роза"],
      ["🌷", "Тюльпан"],
      ["🌸", "Сакура"],
      ["🌺", "Гибискус"],
      ["🌻", "Подсолнух"],
      ["🌼", "Ромашка"],
      ["🪻", "Гиацинт"],
      ["🌿", "Зелень"],
      ["✨", "Искорки"],
      ["🎁", "Подарок"],
      ["🎉", "Поздравление"],
    ],
  },
  {
    name: "Жесты",
    icon: "👍",
    items: [
      ["👍", "Отлично"],
      ["👋", "Привет"],
      ["👌", "Хорошо"],
      ["🙏", "Спасибо"],
      ["🤝", "Договорились"],
      ["👏", "Аплодисменты"],
      ["🙌", "Ура"],
      ["🫶", "Сердце руками"],
      ["🤞", "На удачу"],
      ["💪", "Сила"],
      ["✅", "Готово"],
      ["🚚", "Доставка"],
    ],
  },
];

export function ChatEmojiPicker({
  disabled,
  insert,
}: {
  disabled: boolean;
  insert: (emoji: string) => boolean;
}) {
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const id = useId();
  return (
    <>
      <button
        ref={trigger}
        className="chat-emoji-toggle"
        type="button"
        aria-label="Добавить смайлик"
        title="Добавить смайлик"
        aria-haspopup="dialog"
        aria-expanded={open && !disabled}
        aria-controls={open && !disabled ? id : undefined}
        disabled={disabled}
        onClick={() => setOpen((value) => !value)}
      >
        <Smile size={21} />
      </button>
      {open && !disabled && trigger.current && (
        <EmojiPanel
          id={id}
          trigger={trigger.current}
          close={() => setOpen(false)}
          insert={insert}
        />
      )}
    </>
  );
}

function EmojiPanel({
  id,
  trigger,
  close,
  insert,
}: {
  id: string;
  trigger: HTMLButtonElement;
  close: () => void;
  insert: (emoji: string) => boolean;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const [category, setCategory] = useState(0);
  const [limitReached, setLimitReached] = useState(false);
  const [position, setPosition] = useState({ left: 8, top: 8 });
  useLayoutEffect(() => {
    function place() {
      const viewport = window.visualViewport;
      const left = (viewport?.offsetLeft || 0) + 8;
      const top = (viewport?.offsetTop || 0) + 8;
      const width = viewport?.width || window.innerWidth;
      const height = viewport?.height || window.innerHeight;
      const anchor = trigger.getBoundingClientRect();
      const box = panel.current!.getBoundingClientRect();
      setPosition({
        left: Math.max(
          left,
          Math.min(anchor.left, left + width - box.width - 16),
        ),
        top: Math.max(
          top,
          Math.min(anchor.top - box.height - 8, top + height - box.height - 16),
        ),
      });
    }
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    window.visualViewport?.addEventListener("resize", place);
    window.visualViewport?.addEventListener("scroll", place);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
      window.visualViewport?.removeEventListener("resize", place);
      window.visualViewport?.removeEventListener("scroll", place);
    };
  }, [trigger, category, limitReached]);
  useLayoutEffect(() => {
    panel.current
      ?.querySelector<HTMLButtonElement>('[aria-pressed="true"]')
      ?.focus({ preventScroll: true });
  }, []);
  useEffect(() => {
    function outside(event: Event) {
      if (
        !panel.current?.contains(event.target as Node) &&
        !trigger.contains(event.target as Node)
      )
        close();
    }
    document.addEventListener("pointerdown", outside);
    document.addEventListener("focusin", outside);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("focusin", outside);
    };
  }, [close, trigger]);
  function dismiss() {
    close();
    trigger.focus({ preventScroll: true });
  }
  return createPortal(
    <div
      ref={panel}
      id={id}
      className="chat-emoji-panel"
      role="dialog"
      aria-label="Выбор смайлика"
      style={position}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.preventDefault();
          event.stopPropagation();
          dismiss();
        }
      }}
    >
      <header>
        <strong>Смайлики</strong>
        <button type="button" aria-label="Закрыть смайлики" onClick={dismiss}>
          <X size={17} />
        </button>
      </header>
      <div
        className="chat-emoji-categories"
        role="group"
        aria-label="Категории смайликов"
      >
        {categories.map((item, index) => (
          <button
            key={item.name}
            type="button"
            aria-pressed={category === index}
            onClick={() => setCategory(index)}
          >
            <span aria-hidden="true">{item.icon}</span>
            {item.name}
          </button>
        ))}
      </div>
      <div
        className="chat-emoji-grid"
        role="group"
        aria-label={categories[category].name}
      >
        {categories[category].items.map(([emoji, label]) => (
          <button
            key={emoji}
            type="button"
            aria-label={label}
            title={label}
            onClick={() => {
              if (insert(emoji)) close();
              else setLimitReached(true);
            }}
          >
            {emoji}
          </button>
        ))}
      </div>
      <p role="status">
        {limitReached
          ? "Достигнут лимит сообщения. Сократите текст, чтобы добавить смайлик."
          : "Смайлик добавится в текст сообщения"}
      </p>
    </div>,
    document.body,
  );
}
