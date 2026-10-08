import { useEffect, useRef, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";

export function Modal({
  title,
  close,
  children,
  busy = false,
  drawer = false,
}: {
  title: string;
  close: () => void;
  children: ReactNode;
  busy?: boolean;
  drawer?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog
      ref={ref}
      className={drawer ? "order-drawer" : undefined}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) close();
      }}
    >
      <header className="modal-header">
        <h2>{title}</h2>
        <button
          type="button"
          className="icon-button"
          aria-label="Закрыть"
          disabled={busy}
          onClick={close}
        >
          <X size={20} />
        </button>
      </header>
      {children}
    </dialog>
  );
}

export function Pager({
  count,
  offset,
  setOffset,
  limit = 50,
}: {
  count: number;
  offset: number;
  setOffset: (n: number) => void;
  limit?: number;
}) {
  return (
    <div className="pager">
      <span>
        {count
          ? `${offset + 1}–${Math.min(offset + limit, count)} из ${count}`
          : "Нет записей"}
      </span>
      <div>
        <button
          className="icon-button"
          aria-label="Предыдущая страница"
          disabled={!offset}
          onClick={() => setOffset(Math.max(0, offset - limit))}
        >
          <ChevronLeft size={18} />
        </button>
        <button
          className="icon-button"
          aria-label="Следующая страница"
          disabled={offset + limit >= count}
          onClick={() => setOffset(offset + limit)}
        >
          <ChevronRight size={18} />
        </button>
      </div>
    </div>
  );
}

export function Notice({ children }: { children: ReactNode }) {
  return (
    <div role="alert" className="notice">
      {children}
    </div>
  );
}

export function SettingsConflict({
  reload,
  busy,
}: {
  reload: () => void;
  busy: boolean;
}) {
  return (
    <div className="selection">
      <p>
        Черновик оставлен в форме. При загрузке актуальных настроек
        несохранённые изменения будут заменены.
      </p>
      <button type="button" className="btn" disabled={busy} onClick={reload}>
        Загрузить актуальные настройки
      </button>
    </div>
  );
}
