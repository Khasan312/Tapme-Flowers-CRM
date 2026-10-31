import { useEffect, useRef, useState } from "react";
import {
  Folder,
  Folders,
  FolderPlus,
  Inbox,
  Pencil,
  Plus,
  Settings2,
  Trash2,
} from "lucide-react";
import { businessPath, errorText, request } from "./api";
import { Modal, Notice } from "./components";
import { useRemote } from "./hooks";
import type { ChatDetail, ChatFolder, ChatFoldersData } from "./chat-types";

export type FolderDialog =
  | { kind: "create" }
  | { kind: "manage" }
  | { kind: "rename"; folder: ChatFolder }
  | { kind: "delete"; folder: ChatFolder }
  | { kind: "assign"; chatId: string };

function storedFolder(key: string) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function useChatFolderSelection(userId: string, businessId: string) {
  const key = `tapme-chat-folder:${userId}:${businessId}`;
  const [selection, setSelection] = useState(() => ({
    key,
    id: storedFolder(key),
  }));
  useEffect(() => {
    setSelection({ key, id: storedFolder(key) });
  }, [key]);
  return [
    selection.key === key ? selection.id : null,
    (id: string | null) => {
      setSelection({ key, id });
      try {
        if (id) localStorage.setItem(key, id);
        else localStorage.removeItem(key);
      } catch {
        /* Selection still works when browser storage is disabled. */
      }
    },
  ] as const;
}

export function ChatFolderRail({
  data,
  selected,
  choose,
  show,
  loading,
  error,
}: {
  data: ChatFoldersData | null;
  selected: string | null;
  choose: (id: string | null) => void;
  show: (dialog: FolderDialog) => void;
  loading: boolean;
  error: string;
}) {
  return (
    <aside className="chat-folder-rail" aria-label="Папки чатов">
      <header>
        <h2>Папки</h2>
        <button
          className="chat-icon"
          aria-label="Создать папку"
          onClick={() => show({ kind: "create" })}
        >
          <Plus size={18} />
        </button>
      </header>
      <nav aria-label="Выбор папки">
        <button
          className={`chat-folder-row ${!selected ? "active" : ""}`}
          aria-current={!selected ? "true" : undefined}
          onClick={() => choose(null)}
        >
          <Inbox size={18} />
          <span>Все чаты</span>
          <small>{data?.all_count ?? "—"}</small>
        </button>
        {data?.results.map((folder) => (
          <button
            key={folder.id}
            className={`chat-folder-row ${selected === folder.id ? "active" : ""}`}
            aria-current={selected === folder.id ? "true" : undefined}
            title={folder.name}
            onClick={() => choose(folder.id)}
          >
            <Folder size={18} />
            <span>{folder.name}</span>
            <small>{folder.count}</small>
          </button>
        ))}
        {!data && loading && (
          <p className="chat-folder-hint" role="status">
            Загружаем…
          </p>
        )}
        {error && (
          <p className="chat-folder-hint" role="alert">
            {error}
          </p>
        )}
        {data && !data.results.length && (
          <p className="chat-folder-hint">Соберите чаты в удобные группы</p>
        )}
        <button
          className="chat-folder-new"
          onClick={() => show({ kind: "create" })}
        >
          <Plus size={16} />
          <span>Новая папка</span>
        </button>
      </nav>
      <button
        className="chat-folder-manage"
        onClick={() => show({ kind: "manage" })}
      >
        <Settings2 size={16} />
        <span>Настроить</span>
      </button>
    </aside>
  );
}

export function ChatFolderButton({
  names,
  open,
}: {
  names: string[];
  open: () => void;
}) {
  return (
    <button
      type="button"
      className="chat-folder-chip"
      onClick={open}
      aria-label="Изменить папки чата"
      title={names.join(", ") || "Добавить чат в папки"}
    >
      <Folders size={15} />
      <span>{names.length ? names.join(" · ") : "В папку"}</span>
      <Plus size={13} />
    </button>
  );
}

