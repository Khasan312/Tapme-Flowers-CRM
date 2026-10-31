import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type RefObject,
} from "react";
import { Check, ChevronLeft, Folder, Plus } from "lucide-react";
import { businessPath, errorText, request } from "./api";
import { useRemote } from "./hooks";
import type { ChatDetail, ChatFoldersData } from "./chat-types";
import "./chat-folder-submenu.css";

export function ChatFolderSubmenu({
  id,
  ref,
  anchor,
  menu,
  menuPosition,
  businessId,
  chatId,
  chatName,
  focusFirst,
  enter,
  leave,
  back,
  close,
  create,
  busyChanged,
  changed,
}: {
  id: string;
  ref: RefObject<HTMLDivElement | null>;
  anchor: RefObject<HTMLButtonElement | null>;
  menu: RefObject<HTMLDivElement | null>;
  menuPosition: { left: number; top: number };
  businessId: string;
  chatId: string;
  chatName: string;
  focusFirst: boolean;
  enter: () => void;
  leave: () => void;
  back: () => void;
  close: () => void;
  create: () => void;
  busyChanged: (busy: boolean) => void;
  changed: () => void;
}) {
  const [revision, setRevision] = useState(0);
  const path = businessPath(businessId, `chats/${chatId}`);
  const detail = useRemote<ChatDetail>(path, revision, {
    refreshOnAppear: false,
  });
  const folders = useRemote<ChatFoldersData>(
    businessPath(businessId, "chat-folders"),
    revision,
    { refreshOnAppear: false },
  );
  const [saved, setSaved] = useState<ChatDetail | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");
  const running = useRef(false);
  const focused = useRef(false);
  const returnFocus = useRef<HTMLButtonElement | null>(null);
  const row = saved ?? detail.data;
  const loading = detail.initialLoading || folders.initialLoading;
  const unavailable = !!(detail.error || folders.error);
  function position() {
    if (!ref.current || !anchor.current || !menu.current) return;
    const popup = ref.current,
      trigger = anchor.current.getBoundingClientRect(),
      parent = menu.current.getBoundingClientRect();
    const viewport = window.visualViewport;
    const x = viewport?.offsetLeft || 0,
      y = viewport?.offsetTop || 0;
    const width = viewport?.width || innerWidth,
      height = viewport?.height || innerHeight;
    popup.style.width = `${Math.min(252, width - 16)}px`;
    popup.style.maxHeight = `${height - 16}px`;
    const size = popup.getBoundingClientRect();
    const right = parent.right + 4,
      left = parent.left - size.width - 4;
    const nextX =
      right + size.width <= x + width - 8
        ? right
        : left >= x + 8
          ? left
          : Math.max(x + 8, Math.min(trigger.left, x + width - size.width - 8));
    popup.style.left = `${nextX}px`;
    popup.style.top = `${Math.max(y + 8, Math.min(trigger.top - 6, y + height - size.height - 8))}px`;
  }
  useLayoutEffect(position, [
    menuPosition.left,
    menuPosition.top,
    folders.data,
    detail.data,
    error,
    pending,
  ]);
  useEffect(() => {
    const observer = new ResizeObserver(position);
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!focusFirst) {
      focused.current = false;
      return;
    }
    if (!loading && !focused.current) {
      ref.current
        ?.querySelector<HTMLButtonElement>('[role^="menuitem"]:not(:disabled)')
        ?.focus({ preventScroll: true });
      focused.current = true;
    }
  }, [focusFirst, loading]);
  useEffect(() => {
    if (!pending && returnFocus.current) {
      const trigger = returnFocus.current;
      returnFocus.current = null;
      if (
        document.activeElement === document.body &&
        trigger.isConnected &&
        !trigger.disabled
      )
        trigger.focus({ preventScroll: true });
    }
  }, [pending]);
  async function toggle(folderId: string, trigger: HTMLButtonElement) {
    if (!row || running.current || unavailable) return;
    running.current = true;
    returnFocus.current = trigger;
    setPending(folderId);
    busyChanged(true);
    setError("");
    const selected = row.folder_ids || [];
    try {
      const result = await request<ChatDetail>(path + "folders/", {
        method: "PUT",
        body: JSON.stringify({
          version: row.version,
          folder_ids: selected.includes(folderId)
            ? selected.filter((id) => id !== folderId)
            : [...selected, folderId],
        }),
      });
      setSaved(result);
    } catch (reason) {
      setError(errorText(reason));
      setSaved(null);
      setRevision((value) => value + 1);
    } finally {
      running.current = false;
      setPending(null);
      busyChanged(false);
      changed();
    }
  }
  return (
    <div
      id={id}
      ref={ref}
      className="chat-context-menu chat-folder-submenu"
      role="menu"
      aria-label={`Папки чата: ${chatName}`}
      aria-busy={!!pending || loading}
      onPointerEnter={enter}
      onPointerLeave={leave}
      onContextMenu={(event) => event.preventDefault()}
      onKeyDown={(event) => {
        if (["Escape", "ArrowLeft"].includes(event.key)) {
          event.preventDefault();
          event.stopPropagation();
          back();
        } else if (event.key === "Tab") close();
        else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
          event.preventDefault();
          const items = [
            ...ref.current!.querySelectorAll<HTMLButtonElement>(
              '[role^="menuitem"]:not(:disabled)',
            ),
          ];
          const index = items.indexOf(
            document.activeElement as HTMLButtonElement,
          );
          const next =
            event.key === "Home"
              ? 0
              : event.key === "End"
                ? items.length - 1
                : (index +
                    (event.key === "ArrowDown" ? 1 : -1) +
                    items.length) %
                  items.length;
          items[next]?.focus();
        }
      }}
    >
      <header className="chat-folder-submenu-heading">
        <button type="button" aria-label="Назад в меню чата" onClick={back}>
          <ChevronLeft size={16} />
        </button>
        <span>
          Папки чата<small>Можно выбрать несколько</small>
        </span>
      </header>
      {loading && (
        <p className="chat-folder-submenu-note" role="status">
          Загружаем папки…
        </p>
      )}
      {(error || detail.error || folders.error) && (
        <p className="chat-context-error" role="alert">
          {error || detail.error || folders.error}
        </p>
      )}
      <div className="chat-folder-submenu-options" role="presentation">
        {folders.data?.results.map((folder) => (
          <button
            key={folder.id}
            type="button"
            role="menuitemcheckbox"
            aria-checked={!!row?.folder_ids?.includes(folder.id)}
            disabled={!!pending || !row || unavailable}
            title={folder.name}
            onClick={(event) => void toggle(folder.id, event.currentTarget)}
          >
            <Folder size={18} />
            <span>{folder.name}</span>
            {pending === folder.id ? (
              <i className="chat-folder-saving" aria-label="Сохраняем" />
            ) : row?.folder_ids?.includes(folder.id) ? (
              <Check size={17} className="chat-folder-submenu-check" />
            ) : null}
          </button>
        ))}
      </div>
      {!loading && !folders.error && !folders.data?.results.length && (
        <p className="chat-folder-submenu-note">Папок пока нет</p>
      )}
      <button
        type="button"
        role="menuitem"
        className="chat-folder-submenu-create"
        disabled={!!pending}
        onClick={create}
      >
        <Plus size={18} />
        Создать папку
      </button>
      <span
        className="chat-folder-submenu-status"
        role="status"
        aria-live="polite"
      >
        {pending ? "Сохраняем…" : ""}
      </span>
    </div>
  );
}
