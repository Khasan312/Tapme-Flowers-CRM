import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowUpRight,
  CalendarDays,
  Check,
  CheckCheck,
  Clock3,
  Flower2,
  MessageCircle,
  PackageCheck,
  Phone,
  RefreshCw,
  ShoppingBag,
  Star,
  Truck,
  X,
} from "lucide-react";
import { errorText, request } from "./api";
import { useRemote } from "./hooks";
import { initials, shortDate } from "./ui";
import "./public.css";

type PublicOrder = {
  number: number;
  status: string;
  fulfillment: string;
  delivery_date: string;
  window_start: string;
  window_end: string;
  shop_name: string;
  shop_phone: string;
  can_review: boolean;
};

const states: Record<
  string,
  { label: string; title: string; description: string }
> = {
  new: {
    label: "Принят",
    title: "Ваш заказ принят",
    description:
      "Магазин принял ваш заказ. Впереди — выбор цветов и сборка букета.",
  },
  work: {
    label: "Собираем",
    title: "Собираем ваш букет",
    description:
      "Флорист собирает композицию, подбирает цветы и завершает детали.",
  },
  ready: {
    label: "Собран",
    title: "Ваш букет готов",
    description: "Букет собран и упакован. Осталось передать его в ваши руки.",
  },
  route: {
    label: "В пути",
    title: "Цветы уже в пути",
    description: "Курьер везёт букет получателю. Время доставки указано ниже.",
  },
  done: {
    label: "Вручён",
    title: "Букет у получателя",
    description:
      "Букет уже у получателя. Спасибо, что доверили нам этот момент.",
  },
  cancelled: {
    label: "Отменён",
    title: "Заказ отменён",
    description:
      "Если остались вопросы или хочется выбрать другой букет, свяжитесь с магазином.",
  },
};

function BouquetArt({
  done,
  cancelled,
}: {
  done: boolean;
  cancelled: boolean;
}) {
  return (
    <div
      className={`tracking-art${cancelled ? " is-muted" : ""}`}
      aria-hidden="true"
    >
      <div className="tracking-art-halo" />
      <svg viewBox="0 0 240 240" className="tracking-bouquet" fill="none">
        <path d="M72 132 121 214 174 125 128 147Z" fill="#d3dcc7" />
        <path d="m76 120 45 94 12-77Z" fill="#e6eadc" />
        <path d="m121 214 9-77 40-23Z" fill="#f5f3e9" />
        <g stroke="#48745c" strokeWidth="3" strokeLinecap="round">
          <path d="M121 170 107 68M120 169l36-76M121 169 77 94" />
          <path
            d="M119 137c-34-27-41-13-12 3M132 129c28-30 39-15 3 3"
            fill="#87a281"
          />
          <path
            d="M106 101C83 75 85 64 104 78M143 114c33-13 35-33 11-18"
            fill="#b1bfa0"
          />
        </g>
        {[
          { x: 79, y: 88, color: "#d1b5d9", center: "#a778ac", size: 15 },
          { x: 153, y: 80, color: "#f0c9be", center: "#c58a86", size: 18 },
          { x: 109, y: 58, color: "#f6eee0", center: "#c7ae73", size: 20 },
        ].map(({ x, y, color, center, size }) => (
          <g key={x}>
            {[0, 60, 120, 180, 240, 300].map((angle) => (
              <ellipse
                key={angle}
                cx={x}
                cy={y - size * 0.55}
                rx={size * 0.55}
                ry={size * 0.85}
                fill={color}
                transform={`rotate(${angle} ${x} ${y})`}
              />
            ))}
            <circle cx={x} cy={y} r={size * 0.35} fill={center} />
          </g>
        ))}
        <path
          d="M102 174c15 8 24 7 39-1"
          stroke="#a48bb4"
          strokeWidth="6"
          strokeLinecap="round"
        />
        <path
          d="M122 177c-24-30-41-9-8 0m8 0c28-28 39-7 9 1m-9-1-11 25m12-25 13 20"
          stroke="#9b7baa"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <circle cx="39" cy="59" r="3" fill="#b8c8af" />
        <circle cx="195" cy="144" r="4" fill="#d7c3df" />
        <path
          d="M188 47v12m-6-6h12M47 151v8m-4-4h8"
          stroke="#baa1c5"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
      {done && (
        <span className="tracking-art-check">
          <CheckCheck size={24} />
        </span>
      )}
    </div>
  );
}

