import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import {
  ArrowDown,
  ArrowLeft,
  CalendarDays,
  Check,
  CheckCheck,
  CircleAlert,
  Clock3,
  MessageCircle,
  Paperclip,
  Search,
  Send,
  Settings2,
  ShoppingBag,
  UserRound,
  X,
} from "lucide-react";
import { ApiError, businessPath, errorText, price, request } from "./api";
import { Notice, Pager } from "./components";
import { useRemote } from "./hooks";
import { Avatar, shortDate } from "./ui";
import { newUuid } from "./uuid";
import { useChatDraft } from "./chat-drafts";
import type { Business, Customer, Page } from "./types";
import type {
  Channel,
  ChatDetail,
  ChatMessage,
  Conversation,
} from "./chat-types";
import "./chats.css";
import { PaymentDialog, QuickReplies } from "./chat-extras";
import { OrderDraftCard } from "./order-draft";
import {
  ChatContextMenu,
  ChatListItem,
  type ChatMenuTarget,
} from "./chat-menu";

const filters = {
  all: "Все",
  waiting: "Ждут ответа",
  mine: "Мои",
  closed: "Архив",
};
const statuses = {
  queued: "В очереди",
  sending: "Отправляем",
  unknown: "Нет подтверждения",
  sent: "Отправлено",
  delivered: "Доставлено",
  read: "Прочитано",
  failed: "Не отправлено",
  received: "Получено",
};

function waitingTime(since: string) {
  const minutes = Math.max(
    1,
    Math.floor((Date.now() - new Date(since).getTime()) / 60000),
  );
  if (minutes < 60) return `${minutes} мин`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder ? `${hours}ч ${remainder}мин` : `${hours}ч`;
}