export function ChatFolderDialog({
  dialog,
  businessId,
  data,
  show,
  close,
  changed,
}: {
  dialog: FolderDialog;
  businessId: string;
  data: ChatFoldersData | null;
  show: (dialog: FolderDialog) => void;
  close: () => void;
  changed: () => void;
}) {
  if (dialog.kind === "assign")
    return (
      <ChatFolderAssignment
        businessId={businessId}
        chatId={dialog.chatId}
        data={data}
        close={close}
        changed={changed}
      />
    );
  if (dialog.kind === "manage")
    return (
      <Modal title="Мои папки" close={close}>
        <div className="modal-body stack chat-folder-modal">
          <p className="muted">
            Папки общие для команды магазина. Один чат может быть в нескольких
            папках.
          </p>
          {data?.results.map((folder) => (
            <div className="chat-folder-editor-row" key={folder.id}>
              <Folder size={20} />
              <span>
                <strong>{folder.name}</strong>
                <small>Чатов: {folder.total}</small>
              </span>
              <button
                type="button"
                className="icon-button"
                aria-label={`Переименовать папку ${folder.name}`}
                onClick={() => show({ kind: "rename", folder })}
              >
                <Pencil size={17} />
              </button>
              <button
                type="button"
                className="icon-button chat-folder-trash"
                aria-label={`Удалить папку ${folder.name}`}
                onClick={() => show({ kind: "delete", folder })}
              >
                <Trash2 size={17} />
              </button>
            </div>
          ))}
          {!data?.results.length && (
            <p className="muted">
              Создайте первую папку — например, «Клиенты» или «Ждём оплату».
            </p>
          )}
          <button className="btn" onClick={() => show({ kind: "create" })}>
            <FolderPlus size={17} />
            Создать папку
          </button>
          <div className="form-actions">
            <button className="btn primary" onClick={close}>
              Готово
            </button>
          </div>
        </div>
      </Modal>
    );
  return (
    <ChatFolderEditor
      key={dialog.kind + ("folder" in dialog ? dialog.folder.id : "")}
      dialog={dialog}
      businessId={businessId}
      close={close}
      changed={changed}
    />
  );
}