export function PublicOrderPage({ token }: { token: string }) {
  const [revision, setRevision] = useState(0),
    [error, setError] = useState("");
  const [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const [rating, setRating] = useState(5);
  const path = `/public/orders/${encodeURIComponent(token)}/`;
  // This page owns its polling and stops all automatic requests for final statuses.
  const source = useRemote<PublicOrder>(path, revision, {
    refreshOnAppear: false,
  });
  const status = source.data?.status;
  useEffect(() => {
    if (!status || status === "done" || status === "cancelled") return;
    let requested = false;
    const refresh = () => {
      if (
        requested ||
        source.loading ||
        document.visibilityState !== "visible" ||
        !navigator.onLine
      )
        return;
      requested = true;
      setRevision((v) => v + 1);
    };
    // Wait for the preceding request to finish; slow connections never pile up requests.
    const timer =
      !source.loading &&
      document.visibilityState === "visible" &&
      navigator.onLine
        ? window.setTimeout(refresh, source.error ? 30000 : 15000)
        : undefined;
    document.addEventListener("visibilitychange", refresh);
    window.addEventListener("online", refresh);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", refresh);
      window.removeEventListener("online", refresh);
    };
  }, [path, status, source.loading, source.error]);
  async function review(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(e.currentTarget);
    try {
      await request(path, {
        method: "POST",
        body: JSON.stringify({
          rating: Number(data.get("rating")),
          message: data.get("message"),
        }),
      });
      setNotice("Спасибо за отзыв! Магазин получил вашу оценку.");
      setRevision((v) => v + 1);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  const o = source.data;
  const state = states[o?.status || "new"] || states.new;
  const done = o?.status === "done",
    cancelled = o?.status === "cancelled";
  const pickup = o?.fulfillment === "pickup";
  const steps = [
    {
      key: "new",
      label: "Принят",
      detail: "Заказ подтверждён магазином",
      icon: ShoppingBag,
    },
    {
      key: "ready",
      label: "Собран",
      detail: "Цветы собраны и упакованы",
      icon: Flower2,
    },
    ...(!pickup
      ? [
          {
            key: "route",
            label: "В пути",
            detail: "Букет передан курьеру",
            icon: Truck,
          },
        ]
      : []),
    {
      key: "done",
      label: pickup ? "Выдан" : "Доставлен",
      detail: "Букет у получателя",
      icon: PackageCheck,
    },
  ];
  const current = steps.findIndex(
    (s) => s.key === (o?.status === "work" ? "new" : o?.status),
  );
  const refresh = () => setRevision((v) => v + 1);
  return (
    <main className="tracking-page">
      <div className="tracking-shell">
        <header className="tracking-header">
          <div className="tracking-store">
            <span className="tracking-store-mark" aria-hidden="true">
              {o ? initials(o.shop_name) : <Flower2 size={24} />}
            </span>
            <div>
              <strong>{o?.shop_name || "Tapme Flowers"}</strong>
              <span>Цветы для ваших моментов</span>
            </div>
          </div>
          {o && (
            <span className="tracking-order-number">Заказ №{o.number}</span>
          )}
        </header>
        {!o ? (
          <section className="tracking-unavailable">
            <Flower2 size={42} aria-hidden="true" />
            {source.initialLoading ? (
              <>
                <h1>Открываем ваш заказ</h1>
                <p role="status">Ещё немного…</p>
                <div className="tracking-loading" />
              </>
            ) : (
              <>
                <h1>Не удалось открыть заказ</h1>
                <p role="alert">
                  {source.error ||
                    "Проверьте ссылку или уточните её у магазина."}
                </p>
                <button
                  type="button"
                  className="tracking-primary"
                  onClick={refresh}
                >
                  <RefreshCw size={17} />
                  Попробовать снова
                </button>
              </>
            )}
          </section>
        ) : (
          <>
            {source.error && (
              <div role="alert" className="tracking-error">
                {source.error}
              </div>
            )}
            <section
              className={`tracking-hero${cancelled ? " is-cancelled" : ""}`}
            >
              <div className="tracking-hero-copy">
                <span
                  className={`tracking-status${done ? " is-done" : cancelled ? " is-cancelled" : ""}`}
                >
                  {done ? (
                    <Check size={14} />
                  ) : cancelled ? (
                    <X size={14} />
                  ) : (
                    <span className="tracking-live-dot" />
                  )}
                  {state.label}
                </span>
                <h1 aria-live="polite">{state.title}</h1>
                <p>
                  {o.status === "ready"
                    ? pickup
                      ? "Букет собран и упакован. Можно забирать его в магазине в указанное время."
                      : "Букет собран и упакован. Скоро передадим его курьеру."
                    : state.description}
                </p>
              </div>
              <BouquetArt done={done} cancelled={cancelled} />
            </section>
            <div className="tracking-grid">
              <section className="tracking-card tracking-progress">
                <div className="tracking-card-heading">
                  <h2>Путь вашего букета</h2>
                  <Flower2 size={19} aria-hidden="true" />
                </div>
                {cancelled ? (
                  <div className="tracking-cancelled">
                    <X size={24} aria-hidden="true" />
                    <div>
                      <strong>Выполнение заказа остановлено</strong>
                      <p>Магазин поможет уточнить детали отмены.</p>
                    </div>
                  </div>
                ) : (
                  <ol className="tracking-steps" aria-label="Этапы заказа">
                    {steps.map((step, index) => {
                      const completed = done || index < current;
                      const active = !done && index === current;
                      const Icon = step.icon;
                      return (
                        <li
                          key={step.key}
                          className={`${completed ? "is-complete" : active ? "is-current" : "is-future"}`}
                          aria-current={active ? "step" : undefined}
                        >
                          <span
                            className="tracking-step-dot"
                            aria-hidden="true"
                          >
                            {completed ? (
                              <Check size={16} strokeWidth={2.8} />
                            ) : (
                              <Icon size={18} />
                            )}
                          </span>
                          <div>
                            <strong>{step.label}</strong>
                            <span>
                              {active && o.status === "work"
                                ? "Флорист сейчас собирает букет"
                                : active
                                  ? "Сейчас на этом этапе"
                                  : completed
                                    ? step.detail
                                    : "Впереди"}
                            </span>
                          </div>
                          {active && (
                            <span className="tracking-now">Сейчас</span>
                          )}
                        </li>
                      );
                    })}
                  </ol>
                )}
                <button
                  type="button"
                  className="tracking-refresh"
                  onClick={refresh}
                  disabled={source.loading}
                >
                  <RefreshCw
                    size={15}
                    className={source.refreshing ? "spinning" : ""}
                    aria-hidden="true"
                  />
                  {source.refreshing ? "Обновляем статус…" : "Обновить статус"}
                </button>
                {!done && !cancelled && (
                  <p className="tracking-auto-refresh">
                    Статус обновляется автоматически
                  </p>
                )}
              </section>
              <div className="tracking-side">
                <section className="tracking-card tracking-details">
                  <div className="tracking-card-heading">
                    <h2>{pickup ? "Самовывоз" : "Доставка"}</h2>
                    {pickup ? <ShoppingBag size={19} /> : <Truck size={19} />}
                  </div>
                  <div className="tracking-detail">
                    <span>
                      <CalendarDays size={19} />
                    </span>
                    <div>
                      <small>Дата получения</small>
                      <strong>{shortDate(o.delivery_date)}</strong>
                    </div>
                  </div>
                  <div className="tracking-detail">
                    <span>
                      <Clock3 size={19} />
                    </span>
                    <div>
                      <small>Время {pickup ? "получения" : "доставки"}</small>
                      <strong>
                        {o.window_start.slice(0, 5)} —{" "}
                        {o.window_end.slice(0, 5)}
                      </strong>
                    </div>
                  </div>
                  {!done && !cancelled && (
                    <p className="tracking-detail-note">
                      {pickup
                        ? "Букет будет ждать вас в магазине."
                        : "Курьер доставит букет в этот промежуток времени."}
                    </p>
                  )}
                </section>
                {o.shop_phone && (
                  <section className="tracking-contact">
                    <h2>Мы на связи</h2>
                    <p>
                      Вопрос о букете или деталях заказа? Обратитесь прямо в
                      магазин.
                    </p>
                    <div className="tracking-contact-actions">
                      <a
                        href={`https://wa.me/${o.shop_phone.replace(/\D/g, "")}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <MessageCircle size={18} />
                        Написать магазину
                        <ArrowUpRight size={16} />
                      </a>
                      <a
                        href={`tel:${o.shop_phone}`}
                        aria-label="Позвонить магазину"
                      >
                        <Phone size={18} />
                      </a>
                    </div>
                  </section>
                )}
              </div>
            </div>
            {notice ? (
              <section className="tracking-card tracking-thanks" role="status">
                <span>
                  <CheckCheck size={24} />
                </span>
                <div>
                  <h2>Спасибо за ваши слова</h2>
                  <p>{notice}</p>
                </div>
              </section>
            ) : (
              o.can_review && (
                <section className="tracking-card tracking-feedback">
                  <div>
                    <span className="tracking-eyebrow">ВАШЕ ВПЕЧАТЛЕНИЕ</span>
                    <h2>Как вам букет?</h2>
                    <p>
                      Пара слов о цветах и доставке поможет магазину стать
                      лучше.
                    </p>
                  </div>
                  <form onSubmit={review}>
                    <fieldset
                      disabled={busy}
                      className="tracking-review-fields"
                    >
                      <fieldset className="tracking-stars">
                        <legend>Оценка букета</legend>
                        {[1, 2, 3, 4, 5].map((n) => (
                          <label
                            key={n}
                            className={n <= rating ? "is-filled" : ""}
                          >
                            <input
                              type="radio"
                              name="rating"
                              value={n}
                              checked={rating === n}
                              onChange={() => setRating(n)}
                              aria-label={`${n} из 5`}
                            />
                            <Star size={25} aria-hidden="true" />
                          </label>
                        ))}
                      </fieldset>
                      <label className="tracking-review-label">
                        Ваш отзыв
                        <textarea
                          name="message"
                          maxLength={2000}
                          placeholder="Расскажите о букете и вашем впечатлении"
                        />
                      </label>
                      {error && (
                        <p role="alert" className="tracking-error">
                          {error}
                        </p>
                      )}
                      <button className="tracking-primary" disabled={busy}>
                        {busy ? "Отправляем…" : "Отправить отзыв"}
                        <ArrowUpRight size={17} />
                      </button>
                    </fieldset>
                  </form>
                </section>
              )
            )}
          </>
        )}
        <footer className="tracking-footer">
          <Flower2 size={17} aria-hidden="true" />
          <span>
            Работает на <strong>Tapme Flowers</strong>
          </span>
        </footer>
      </div>
    </main>
  );
}
