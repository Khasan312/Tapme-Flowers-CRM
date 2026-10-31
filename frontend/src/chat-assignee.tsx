import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown, UserRound, UserRoundMinus } from "lucide-react";
import { Avatar } from "./ui";
import type { ChatDetail } from "./chat-types";
import "./chat-assignee.css";

export function ChatAssignee({
  value,
  assignedName,
  staff,
  disabled,
  onChange,
}: {
  value: string | null;
  assignedName: string;
  staff: ChatDetail["staff"];
  disabled: boolean;
  onChange: (value: string | null) => void;
}) {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const popup = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const search = useRef({ text: "", time: 0 });
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const options = [
    { id: "", name: "Не назначен" },
    ...(value && !staff.some((person) => person.id === value)
      ? [{ id: value, name: assignedName || "Сотрудник" }]
      : []),
    ...staff,
  ];
  const selected = Math.max(
    0,
    options.findIndex((person) => person.id === (value || "")),
  );
  const current = options[selected];
  const activeIndex = Math.min(active, options.length - 1);

  function position() {
    if (!trigger.current || !popup.current) return;
    const anchor = trigger.current.getBoundingClientRect();
    const viewport = window.visualViewport;
    const left = viewport?.offsetLeft || 0;
    const top = viewport?.offsetTop || 0;
    const width = viewport?.width || window.innerWidth;
    const height = viewport?.height || window.innerHeight;
    const below = top + height - anchor.bottom - 16;
    const above = anchor.top - top - 16;
    const down = below >= 240 || below >= above;
    const popupWidth = Math.min(Math.max(anchor.width, 280), width - 16);
    popup.current.style.width = `${popupWidth}px`;
    popup.current.style.maxHeight = `${Math.min(360, height - 16, Math.max(140, down ? below : above))}px`;
    popup.current.style.left = `${Math.max(left + 8, Math.min(anchor.left, left + width - popupWidth - 8))}px`;
    const popupHeight = popup.current.offsetHeight;
    popup.current.style.top = `${Math.max(top + 8, Math.min(down ? anchor.bottom + 6 : anchor.top - popupHeight - 6, top + height - popupHeight - 8))}px`;
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
    if (disabled) popup.current?.hidePopover();
  }, [disabled]);

  useEffect(() => {
    if (!open || !list.current) return;
    const option = list.current.children[activeIndex] as
      HTMLElement | undefined;
    if (!option) return;
    const row = option.getBoundingClientRect();
    const box = list.current.getBoundingClientRect();
    if (row.bottom > box.bottom)
      list.current.scrollTop += row.bottom - box.bottom;
    else if (row.top < box.top) list.current.scrollTop -= box.top - row.top;
  }, [activeIndex, open]);

  function show() {
    if (disabled) return;
    setActive(selected);
    search.current = { text: "", time: 0 };
    popup.current?.showPopover();
    position();
    list.current?.focus({ preventScroll: true });
  }
  function close() {
    popup.current?.hidePopover();
    trigger.current?.focus({ preventScroll: true });
  }
  function choose(index: number) {
    if (disabled || !options[index]) return;
    close();
    if (options[index].id !== (value || ""))
      onChange(options[index].id || null);
  }

  return (
    <>
      <button
        ref={trigger}
        type="button"
        className={`chat-assignee${value ? "" : " is-unassigned"}`}
        aria-label="Ответственный за диалог"
        aria-describedby={`${id}-value`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        disabled={disabled}
        popoverTarget={`${id}-popup`}
        onClick={() => {
          setActive(selected);
          search.current = { text: "", time: 0 };
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            show();
          }
        }}
      >
        <UserRound
          className="chat-assignee-icon"
          size={18}
          aria-hidden="true"
        />
        <span className="chat-assignee-content">
          <span className="chat-assignee-caption">Ответственный</span>
          <span className="chat-assignee-field">
            <span
              id={`${id}-value`}
              className="chat-assignee-name"
              title={current.name}
            >
              {current.name}
            </span>
            <ChevronDown size={14} aria-hidden="true" />
          </span>
        </span>
      </button>
      <div
        ref={popup}
        id={`${id}-popup`}
        popover="auto"
        className="chat-assignee-popup"
        onToggle={(event) => {
          const visible = event.newState === "open";
          setOpen(visible);
          if (visible) {
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
        <div className="chat-assignee-heading" id={`${id}-label`}>
          Назначить ответственного
        </div>
        <div
          ref={list}
          id={`${id}-list`}
          className="chat-assignee-list"
          role="listbox"
          aria-labelledby={`${id}-label`}
          aria-activedescendant={`${id}-option-${activeIndex}`}
          tabIndex={-1}
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
            else if (event.key === "ArrowUp")
              setActive((index) => Math.max(index - 1, 0));
            else if (event.key === "Home") setActive(0);
            else if (event.key === "End") setActive(options.length - 1);
            else if (event.key === "Enter" || event.key === " ")
              choose(activeIndex);
            else if (event.key === "Escape") {
              event.stopPropagation();
              close();
            } else if (event.key === "Tab") close();
            else if (
              event.key.length === 1 &&
              !event.ctrlKey &&
              !event.metaKey &&
              !event.altKey
            ) {
              const now = Date.now();
              const key = event.key.toLocaleLowerCase("ru");
              const query =
                (now - search.current.time < 700 ? search.current.text : "") +
                key;
              const find = (prefix: string) =>
                options.findIndex((_, offset) =>
                  options[(activeIndex + offset + 1) % options.length].name
                    .toLocaleLowerCase("ru")
                    .startsWith(prefix),
                );
              let offset = find(query);
              if (offset < 0) offset = find(key);
              if (offset >= 0)
                setActive((activeIndex + offset + 1) % options.length);
              search.current = {
                text: offset >= 0 && find(query) >= 0 ? query : key,
                time: now,
              };
            }
          }}
        >
          {options.map((person, index) => (
            <div
              key={person.id}
              id={`${id}-option-${index}`}
              role="option"
              aria-label={person.name}
              aria-selected={person.id === (value || "")}
              className={`chat-assignee-option${index === activeIndex ? " is-active" : ""}${person.id ? "" : " is-unassigned"}`}
              onClick={() => choose(index)}
            >
              {person.id ? (
                <Avatar name={person.name} />
              ) : (
                <span className="chat-assignee-empty-icon">
                  <UserRoundMinus size={18} aria-hidden="true" />
                </span>
              )}
              <span className="chat-assignee-option-name">{person.name}</span>
              {person.id === (value || "") && (
                <span className="chat-assignee-check">
                  <Check size={13} strokeWidth={2.5} aria-hidden="true" />
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
