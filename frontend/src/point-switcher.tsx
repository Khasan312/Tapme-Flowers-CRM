import { useEffect, useId, useRef, useState } from "react";
import { Building2, Check, ChevronDown, MapPin } from "lucide-react";
import type { Point } from "./types";
import { Avatar } from "./ui";
import "./point-switcher.css";

export function PointSwitcher({
  businessName,
  points,
  value,
  onChange,
}: {
  businessName: string;
  points: Point[];
  value: string;
  onChange: (id: string) => void;
}) {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const popup = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const options = [
    {
      id: "all",
      name: "Все точки",
      address: "Общий обзор филиалов",
      primary: false,
    },
    ...points
      .filter((point) => point.active)
      .map((point) => ({
        id: point.id,
        name: point.short_name,
        address:
          [point.city, point.address].filter(Boolean).join(" · ") ||
          "Адрес не указан",
        primary: point.is_primary,
      })),
  ];
  const selected = Math.max(
    0,
    options.findIndex((option) => option.id === value),
  );
  const current = options[selected];

  function position() {
    if (!trigger.current || !popup.current) return;
    const anchor = trigger.current.getBoundingClientRect();
    const viewport = window.visualViewport;
    const left = viewport?.offsetLeft || 0;
    const top = viewport?.offsetTop || 0;
    const width = viewport?.width || window.innerWidth;
    const height = viewport?.height || window.innerHeight;
    const below = top + height - anchor.bottom - 20;
    const above = anchor.top - top - 20;
    const down = below >= 300 || below >= above;
    const popupWidth = Math.min(Math.max(anchor.width, 280), width - 24);
    popup.current.style.width = `${popupWidth}px`;
    popup.current.style.maxHeight = `${Math.min(height - 24, Math.max(140, Math.min(380, down ? below : above)))}px`;
    popup.current.style.left = `${Math.max(left + 12, Math.min(anchor.left, left + width - popupWidth - 12))}px`;
    const popupHeight = popup.current.offsetHeight;
    popup.current.style.top = `${Math.max(top + 12, Math.min(down ? anchor.bottom + 8 : anchor.top - popupHeight - 8, top + height - popupHeight - 12))}px`;
  }

  useEffect(() => {
    if (!open) return;
    const observer = new ResizeObserver(position);
    if (popup.current) observer.observe(popup.current);
    window.addEventListener("resize", position);
    window.addEventListener("scroll", position, true);
    window.visualViewport?.addEventListener("resize", position);
    window.visualViewport?.addEventListener("scroll", position);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", position);
      window.removeEventListener("scroll", position, true);
      window.visualViewport?.removeEventListener("resize", position);
      window.visualViewport?.removeEventListener("scroll", position);
    };
  }, [open]);

  useEffect(() => {
    if (!open || !list.current) return;
    const option = list.current.children[active] as HTMLElement | undefined;
    if (!option) return;
    const row = option.getBoundingClientRect(),
      box = list.current.getBoundingClientRect();
    if (row.bottom > box.bottom)
      list.current.scrollTop += row.bottom - box.bottom;
    else if (row.top < box.top) list.current.scrollTop -= box.top - row.top;
  }, [active, open]);

  function show() {
    setActive(selected);
    popup.current?.showPopover();
    position();
    list.current?.focus({ preventScroll: true });
  }
  function close() {
    popup.current?.hidePopover();
    trigger.current?.focus({ preventScroll: true });
  }
  function choose(index: number) {
    close();
    if (options[index] && options[index].id !== value)
      onChange(options[index].id);
  }

  return (
    <div className="point-switch">
      <button
        ref={trigger}
        type="button"
        className="point-switch-trigger"
        aria-label={`${businessName}, филиал: ${current.name}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        popoverTarget={`${id}-popup`}
        onClick={() => setActive(selected)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            show();
          }
        }}
      >
        <Avatar name={businessName} />
        <span className="point-switch-copy">
          <strong title={businessName}>{businessName}</strong>
          <span className="point-switch-current" title={current.name}>
            {current.id === "all" ? current.name : `Филиал: ${current.name}`}
          </span>
        </span>
        <ChevronDown
          size={16}
          className="point-switch-chevron"
          aria-hidden="true"
        />
      </button>
      <div
        ref={popup}
        id={`${id}-popup`}
        popover="auto"
        className="point-switch-popup"
        onToggle={(event) => {
          const isOpen = event.newState === "open";
          setOpen(isOpen);
          if (isOpen) {
            position();
            list.current?.focus({ preventScroll: true });
          }
        }}
        onBlur={(event) => {
          if (
            !event.currentTarget.contains(event.relatedTarget) &&
            event.relatedTarget !== trigger.current
          )
            popup.current?.hidePopover();
        }}
      >
        <div className="point-switch-heading" id={`${id}-label`}>
          Выберите филиал
        </div>
        <div
          ref={list}
          id={`${id}-list`}
          role="listbox"
          aria-labelledby={`${id}-label`}
          aria-activedescendant={`${id}-option-${Math.min(active, options.length - 1)}`}
          tabIndex={0}
          className="point-switch-list"
          onKeyDown={(event) => {
            if (
              [
                "ArrowDown",
                "ArrowUp",
                "Home",
                "End",
                "Enter",
                " ",
                "Escape",
              ].includes(event.key)
            )
              event.preventDefault();
            if (event.key === "ArrowDown")
              setActive((index) => Math.min(index + 1, options.length - 1));
            if (event.key === "ArrowUp")
              setActive((index) => Math.max(index - 1, 0));
            if (event.key === "Home") setActive(0);
            if (event.key === "End") setActive(options.length - 1);
            if (event.key === "Enter" || event.key === " ") choose(active);
            if (event.key === "Escape") {
              event.stopPropagation();
              close();
            }
            if (event.key === "Tab") close();
          }}
        >
          {options.map((option, index) => {
            const Icon = option.id === "all" ? Building2 : MapPin;
            return (
              <div
                key={option.id}
                id={`${id}-option-${index}`}
                role="option"
                aria-label={option.name}
                aria-describedby={`${id}-address-${index}`}
                aria-selected={option.id === current.id}
                className={`point-switch-option${active === index ? " is-active" : ""}`}
                onClick={() => choose(index)}
              >
                <span className="point-option-icon">
                  <Icon size={19} strokeWidth={1.7} aria-hidden="true" />
                </span>
                <span className="point-option-copy">
                  <span className="point-option-title">
                    <strong>{option.name}</strong>
                    {option.primary && <small>Основной</small>}
                  </span>
                  <span
                    id={`${id}-address-${index}`}
                    className="point-option-address"
                  >
                    {option.address}
                  </span>
                </span>
                {option.id === current.id && (
                  <span className="point-option-check">
                    <Check size={13} strokeWidth={2.5} aria-hidden="true" />
                  </span>
                )}
              </div>
            );
          })}
        </div>
        <div className="point-switch-hint">
          Заказы, доставка и напоминания выбранной точки
        </div>
      </div>
    </div>
  );
}