function ChatFolderEditor({
  dialog,
  businessId,
  close,
  changed,
}: {
  dialog: Exclude<FolderDialog, { kind: "manage" } | { kind: "assign" }>;
  businessId: string;
  close: () => void;
  changed: () => void;
}) {
  const [name, setName] = useState(
    "folder" in dialog ? dialog.folder.name : "",
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const running = useRef(false);
  const nameInput = useRef<HTMLInputElement>(null);
  useEffect(() => {
    nameInput.current?.focus();
  }, []);
  const deleting = dialog.kind === "delete";
  const title = deleting
    ? "Удалить папку?"
    : dialog.kind === "rename"
      ? "Переименовать папку"
      : "Новая папка";
  return (
    <Modal title={title} close={close} busy={busy}>
      <form
        className="modal-body stack chat-folder-modal"
        onSubmit={async (event) => {
          event.preventDefault();
          if (running.current) return;
          running.current = true;
          setBusy(true);
          setError("");
          try {
            const suffix =
              "folder" in dialog
                ? `chat-folders/${dialog.folder.id}`
                : "chat-folders";
            await request(businessPath(businessId, suffix), {
              method: deleting
                ? "DELETE"
                : dialog.kind === "rename"
                  ? "PATCH"
                  : "POST",
              body: JSON.stringify({
                ...(deleting ? {} : { name: name.trim() }),
                ...("folder" in dialog
                  ? { version: dialog.folder.version }
                  : {}),
              }),
            });
            changed();
            close();
          } catch (reason) {
            setError(errorText(reason));
            changed();
          } finally {
            running.current = false;
            setBusy(false);
          }
        }}
      >
        {error && <Notice>{error}</Notice>}
        {deleting ? (
          <>
            <div className="chat-folder-delete-name">
              <Folder size={23} />
              <strong>{dialog.folder.name}</strong>
            </div>
            <p>
              Удалится только папка. Все переписки сохранятся во «Все чаты» и в
              других папках.
            </p>
          </>
        ) : (
          <>
            <label>
              Название папки
              <input
                ref={nameInput}
                autoFocus
                required
                maxLength={40}
                placeholder="Например, Ждём оплату"
                value={name}
                disabled={busy}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <p className="muted">
              До 40 символов. Папка будет доступна команде магазина.
            </p>
          </>
        )}
        <div className="form-actions">
          <button type="button" className="btn" disabled={busy} onClick={close}>
            Отмена
          </button>
          <button
            type="submit"
            className={`btn ${deleting ? "danger" : "primary"}`}
            disabled={busy || (!deleting && !name.trim())}
          >
            {busy
              ? "Сохраняем…"
              : deleting
                ? "Удалить папку"
                : dialog.kind === "rename"
                  ? "Сохранить"
                  : "Создать папку"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ChatFolderAssignment({
  businessId,
  chatId,
  data,
  close,
  changed,
}: {
  businessId: string;
  chatId: string;
  data: ChatFoldersData | null;
  close: () => void;
  changed: () => void;
}) {
  const path = businessPath(businessId, `chats/${chatId}`);
  const remote = useRemote<ChatDetail>(path, 0, { refreshOnAppear: false });
  const [selection, setSelection] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [newName, setNewName] = useState<string | null>(null);
  const [added, setAdded] = useState<ChatFolder[]>([]);
  const running = useRef(false);
  const folders = [
    ...(data?.results || []),
    ...added.filter((f) => !data?.results.some((row) => row.id === f.id)),
  ];
  const selected = selection ?? remote.data?.folder_ids ?? [];
  return (
    <Modal title="Папки чата" close={close} busy={busy}>
      <form
        className="modal-body stack chat-folder-modal"
        onSubmit={async (event) => {
          event.preventDefault();
          if (!remote.data || running.current) return;
          running.current = true;
          setBusy(true);
          setError("");
          try {
            await request(path + "folders/", {
              method: "PUT",
              body: JSON.stringify({
                version: remote.data.version,
                folder_ids: selected,
              }),
            });
            changed();
            close();
          } catch (reason) {
            setError(errorText(reason));
            changed();
          } finally {
            running.current = false;
            setBusy(false);
          }
        }}
      >
        <p className="muted">
          {remote.data?.name || "Загружаем чат…"} · можно выбрать несколько
          папок
        </p>
        {(error || remote.error) && <Notice>{error || remote.error}</Notice>}
        <div className="chat-folder-checks">
          {folders.map((folder) => (
            <label className="chat-folder-check" key={folder.id}>
              <input
                type="checkbox"
                checked={selected.includes(folder.id)}
                disabled={busy || !remote.data}
                onChange={(event) =>
                  setSelection(
                    event.target.checked
                      ? [...selected, folder.id]
                      : selected.filter((id) => id !== folder.id),
                  )
                }
              />
              <Folder size={19} />
              <span>{folder.name}</span>
            </label>
          ))}
        </div>
        {newName !== null ? (
          <div className="chat-folder-inline-create">
            <input
              autoFocus
              aria-label="Название новой папки"
              maxLength={40}
              value={newName}
              disabled={busy}
              onChange={(event) => setNewName(event.target.value)}
              placeholder="Название папки"
            />
            <button
              className="btn"
              type="button"
              disabled={busy || !newName.trim() || !remote.data}
              onClick={async () => {
                if (running.current) return;
                running.current = true;
                setBusy(true);
                setError("");
                try {
                  const folder = await request<ChatFolder>(
                    businessPath(businessId, "chat-folders"),
                    {
                      method: "POST",
                      body: JSON.stringify({ name: newName.trim() }),
                    },
                  );
                  setAdded((rows) => [...rows, folder]);
                  setSelection([...selected, folder.id]);
                  setNewName(null);
                  changed();
                } catch (reason) {
                  setError(errorText(reason));
                } finally {
                  running.current = false;
                  setBusy(false);
                }
              }}
            >
              Создать
            </button>
          </div>
        ) : (
          <button
            type="button"
            className="chat-folder-new"
            disabled={busy}
            onClick={() => setNewName("")}
          >
            <Plus size={17} />
            Новая папка
          </button>
        )}
        <p className="muted">
          Если снять все отметки, чат останется во «Все чаты».
        </p>
        <div className="form-actions">
          <button className="btn" type="button" disabled={busy} onClick={close}>
            Отмена
          </button>
          <button
            className="btn primary"
            type="submit"
            disabled={busy || !remote.data || !!remote.error}
          >
            {busy ? "Сохраняем…" : "Сохранить"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
