import { useEffect, useId, useRef, useState } from "react";
import { CircleHelp } from "lucide-react";

export function RecipientHelp() {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const popup = useRef<HTMLDivElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const [open, setOpen] = useState(false);
  function position() {
    if (!trigger.current || !popup.current) return;
    const anchor = trigger.current.getBoundingClientRect();
    const box = popup.current.getBoundingClientRect();
    popup.current.style.left = `${Math.max(12, Math.min(anchor.right - box.width, window.innerWidth - box.width - 12))}px`;
    popup.current.style.top = `${anchor.bottom + box.height + 20 <= window.innerHeight ? anchor.bottom + 8 : Math.max(12, anchor.top - box.height - 8)}px`;
  }
  function show() {
    clearTimeout(timer.current);
    popup.current?.showPopover();
    position();
  }
  function leave() {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      if (document.activeElement !== trigger.current)
        popup.current?.hidePopover();
    }, 150);
  }
  useEffect(() => () => clearTimeout(timer.current), []);
  useEffect(() => {
    if (!open) return;
    window.addEventListener("resize", position);
    window.addEventListener("scroll", position, true);
    return () => {
      window.removeEventListener("resize", position);
      window.removeEventListener("scroll", position, true);
    };
  }, [open]);
  return (
    <>
      <button
        ref={trigger}
        type="button"
        className="recipient-help-trigger"
        aria-label="Кто такой получатель?"
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        onPointerEnter={(event) => {
          if (event.pointerType === "mouse") show();
        }}
        onPointerLeave={leave}
        onFocus={show}
        onBlur={leave}
        onClick={show}
      >
        <CircleHelp size={17} aria-hidden="true" />
      </button>
      <div
        ref={popup}
        id={id}
        popover="auto"
        role="tooltip"
        className="recipient-help-popup"
        onToggle={(event) =>
          setOpen(event.currentTarget.matches(":popover-open"))
        }
        onPointerEnter={() => clearTimeout(timer.current)}
        onPointerLeave={leave}
      >
        Получатель — человек, которому клиент заказывает букет: например, мама
        или коллега. Сохраните его имя, телефон и адрес, чтобы быстро выбирать
        его в следующих заказах.
      </div>
    </>
  );
}
