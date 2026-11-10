import { useRef, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Bell,
  CalendarDays,
  Check,
  ChevronDown,
  ClipboardList,
  Clock3,
  LayoutGrid,
  MapPin,
  MessageCircle,
  Sparkles,
  Truck,
  Users,
} from "lucide-react";
import { BrandBadge } from "./brand";

const views = [
  { id: "chats", label: "Переписка", icon: MessageCircle },
  { id: "orders", label: "Заказы", icon: ClipboardList },
  { id: "delivery", label: "Доставка", icon: Truck },
] as const;
type DemoView = (typeof views)[number]["id"];

const railItems = [
  { icon: LayoutGrid, label: "Сегодня", id: "today" },
  { icon: MessageCircle, label: "Чаты", id: "chats" },
  { icon: ClipboardList, label: "Заказы", id: "orders" },
  { icon: Truck, label: "Доставка", id: "delivery" },
  { icon: Users, label: "Клиенты", id: "customers" },
  { icon: Bell, label: "Напоминания", id: "reminders" },
];

const conversations = [
  {
    name: "Айдана",
    initials: "А",
    time: "10:42",
    channel: "WhatsApp",
    color: "lilac",
    message: "Здравствуйте! Можно букет с розовыми пионами на завтра?",
    reply: "Здравствуйте, Айдана! Конечно. На какое время нужна доставка?",
    followup: "К 18:00, пожалуйста. И добавьте открытку «С днём рождения!»",
    item: "Букет с розовыми пионами",
    detail: "Завтра, к 18:00",
    note: "«С днём рождения!»",
  },
  {
    name: "Данияр",
    initials: "Д",
    time: "10:25",
    channel: "Instagram",
    color: "peach",
    message: "Добрый день! Можно заказать белые розы и забрать сегодня?",
    reply: "Добрый день! Подготовим букет. Во сколько вам удобно забрать?",
    followup: "Подъеду к 17:30. Нужна светлая упаковка.",
    item: "Букет из белых роз",
    detail: "Сегодня, 17:30 · самовывоз",
    note: "Светлая упаковка",
  },
  {
    name: "Алина",
    initials: "А",
    time: "09:58",
    channel: "WhatsApp",
    color: "green",
    message: "Здравствуйте! Хочу сезонный букет с доставкой.",
    reply: "Здравствуйте! Соберём сезонный микс. К какому времени привезти?",
    followup: "Завтра к 12:00. Если можно, добавьте лавандовый акцент.",
    item: "Сезонный букет",
    detail: "Завтра, к 12:00",
    note: "Лавандовый акцент",
  },
] as const;

