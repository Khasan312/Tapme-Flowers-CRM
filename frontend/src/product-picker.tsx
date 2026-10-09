import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown, Flower2, Search, X } from "lucide-react";
import { businessPath, errorText, price, request } from "./api";
import type { Page, Product } from "./types";

function Thumbnail({ product }: { product: Product | null }) {
  const [failed, setFailed] = useState("");
  return (
    <span className="bouquet-thumb" aria-hidden="true">
      {product?.photo_url && failed !== product.photo_url ? (
        <img
          src={product.photo_url}
          alt=""
          loading="lazy"
          onError={() => setFailed(product.photo_url!)}
        />
      ) : (
        <Flower2 size={23} strokeWidth={1.5} />
      )}
    </span>
  );
}

export function ProductPicker({
  businessId,
  value,
  onChange,
  disabled = false,
}: {
  businessId: string;
  value: Product | null;
  onChange: (product: Product) => void;
  disabled?: boolean;
}) {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const popup = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const selection = useRef(value);
  selection.current = value;
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [shown, setShown] = useState(20);
  const [active, setActive] = useState(-1);
  const matches = products.filter((p) =>
    p.name
      .toLocaleLowerCase("ru")
      .includes(query.trim().toLocaleLowerCase("ru")),
  );
  const visible = matches.slice(0, shown);

  useEffect(() => {
    const abort = new AbortController();
    setLoading(true);
    setError("");
    (async () => {
      try {
        // Load metadata in API-sized pages so search includes the entire price list.
        // Images are lazy loaded only for the options currently shown.
        const all: Product[] = [];
        let count = 1;
        while (all.length < count) {
          const page = await request<Page<Product>>(
            businessPath(businessId, "products") +
              `?limit=100&offset=${all.length}`,
            { signal: abort.signal },
          );
          if (abort.signal.aborted) return;
          count = page.count;
          all.push(...page.results);
          if (!page.results.length) break;
        }
        setProducts([...new Map(all.map((p) => [p.id, p])).values()]);
        if (!selection.current && all[0]) onChange(all[0]);
      } catch (e) {
        if (!abort.signal.aborted) setError(errorText(e));
      } finally {
        if (!abort.signal.aborted) setLoading(false);
      }
    })();
    return () => abort.abort();
  }, [businessId, retry, onChange]);

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
    const down = below >= 280 || below >= above;
    const popupWidth = Math.min(Math.max(anchor.width, 350), width - 24);
    popup.current.style.width = `${popupWidth}px`;
    popup.current.style.maxHeight = `${Math.min(height - 24, Math.max(120, Math.min(430, down ? below : above)))}px`;
    popup.current.style.left = `${Math.max(left + 12, Math.min(anchor.left, left + width - popupWidth - 12))}px`;
    const popupHeight = popup.current.offsetHeight;
    const wantedTop = down ? anchor.bottom + 8 : anchor.top - popupHeight - 8;
    popup.current.style.top = `${Math.max(top + 12, Math.min(wantedTop, top + height - popupHeight - 12))}px`;
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
    const option = list.current?.querySelector<HTMLElement>(
      `[data-index="${active}"]`,
    );
    if (open && option && list.current) {
      const row = option.getBoundingClientRect(),
        box = list.current.getBoundingClientRect();
      if (row.bottom > box.bottom)
        list.current.scrollTop += row.bottom - box.bottom;
      else if (row.top < box.top) list.current.scrollTop -= box.top - row.top;
    }
  }, [active, open]);
  function show() {
    // Toggle events arrive asynchronously; use the actual state for rapid reopen.
    if (popup.current?.matches(":popover-open")) {
      popup.current?.hidePopover();
      return;
    }
    setQuery("");
    const index = products.findIndex((p) => p.id === value?.id);
    setShown(Math.max(20, index + 1));
    setActive(index);
    popup.current?.showPopover();
    position();
    input.current?.focus({ preventScroll: true });
  }
  function close() {
    popup.current?.hidePopover();
    trigger.current?.focus({ preventScroll: true });
  }
  function choose(product: Product) {
    onChange(product);
    close();
  }
  return (
    <div className="bouquet-picker">
      <span className="bouquet-label" id={`${id}-label`}>
        Позиция прайса
      </span>
      <button
        ref={trigger}
        type="button"
        className="bouquet-trigger"
        aria-label="Позиция прайса"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={`${id}-popup`}
        disabled={disabled}
        onClick={show}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            show();
          }
        }}
      >
        <Thumbnail product={value} />
        <span className="bouquet-copy">
          <strong>
            {value?.name || (loading ? "Загружаем букеты…" : "Выберите букет")}
          </strong>
          <span>{value ? price(value.price) : "Фото, название и цена"}</span>
        </span>
        <ChevronDown
          size={18}
          className={open ? "turned" : ""}
          aria-hidden="true"
        />
      </button>
      <div
        ref={popup}
        id={`${id}-popup`}
        popover="auto"
        role="dialog"
        aria-label="Выбор букета"
        className="bouquet-popup"
        onToggle={(e) => setOpen(e.currentTarget.matches(":popover-open"))}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            e.preventDefault();
            e.stopPropagation();
            close();
          }
        }}
        onBlur={(e) => {
          if (
            e.relatedTarget &&
            !e.currentTarget.contains(e.relatedTarget as Node)
          )
            popup.current?.hidePopover();
        }}
      >
        <div className="bouquet-search">
          <Search size={17} aria-hidden="true" />
          <input
            ref={input}
            role="combobox"
            type="text"
            autoComplete="off"
            aria-label="Найти букет"
            aria-expanded={open}
            aria-controls={`${id}-list`}
            aria-autocomplete="list"
            aria-activedescendant={
              active >= 0 && visible[active]
                ? `${id}-option-${active}`
                : undefined
            }
            placeholder="Найти букет по названию"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setShown(20);
              setActive(-1);
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                e.preventDefault();
                setActive((i) =>
                  Math.max(
                    0,
                    Math.min(
                      visible.length - 1,
                      i + (e.key === "ArrowDown" ? 1 : -1),
                    ),
                  ),
                );
              }
              if (e.key === "Enter") {
                e.preventDefault();
                const product = visible[active < 0 ? 0 : active];
                if (product && !loading && !error) choose(product);
              }
            }}
          />
          {query && (
            <button
              type="button"
              className="bouquet-clear"
              aria-label="Очистить поиск букетов"
              onClick={() => {
                setQuery("");
                setActive(-1);
                input.current?.focus();
              }}
            >
              <X size={16} />
            </button>
          )}
        </div>
        <div className="bouquet-caption" aria-live="polite">
          {loading
            ? "Загружаем прайс…"
            : query.trim()
              ? `Найдено: ${matches.length}`
              : `Позиций в прайсе: ${products.length}`}
        </div>
        {error ? (
          <div className="bouquet-empty" role="alert">
            <p>{error}</p>
            <button type="button" onClick={() => setRetry((n) => n + 1)}>
              Попробовать снова
            </button>
          </div>
        ) : (
          <div
            ref={list}
            id={`${id}-list`}
            role="listbox"
            aria-label="Доступные букеты"
            aria-busy={loading}
            className="bouquet-options"
          >
            {!loading &&
              visible.map((product, index) => (
                <button
                  type="button"
                  role="option"
                  id={`${id}-option-${index}`}
                  data-index={index}
                  key={product.id}
                  tabIndex={-1}
                  aria-selected={value?.id === product.id}
                  className={`bouquet-option${active === index ? " is-active" : ""}`}
                  onPointerMove={() => setActive(index)}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => choose(product)}
                >
                  <Thumbnail product={product} />
                  <span className="bouquet-copy">
                    <strong>{product.name}</strong>
                    <span>{price(product.price)}</span>
                  </span>
                  {value?.id === product.id && (
                    <Check size={18} aria-hidden="true" />
                  )}
                </button>
              ))}
          </div>
        )}
        {!loading && !error && !matches.length && (
          <div className="bouquet-empty">
            <Flower2 size={26} aria-hidden="true" />
            <strong>
              {query.trim() ? "Букет не найден" : "В прайсе пока нет букетов"}
            </strong>
            <p>
              {query.trim()
                ? "Попробуйте другое название."
                : "Добавьте первую позицию в настройках прайса."}
            </p>
          </div>
        )}
        {!loading && !error && matches.length > shown && (
          <button
            type="button"
            className="bouquet-more"
            onClick={() => setShown((n) => n + 20)}
          >
            Показать ещё · {matches.length - shown}
          </button>
        )}
        <div className="bouquet-foot">
          Выберите букет, затем нажмите «Добавить в заказ»
        </div>
      </div>
    </div>
  );
}
