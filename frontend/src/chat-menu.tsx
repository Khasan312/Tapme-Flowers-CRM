import {
  useEffect,
  useLayoutEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import {
  Archive,
  ArchiveRestore,
  FolderPlus,
  ChevronRight,
  MessageCircle,
  UserMinus,
  UserRoundCheck,
} from "lucide-react";
import { businessPath, errorText, request } from "./api";
import type { Conversation } from "./chat-types";
import { ChatFolderSubmenu } from "./chat-folder-submenu";

export type ChatMenuTarget = {
  row: Conversation;
  trigger: HTMLButtonElement;
  x: number;
  y: number;
};

export function ChatListItem({
  row,
  selected,
  expanded,
  open,
  menu,
  children,
}: {
  row: Conversation;
  selected: boolean;
  expanded: boolean;
  open: () => void;
  menu: (target: ChatMenuTarget) => void;
  children: ReactNode;
}) {
  const press = useRef<{ timer: number; x: number; y: number } | null>(null);
  const held = useRef(false);
  const moved = useRef(false);
  function cancelPress() {
    if (press.current) window.clearTimeout(press.current.timer);
    press.current = null;
  }
  useEffect(() => cancelPress, []);
  return (
    <button
      className={`chat-row ${selected ? "selected" : ""} ${expanded ? "menu-open" : ""}`}
      aria-label={`Диалог: ${row.name}`}
      aria-current={selected ? "true" : undefined}
      aria-haspopup="menu"
      aria-expanded={expanded}
      title="Правый клик или удержание — действия с чатом"
      onClick={(event) => {
        if (held.current || moved.current) {
          event.preventDefault();
          held.current = false;
          return;
        }
        open();
      }}
      onContextMenu={(event) => {
        event.preventDefault();
        cancelPress();
        if (moved.current) return;
        held.current = true;
        menu({
          row,
          trigger: event.currentTarget,
          x: event.clientX,
          y: event.clientY,
        });
      }}
      onKeyDown={(event) => {
        held.current = false;
        moved.current = false;
        if (
          event.key !== "ContextMenu" &&
          !(event.shiftKey && event.key === "F10")
        )
          return;
        event.preventDefault();
        const rect = event.currentTarget.getBoundingClientRect();
        menu({
          row,
          trigger: event.currentTarget,
          x: rect.left + 16,
          y: rect.bottom,
        });
      }}
      onPointerDown={(event) => {
        cancelPress();
        held.current = false;
        moved.current = false;
        if (event.pointerType !== "touch" || !event.isPrimary) return;
        const trigger = event.currentTarget,
          x = event.clientX,
          y = event.clientY;
        press.current = {
          x,
          y,
          timer: window.setTimeout(() => {
            press.current = null;
            held.current = true;
            menu({ row, trigger, x, y });
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
          cancelPress();
        }
      }}
      onPointerUp={cancelPress}
      onPointerCancel={() => {
        moved.current = true;
        cancelPress();
      }}
      onPointerLeave={cancelPress}
    >
      {children}
    </button>
  );
}

export function ChatContextMenu({
  target,
  businessId,
  userId,
  close,
  open,
  changed,
  createFolder,
}: {
  target: ChatMenuTarget;
  businessId: string;
  userId: string;
  close: () => void;
  open: (id: string) => void;
  changed: () => void;
  createFolder: () => void;
}) {
  const element = useRef<HTMLDivElement>(null);
  const folderTrigger = useRef<HTMLButtonElement>(null);
  const submenu = useRef<HTMLDivElement>(null);
  const submenuId = useId();
  const leaveTimer = useRef<number | undefined>(undefined);
  const [foldersOpen, setFoldersOpen] = useState(false);
  const [focusFolders, setFocusFolders] = useState(false);
  const [position, setPosition] = useState({ left: target.x, top: target.y });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const running = useRef(false);
  const row = target.row;
  function cancelLeave() {
    window.clearTimeout(leaveTimer.current);
  }
  function hideFolders() {
    cancelLeave();
    setFoldersOpen(false);
    setFocusFolders(false);
  }
  function leaveFolders() {
    cancelLeave();
    leaveTimer.current = window.setTimeout(hideFolders, 220);
  }
  function showFolders(focus = false) {
    if (busy) return;
    cancelLeave();
    setFocusFolders(focus);
    setFoldersOpen(true);
  }
  useEffect(() => () => window.clearTimeout(leaveTimer.current), []);
  function restoreFocus() {
    target.trigger.focus({ preventScroll: true });
  }
  useLayoutEffect(() => {
    const rect = element.current!.getBoundingClientRect();
    setPosition({
      left: Math.max(8, Math.min(target.x, window.innerWidth - rect.width - 8)),
      top: Math.max(
        8,
        Math.min(target.y, window.innerHeight - rect.height - 8),
      ),
    });
  }, [target, error]);
  useEffect(() => {
    element.current
      ?.querySelector<HTMLButtonElement>("button")
      ?.focus({ preventScroll: true });
    const outside = (event: Event) => {
      if (
        !element.current?.contains(event.target as Node) &&
        !submenu.current?.contains(event.target as Node)
      )
        close();
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("scroll", outside, true);
    window.addEventListener("resize", close);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("scroll", outside, true);
      window.removeEventListener("resize", close);
    };
  }, [close]);
  async function update(values: object) {
    if (running.current) return;
    running.current = true;
    setBusy(true);
    setError("");
    try {
      await request(businessPath(businessId, `chats/${row.id}`), {
        method: "PATCH",
        body: JSON.stringify({ version: row.version, ...values }),
      });
      restoreFocus();
      close();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      running.current = false;
      setBusy(false);
      changed();
    }
  }
  return createPortal(
    <>
      <div
        ref={element}
        className="chat-context-menu"
        role="menu"
        aria-label={`Действия с чатом: ${row.name}`}
        aria-busy={busy}
        style={position}
        onPointerEnter={cancelLeave}
        onPointerLeave={leaveFolders}
        onFocusCapture={(event) => {
          if (!folderTrigger.current?.contains(event.target as Node))
            hideFolders();
        }}
        onContextMenu={(event) => event.preventDefault()}
        onKeyDown={(event) => {
          if (
            event.key === "ArrowRight" &&
            event.target === folderTrigger.current
          ) {
            event.preventDefault();
            showFolders(true);
          } else if (event.key === "Escape") {
            event.preventDefault();
            event.stopPropagation();
            restoreFocus();
            close();
          } else if (event.key === "Tab") {
            restoreFocus();
            close();
          } else if (
            ["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)
          ) {
            event.preventDefault();
            const items = [
              ...element.current!.querySelectorAll<HTMLButtonElement>(
                "button:not(:disabled)",
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
        <p className="chat-context-title">{row.name}</p>
        <button
          role="menuitem"
          disabled={busy}
          onPointerEnter={hideFolders}
          onClick={() => {
            restoreFocus();
            close();
            open(row.id);
          }}
        >
          <MessageCircle size={17} />
          Открыть чат
        </button>
        <button
          ref={folderTrigger}
          role="menuitem"
          disabled={busy}
          aria-haspopup="menu"
          aria-expanded={foldersOpen}
          aria-controls={foldersOpen ? submenuId : undefined}
          className={foldersOpen ? "chat-context-submenu-active" : ""}
          onPointerEnter={(event) => {
            if (event.pointerType !== "touch") showFolders();
          }}
          onPointerLeave={leaveFolders}
          onClick={() => showFolders(true)}
        >
          <FolderPlus size={17} />
          Добавить в папки
          <ChevronRight className="chat-context-chevron" size={15} />
        </button>
        <button
          role="menuitem"
          disabled={busy}
          onPointerEnter={hideFolders}
          onClick={() =>
            void update({
              assigned_to: row.assigned_to === userId ? null : userId,
            })
          }
        >
          {row.assigned_to === userId ? (
            <UserMinus size={17} />
          ) : (
            <UserRoundCheck size={17} />
          )}
          {row.assigned_to === userId ? "Снять с себя" : "Взять себе"}
        </button>
        <button
          role="menuitem"
          disabled={busy}
          onPointerEnter={hideFolders}
          onClick={() =>
            void update({ mode: row.mode === "closed" ? "human" : "closed" })
          }
        >
          {row.mode === "closed" ? (
            <ArchiveRestore size={17} />
          ) : (
            <Archive size={17} />
          )}
          {row.mode === "closed" ? "Вернуть из архива" : "В архив"}
        </button>
        {error && (
          <p className="chat-context-error" role="alert">
            {error}
          </p>
        )}
      </div>
      {foldersOpen && (
        <ChatFolderSubmenu
          id={submenuId}
          ref={submenu}
          anchor={folderTrigger}
          menu={element}
          menuPosition={position}
          businessId={businessId}
          chatId={row.id}
          chatName={row.name}
          focusFirst={focusFolders}
          enter={cancelLeave}
          leave={leaveFolders}
          back={() => {
            hideFolders();
            folderTrigger.current?.focus({ preventScroll: true });
          }}
          close={() => {
            restoreFocus();
            close();
          }}
          create={() => {
            restoreFocus();
            close();
            createFolder();
          }}
          busyChanged={setBusy}
          changed={changed}
        />
      )}
    </>,
    document.body,
  );
}