export function ProductDemo() {
  const [view, setView] = useState<DemoView>("chats");
  const [activeChat, setActiveChat] = useState(0);
  const [draft, setDraft] = useState<number | null>(null);
  const viewButtons = useRef<
    Partial<Record<DemoView, HTMLButtonElement | null>>
  >({});
  const contact = conversations[activeChat];
  const order = conversations[draft ?? 0];

  function showView(next: DemoView) {
    setView(next);
    viewButtons.current[next]?.focus({ preventScroll: true });
  }

  return (
    <section className="mk-demo" aria-label="Интерактивное демо Tapme Flowers">
      <div className="mk-demo-tabs" role="group" aria-label="Разделы демо">
        {views.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            ref={(node) => {
              viewButtons.current[id] = node;
            }}
            aria-pressed={view === id}
            onClick={() => setView(id)}
          >
            <Icon size={17} aria-hidden="true" /> {label}
          </button>
        ))}
      </div>
      <div className="mk-demo-backdrop">
        <div className="mk-demo-window">
          <aside className="mk-demo-rail" aria-hidden="true">
            <div className="mk-demo-brand">
              <BrandBadge size={18} />
              <span>
                tapme <small>FLOWERS</small>
              </span>
            </div>
            <span className="mk-demo-point">
              <MapPin size={13} /> Цветочный магазин <ChevronDown size={12} />
            </span>
            <span className="mk-demo-rail-label">РАБОЧЕЕ ПРОСТРАНСТВО</span>
            {railItems.map(({ icon: Icon, label, id }) => (
              <span key={id} className={id === view ? "is-active" : ""}>
                <Icon size={15} />
                {label}
              </span>
            ))}
          </aside>
          {view === "chats" ? (
            <div className="mk-demo-chat">
              <div className="mk-demo-conversations">
                <strong>Чаты</strong>
                <p>Входящие сообщения</p>
                {conversations.map((chat, index) => (
                  <button
                    key={chat.name}
                    type="button"
                    aria-pressed={index === activeChat}
                    onClick={() => setActiveChat(index)}
                  >
                    <span className={`mk-demo-avatar ${chat.color}`}>
                      {chat.initials}
                    </span>
                    <span className="mk-demo-chat-name">
                      <b>{chat.name}</b>
                      <small>{chat.channel}</small>
                    </span>
                    <time>{chat.time}</time>
                  </button>
                ))}
              </div>
              <div className="mk-demo-thread">
                <div className="mk-demo-thread-head">
                  <span className={`mk-demo-avatar ${contact.color}`}>
                    {contact.initials}
                  </span>
                  <span>
                    <b>{contact.name}</b>
                    <small>{contact.channel} · клиент магазина</small>
                  </span>
                </div>
                <div className="mk-demo-messages" aria-live="polite">
                  <span className="mk-demo-day">Сегодня</span>
                  <p>{contact.message}</p>
                  <p className="is-reply">{contact.reply}</p>
                  <p>{contact.followup}</p>
                </div>
                <div className="mk-demo-thread-foot">
                  <button
                    type="button"
                    onClick={() => {
                      setDraft(activeChat);
                      showView("orders");
                    }}
                  >
                    <Sparkles size={14} aria-hidden="true" /> Собрать заказ{" "}
                    <ArrowUpRight size={14} aria-hidden="true" />
                  </button>
                </div>
              </div>
            </div>
          ) : view === "orders" ? (
            <div className="mk-demo-sheet" aria-live="polite">
              <div className="mk-demo-sheet-head">
                <div>
                  <span>ЗАКАЗ № 1042</span>
                  <h3>
                    {draft === null ? "Карточка заказа" : "Черновик заказа"}
                  </h3>
                </div>
                <span className="mk-demo-badge">
                  {draft === null ? "В работе" : "Проверка деталей"}
                </span>
              </div>
              <dl>
                <div>
                  <dt>Клиент</dt>
                  <dd>{order.name}</dd>
                </div>
                <div>
                  <dt>Состав</dt>
                  <dd>{order.item}</dd>
                </div>
                <div>
                  <dt>Получение</dt>
                  <dd>{order.detail}</dd>
                </div>
                <div>
                  <dt>Пожелание</dt>
                  <dd>{order.note}</dd>
                </div>
              </dl>
              <button type="button" onClick={() => showView("delivery")}>
                Смотреть пример доставки{" "}
                <ArrowRight size={15} aria-hidden="true" />
              </button>
            </div>
          ) : (
            <div className="mk-demo-sheet" aria-live="polite">
              <div className="mk-demo-sheet-head">
                <div>
                  <span>ЗАКАЗ № 1041</span>
                  <h3>Букет уже в пути</h3>
                </div>
                <span className="mk-demo-badge">
                  <Truck size={13} aria-hidden="true" /> В пути
                </span>
              </div>
              <div className="mk-demo-delivery">
                <span>
                  <CalendarDays size={17} /> Сегодня
                </span>
                <span>
                  <Clock3 size={17} /> 16:00–18:00
                </span>
                <span>
                  <MapPin size={17} /> Бишкек
                </span>
              </div>
              <ol className="mk-demo-timeline">
                <li>
                  <Check size={14} /> Заказ принят
                </li>
                <li>
                  <Check size={14} /> Букет собран
                </li>
                <li aria-current="step">
                  <Truck size={14} /> Курьер в пути
                </li>
              </ol>
              <button type="button" onClick={() => showView("chats")}>
                Вернуться к переписке{" "}
                <ArrowRight size={15} aria-hidden="true" />
              </button>
            </div>
          )}
        </div>
      </div>
      <p className="mk-demo-caption">
        <span /> Интерактивный пример с вымышленными данными
      </p>
    </section>
  );
}