type Props = {
  userId: string;
  business: Business;
  chatId: string | null;
  select: (id: string | null) => void;
  settings: () => void;
  openCustomer: (id: string) => void;
  openOrder: (id: string) => void;
  newOrder: (customer: Customer) => void;
};
export function Chats(props: Props) {
  const { business, chatId, select, settings } = props;
  const [revision, setRevision] = useState(0);
  const [category, setCategory] = useState<keyof typeof filters>("all");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [menu, setMenu] = useState<ChatMenuTarget | null>(null);
  const [actionRevision, setActionRevision] = useState(0);
  const closeMenu = useCallback(() => setMenu(null), []);
  useEffect(closeMenu, [
    business.id,
    business.point_id,
    category,
    search,
    offset,
    chatId,
    closeMenu,
  ]);
  const channel = useRemote<Channel>(
    businessPath(business.id, "channels/whatsapp"),
    revision,
  );
  const list = useRemote<
    Page<Conversation> & { stats: Record<string, number> }
  >(
    businessPath(business.id, "chats") +
      `?category=${category}&search=${encodeURIComponent(search)}&offset=${offset}&limit=50`,
    revision,
  );
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible" && navigator.onLine)
        setRevision((v) => v + 1);
    }, 5000);
    return () => window.clearInterval(timer);
  }, []);
  return (
    <section
      className={`chat-workspace ${chatId ? "has-conversation" : ""}`}
      aria-label="Переписка с клиентами"
    >
      <aside className="chat-list-panel">
        <div className="chat-list-heading">
          <h1>Чаты</h1>
          <span>WhatsApp</span>
          <button
            className="chat-icon"
            aria-label="Подключение WhatsApp"
            onClick={settings}
          >
            <Settings2 size={18} />
          </button>
        </div>
        <label className="chat-search">
          <Search size={16} />
          <input
            aria-label="Поиск диалогов"
            placeholder="Имя или телефон"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <div className="chat-filters" role="tablist" aria-label="Фильтры чатов">
          {Object.entries(filters).map(([key, label]) => (
            <button
              key={key}
              role="tab"
              aria-selected={category === key}
              className={category === key ? "active" : ""}
              onClick={() => {
                setCategory(key as keyof typeof filters);
                setOffset(0);
              }}
            >
              {label}
              <span>{list.data?.stats[key] || 0}</span>
            </button>
          ))}
        </div>
        {list.error && <Notice>{list.error}</Notice>}
        <div className="chat-list">
          {list.data?.results.map((row) => (
            <ChatListItem
              key={row.id}
              row={row}
              selected={chatId === row.id}
              expanded={menu?.row.id === row.id}
              open={() => select(row.id)}
              menu={setMenu}
            >
              <span className="chat-avatar">
                <Avatar name={row.name} />
                <MessageCircle size={13} />
              </span>
              <span className="chat-row-copy">
                <strong>{row.name}</strong>
                {row.new_customer && (
                  <small className="chat-mini green">новый клиент</small>
                )}
                <span>{row.preview || "Новый диалог"}</span>
              </span>
              <span className="chat-row-meta">
                <time>
                  {new Date(row.last_message_at).toLocaleTimeString("ru-RU", {
                    timeZone: business.timezone,
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </time>
                {row.unread > 0 ? (
                  <b>{row.unread}</b>
                ) : row.waiting_since ? (
                  <em>ждёт {waitingTime(row.waiting_since)}</em>
                ) : null}
              </span>
            </ChatListItem>
          ))}
        </div>
        {!list.loading && !list.data?.results.length && (
          <div className="chat-list-empty">
            <MessageCircle size={28} />
            <strong>
              {search ? "Диалоги не найдены" : "Здесь появятся диалоги"}
            </strong>
            <p>
              {channel.data?.status === "active"
                ? "Когда клиент напишет на подключённый номер, его сообщение появится здесь."
                : "Подключите WhatsApp, чтобы принимать сообщения клиентов."}
            </p>
          </div>
        )}
        {(list.data?.count || 0) > 50 && (
          <Pager
            count={list.data!.count}
            offset={offset}
            setOffset={setOffset}
          />
        )}
        <button
          className={`chat-connection ${channel.data?.status === "active" ? "connected" : ""}`}
          onClick={settings}
        >
          <i />
          {channel.data?.status === "active"
            ? channel.data.display_phone
            : "Подключить WhatsApp"}
        </button>
      </aside>
      {chatId ? (
        <ConversationPane
          key={business.id + chatId}
          {...props}
          chatId={chatId}
          actionRevision={actionRevision}
          changed={() => setRevision((v) => v + 1)}
        />
      ) : (
        <div className="chat-welcome">
          <span>
            <MessageCircle size={46} />
          </span>
          <h2>
            {channel.data?.status === "active"
              ? "Все разговоры — рядом"
              : "Ваш WhatsApp — в CRM"}
          </h2>
          <p>
            {channel.data?.status === "active"
              ? "Выберите диалог слева, чтобы прочитать сообщения и ответить клиенту."
              : "Подключите номер: сообщения будут приходить сюда, а рядом с перепиской будут заказы и карточка клиента."}
          </p>
          {channel.data?.status !== "active" && (
            <button className="btn primary" onClick={settings}>
              Настроить подключение
            </button>
          )}
          <div className="chat-welcome-facts">
            <span>
              <MessageCircle size={18} />
              Переписка и ответы
            </span>
            <span>
              <UserRound size={18} />
              Карточка клиента
            </span>
            <span>
              <ShoppingBag size={18} />
              Заказы из диалога
            </span>
          </div>
        </div>
      )}
      {menu && (
        <ChatContextMenu
          key={menu.row.id}
          target={{
            ...menu,
            row:
              list.data?.results.find((row) => row.id === menu.row.id) ||
              menu.row,
          }}
          businessId={business.id}
          userId={props.userId}
          close={closeMenu}
          open={select}
          changed={() => {
            setRevision((value) => value + 1);
            setActionRevision((value) => value + 1);
          }}
        />
      )}
    </section>
  );
}

function ConversationPane({
  userId,
  business,
  chatId,
  select,
  openCustomer,
  openOrder,
  newOrder,
  changed,
  actionRevision,
}: Props & { chatId: string; changed: () => void; actionRevision: number }) {
  const path = businessPath(business.id, `chats/${chatId}`);
  const [revision, setRevision] = useState(0);
  useEffect(() => setRevision((value) => value + 1), [actionRevision]);
  const detail = useRemote<ChatDetail>(path, revision);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [{ text, requestId }, setDraft] = useChatDraft(
    userId,
    business.id,
    chatId,
  );
  const [file, setFile] = useState<File | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const [templatesOpen, setTemplatesOpen] = useState(false);
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [quickOpen, setQuickOpen] = useState(false);
  const [customerName, setCustomerName] = useState("");
  const templates = useRemote<{
    custom_templates: { id: string; name: string; text: string }[];
  }>(templatesOpen ? businessPath(business.id, "reminder-rules") : null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [denied, setDenied] = useState(false);
  const [more, setMore] = useState(false),
    [olderBusy, setOlderBusy] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [newMessages, setNewMessages] = useState(false);
  const scroll = useRef<HTMLDivElement>(null),
    bottom = useRef(true),
    initial = useRef(true);
  const messageRef = useRef(messages);
  messageRef.current = messages;
  const preserveHeight = useRef<number | null>(null);
  function merge(rows: ChatMessage[], older = false) {
    if (
      !older &&
      !bottom.current &&
      rows.some((m) => !messageRef.current.some((old) => old.id === m.id))
    )
      setNewMessages(true);
    setMessages((old) =>
      [...new Map([...old, ...rows].map((m) => [m.id, m])).values()].sort(
        (a, b) => Number(a.id) - Number(b.id),
      ),
    );
  }
  useEffect(() => {
    let live = true,
      active = false;
    const controller = new AbortController();
    async function poll() {
      if (active || document.visibilityState !== "visible" || !navigator.onLine)
        return;
      active = true;
      try {
        const result = await request<{
          results: ChatMessage[];
          has_more: boolean;
        }>(path + "messages/?limit=50", { signal: controller.signal });
        if (!live) return;
        // Also fetch a gap after the newest known message if a large burst arrived.
        let rows = result.results;
        const newest = messageRef.current.at(-1)?.id;
        if (newest && rows.length && Number(rows[0].id) > Number(newest)) {
          let after = newest;
          for (;;) {
            const delta = await request<{
              results: ChatMessage[];
              has_more: boolean;
            }>(path + `messages/?after=${after}&limit=100`, {
              signal: controller.signal,
            });
            if (!live) return;
            rows = [...rows, ...delta.results];
            if (!delta.has_more || !delta.results.length) break;
            after = delta.results.at(-1)!.id;
          }
        }
        merge(rows);
        if (initial.current) {
          setMore(result.has_more);
          initial.current = false;
        }
        if (bottom.current && result.results.length)
          await request(path + "read/", {
            method: "POST",
            body: JSON.stringify({
              last_message_id: result.results.at(-1)!.id,
            }),
            signal: controller.signal,
          });
        if (live) {
          setRevision((v) => v + 1);
          changed();
        }
      } catch (e) {
        if (!live || (e instanceof DOMException && e.name === "AbortError"))
          return;
        setError(errorText(e));
        if (e instanceof ApiError && [401, 403, 404].includes(e.status)) {
          setMessages([]);
          setDenied(true);
        }
      } finally {
        active = false;
      }
    }
    void poll();
    const timer = window.setInterval(() => void poll(), 3000);
    const refresh = () => void poll();
    window.addEventListener("focus", refresh);
    window.addEventListener("online", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      live = false;
      controller.abort();
      window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
      window.removeEventListener("online", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [path]);
  useLayoutEffect(() => {
    const node = scroll.current;
    if (!node) return;
    if (preserveHeight.current !== null) {
      node.scrollTop += node.scrollHeight - preserveHeight.current;
      preserveHeight.current = null;
    } else if (bottom.current) node.scrollTop = node.scrollHeight;
  }, [messages]);
  async function older() {
    setOlderBusy(true);
    try {
      const result = await request<{
        results: ChatMessage[];
        has_more: boolean;
      }>(path + `messages/?before=${messages[0]?.id || 0}`);
      preserveHeight.current = scroll.current?.scrollHeight || 0;
      merge(result.results, true);
      setMore(result.has_more);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setOlderBusy(false);
    }
  }
  async function send() {
    if ((!text.trim() && !file) || busy) return;
    setBusy(true);
    setError("");
    try {
      const attachment = new FormData();
      if (file) {
        attachment.set("file", file);
        attachment.set("text", text);
        attachment.set("request_id", requestId);
      }
      const row = await request<ChatMessage>(
        path + (file ? "attachments/" : "messages/"),
        {
          method: "POST",
          body: file
            ? attachment
            : JSON.stringify({ text, request_id: requestId }),
        },
      );
      bottom.current = true;
      merge([row]);
      setDraft({ text: "", requestId: newUuid() });
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
      changed();
      setRevision((v) => v + 1);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function update(values: object) {
    if (!detail.data) return;
    setBusy(true);
    setError("");
    try {
      await request(path, {
        method: "PATCH",
        body: JSON.stringify({ version: detail.data.version, ...values }),
      });
      setRevision((v) => v + 1);
      changed();
    } catch (e) {
      setError(errorText(e));
      setRevision((v) => v + 1);
    } finally {
      setBusy(false);
    }
  }
  async function retry(id: string) {
    setBusy(true);
    try {
      merge([
        await request<ChatMessage>(path + `messages/${id}/retry/`, {
          method: "POST",
        }),
      ]);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  const row = detail.data;
  if (denied)
    return (
      <div className="chat-welcome">
        <Notice>{error || "Диалог недоступен"}</Notice>
        <button className="btn" onClick={() => select(null)}>
          К списку диалогов
        </button>
      </div>
    );
  return (
    <>
      <div className="chat-dialog-panel">
        <header className="chat-dialog-heading">
          <button
            className="chat-icon chat-back"
            aria-label="К списку диалогов"
            onClick={() => select(null)}
          >
            <ArrowLeft size={20} />
          </button>
          <Avatar name={row?.name || "Клиент"} />
          <div>
            <h2>{row?.name || "Загружаем диалог…"}</h2>
            <p>
              WhatsApp {row?.channel_phone ? `· ${row.channel_phone}` : ""}
              {row?.provider_mode === "fake" ? " · тестовый режим" : ""}
            </p>
          </div>
          <button
            className="chat-icon"
            aria-label="Карточка рядом с чатом"
            onClick={() => setShowProfile((v) => !v)}
          >
            <UserRound size={20} />
          </button>
        </header>
        {row && (
          <div className="chat-owner">
            <label>
              Ответственный
              <select
                aria-label="Ответственный за диалог"
                disabled={busy}
                value={row.assigned_to || ""}
                onChange={(e) =>
                  void update({ assigned_to: e.target.value || null })
                }
              >
                <option value="">Не назначен</option>
                {row.staff.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              disabled={busy}
              onClick={() =>
                void update({
                  mode: row.mode === "closed" ? "human" : "closed",
                })
              }
            >
              {row.mode === "closed" ? "Открыть диалог" : "Закрыть диалог"}
            </button>
          </div>
        )}
        {(error || detail.error) && <Notice>{error || detail.error}</Notice>}
        <div
          className="chat-thread"
          ref={scroll}
          onScroll={() => {
            const el = scroll.current!;
            bottom.current =
              el.scrollHeight - el.scrollTop - el.clientHeight < 70;
            if (bottom.current) setNewMessages(false);
          }}
          role="log"
          aria-label="Сообщения диалога"
          aria-live="polite"
        >
          {more && (
            <button
              className="chat-load-history"
              disabled={olderBusy}
              onClick={() => void older()}
            >
              {olderBusy ? "Загружаем…" : "Предыдущие сообщения"}
            </button>
          )}
          {messages.map((m, index) => (
            <div className="chat-message-group" key={m.id}>
              {(!index ||
                new Date(m.happened_at).toLocaleDateString("ru-RU", {
                  timeZone: business.timezone,
                }) !==
                  new Date(messages[index - 1].happened_at).toLocaleDateString(
                    "ru-RU",
                    { timeZone: business.timezone },
                  )) && (
                <div className="chat-day">
                  {new Date(m.happened_at).toLocaleDateString("ru-RU", {
                    timeZone: business.timezone,
                    day: "numeric",
                    month: "long",
                  })}
                </div>
              )}
              <article
                className={`chat-bubble ${m.direction === "system" ? "system" : m.direction === "out" ? "outgoing" : "incoming"} ${m.automated ? "automated" : ""}`}
                aria-label={`${m.direction === "system" ? "Системное" : m.direction === "out" ? "Исходящее" : "Входящее"} сообщение`}
              >
                {m.direction === "out" && (
                  <strong className="chat-author">
                    {m.automated ? "Автоответ" : m.sender || "Сотрудник"}
                  </strong>
                )}
                {m.media_url &&
                  (m.media_type.startsWith("image/") ? (
                    <a href={m.media_url} target="_blank" rel="noreferrer">
                      <img src={m.media_url} alt="Фото из переписки" />
                    </a>
                  ) : m.media_type.startsWith("audio/") ? (
                    <audio controls src={m.media_url} />
                  ) : (
                    <a href={m.media_url}>{m.media_name || "Скачать файл"}</a>
                  ))}
                {m.context_id && (
                  <blockquote className="chat-quote">
                    {messages.find((item) => item.external_id === m.context_id)
                      ?.text || "Ответ на предыдущее сообщение"}
                  </blockquote>
                )}
                <p>{m.text}</p>
                <footer>
                  <time>
                    {new Date(m.happened_at).toLocaleTimeString("ru-RU", {
                      timeZone: business.timezone,
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </time>
                  {m.direction === "out" && (
                    <span
                      title={statuses[m.status]}
                      aria-label={statuses[m.status]}
                      className={m.status === "read" ? "read" : ""}
                    >
                      {["queued", "sending"].includes(m.status) ? (
                        <Clock3 size={14} />
                      ) : ["unknown", "failed"].includes(m.status) ? (
                        <CircleAlert size={15} />
                      ) : m.status === "sent" ? (
                        <Check size={15} />
                      ) : (
                        <CheckCheck size={16} />
                      )}
                    </span>
                  )}
                </footer>
                {m.error && (
                  <div className="chat-message-error">
                    {m.error}
                    {m.status === "failed" && (
                      <button
                        disabled={busy || !row?.can_reply}
                        onClick={() => void retry(m.id)}
                      >
                        Повторить
                      </button>
                    )}
                  </div>
                )}
              </article>
            </div>
          ))}
          {!messages.length && row && (
            <p className="chat-start-note">
              История пока пуста. Ответить можно после первого сообщения клиента
              на подключённый номер.
            </p>
          )}
        </div>
        {newMessages && (
          <button
            className="chat-new-messages"
            onClick={() => {
              bottom.current = true;
              scroll.current?.scrollTo({
                top: scroll.current.scrollHeight,
                behavior: "smooth",
              });
              setNewMessages(false);
            }}
          >
            Новые сообщения <ArrowDown size={16} />
          </button>
        )}
        <form
          className="chat-composer"
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
        >
          <div className="chat-compose-tools">
            <button
              type="button"
              disabled={busy || !row?.can_reply}
              onClick={() => fileInput.current?.click()}
            >
              <Paperclip size={16} />
              Фото / PDF
            </button>
            <button
              type="button"
              aria-expanded={templatesOpen}
              onClick={() => setTemplatesOpen((v) => !v)}
            >
              Шаблоны
            </button>
            <button type="button" onClick={() => setQuickOpen(true)}>
              Быстрые ответы
            </button>
            <button
              type="button"
              disabled={busy || !row?.can_reply}
              onClick={() => setPaymentOpen(true)}
            >
              Отправить QR
            </button>
            <input
              ref={fileInput}
              type="file"
              accept="image/jpeg,image/png,image/webp,application/pdf"
              hidden
              aria-label="Вложение в чат"
              onChange={(e) => {
                const next = e.target.files?.[0];
                if (
                  next &&
                  next.size >
                    (next.type.startsWith("image/") ? 5 : 16) * 1024 * 1024
                ) {
                  setError("Фото — до 5 МБ, PDF — до 16 МБ.");
                  e.target.value = "";
                  return;
                }
                setFile(next || null);
                setDraft({ text, requestId: newUuid() });
              }}
            />
          </div>
          {templatesOpen && (
            <div className="chat-quick-replies">
              {[
                {
                  id: "greeting",
                  name: "Приветствие",
                  text: `${row?.name || ""}, здравствуйте! Это ${business.name}. Чем можем помочь?`,
                },
                ...(templates.data?.custom_templates || []),
              ].map((t) => (
                <button
                  type="button"
                  key={t.id}
                  disabled={busy}
                  onClick={() => {
                    setDraft({
                      text: t.text
                        .replaceAll("{имя}", row?.name || "")
                        .replaceAll("{магазин}", business.name),
                      requestId: newUuid(),
                    });
                    setTemplatesOpen(false);
                  }}
                >
                  {t.name}
                </button>
              ))}
              {templates.error && <Notice>{templates.error}</Notice>}
            </div>
          )}
          {file && (
            <div className="chat-file-selected">
              <Paperclip size={15} />
              <span>{file.name}</span>
              <button
                type="button"
                aria-label="Убрать вложение"
                disabled={busy}
                onClick={() => {
                  setFile(null);
                  setDraft({ text, requestId: newUuid() });
                  if (fileInput.current) fileInput.current.value = "";
                }}
              >
                <X size={15} />
              </button>
            </div>
          )}
          {row && !row.can_reply && (
            <p className="chat-reply-reason">
              <Clock3 size={16} />
              {row.reply_reason}
            </p>
          )}
          {row?.can_reply && row.last_inbound_at && (
            <p className="chat-window">
              Можно ответить ещё{" "}
              {Math.max(
                0,
                Math.floor(
                  (new Date(row.last_inbound_at).getTime() +
                    86400000 -
                    Date.now()) /
                    3600000,
                ),
              )}{" "}
              ч · окно WhatsApp 24 часа
            </p>
          )}
          <div className="chat-compose-field">
            <textarea
              aria-label="Сообщение в WhatsApp"
              placeholder="Ответить в WhatsApp…"
              maxLength={file ? 1024 : 4096}
              rows={2}
              value={text}
              disabled={busy}
              onChange={(e) => {
                setDraft({ text: e.target.value, requestId: newUuid() });
              }}
              onKeyDown={(e) => {
                if (
                  e.key === "Enter" &&
                  !e.shiftKey &&
                  !e.nativeEvent.isComposing
                ) {
                  e.preventDefault();
                  void send();
                }
              }}
            />
            <button
              type="submit"
              aria-label="Отправить сообщение"
              disabled={
                busy ||
                !row?.can_reply ||
                (!text.trim() && !file) ||
                (Boolean(file) && text.length > 1024)
              }
            >
              <Send size={21} />
            </button>
          </div>
          <span className="chat-compose-hint">
            {file
              ? "Подпись к вложению — до 1024 символов"
              : "Enter — отправить · Shift + Enter — новая строка"}
          </span>
          {row?.customer_id && (
            <button
              className="chat-mobile-draft"
              type="button"
              onClick={() => {
                setShowProfile(true);
                requestAnimationFrame(() =>
                  document
                    .querySelector(".order-draft-card")
                    ?.scrollIntoView({ block: "nearest" }),
                );
              }}
            >
              <ShoppingBag size={16} />
              Черновик заказа<span>Открыть →</span>
            </button>
          )}
        </form>
      </div>
      <aside
        className={`chat-profile ${showProfile ? "show" : ""}`}
        aria-label="Клиент в переписке"
      >
        <header>
          <h2>Клиент</h2>
          <button
            className="chat-icon"
            aria-label="Скрыть карточку клиента"
            onClick={() => setShowProfile(false)}
          >
            <X size={18} />
          </button>
        </header>
        {row && (
          <>
            <div className="chat-profile-card">
              <Avatar name={row.name} />
              <h3>{row.name}</h3>
              <a href={`tel:${row.phone}`}>{row.phone}</a>
              <div className="chat-tags">
                {row.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
              {row.customer_id && (
                <button
                  className="btn"
                  onClick={() => openCustomer(row.customer_id!)}
                >
                  Открыть карточку
                </button>
              )}
            </div>
            {row.new_customer && row.customer_id && (
              <form
                className="chat-name-card"
                onSubmit={(e) => {
                  e.preventDefault();
                  void update({ customer_name: customerName });
                }}
              >
                <span className="chat-mini green">
                  Новый клиент · из WhatsApp
                </span>
                <h3>Как зовут клиента?</h3>
                <p>
                  Номер уже сохранён. Уточните имя, чтобы быстрее найти клиента
                  в следующий раз.
                </p>
                <input
                  aria-label="Имя клиента из чата"
                  required
                  maxLength={150}
                  placeholder={row.name}
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                />
                <button
                  className="btn primary"
                  disabled={busy || !customerName.trim()}
                >
                  Сохранить имя
                </button>
              </form>
            )}
            {row.needs_customer_link && (
              <div className="chat-profile-card">
                <h3>Уточните клиента</h3>
                <p>
                  Этот номер есть в нескольких карточках. Выберите, кому
                  принадлежит переписка.
                </p>
                {row.link_candidates.map((c) => (
                  <button
                    className="btn"
                    key={c.id}
                    disabled={busy}
                    onClick={() => void update({ customer_id: c.id })}
                  >
                    {c.name} · {c.phone}
                  </button>
                ))}
              </div>
            )}
            {row.customer && (
              <>
                <OrderDraftCard
                  business={business}
                  chatId={chatId}
                  userId={userId}
                  canEdit={row.mode === "human" && !row.needs_customer_link}
                  openOrder={openOrder}
                  changed={() => {
                    setRevision((v) => v + 1);
                    changed();
                  }}
                />
                <div className="chat-profile-card">
                  <h3>
                    <ShoppingBag size={17} />
                    Заказы <span>{row.customer.orders_count}</span>
                  </h3>
                  {row.customer.orders.map((o) => (
                    <button
                      className="chat-order-link"
                      key={o.id}
                      onClick={() => openOrder(o.id)}
                    >
                      <strong>№{o.number}</strong>
                      <span>{shortDate(o.date)}</span>
                      <b>{price(o.total)}</b>
                    </button>
                  ))}
                  {!row.customer.orders_count && <p>Заказов пока нет</p>}
                  <button
                    className="btn primary"
                    disabled={busy}
                    onClick={() => {
                      void request<Customer>(
                        businessPath(
                          business.id,
                          `customers/${row.customer_id}`,
                        ),
                      )
                        .then(newOrder)
                        .catch((e) => setError(errorText(e)));
                    }}
                  >
                    Создать заказ
                  </button>
                  <button
                    className="btn"
                    disabled={busy || !row.can_reply}
                    onClick={() => setPaymentOpen(true)}
                  >
                    Отправить QR для оплаты
                  </button>
                </div>
                <div className="chat-profile-card">
                  <h3>
                    <CalendarDays size={17} />
                    Важные даты
                  </h3>
                  {row.customer.dates.map((d) => (
                    <p key={d.id}>
                      <strong>
                        {String(d.day).padStart(2, "0")}.
                        {String(d.month).padStart(2, "0")}
                      </strong>{" "}
                      · {d.label}
                      {d.person ? ` · ${d.person}` : ""}
                    </p>
                  ))}
                  {!row.customer.dates.length && <p>Пока не добавлены</p>}
                </div>
                <div className="chat-profile-card">
                  <h3>Заметки</h3>
                  <p className="chat-notes">
                    {row.customer.notes ||
                      "Здесь появятся заметки из карточки клиента."}
                  </p>
                </div>
              </>
            )}
          </>
        )}
      </aside>
      {paymentOpen && (
        <PaymentDialog
          businessId={business.id}
          chatId={chatId}
          close={() => setPaymentOpen(false)}
          sent={() => {
            setRevision((v) => v + 1);
            changed();
          }}
        />
      )}
      {quickOpen && (
        <QuickReplies
          businessId={business.id}
          close={() => setQuickOpen(false)}
          insert={(value) =>
            setDraft({
              text: value
                .replaceAll("{имя}", row?.name || "")
                .replaceAll("{магазин}", business.name),
              requestId: newUuid(),
            })
          }
        />
      )}
    </>
  );
}
