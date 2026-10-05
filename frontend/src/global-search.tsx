import { useEffect, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { businessPath, errorText, request } from "./api";
import { Avatar } from "./ui";
import type { Business, Customer, Order, Page } from "./types";
type Match =
  { kind: "customer"; value: Customer } | { kind: "order"; value: Order };
export function GlobalSearch({
  business,
  openCustomer,
  openOrder,
}: {
  business: Business;
  openCustomer: (id: string) => void;
  openOrder: (order: Order) => void;
}) {
  const [query, setQuery] = useState(""),
    [matches, setMatches] = useState<Match[]>([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [open, setOpen] = useState(false),
    [active, setActive] = useState(-1);
  const input = useRef<HTMLInputElement>(null),
    box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    function keys(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      if (
        e.key === "/" &&
        !target.closest("input,textarea,select,[contenteditable],dialog")
      ) {
        e.preventDefault();
        input.current?.focus();
      }
    }
    function outside(e: PointerEvent) {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("keydown", keys);
    document.addEventListener("pointerdown", outside);
    return () => {
      document.removeEventListener("keydown", keys);
      document.removeEventListener("pointerdown", outside);
    };
  }, []);
  useEffect(() => {
    setMatches([]);
    setActive(-1);
    setError("");
    if (query.trim().length < 2) {
      setBusy(false);
      return;
    }
    const controller = new AbortController();
    setBusy(true);
    const timer = setTimeout(async () => {
      try {
        const params = new URLSearchParams({
          search: query.trim(),
          limit: "8",
        });
        const [customers, orders] = await Promise.all([
          request<Page<Customer>>(
            businessPath(business.id, "customers") + "?" + params,
            { signal: controller.signal },
          ),
          request<Page<Order>>(
            businessPath(business.id, "orders") + "?" + params,
            { signal: controller.signal },
          ),
        ]);
        if (!controller.signal.aborted)
          setMatches([
            ...orders.results.map((value) => ({
              kind: "order" as const,
              value,
            })),
            ...customers.results.map((value) => ({
              kind: "customer" as const,
              value,
            })),
          ]);
      } catch (e) {
        if (!controller.signal.aborted) setError(errorText(e));
      } finally {
        if (!controller.signal.aborted) setBusy(false);
      }
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [business.id, query]);
  function choose(match: Match) {
    setOpen(false);
    setQuery("");
    if (match.kind === "customer") openCustomer(match.value.id);
    else openOrder(match.value);
  }
  return (
    <div className="global-search" ref={box}>
      <div className="search">
        <Search size={14} />
        <input
          ref={input}
          type="search"
          role="combobox"
          aria-expanded={open && query.trim().length >= 2}
          aria-controls="global-results"
          aria-activedescendant={
            active >= 0 ? `global-result-${active}` : undefined
          }
          aria-autocomplete="list"
          aria-label="Поиск"
          placeholder="Телефон, имя, ID клиента или получателя, № или ID заказа"
          value={query}
          onFocus={() => setOpen(true)}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setOpen(false);
              input.current?.blur();
            }
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setActive((n) => Math.min(n + 1, matches.length - 1));
            }
            if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((n) => Math.max(n - 1, 0));
            }
            if (e.key === "Enter" && matches.length) {
              e.preventDefault();
              choose(matches[active < 0 ? 0 : active]);
            }
          }}
        />
        <span className="kbd">/</span>
      </div>
      {open && query.trim().length >= 2 && (
        <div
          className="search-results"
          id="global-results"
          role="listbox"
          aria-label="Результаты поиска"
        >
          {busy ? (
            <p className="empty">Ищем…</p>
          ) : error ? (
            <p className="empty">{error}</p>
          ) : !matches.length ? (
            <p className="empty">Ничего не найдено</p>
          ) : (
            matches.map((match, i) => (
              <button
                type="button"
                role="option"
                aria-selected={active === i}
                id={`global-result-${i}`}
                key={match.kind + match.value.id}
                className="lrow"
                onClick={() => choose(match)}
              >
                <Avatar
                  name={
                    match.kind === "customer"
                      ? match.value.name
                      : match.value.recipient_name
                  }
                />
                <span>
                  <span className="t">
                    {match.kind === "customer"
                      ? match.value.name
                      : `№${match.value.number} · ${match.value.recipient_name}`}
                  </span>
                  <span className="s">
                    {match.kind === "customer"
                      ? match.value.phone
                      : `${match.value.customer_name} · ${match.value.delivery_date}`}
                  </span>
                </span>
                <span className="tag">
                  {match.kind === "customer" ? "Клиент" : "Заказ"}
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
