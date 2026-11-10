import {
  useCallback,
  useEffect,
  useId,
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
  CircleCheck,
  Clock3,
  ContactRound,
  Copy,
  MessageCircle,
  Paperclip,
  Plus,
  QrCode,
  Reply,
  Search,
  Send,
  Settings2,
  ShoppingBag,
  TextQuote,
  UserRound,
  X,
  Zap,
} from "lucide-react";
import { ApiError, businessPath, errorText, price, request } from "./api";
import { Notice, Pager } from "./components";
import { useDebouncedValue, useRemote } from "./hooks";
import { Avatar, shortDate } from "./ui";
import { newUuid } from "./uuid";
import { useChatDraft } from "./chat-drafts";
import { startChatPolling } from "./chat-polling";
import {
  observeChatThreadResize,
  shouldSendChatOnEnter,
} from "./chat-keyboard";
import { ChatEmojiPicker } from "./chat-emoji";
import { ChatAssignee } from "./chat-assignee";
import {
  ChatFolderButton,
  ChatFolderDialog,
  ChatFolderRail,
  useChatFolderSelection,
  type FolderDialog,
} from "./chat-folders";
import {
  MessageActionsMenu,
  MessageBubble,
  copyMessageText,
  messageText,
  type MessageMenuTarget,
} from "./chat-message-actions";
import type { Business, Customer, Page } from "./types";
import type {
  Channel,
  ChatChannel,
  ChatDetail,
  ChatMessage,
  ChatMessagePage,
  Conversation,
  ChatFoldersData,
} from "./chat-types";
import "./chats.css";
import { PaymentDialog, QuickReplies } from "./chat-extras";
import { InstagramCustomerLink } from "./instagram-customer-link";
import { OrderDraftCard, useChatOrderDraft } from "./order-draft";
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

