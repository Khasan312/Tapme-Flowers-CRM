import { useCallback, useLayoutEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Check,
  CheckCheck,
  CircleCheck,
  Copy,
  FlaskConical,
  Instagram,
  MessageCircle,
  MessagesSquare,
  Pencil,
  Reply,
  Search,
  Send,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import { ChatAssignee } from "./chat-assignee";
import { ChatEmojiPicker } from "./chat-emoji";
import {
  ChatFolderButton,
  ChatFolderRail,
  type FolderDialog,
} from "./chat-folders";
import {
  copyMessageText,
  MessageActionsMenu,
  MessageBubble,
  type MessageMenuTarget,
} from "./chat-message-actions";
import { Modal } from "./components";
import { Avatar } from "./ui";
import { InstagramProfile } from "./instagram-profile";
import { ChatMobileDetails, revealChatDetails } from "./chat-mobile-details";
import {
  observeChatThreadResize,
  shouldSendChatOnEnter,
} from "./chat-keyboard";
import { newUuid } from "./uuid";
import type { ChatMessage } from "./chat-types";
import {
  createInstagramPreview,
  previewMessage,
  previewStaff,
  type InstagramPreviewChat,
  type InstagramPreviewFolder,
} from "./instagram-preview";
import "./instagram-chats.css";

type Category = "all" | "waiting" | "mine" | "closed";
const categories: Record<Category, string> = {
  all: "Все",
  waiting: "Ждут ответа",
  mine: "Мои",
  closed: "Архив",
};

export function InstagramChats({ timezone }: { timezone: string }) {
  const [data, setData] = useState(createInstagramPreview);
  const [chatId, setChatId] = useState<string | null>(null);
  const [folderId, setFolderId] = useState<string | null>(null);
  const [category, setCategory] = useState<Category>("all");
  const [search, setSearch] = useState("");
  const [profile, setProfile] = useState(false);
  const profilePanel = useRef<HTMLElement>(null);
  const [dialog, setDialog] = useState<FolderDialog | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [replies, setReplies] = useState<Record<string, ChatMessage | null>>(
    {},
  );
  const [menu, setMenu] = useState<MessageMenuTarget | null>(null);
  const [selection, setSelection] = useState<Set<string> | null>(null);
  const [feedback, setFeedback] = useState("");
  const input = useRef<HTMLTextAreaElement>(null);
  const thread = useRef<HTMLDivElement>(null);
  const caret = useRef<number | null>(null);
  const nearBottom = useRef(true);
  const chat = data.chats.find((c) => c.id === chatId);
  const folder = data.folders.find((f) => f.id === folderId);
  const draft = chatId ? drafts[chatId] || "" : "";
  const reply = chatId ? replies[chatId] : null;
  const inFolder = data.chats.filter(
    (c) => !folderId || c.folders.includes(folderId),
  );
  const stats: Record<Category, number> = {
    all: inFolder.filter((c) => !c.closed).length,
    waiting: inFolder.filter((c) => !c.closed && c.waiting).length,
    mine: inFolder.filter((c) => !c.closed && c.assigned === "aisuluu").length,
    closed: inFolder.filter((c) => c.closed).length,
  };
  const needle = search.trim().toLocaleLowerCase("ru");
  const visible = inFolder.filter(
    (c) =>
      (category === "closed" ? c.closed : !c.closed) &&
      (category !== "waiting" || c.waiting) &&
      (category !== "mine" || c.assigned === "aisuluu") &&
      `${c.name} ${c.handle}`.toLocaleLowerCase("ru").includes(needle),
  );
  const folderData = {
    all_count: data.chats.filter((c) => !c.closed).length,
    results: data.folders.map((f) => ({
      ...f,
      version: 1,
      count: data.chats.filter((c) => !c.closed && c.folders.includes(f.id))
        .length,
      total: data.chats.filter((c) => c.folders.includes(f.id)).length,
    })),
  };
  const formatTime = (date: string) =>
    new Date(date).toLocaleTimeString("ru-RU", {
      timeZone: timezone,
      hour: "2-digit",
      minute: "2-digit",
    });
  const closeMenu = useCallback(() => setMenu(null), []);
  function updateChat(id: string, patch: Partial<InstagramPreviewChat>) {
    setData((old) => ({
      ...old,
      chats: old.chats.map((c) => (c.id === id ? { ...c, ...patch } : c)),
    }));
  }
  function chooseChat(id: string | null) {
    setChatId(id);
    setProfile(false);
    setSelection(null);
    setFeedback("");
    setMenu(null);
    nearBottom.current = true;
    if (id) updateChat(id, { unread: 0 });
  }
  useLayoutEffect(() => {
    if (input.current) {
      input.current.style.height = "0px";
      input.current.style.height = `${Math.min(144, Math.max(40, input.current.scrollHeight))}px`;
      if (caret.current !== null) {
        input.current.setSelectionRange(caret.current, caret.current);
        input.current.focus({ preventScroll: true });
        caret.current = null;
      }
    }
    if (thread.current && nearBottom.current)
      thread.current.scrollTop = thread.current.scrollHeight;
  }, [chatId, chat?.messages.length, chat?.closed, draft, reply?.id, feedback]);
  useLayoutEffect(() => {
    const node = thread.current;
    if (node)
      return observeChatThreadResize(
        node,
        () => nearBottom.current,
        () => {
          nearBottom.current =
            node.scrollHeight - node.scrollTop - node.clientHeight < 70;
        },
      );
  }, [chatId]);
  function insertEmoji(emoji: string) {
    if (!chatId) return false;
    const start = input.current?.selectionStart ?? draft.length;
    const end = input.current?.selectionEnd ?? start;
    const text = draft.slice(0, start) + emoji + draft.slice(end);
    if (text.length > 2000) return false;
    caret.current = start + emoji.length;
    setDrafts((old) => ({ ...old, [chatId]: text }));
    return true;
  }
  function send() {
    if (!chat || chat.closed || !draft.trim()) return;
    const message = previewMessage(draft.trim(), "out", 0, reply || null);
    message.sender =
      previewStaff.find((s) => s.id === chat.assigned)?.name || "Вы";
    updateChat(chat.id, {
      messages: [...chat.messages, message],
      waiting: false,
    });
    setDrafts((old) => ({ ...old, [chat.id]: "" }));
    setReplies((old) => ({ ...old, [chat.id]: null }));
    nearBottom.current = true;
    setFeedback("Ответ добавлен в пример. В Instagram он не отправлялся.");
  }
  async function copy(rows: ChatMessage[]) {
    try {
      await copyMessageText(rows.map((m) => m.text).join("\n\n"));
      setFeedback(
        rows.length === 1 ? "Сообщение скопировано" : "Сообщения скопированы",
      );
      return true;
    } catch {
      setFeedback("Не удалось скопировать. Проверьте доступ к буферу обмена.");
      return false;
    }
  }
  function toggleSelection(id: string) {
    setSelection((old) => {
      const next = new Set(old);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  return (
    <section className="ig-preview" aria-label="Переписка в Instagram">
      <div className="ig-preview-notice">
        <FlaskConical size={17} aria-hidden="true" />
        <p>
          <strong>Интерактивный пример</strong>
          <span>Вымышленные диалоги. Ответы никуда не отправляются.</span>
        </p>
        <span className="ig-preview-label">Instagram Direct</span>
      </div>
      <div className={`ig-workspace ${chat ? "has-conversation" : ""}`}>
        <ChatFolderRail
          data={folderData}
          selected={folderId}
          loading={false}
          error=""
          show={setDialog}
          choose={(id) => {
            setFolderId(id);
            chooseChat(null);
          }}
        />
        <aside className="chat-list-panel ig-list">
          <header className="chat-list-heading">
            <h1>{folder?.name || "Чаты"}</h1>
            <span className="ig-channel-mark">
              <Instagram size={15} /> Direct
            </span>
          </header>
          <label className="chat-search">
            <Search size={17} />
            <input
              aria-label="Поиск диалогов Instagram"
              placeholder="Имя или @ник"
              value={search}
              maxLength={150}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          <div
            className="chat-filters"
            role="tablist"
            aria-label="Фильтры Instagram"
          >
            {(Object.entries(categories) as [Category, string][]).map(
              ([key, label]) => (
                <button
                  key={key}
                  role="tab"
                  aria-selected={category === key}
                  className={category === key ? "active" : ""}
                  onClick={() => {
                    setCategory(key);
                    chooseChat(null);
                  }}
                >
                  {label}
                  <span>{stats[key]}</span>
                </button>
              ),
            )}
          </div>
          <div className="chat-list">
            {visible.map((c) => {
              const last = c.messages.at(-1)!;
              return (
                <button
                  key={c.id}
                  className={`chat-row ${chatId === c.id ? "selected" : ""}`}
                  aria-label={`Диалог Instagram: ${c.name}`}
                  aria-current={chatId === c.id ? "true" : undefined}
                  onClick={() => chooseChat(c.id)}
                >
                  <span className={`chat-avatar ig-avatar ig-avatar-${c.id}`}>
                    <Avatar name={c.name} />
                    <Instagram size={15} aria-hidden="true" />
                  </span>
                  <span className="chat-row-copy">
                    <strong>{c.name}</strong>
                    <small>@{c.handle}</small>
                    <span>
                      {last.direction === "out" ? "Вы: " : ""}
                      {last.text}
                    </span>
                  </span>
                  <span className="chat-row-meta">
                    <time>{formatTime(last.happened_at)}</time>
                    {c.unread > 0 ? (
                      <b>{c.unread}</b>
                    ) : c.waiting && !c.closed ? (
                      <em>ждёт ответа</em>
                    ) : last.direction === "out" ? (
                      <CheckCheck size={15} />
                    ) : null}
                  </span>
                </button>
              );
            })}
            {!visible.length && (
              <div className="chat-list-empty">
                <MessagesSquare size={28} />
                <strong>
                  {search ? "Ничего не найдено" : "Здесь пока нет диалогов"}
                </strong>
                <p>
                  {search
                    ? "Попробуйте другое имя или ник."
                    : "Выберите другую папку или фильтр."}
                </p>
              </div>
            )}
          </div>
          <div className="ig-account">
            <Instagram size={17} />
            <span>
              Аккаунт магазина<small>Предпросмотр Direct</small>
            </span>
            <span className="ig-account-demo">Пример</span>
          </div>
        </aside>
        {chat ? (
          <div className="chat-dialog-panel ig-dialog">
            <header className="ig-dialog-header">
              <button
                className="chat-icon ig-back"
                aria-label="К списку Instagram"
                onClick={() => chooseChat(null)}
              >
                <ArrowLeft size={20} />
              </button>
              <Avatar name={chat.name} />
              <div>
                <h2>{chat.name}</h2>
                <p>
                  <Instagram size={12} /> @{chat.handle}
                  <span className="chat-preview-mobile-label"> · пример</span>
                </p>
              </div>
              <button
                className="chat-icon ig-profile-toggle"
                aria-label="Клиент и заказы Instagram"
                title="Карточка клиента, черновик и заказы"
                aria-expanded={profile}
                onClick={() => setProfile((v) => !v)}
              >
                <UserRound size={20} />
                <span>Клиент и заказы</span>
              </button>
            </header>
            <div className="ig-dialog-actions">
              <ChatAssignee
                value={chat.assigned}
                assignedName={
                  previewStaff.find((s) => s.id === chat.assigned)?.name || ""
                }
                staff={previewStaff}
                disabled={false}
                onChange={(assigned) => updateChat(chat.id, { assigned })}
              />
              <button
                className={`chat-resolve ${chat.closed ? "is-closed" : ""}`}
                onClick={() => updateChat(chat.id, { closed: !chat.closed })}
              >
                {chat.closed ? (
                  <MessageCircle size={17} />
                ) : (
                  <CircleCheck size={17} />
                )}
                <span>{chat.closed ? "Открыть диалог" : "Закрыть диалог"}</span>
              </button>
            </div>
            <div className="ig-folder-toolbar">
              <ChatFolderButton
                names={data.folders
                  .filter((f) => chat.folders.includes(f.id))
                  .map((f) => f.name)}
                open={() => setDialog({ kind: "assign", chatId: chat.id })}
              />
            </div>
            <ChatMobileDetails
              canDraft
              open={(section) => {
                setProfile(true);
                revealChatDetails(profilePanel, section);
              }}
            />
            {selection && (
              <div
                className="chat-selection-bar"
                role="region"
                aria-label="Выбранные сообщения"
              >
                <strong>Выбрано: {selection.size}</strong>
                <button
                  disabled={!selection.size}
                  onClick={() =>
                    void copy(chat.messages.filter((m) => selection.has(m.id)))
                  }
                >
                  <Copy size={15} />
                  Скопировать
                </button>
                <button
                  aria-label="Отменить выбор сообщений"
                  onClick={() => setSelection(null)}
                >
                  <X size={17} />
                </button>
              </div>
            )}
            <div
              className="chat-thread ig-thread"
              ref={thread}
              role="log"
              aria-label="Сообщения Instagram"
              aria-live="polite"
              onScroll={() => {
                const n = thread.current!;
                nearBottom.current =
                  n.scrollHeight - n.scrollTop - n.clientHeight < 70;
              }}
            >
              <div className="chat-day">Сегодня</div>
              {chat.messages.map((m) => (
                <MessageBubble
                  key={m.id}
                  message={m}
                  className={`chat-bubble ${m.direction === "out" ? "outgoing" : "incoming"}`}
                  selecting={!!selection}
                  selected={!!selection?.has(m.id)}
                  toggle={() => toggleSelection(m.id)}
                  menu={setMenu}
                >
                  {m.direction === "out" && (
                    <strong className="chat-author">{m.sender}</strong>
                  )}
                  {m.reply_to && (
                    <blockquote className="chat-quote">
                      <strong>
                        {m.reply_to.direction === "in"
                          ? chat.name
                          : m.reply_to.sender}
                      </strong>
                      {m.reply_to.text}
                    </blockquote>
                  )}
                  <p>{m.text}</p>
                  <footer>
                    <time>{formatTime(m.happened_at)}</time>
                    {m.direction === "out" && (
                      <span
                        aria-label={
                          m.status === "read"
                            ? "Прочитано в примере"
                            : "Добавлено в пример"
                        }
                      >
                        {m.status === "read" ? (
                          <CheckCheck size={15} />
                        ) : (
                          <Check size={15} />
                        )}
                      </span>
                    )}
                  </footer>
                </MessageBubble>
              ))}
            </div>
            <form
              className="chat-composer ig-composer"
              onSubmit={(e) => {
                e.preventDefault();
                send();
              }}
            >
              {reply && (
                <div className="chat-reply-preview">
                  <Reply size={18} />
                  <div>
                    <strong>
                      {reply.direction === "in" ? chat.name : reply.sender}
                    </strong>
                    <p>{reply.text}</p>
                  </div>
                  <button
                    type="button"
                    className="chat-icon"
                    aria-label="Отменить ответ"
                    onClick={() =>
                      setReplies((old) => ({ ...old, [chat.id]: null }))
                    }
                  >
                    <X size={16} />
                  </button>
                </div>
              )}
              {feedback && (
                <p className="ig-feedback" role="status">
                  {feedback}
                </p>
              )}
              {chat.closed ? (
                <div className="ig-closed">
                  <CircleCheck size={17} />
                  Диалог в архиве. Откройте его, чтобы продолжить переписку.
                </div>
              ) : (
                <>
                  <div className="chat-compose-field">
                    <ChatEmojiPicker disabled={false} insert={insertEmoji} />
                    <textarea
                      ref={input}
                      aria-label="Сообщение в примере Instagram"
                      placeholder="Ответить в Instagram…"
                      rows={1}
                      enterKeyHint="enter"
                      maxLength={2000}
                      value={draft}
                      onChange={(e) =>
                        setDrafts((old) => ({
                          ...old,
                          [chat.id]: e.target.value,
                        }))
                      }
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
                          send();
                        }
                      }}
                    />
                    <button
                      className="chat-send"
                      type="submit"
                      aria-label="Отправить в примере"
                      onMouseDown={(e) => e.preventDefault()}
                      disabled={!draft.trim()}
                    >
                      <Send size={21} />
                    </button>
                  </div>
                  <div className="ig-compose-hint">
                    <span>Ответ останется только в этом примере</span>
                    <span>
                      Enter — отправить · Shift + Enter — новая строка
                    </span>
                  </div>
                </>
              )}
            </form>
          </div>
        ) : (
          <div className="ig-welcome">
            <span>
              <Instagram size={36} strokeWidth={1.5} />
            </span>
            <h2>Все сообщения Direct — рядом</h2>
            <p>
              Выберите диалог, чтобы посмотреть переписку и попробовать
              ответить.
            </p>
            <small>Это интерактивный пример будущего раздела Instagram.</small>
          </div>
        )}
        {chat && (
          <InstagramProfile
            key={chat.id}
            panelRef={profilePanel}
            chat={chat}
            open={profile}
            close={() => setProfile(false)}
            change={(patch) => updateChat(chat.id, patch)}
          />
        )}
      </div>
      {menu && chat && (
        <MessageActionsMenu
          target={menu}
          close={closeMenu}
          canReply={!chat.closed}
          replyReason="Сначала откройте диалог"
          reply={() => {
            setReplies((old) => ({ ...old, [chat.id]: menu.message }));
            input.current?.focus();
          }}
          copy={() => copy([menu.message])}
          select={() => setSelection(new Set([menu.message.id]))}
        />
      )}
      {dialog && (
        <InstagramPreviewFolders
          key={
            dialog.kind === "rename" || dialog.kind === "delete"
              ? dialog.folder.id
              : dialog.kind
          }
          dialog={dialog}
          folders={data.folders}
          chat={data.chats.find(
            (c) => c.id === (dialog.kind === "assign" ? dialog.chatId : ""),
          )}
          show={setDialog}
          close={() => setDialog(null)}
          save={(folders) => setData((old) => ({ ...old, folders }))}
          remove={(id) => {
            setData((old) => ({
              folders: old.folders.filter((f) => f.id !== id),
              chats: old.chats.map((c) => ({
                ...c,
                folders: c.folders.filter((f) => f !== id),
              })),
            }));
            if (folderId === id) setFolderId(null);
            setDialog(null);
          }}
          assign={(id, folders) => updateChat(id, { folders })}
        />
      )}
    </section>
  );
}

function InstagramPreviewFolders({
  dialog,
  folders,
  chat,
  show,
  close,
  save,
  remove,
  assign,
}: {
  dialog: FolderDialog;
  folders: InstagramPreviewFolder[];
  chat?: InstagramPreviewChat;
  show: (dialog: FolderDialog) => void;
  close: () => void;
  save: (folders: InstagramPreviewFolder[]) => void;
  remove: (id: string) => void;
  assign: (id: string, folders: string[]) => void;
}) {
  const [name, setName] = useState(
    dialog.kind === "rename" ? dialog.folder.name : "",
  );
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(chat?.folders || []);
  const titles = {
    create: "Новая папка",
    manage: "Папки Instagram",
    rename: "Переименовать папку",
    delete: "Удалить папку?",
    assign: "Добавить в папки",
  };
  return (
    <Modal title={titles[dialog.kind]} close={close}>
      <div className="modal-body ig-folder-modal">
        <p className="muted">
          Изменения папок относятся только к этому примеру.
        </p>
        {dialog.kind === "manage" ? (
          <>
            <div className="ig-manage-folders">
              {folders.map((f) => (
                <div key={f.id}>
                  <span>{f.name}</span>
                  <button
                    aria-label={`Переименовать ${f.name}`}
                    onClick={() =>
                      show({
                        kind: "rename",
                        folder: { ...f, version: 1, count: 0, total: 0 },
                      })
                    }
                  >
                    <Pencil size={16} />
                  </button>
                  <button
                    aria-label={`Удалить ${f.name}`}
                    onClick={() =>
                      show({
                        kind: "delete",
                        folder: { ...f, version: 1, count: 0, total: 0 },
                      })
                    }
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
            <button
              className="primary"
              onClick={() => show({ kind: "create" })}
            >
              Создать папку
            </button>
          </>
        ) : dialog.kind === "delete" ? (
          <>
            <p>
              Папка «{dialog.folder.name}» будет удалена. Переписки останутся во
              «Все чаты» и других папках.
            </p>
            <button className="danger" onClick={() => remove(dialog.folder.id)}>
              Удалить папку
            </button>
          </>
        ) : dialog.kind === "assign" && chat ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              assign(chat.id, selected);
              close();
            }}
          >
            <div className="ig-folder-options">
              {folders.map((f) => (
                <label key={f.id}>
                  <input
                    type="checkbox"
                    checked={selected.includes(f.id)}
                    onChange={(e) =>
                      setSelected((old) =>
                        e.target.checked
                          ? [...old, f.id]
                          : old.filter((id) => id !== f.id),
                      )
                    }
                  />
                  <span>{f.name}</span>
                </label>
              ))}
            </div>
            <button className="primary" type="submit">
              Сохранить
            </button>
          </form>
        ) : (
          (dialog.kind === "create" || dialog.kind === "rename") && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const clean = name.replace(/\s+/g, " ").trim();
                const currentId =
                  dialog.kind === "rename" ? dialog.folder.id : null;
                if (!clean) return setError("Введите название папки.");
                if (
                  folders.some(
                    (f) =>
                      f.id !== currentId &&
                      f.name.toLocaleLowerCase("ru") ===
                        clean.toLocaleLowerCase("ru"),
                  )
                )
                  return setError("Папка с таким названием уже есть.");
                if (!currentId && folders.length >= 30)
                  return setError("Можно создать не больше 30 папок.");
                save(
                  currentId
                    ? folders.map((f) =>
                        f.id === currentId ? { ...f, name: clean } : f,
                      )
                    : [...folders, { id: newUuid(), name: clean }],
                );
                close();
              }}
            >
              <label>
                Название папки
                <input
                  autoFocus
                  maxLength={40}
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    setError("");
                  }}
                  placeholder="Например, Корпоративные"
                />
              </label>
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              <button className="primary" type="submit">
                {dialog.kind === "create" ? "Создать папку" : "Сохранить"}
              </button>
            </form>
          )
        )}
      </div>
    </Modal>
  );
}