export type ChatsProps = {
  channelKind?: ChatChannel;
  userId: string;
  activityRevision: number;
  workspaceRevision: number;
  business: Business;
  chatId: string | null;
  select: (id: string | null) => void;
  settings: () => void;
  openCustomer: (id: string) => void;
  openOrder: (id: string) => void;
  newOrder: (customer: Customer) => void;
};
export function Chats(props: ChatsProps) {
  const {
    business,
    chatId,
    select,
    settings,
    channelKind = "whatsapp",
  } = props;
  const channelName = channelKind === "instagram" ? "Instagram" : "WhatsApp";
  const [revision, setRevision] = useState(0);
  const [folderRevision, setFolderRevision] = useState(0);
  const [channelRevision, setChannelRevision] = useState(0);
  const refreshInbox = useCallback((folders = false) => {
    setRevision((value) => value + 1);
    if (folders) setFolderRevision((value) => value + 1);
  }, []);
  const [category, setCategory] = useState<keyof typeof filters>("all");
  const [search, setSearch] = useState("");
  const settledSearch = useDebouncedValue(search);
  const [offset, setOffset] = useState(0);
  const [menu, setMenu] = useState<ChatMenuTarget | null>(null);
  const [actionRevision, setActionRevision] = useState(0);
  const [folderId, setFolderId] = useChatFolderSelection(
    props.userId,
    business.id,
  );
  const [folderDialog, setFolderDialog] = useState<FolderDialog | null>(null);
  const folders = useRemote<ChatFoldersData>(
    businessPath(business.id, "chat-folders") + `?channel_kind=${channelKind}`,
    folderRevision,
  );
  const activeFolder = folders.data?.results.find(
    (folder) => folder.id === folderId,
  );
  useEffect(() => {
    setFolderDialog(null);
    setOffset(0);
  }, [business.id]);
  useEffect(() => {
    if (folders.data && folderId && !activeFolder) {
      setFolderId(null);
      setOffset(0);
    }
  }, [folders.data, folderId, activeFolder]);
  const closeMenu = useCallback(() => setMenu(null), []);
  useEffect(closeMenu, [
    business.id,
    business.point_id,
    category,
    search,
    offset,
    chatId,
    folderId,
    closeMenu,
  ]);
  const channel = useRemote<Channel>(
    businessPath(business.id, `channels/${channelKind}`),
    channelRevision,
  );
  const list = useRemote<
    Page<Conversation> & { stats: Record<string, number> }
  >(
    businessPath(business.id, "chats") +
      `?channel_kind=${channelKind}&category=${category}&search=${encodeURIComponent(settledSearch)}&offset=${offset}&limit=50${activeFolder ? `&folder_id=${activeFolder.id}` : ""}`,
    revision,
  );
  useEffect(() => {
    let ticks = 0;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible" && navigator.onLine) {
        ticks += 1;
        setRevision((v) => v + 1);
        if (ticks % 2 === 0) setFolderRevision((v) => v + 1);
        if (ticks % 4 === 0) setChannelRevision((v) => v + 1);
      }
    }, 15000);
    return () => window.clearInterval(timer);
  }, []);
  const external = useRef({
    activity: props.activityRevision,
    workspace: props.workspaceRevision,
    point: business.point_id,
  });
  useEffect(() => {
    const old = external.current;
    const workspaceChanged =
      old.workspace !== props.workspaceRevision ||
      old.point !== business.point_id;
    if (
      (workspaceChanged || old.activity !== props.activityRevision) &&
      document.visibilityState === "visible" &&
      navigator.onLine
    )
      refreshInbox(true);
    if (workspaceChanged) setActionRevision((value) => value + 1);
    external.current = {
      activity: props.activityRevision,
      workspace: props.workspaceRevision,
      point: business.point_id,
    };
  }, [
    props.activityRevision,
    props.workspaceRevision,
    business.point_id,
    refreshInbox,
  ]);
  return (
    <section
      className={`chat-workspace has-folders ${chatId ? "has-conversation" : ""}`}
      aria-label="Переписка с клиентами"
    >
      <ChatFolderRail
        data={folders.data}
        selected={activeFolder?.id || null}
        loading={folders.loading}
        error={folders.error}
        show={setFolderDialog}
        choose={(id) => {
          setFolderId(id);
          setOffset(0);
          select(null);
        }}
      />
      <aside className="chat-list-panel">
        <div className="chat-list-heading">
          <h1 title={activeFolder?.name}>{activeFolder?.name || "Чаты"}</h1>
          <span>{channelName}</span>
          <button
            className="chat-icon"
            aria-label={`Подключение ${channelName}`}
            onClick={settings}
          >
            <Settings2 size={18} />
          </button>
        </div>
        <label className="chat-search">
          <Search size={16} />
          <input
            aria-label="Поиск диалогов"
            maxLength={150}
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
                <span className="chat-row-title">
                  <strong>{row.name}</strong>
                  {row.new_customer && (
                    <small className="chat-mini green">новый клиент</small>
                  )}
                </span>
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
              {search
                ? "Диалоги не найдены"
                : activeFolder
                  ? "В папке пока нет чатов"
                  : "Здесь появятся диалоги"}
            </strong>
            <p>
              {activeFolder
                ? "Добавьте диалог через меню чата или кнопку «В папку» в переписке. Проверьте также выбранный фильтр."
                : channel.data?.status === "active"
                  ? `Когда клиент напишет в ${channelName}, его сообщение появится здесь.`
                  : `Подключите ${channelName}, чтобы принимать сообщения клиентов.`}
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
            ? channel.data.display_phone || channel.data.display_name
            : `Подключить ${channelName}`}
        </button>
      </aside>
      {chatId ? (
        <ConversationPane
          key={business.id + chatId}
          {...props}
          chatId={chatId}
          actionRevision={actionRevision}
          folderNames={(idList) =>
            folders.data?.results
              .filter((folder) => idList.includes(folder.id))
              .map((folder) => folder.name) || []
          }
          editFolders={() => setFolderDialog({ kind: "assign", chatId })}
          changed={refreshInbox}
        />
      ) : (
        <div className="chat-welcome">
          <span>
            <MessageCircle size={46} />
          </span>
          <h2>
            {channel.data?.status === "active"
              ? "Все разговоры — рядом"
              : `Ваш ${channelName} — в CRM`}
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
          createFolder={() => {
            closeMenu();
            setFolderDialog({ kind: "create" });
          }}
          changed={() => {
            refreshInbox(true);
            setActionRevision((value) => value + 1);
          }}
        />
      )}
      {folderDialog && (
        <ChatFolderDialog
          key={
            folderDialog.kind +
            (folderDialog.kind === "assign" ? folderDialog.chatId : "")
          }
          dialog={folderDialog}
          businessId={business.id}
          data={folders.data}
          show={setFolderDialog}
          close={() => setFolderDialog(null)}
          changed={() => {
            refreshInbox(true);
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
  activityRevision,
  folderNames,
  editFolders,
}: ChatsProps & {
  chatId: string;
  changed: (folders?: boolean) => void;
  actionRevision: number;
  folderNames: (ids: string[]) => string[];
  editFolders: () => void;
}) {
  const path = businessPath(business.id, `chats/${chatId}`);
  const [revision, setRevision] = useState(0);
  const detail = useRemote<ChatDetail>(path, revision);
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible" && navigator.onLine)
        setRevision((value) => value + 1);
    }, 30000);
    return () => window.clearInterval(timer);
  }, []);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [{ text, requestId, replyTo }, setDraft] = useChatDraft(
    userId,
    business.id,
    chatId,
  );
  const [file, setFile] = useState<File | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const messageInput = useRef<HTMLTextAreaElement>(null);
  const pendingCaret = useRef<number | null>(null);
  useLayoutEffect(() => {
    const input = messageInput.current;
    if (!input) return;
    input.style.height = "0px";
    input.style.height = `${Math.min(144, Math.max(40, input.scrollHeight))}px`;
    if (pendingCaret.current !== null) {
      input.setSelectionRange(pendingCaret.current, pendingCaret.current);
      input.focus({ preventScroll: true });
      pendingCaret.current = null;
    }
  }, [text, requestId]);
  const [templatesOpen, setTemplatesOpen] = useState(false);
  const [toolsOpen, setToolsOpen] = useState(false);
  const toolsId = useId();
  const toolsButton = useRef<HTMLButtonElement>(null);
  const toolsPanel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!toolsOpen) return;
    function dismiss(event: PointerEvent) {
      const target = event.target as Node;
      if (
        !toolsButton.current?.contains(target) &&
        !toolsPanel.current?.contains(target)
      )
        setToolsOpen(false);
    }
    function escape(event: KeyboardEvent) {
      if (event.key !== "Escape" || event.defaultPrevented) return;
      setToolsOpen(false);
      toolsButton.current?.focus();
    }
    toolsPanel.current
      ?.querySelector<HTMLButtonElement>("button:not(:disabled)")
      ?.focus();
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", escape);
    };
  }, [toolsOpen]);
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [quickOpen, setQuickOpen] = useState(false);
  const [customerName, setCustomerName] = useState("");
  const templates = useRemote<{
    custom_templates: { id: string; name: string; text: string }[];
  }>(templatesOpen ? businessPath(business.id, "reminder-rules") : null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [pollError, setPollError] = useState("");
  const [denied, setDenied] = useState(false);
  const [more, setMore] = useState(false),
    [olderBusy, setOlderBusy] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const profilePanel = useRef<HTMLElement>(null);
  const profileButton = useRef<HTMLButtonElement>(null);
  const [newMessages, setNewMessages] = useState(false);
  const [scrolledUp, setScrolledUp] = useState(false);
  const [messageMenu, setMessageMenu] = useState<MessageMenuTarget | null>(
    null,
  );
  const [selecting, setSelecting] = useState(false);
  const [selectedMessages, setSelectedMessages] = useState<Set<string>>(
    new Set(),
  );
  const [copyStatus, setCopyStatus] = useState("");
  useEffect(() => {
    if (!copyStatus) return;
    const timer = window.setTimeout(() => setCopyStatus(""), 5000);
    return () => window.clearTimeout(timer);
  }, [copyStatus]);
  function toggleMessage(id: string) {
    setSelectedMessages((old) => {
      const next = new Set(old);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  async function copyMessages(rows: ChatMessage[]) {
    const value =
      rows.length === 1
        ? messageText(rows[0])
        : rows
            .map((m) => {
              const when = new Date(m.happened_at).toLocaleString("ru-RU", {
                timeZone: business.timezone,
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              });
              const author =
                m.direction === "in"
                  ? detail.data?.name || "Клиент"
                  : m.direction === "system"
                    ? "Система"
                    : m.automated
                      ? "Автоответ"
                      : m.sender || "Сотрудник";
              return `[${when}] ${author}:\n${messageText(m)}`;
            })
            .join("\n\n");
    try {
      await copyMessageText(value);
      setCopyStatus(
        rows.length === 1
          ? "Сообщение скопировано"
          : `Скопировано сообщений: ${rows.length}`,
      );
      return true;
    } catch {
      setCopyStatus(
        "Не удалось скопировать. Разрешите доступ к буферу обмена или попробуйте ещё раз.",
      );
      return false;
    }
  }
  const scroll = useRef<HTMLDivElement>(null),
    bottom = useRef(true),
    initial = useRef(true);
  const pollNow = useRef<() => void>(() => {});
  const readWatermark = useRef("0");
  const syncScrollPosition = useCallback(() => {
    const node = scroll.current;
    if (!node) return;
    const wasBottom = bottom.current;
    bottom.current =
      node.scrollHeight - node.scrollTop - node.clientHeight < 70;
    setScrolledUp(!bottom.current);
    if (bottom.current) setNewMessages(false);
    if (!wasBottom && bottom.current) pollNow.current();
  }, []);
  useLayoutEffect(() => {
    const node = scroll.current;
    if (node)
      return observeChatThreadResize(
        node,
        () => bottom.current,
        syncScrollPosition,
      );
  }, [chatId, denied, syncScrollPosition]);
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
    let live = true;
    let cursor = "",
      signature = "",
      metadata = "",
      pageHead = "";
    const controller = new AbortController();
    async function poll(): Promise<boolean> {
      try {
        const result = await request<ChatMessagePage>(
          path + `messages/?limit=50${cursor ? `&cursor=${cursor}` : ""}`,
          { signal: controller.signal },
        );
        if (!live) return false;
        const nextSignature = result.cursor || JSON.stringify(result.results);
        const payloadChanged = !result.unchanged && nextSignature !== signature;
        const metadataChanged =
          !!metadata &&
          !!result.conversation_cursor &&
          metadata !== result.conversation_cursor;
        // Also fetch a gap after the newest known message if a large burst arrived.
        let rows = result.results;
        const newest = messageRef.current.at(-1)?.id;
        if (
          payloadChanged &&
          newest &&
          rows.length &&
          Number(rows[0].id) > Number(newest)
        ) {
          let after = newest;
          for (;;) {
            const delta = await request<{
              results: ChatMessage[];
              has_more: boolean;
            }>(path + `messages/?after=${after}&limit=100`, {
              signal: controller.signal,
            });
            if (!live) return false;
            rows = [...rows, ...delta.results];
            if (!delta.has_more || !delta.results.length) break;
            after = delta.results.at(-1)!.id;
          }
        }
        if (payloadChanged) {
          merge(rows);
          pageHead = result.results.at(-1)?.id || pageHead;
        }
        cursor = result.cursor || "";
        signature = nextSignature;
        metadata = result.conversation_cursor || "";
        if (initial.current && !result.unchanged) {
          setMore(result.has_more);
          initial.current = false;
        }
        if (
          document.visibilityState === "visible" &&
          bottom.current &&
          pageHead &&
          BigInt(pageHead) > BigInt(readWatermark.current)
        ) {
          await request(path + "read/", {
            method: "POST",
            body: JSON.stringify({
              last_message_id: pageHead,
            }),
            signal: controller.signal,
          });
          if (!live) return false;
          readWatermark.current = pageHead;
          changed();
        }
        if (live && metadataChanged) {
          setRevision((v) => v + 1);
          changed(true);
        }
        if (live) setPollError("");
        return payloadChanged || metadataChanged;
      } catch (e) {
        if (!live || (e instanceof DOMException && e.name === "AbortError"))
          return false;
        setPollError(errorText(e));
        if (e instanceof ApiError && [401, 403, 404].includes(e.status)) {
          setMessages([]);
          setDenied(true);
        }
        return false;
      }
    }
    const polling = startChatPolling(poll);
    pollNow.current = polling.wake;
    const refresh = polling.wake;
    window.addEventListener("focus", refresh);
    window.addEventListener("online", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      live = false;
      controller.abort();
      polling.stop();
      pollNow.current = () => {};
      window.removeEventListener("focus", refresh);
      window.removeEventListener("online", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [path, business.point_id]);
  const seenUpdates = useRef({
    activity: activityRevision,
    action: actionRevision,
  });
  useEffect(() => {
    const previous = seenUpdates.current;
    if (previous.action !== actionRevision) setRevision((value) => value + 1);
    if (
      previous.action !== actionRevision ||
      previous.activity !== activityRevision
    )
      pollNow.current();
    seenUpdates.current = {
      activity: activityRevision,
      action: actionRevision,
    };
  }, [activityRevision, actionRevision]);
  useLayoutEffect(() => {
    const node = scroll.current;
    if (!node) return;
    if (preserveHeight.current !== null) {
      node.scrollTop += node.scrollHeight - preserveHeight.current;
      preserveHeight.current = null;
    } else if (bottom.current) node.scrollTop = node.scrollHeight;
    syncScrollPosition();
  }, [messages, syncScrollPosition]);
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
        if (replyTo) attachment.set("reply_to_id", replyTo.id);
      }
      const row = await request<ChatMessage>(
        path + (file ? "attachments/" : "messages/"),
        {
          method: "POST",
          body: file
            ? attachment
            : JSON.stringify({
                text,
                request_id: requestId,
                reply_to_id: replyTo?.id || null,
              }),
        },
      );
      bottom.current = true;
      merge([row]);
      setDraft({ text: "", requestId: newUuid(), replyTo: null });
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
      changed();
      setRevision((v) => v + 1);
      pollNow.current();
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
      changed(true);
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
      pollNow.current();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  const row = detail.data;
  const isInstagram = row?.channel_kind === "instagram";
  const channelName = isInstagram ? "Instagram" : "WhatsApp";
  const orderDraft = useChatOrderDraft({
    enabled: Boolean(row?.customer) && !denied,
    business,
    chatId,
    userId,
    canEdit: row?.mode === "human" && !row.needs_customer_link,
    openOrder,
    changed: () => {
      setRevision((v) => v + 1);
      changed();
    },
  });
  if (denied)
    return (
      <div className="chat-welcome">
        <Notice>{error || pollError || "Диалог недоступен"}</Notice>
        <button className="btn" onClick={() => select(null)}>
          К списку диалогов
        </button>
      </div>
    );
  return (
    <>
      <div className="chat-dialog-panel">
        <header className="chat-dialog-toolbar">
          <div className="chat-owner">
            {row && (
              <ChatAssignee
                value={row.assigned_to}
                assignedName={row.assigned_name}
                staff={row.staff}
                disabled={busy}
                onChange={(assigned_to) => void update({ assigned_to })}
              />
            )}
            <div className="chat-dialog-heading">
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
                  {channelName}
                  {row?.channel_phone && (
                    <span className="chat-heading-phone">
                      {" "}
                      · {row.channel_phone}
                    </span>
                  )}
                  {row?.provider_mode === "fake" ? " · тестовый режим" : ""}
                </p>
              </div>
              <button
                ref={profileButton}
                className="chat-icon chat-profile-trigger"
                aria-label="Карточка рядом с чатом"
                title="Клиент и заказы"
                aria-expanded={showProfile && !orderDraft.editing}
                disabled={orderDraft.editing}
                onClick={() => {
                  setShowProfile((v) => !v);
                  if (!showProfile)
                    requestAnimationFrame(() =>
                      profilePanel.current
                        ?.querySelector<HTMLButtonElement>("header button")
                        ?.focus({ preventScroll: true }),
                    );
                }}
              >
                <ContactRound size={20} aria-hidden="true" />
              </button>
            </div>
            {row && (
              <button
                className={`chat-resolve ${row.mode === "closed" ? "is-closed" : ""}`}
                type="button"
                disabled={busy || orderDraft.editing}
                onClick={() =>
                  void update({
                    mode: row.mode === "closed" ? "human" : "closed",
                  })
                }
              >
                {row.mode === "closed" ? (
                  <MessageCircle size={18} aria-hidden="true" />
                ) : (
                  <CircleCheck size={18} aria-hidden="true" />
                )}
                <span>
                  {row.mode === "closed" ? "Открыть диалог" : "Закрыть диалог"}
                </span>
              </button>
            )}
          </div>
          {row && (
            <div className="chat-workflow-actions">
              <button
                type="button"
                className="btn primary chat-order-action"
                disabled={!orderDraft.ready || orderDraft.editing}
                title={
                  !row.customer
                    ? "Сначала свяжите диалог с клиентом"
                    : undefined
                }
                onClick={orderDraft.open}
              >
                <ShoppingBag size={16} aria-hidden="true" />
                Оформить заказ
              </button>
              <ChatFolderButton
                names={folderNames(row.folder_ids || [])}
                open={editFolders}
              />
            </div>
          )}
        </header>
        {(error ||
          pollError ||
          detail.error ||
          (!showProfile && (orderDraft.error || orderDraft.loadError))) && (
          <Notice>
            {error ||
              pollError ||
              detail.error ||
              orderDraft.error ||
              orderDraft.loadError}
          </Notice>
        )}
        {selecting && (
          <div
            className="chat-selection-bar"
            role="region"
            aria-label="Выбранные сообщения"
          >
            <strong>Выбрано: {selectedMessages.size}</strong>
            <button
              type="button"
              disabled={!selectedMessages.size}
              onClick={() =>
                void copyMessages(
                  messages.filter((m) => selectedMessages.has(m.id)),
                )
              }
            >
              <Copy size={15} />
              Скопировать выбранные
            </button>
            <button
              type="button"
              aria-label="Отменить выбор сообщений"
              onClick={() => {
                setSelecting(false);
                setSelectedMessages(new Set());
              }}
            >
              <X size={17} />
            </button>
          </div>
        )}
        {copyStatus && (
          <p className="chat-copy-status" role="status">
            {copyStatus}
          </p>
        )}
        <div
          className="chat-thread"
          ref={scroll}
          onScroll={syncScrollPosition}
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
              <MessageBubble
                message={m}
                selecting={selecting}
                selected={selectedMessages.has(m.id)}
                toggle={() => toggleMessage(m.id)}
                menu={setMessageMenu}
                className={`chat-bubble ${m.direction === "system" ? "system" : m.direction === "out" ? "outgoing" : "incoming"} ${m.automated ? "automated" : ""}`}
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
                    {m.reply_to && (
                      <strong>
                        {m.reply_to.direction === "in"
                          ? row?.name || "Клиент"
                          : m.reply_to.sender || "Сотрудник"}
                      </strong>
                    )}
                    {m.reply_to
                      ? messageText(m.reply_to)
                      : messages.find(
                          (item) => item.external_id === m.context_id,
                        )?.text || "Ответ на предыдущее сообщение"}
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
              </MessageBubble>
            </div>
          ))}
          {!messages.length && row && (
            <p className="chat-start-note">
              История пока пуста. Ответить можно после первого сообщения клиента
              на подключённый номер.
            </p>
          )}
        </div>
        <div className="chat-scroll-actions">
          {scrolledUp && (
            <button
              className={`chat-new-messages${newMessages ? " has-new" : ""}`}
              type="button"
              aria-label={
                newMessages ? "Новые сообщения" : "К последним сообщениям"
              }
              title={newMessages ? "Новые сообщения" : "К последним сообщениям"}
              onClick={() => {
                bottom.current = true;
                scroll.current?.scrollTo({
                  top: scroll.current.scrollHeight,
                  behavior: "instant",
                });
                setScrolledUp(false);
                setNewMessages(false);
                pollNow.current();
              }}
            >
              {newMessages && <span>Новые сообщения</span>}
              <ArrowDown size={20} aria-hidden="true" />
            </button>
          )}
        </div>
        <form
          className="chat-composer"
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
        >
          <div
            id={toolsId}
            ref={toolsPanel}
            className={`chat-compose-tools${toolsOpen ? " is-open" : ""}`}
          >
            <button
              type="button"
              aria-expanded={templatesOpen}
              onClick={() => {
                if (toolsOpen)
                  toolsButton.current?.focus({ preventScroll: true });
                setToolsOpen(false);
                setTemplatesOpen((v) => !v);
              }}
            >
              <TextQuote size={15} />
              Шаблоны
            </button>
            <button
              type="button"
              onClick={() => {
                if (toolsOpen)
                  toolsButton.current?.focus({ preventScroll: true });
                setToolsOpen(false);
                setQuickOpen(true);
              }}
            >
              <Zap size={15} />
              Быстрые ответы
            </button>
            <button
              type="button"
              disabled={busy || !row?.can_reply || isInstagram}
              title={
                isInstagram
                  ? "Отправка QR в Instagram пока недоступна"
                  : undefined
              }
              onClick={() => {
                if (toolsOpen)
                  toolsButton.current?.focus({ preventScroll: true });
                setToolsOpen(false);
                setPaymentOpen(true);
              }}
            >
              <QrCode size={15} />
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
          {isInstagram && (
            <p className="chat-reply-reason">
              Текстовые ответы — до 1000 байт. Вложения пока открывайте в
              Instagram.
            </p>
          )}
          {row && !row.can_reply && (
            <p className="chat-reply-reason">
              <Clock3 size={16} />
              {row.reply_reason}
            </p>
          )}
          {replyTo && (
            <div
              className="chat-reply-preview"
              role="region"
              aria-label="Ответ на сообщение"
            >
              <Reply size={18} />
              <div>
                <strong>
                  {replyTo.direction === "in"
                    ? row?.name || "Клиент"
                    : replyTo.sender || "Сотрудник"}
                </strong>
                <p>{messageText(replyTo)}</p>
              </div>
              <button
                type="button"
                aria-label="Отменить ответ"
                disabled={busy}
                onClick={() =>
                  setDraft({ text, requestId: newUuid(), replyTo: null })
                }
              >
                <X size={16} />
              </button>
            </div>
          )}
          <div className="chat-compose-field">
            <button
              type="button"
              className="chat-tools-trigger"
              ref={toolsButton}
              aria-label="Действия с сообщением"
              aria-controls={toolsId}
              aria-expanded={toolsOpen}
              onClick={() => setToolsOpen((v) => !v)}
            >
              <Plus size={20} aria-hidden="true" />
            </button>
            <ChatEmojiPicker
              disabled={busy}
              insert={(emoji) => {
                const input = messageInput.current;
                if (!input || busy) return false;
                const start = input.selectionStart;
                const next =
                  text.slice(0, start) + emoji + text.slice(input.selectionEnd);
                if (next.length > (file ? 1024 : 4096)) return false;
                pendingCaret.current = start + emoji.length;
                setDraft({ text: next, requestId: newUuid() });
                return true;
              }}
            />
            <button
              className="chat-attach"
              type="button"
              aria-label="Фото / PDF"
              title={
                isInstagram
                  ? "Вложения пока отправляются через Instagram"
                  : "Прикрепить фото или PDF"
              }
              disabled={busy || !row?.can_reply || isInstagram}
              onClick={() => fileInput.current?.click()}
            >
              <Paperclip size={20} />
            </button>
            <textarea
              ref={messageInput}
              aria-label={`Сообщение в ${channelName}`}
              placeholder="Сообщение…"
              maxLength={isInstagram ? 1000 : file ? 1024 : 4096}
              rows={1}
              enterKeyHint="enter"
              value={text}
              readOnly={busy}
              aria-busy={busy}
              onChange={(e) => {
                setDraft({ text: e.target.value, requestId: newUuid() });
              }}
              onKeyDown={(e) => {
                if (
                  shouldSendChatOnEnter(
                    {
                      key: e.key,
                      shiftKey: e.shiftKey,
                      isComposing: e.nativeEvent.isComposing,
                      repeat: e.repeat,
                    },
                    window.matchMedia("(max-width: 700px)").matches,
                  )
                ) {
                  e.preventDefault();
                  void send();
                }
              }}
            />
            <button
              className="chat-send"
              type="submit"
              aria-label="Отправить сообщение"
              onMouseDown={(e) => e.preventDefault()}
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
          <div className="chat-compose-status">
            {row?.can_reply && row.last_inbound_at && (
              <p
                className="chat-window"
                title={`Окно ${channelName} — 24 часа после последнего сообщения клиента`}
              >
                <Clock3 size={12} aria-hidden="true" />
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
                ч
              </p>
            )}
            <span className="chat-compose-hint">
              {file
                ? "Подпись к вложению — до 1024 символов"
                : "Enter — отправить · Shift + Enter — новая строка"}
            </span>
          </div>
        </form>
      </div>
      {messageMenu && (
        <MessageActionsMenu
          target={messageMenu}
          close={() => setMessageMenu(null)}
          canReply={
            !busy &&
            Boolean(row?.can_reply) &&
            messageMenu.message.direction !== "system" &&
            Boolean(messageMenu.message.external_id) &&
            ["received", "sent", "delivered", "read"].includes(
              messageMenu.message.status,
            )
          }
          replyReason={
            row?.reply_reason ||
            "Дождитесь подтверждения отправки. Для цитаты нужен идентификатор сообщения."
          }
          copy={() => copyMessages([messageMenu.message])}
          select={() => {
            setSelecting(true);
            setSelectedMessages(
              (old) => new Set([...old, messageMenu.message.id]),
            );
          }}
          reply={() => {
            const m = messageMenu.message;
            pendingCaret.current = text.length;
            setDraft({
              text,
              requestId: newUuid(),
              replyTo: {
                id: m.id,
                text: m.text.slice(0, 500),
                direction: m.direction,
                sender: m.sender,
                kind: m.kind,
                media_name: m.media_name,
              },
            });
          }}
        />
      )}
      <aside
        ref={profilePanel}
        className={`chat-profile ${showProfile ? "show" : ""}`}
        aria-label="Клиент в переписке"
      >
        <header>
          <h2>Клиент</h2>
          <button
            className="chat-icon"
            aria-label="Скрыть карточку клиента"
            onClick={() => {
              setShowProfile(false);
              profileButton.current?.focus({ preventScroll: true });
            }}
          >
            <X size={18} />
          </button>
        </header>
        {row && (
          <>
            <div className="chat-profile-card">
              <Avatar name={row.name} />
              <h3>{row.name}</h3>
              {row.phone ? (
                <a href={`tel:${row.phone}`}>{row.phone}</a>
              ) : (
                <p className="muted">Instagram · {row.external_user_id}</p>
              )}
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
            {isInstagram && !row.customer_id && (
              <InstagramCustomerLink
                businessId={business.id}
                busy={busy}
                link={(customerId) => update({ customer_id: customerId })}
              />
            )}
            {row.new_customer && row.customer_id && (
              <form
                className="chat-name-card"
                onSubmit={(e) => {
                  e.preventDefault();
                  void update({ customer_name: customerName });
                }}
              >
                <span className="chat-mini green">
                  Новый клиент · из {channelName}
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
                <OrderDraftCard controller={orderDraft} openOrder={openOrder} />
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
                    disabled={busy || !row.can_reply || isInstagram}
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
      {orderDraft.editor}
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
