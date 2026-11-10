import { useEffect, useId, useState } from "react";
import {
  Search,
  MapPin,
  MoreHorizontal,
  RefreshCw,
  SlidersHorizontal,
  ChevronDown,
} from "lucide-react";
import { businessPath, errorText, price, request } from "./api";
import { Notice, Pager, RefreshIndicator } from "./components";
import { useRemote } from "./hooks";
import { Status, statusNames } from "./orders";
import { shopDay, shortDate } from "./ui";
import type { Business, Order, Staff } from "./types";
type Desk = {
  count: number;
  results: Order[];
  summary: {
    orders: number;
    done: number;
    route: number;
    build: number;
    late: number;
    total: string;
  };
  urgent_counts?: Record<"build" | "late", number>;
  scopes: Record<string, number>;
  tasks: {
    id: string;
    order_id: string;
    title: string;
    subtitle: string;
    tone: string;
  }[];
  calendar: { delivery_date: string; count: number; total: string }[];
};
const scopes: Record<string, string> = {
  today: "Сегодня",
  tomorrow: "Завтра",
  upcoming: "Предстоящие",
  pickup: "Самовывоз",
  unpaid: "Не оплачены",
  pending: "Ждут подтверждения",
  cancelled: "Отменённые",
  all: "Все",
};
const modes: Record<string, string> = {
  wall: "Плитки",
  board: "Доска",
  list: "Список",
  calendar: "Календарь",
};
const statuses: Record<string, string> = {
  "": "Все",
  build: "Собрать",
  late: "Опаздывают",
  delivery: "Везём",
  pickup: "Самовывоз",
  done: "Вручено",
};
function timing(order: Order, business: Business, now: Date) {
  if (order.status === "pending")
    return { tone: "", text: "ждёт подтверждения" };
  if (order.status === "done") return { tone: "", text: "вручён" };
  if (order.status === "cancelled") return { tone: "", text: "отменён" };
  const today = shopDay(business.timezone);
  const minutes = new Intl.DateTimeFormat("en-GB", {
    timeZone: business.timezone,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  })
    .format(now)
    .split(":")
    .map(Number);
  const clock = minutes[0] * 60 + minutes[1],
    start =
      Number(order.window_start.slice(0, 2)) * 60 +
      Number(order.window_start.slice(3, 5)),
    end =
      Number(order.window_end.slice(0, 2)) * 60 +
      Number(order.window_end.slice(3, 5));
  if (order.delivery_date < today)
    return {
      tone: "crit",
      text: `опоздание · ${shortDate(order.delivery_date)}`,
    };
  if (order.delivery_date > today)
    return { tone: "", text: shortDate(order.delivery_date) };
  const remaining = (clock < start ? start : end) - clock;
  const span = `${Math.floor(Math.abs(remaining) / 60) ? Math.floor(Math.abs(remaining) / 60) + " ч " : ""}${Math.abs(remaining) % 60} мин`;
  return {
    tone: remaining < 0 ? "crit" : remaining < 60 ? "warn" : "ok",
    text:
      remaining < 0
        ? `опоздание ${span}`
        : clock < start
          ? `до ${order.window_start.slice(0, 5)} ${span}`
          : `окно идёт, до ${order.window_end.slice(0, 5)} ${span}`,
  };
}
export function OrderDesk({
  business,
  revision,
  openOrder,
  section,
  chooseSection,
}: {
  business: Business;
  revision: number;
  openOrder: (order: Order) => void;
  section: "orders" | "tasks";
  chooseSection: (section: "orders" | "tasks") => void;
}) {
  const filterId = useId();
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [scope, setScope] = useState("today"),
    [mode, setMode] = useState("wall"),
    [filter, setFilter] = useState(""),
    [query, setQuery] = useState(""),
    [search, setSearch] = useState(""),
    [day, setDay] = useState(""),
    [offset, setOffset] = useState(0),
    [tasksOpen, setTasksOpen] = useState(true),
    [refresh, setRefresh] = useState(0),
    [notesRevision, setNotesRevision] = useState(0),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [now, setNow] = useState(new Date()),
    [calendarShift, setCalendarShift] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(query);
      setOffset(0);
    }, 200);
    return () => clearTimeout(timer);
  }, [query]);
  const params = new URLSearchParams({
    scope,
    day,
    search,
    status: filter,
    limit: "50",
    offset: String(offset),
  });
  if (!day) params.delete("day");
  const data = useRemote<Desk>(
      businessPath(business.id, "orders/desk") + "?" + params,
      revision + refresh,
    ),
    staff = useRemote<Staff[]>(businessPath(business.id, "staff"), refresh),
    notes = useRemote<{ id: string; content: string }[]>(
      businessPath(business.id, "office-tasks"),
      notesRevision,
    );
  const source = data.data,
    orders = source?.results || [];
  const taskPanelOpen = tasksOpen || section === "tasks";
  const totals = source?.summary;
  const urgent = source?.urgent_counts || totals;
  const team = (id: string | null) =>
    staff.data?.find((s) => s.id === id)?.name || "";
  async function openById(id: string) {
    try {
      openOrder(
        await request<Order>(businessPath(business.id, `orders/${id}`)),
      );
    } catch (e) {
      setError(errorText(e));
    }
  }
  async function advance(order: Order) {
    const target =
      order.status === "new"
        ? "work"
        : order.status === "work"
          ? "ready"
          : order.status === "ready"
            ? order.fulfillment === "pickup"
              ? "done"
              : "route"
            : "done";
    if (
      (!order.florist_id && target !== "done") ||
      (target === "route" && !order.courier_id)
    ) {
      openOrder(order);
      return;
    }
    setBusy(true);
    setError("");
    try {
      await request(
        businessPath(business.id, `orders/${order.id}/transition`),
        {
          method: "POST",
          body: JSON.stringify({ version: order.version, status: target }),
        },
      );
      setRefresh((r) => r + 1);
    } catch (e) {
      setError(errorText(e));
      setRefresh((r) => r + 1);
    } finally {
      setBusy(false);
    }
  }
  const action = (order: Order) =>
    ({
      new: "Передать флористу",
      work: "Собран",
      ready: order.fulfillment === "pickup" ? "Выдан" : "Курьер забрал",
      route: "Вручён",
    })[order.status] || "";
  function chooseScope(value: string) {
    setScope(value);
    if (value !== "date") setDay("");
    setFilter("");
    setOffset(0);
    setFiltersOpen(false);
  }
  const calendarStart = new Date(shopDay(business.timezone) + "T12:00:00Z");
  calendarStart.setUTCDate(
    calendarStart.getUTCDate() -
      ((calendarStart.getUTCDay() + 6) % 7) +
      calendarShift * 21,
  );
  return (
    <section
      className={`order-desk${section === "tasks" ? " is-tasks" : ""}${filtersOpen ? " filters-open" : ""}`}
    >
      <div
        className="seg desk-mobile-sections"
        role="group"
        aria-label="Заказы и задачи"
      >
        <button
          className={section === "orders" ? "is-on" : ""}
          aria-label="Показать заказы"
          aria-pressed={section === "orders"}
          onClick={() => chooseSection("orders")}
        >
          Заказы
        </button>
        <button
          className={section === "tasks" ? "is-on" : ""}
          aria-label="Показать задачи"
          aria-description={`${(source?.tasks.length || 0) + (notes.data?.length || 0)} открытых задач`}
          aria-pressed={section === "tasks"}
          onClick={() => chooseSection("tasks")}
        >
          Задачи
          <span className="desk-task-count">
            {(source?.tasks.length || 0) + (notes.data?.length || 0)}
          </span>
        </button>
      </div>
      <div className="thd">
        <div className="thd-clock">
          {new Intl.DateTimeFormat("ru-RU", {
            timeZone: business.timezone,
            hour: "2-digit",
            minute: "2-digit",
          }).format(now)}
        </div>
        <div className="thd-nums">
          {[
            [totals?.orders, "заказов", ""],
            [totals?.done, "вручено", "ok"],
            [totals?.route, "в пути", ""],
            [urgent?.build, "Ждут сборки", "warn", "build"],
            [urgent?.late, "Опаздывают", urgent?.late ? "crit" : "", "late"],
            [
              totals ? price(totals.total).replace(" сом", "") : undefined,
              "сом",
              "",
            ],
          ].map(([value, label, tone, key]) =>
            key === "build" || key === "late" ? (
              <button
                key={key}
                type="button"
                className={`order-urgent-filter ${tone || "neutral"}`}
                aria-pressed={filter === key}
                onClick={() => {
                  setFilter(filter === key ? "" : key);
                  setOffset(0);
                  if (mode === "calendar") setMode("wall");
                }}
              >
                <b className={String(tone)}>{value ?? "—"}</b>
                {label}
              </button>
            ) : (
              <div key={String(label)}>
                <b className={String(tone)}>{value ?? "—"}</b>
                {label}
              </div>
            ),
          )}
        </div>
        <div className="order-desk-actions">
          <div className="seg" aria-label="Вид заказов">
            {Object.entries(modes).map(([key, label]) => (
              <button
                key={key}
                className={mode === key ? "is-on" : ""}
                onClick={() => {
                  setMode(key);
                  if (key === "calendar") chooseScope("all");
                }}
              >
                {label}
              </button>
            ))}
          </div>
          <button
            className={`btn sm desktop-task-toggle${taskPanelOpen ? "" : " ghost"}`}
            aria-expanded={taskPanelOpen}
            onClick={() => {
              setTasksOpen(!taskPanelOpen);
              if (section === "tasks") chooseSection("orders");
            }}
          >
            Задачи
            {Boolean(
              (source?.tasks.length || 0) + (notes.data?.length || 0),
            ) && (
              <span className="tag crit">
                {(source?.tasks.length || 0) + (notes.data?.length || 0)}
              </span>
            )}
          </button>
        </div>
      </div>
      <button
        className="btn desk-filter-toggle"
        aria-expanded={filtersOpen}
        aria-controls={`${filterId}-scopes${mode === "wall" ? ` ${filterId}-statuses` : ""}`}
        onClick={() => setFiltersOpen(!filtersOpen)}
      >
        <SlidersHorizontal size={16} />
        <span>Фильтры</span>
        <span className="desk-filter-summary">
          {scope === "date" ? shortDate(day) : scopes[scope]}
          {filter ? ` · ${statuses[filter]}` : ""}
        </span>
        <ChevronDown size={16} aria-hidden="true" />
      </button>
      <div className="pills order-scopes" id={`${filterId}-scopes`}>
        {Object.entries(scopes).map(([key, label]) => (
          <button
            key={key}
            className={`pill${scope === key ? " is-on" : ""}`}
            onClick={() => chooseScope(key)}
          >
            {label}
            <span className="cnt">{source?.scopes[key] ?? "—"}</span>
          </button>
        ))}
        {scope === "date" && (
          <button className="pill is-on">{shortDate(day)}</button>
        )}
        <label className="date-scope" title="Выбрать дату">
          <input
            type="date"
            aria-label="Дата получения"
            value={day}
            onChange={(e) => {
              setDay(e.target.value);
              chooseScope(e.target.value ? "date" : "all");
            }}
          />
        </label>
      </div>
      {(error || data.error || notes.error) && (
        <Notice>{error || data.error || notes.error}</Notice>
      )}
      <div className={`today-grid${taskPanelOpen ? "" : " solo"}`}>
        <div className="order-main">
          <label className="search order-local-search">
            <Search size={14} />
            <input
              type="search"
              aria-label="Поиск по заказам"
              placeholder="Найти заказ: имя, получатель, адрес, состав, №"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button
              className="iconbtn"
              type="button"
              aria-label="Обновить заказы"
              disabled={data.loading}
              onClick={() => {
                setRefresh((r) => r + 1);
                setNotesRevision((r) => r + 1);
              }}
            >
              <RefreshCw size={14} />
            </button>
          </label>
          {mode === "wall" && (
            <div className="pills wall-filters" id={`${filterId}-statuses`}>
              {Object.entries(statuses).map(([key, label]) => (
                <button
                  key={key}
                  className={`pill${filter === key ? " is-on" : ""}`}
                  onClick={() => {
                    setFilter(key);
                    setOffset(0);
                    setFiltersOpen(false);
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
          <RefreshIndicator active={data.refreshing} />
          {data.initialLoading ? (
            <div className="card empty">Загружаем заказы…</div>
          ) : mode === "calendar" ? (
            <>
              <div className="row calendar-nav">
                <button
                  className="btn sm"
                  aria-label="Предыдущие три недели"
                  onClick={() => setCalendarShift((v) => v - 1)}
                >
                  ←
                </button>
                <strong>
                  {shortDate(calendarStart.toISOString().slice(0, 10))}
                </strong>
                <button
                  className="btn sm"
                  aria-label="Следующие три недели"
                  onClick={() => setCalendarShift((v) => v + 1)}
                >
                  →
                </button>
              </div>
              <div className="cal">
                {["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"].map((d) => (
                  <div className="dow" key={d}>
                    {d}
                  </div>
                ))}
                {Array.from({ length: 21 }, (_, i) => {
                  const date = new Date(calendarStart);
                  date.setUTCDate(date.getUTCDate() + i);
                  const key = date.toISOString().slice(0, 10),
                    count = source?.calendar.find(
                      (c) => c.delivery_date === key,
                    );
                  return (
                    <button
                      className={`cday${key === shopDay(business.timezone) ? " today" : ""}`}
                      key={key}
                      onClick={() => {
                        setDay(key);
                        chooseScope("date");
                        setMode("wall");
                      }}
                    >
                      <span className="dn">{date.getUTCDate()}</span>
                      {count && (
                        <>
                          <span className="tag acc">{count.count} заказов</span>
                          <span className="small mono">
                            {price(count.total)}
                          </span>
                        </>
                      )}
                    </button>
                  );
                })}
              </div>
            </>
          ) : !orders.length ? (
            <div className="card empty">
              Заказов не найдено. Измените фильтр или создайте новый заказ.
            </div>
          ) : mode === "wall" ? (
            <div className="tiles">
              {orders.map((o) => {
                const timer = timing(o, business, now);
                return (
                  <article
                    key={o.id}
                    className={`tk ${timer.tone}${o.status === "done" ? " done" : ""}`}
                    onClick={(event) => {
                      const target = event.target;
                      if (
                        target instanceof Element &&
                        target.closest(
                          "button, a, input, select, textarea, [role='button']",
                        )
                      )
                        return;
                      const selection = window.getSelection();
                      if (
                        selection &&
                        !selection.isCollapsed &&
                        event.currentTarget.contains(selection.anchorNode)
                      )
                        return;
                      openOrder(o);
                    }}
                  >
                    <div className="tk-top">
                      <span className="tk-win">
                        {o.window_start.slice(0, 5)}
                        {o.fulfillment !== "pickup" &&
                          `–${o.window_end.slice(0, 5)}`}
                      </span>
                      <span className="tk-st">{statusNames[o.status]}</span>
                    </div>
                    <div className={`tk-time ${timer.tone}`}>{timer.text}</div>
                    <button
                      className="plain-button tk-items"
                      onClick={() => openOrder(o)}
                    >
                      {o.lines
                        .map(
                          (l) =>
                            l.name + (l.quantity > 1 ? ` ×${l.quantity}` : ""),
                        )
                        .join(", ")}
                    </button>
                    <div className="tk-who">
                      {o.customer_name}
                      {o.recipient_name !== o.customer_name &&
                        ` → ${o.recipient_name}`}
                    </div>
                    <div className="tk-addr">
                      <MapPin size={14} />
                      <span className="tk-addr-t">
                        {o.fulfillment === "pickup" ? "самовывоз" : o.address} ·{" "}
                        {price(o.total)}
                        {team(o.courier_id) && ` · ${team(o.courier_id)}`}
                      </span>
                    </div>
                    <div className="tk-badges">
                      {business.point_id === "all" && o.point_name && (
                        <span className="point-badge">{o.point_name}</span>
                      )}
                      {o.delivery_issue && (
                        <span className="badge crit">{o.delivery_issue}</span>
                      )}
                      {Number(o.paid_amount) < Number(o.total) && (
                        <span className="badge warn">не оплачен полностью</span>
                      )}
                      {o.card && <span className="badge">{o.card}</span>}
                    </div>
                    {o.notes && <p className="small muted">{o.notes}</p>}
                    <div className="tk-foot">
                      {action(o) ? (
                        <button
                          className="tk-btn primary"
                          disabled={busy || data.loading}
                          onClick={() => void advance(o)}
                        >
                          {action(o)}
                        </button>
                      ) : (
                        <span className="tk-done">{statusNames[o.status]}</span>
                      )}
                      <button
                        className="tk-more"
                        aria-label={`Открыть заказ №${o.number}`}
                        onClick={() => openOrder(o)}
                      >
                        <MoreHorizontal size={18} />
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : mode === "board" ? (
            <div className="kanban">
              {(scope === "cancelled"
                ? ["cancelled"]
                : scope === "pending"
                  ? ["pending"]
                  : [
                      ...(orders.some((o) => o.status === "pending")
                        ? ["pending"]
                        : []),
                      "new",
                      "work",
                      "ready",
                      "route",
                      "done",
                      ...(orders.some((o) => o.status === "cancelled")
                        ? ["cancelled"]
                        : []),
                    ]
              ).map((status) => (
                <section className="kcol" key={status}>
                  <div className="kcol-hd">
                    {statusNames[status]}
                    <span className="cnt">
                      {orders.filter((o) => o.status === status).length}
                    </span>
                  </div>
                  {orders
                    .filter((o) => o.status === status)
                    .map((o) => (
                      <button
                        className="kcard plain-button"
                        key={o.id}
                        onClick={() => openOrder(o)}
                      >
                        <span className="kt">
                          <span className="kn">№{o.number}</span>
                          {business.point_id === "all" && o.point_name && (
                            <span className="point-badge">{o.point_name}</span>
                          )}
                          <span>
                            {o.window_start.slice(0, 5)}–
                            {o.window_end.slice(0, 5)}
                          </span>
                        </span>
                        <span className="kb">
                          {o.lines.map((l) => l.name).join(", ")}
                        </span>
                        <span className="ks">
                          {o.customer_name} → {o.recipient_name}
                        </span>
                        <span className="kf">
                          <span className="tag">{price(o.total)}</span>
                          <span className="tag">
                            {o.fulfillment === "pickup"
                              ? "Самовывоз"
                              : "Доставка"}
                          </span>
                        </span>
                      </button>
                    ))}
                </section>
              ))}
            </div>
          ) : (
            <div className="card">
              <div className="tbl-wrap">
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>№</th>
                      <th>Клиент и получатель</th>
                      <th>Дата и окно</th>
                      <th>Состав</th>
                      <th>Статус</th>
                      <th>Оплата</th>
                      <th className="num">Сумма</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map((o) => (
                      <tr key={o.id} onClick={() => openOrder(o)}>
                        <td>
                          <button
                            className="plain-button mono"
                            onClick={(e) => {
                              e.stopPropagation();
                              openOrder(o);
                            }}
                          >
                            №{o.number}
                          </button>
                        </td>
                        <td>
                          <div className="b ink">{o.customer_name}</div>
                          <div className="small muted">{o.recipient_name}</div>
                          {business.point_id === "all" && o.point_name && (
                            <span className="point-badge">{o.point_name}</span>
                          )}
                        </td>
                        <td className="mono small">
                          {shortDate(o.delivery_date)}
                          <br />
                          {o.window_start.slice(0, 5)}–
                          {o.window_end.slice(0, 5)}
                        </td>
                        <td>
                          {o.lines
                            .map((l) => `${l.name} ×${l.quantity}`)
                            .join(", ")}
                        </td>
                        <td>
                          <Status value={o.status} />
                        </td>
                        <td>
                          <span
                            className={`tag${Number(o.paid_amount) >= Number(o.total) ? " ok" : " warn"}`}
                          >
                            {Number(o.paid_amount) >= Number(o.total)
                              ? "Оплачен"
                              : Number(o.paid_amount) > 0
                                ? "Частично"
                                : "Не оплачен"}
                          </span>
                        </td>
                        <td className="num">{price(o.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          {mode !== "calendar" && (
            <Pager
              count={source?.count || 0}
              offset={offset}
              setOffset={setOffset}
            />
          )}
        </div>
        {taskPanelOpen && (
          <aside className="tpanel">
            <div className="card">
              <div className="card-hd">
                <h2>Задачи</h2>
                <RefreshIndicator active={notes.refreshing} />
                <span
                  className={`tag${source?.tasks.length ? " crit" : " ok"}`}
                >
                  {(source?.tasks.length || 0) + (notes.data?.length || 0) ||
                    "всё сделано"}
                </span>
              </div>
              <div className="card-bd tight">
                {source?.tasks.map((task) => (
                  <div className={`task ${task.tone}`} key={task.id}>
                    <span className="task-marker" />
                    <div>
                      <div className="t">{task.title}</div>
                      <div className="s">{task.subtitle}</div>
                    </div>
                    <div className="acts">
                      <button
                        className="btn xs"
                        onClick={() => void openById(task.order_id)}
                      >
                        Открыть заказ
                      </button>
                    </div>
                  </div>
                ))}
                {notes.data?.map((note) => (
                  <div className="task" key={note.id}>
                    <button
                      className="chk"
                      aria-label={`Завершить: ${note.content}`}
                      onClick={async () => {
                        try {
                          await request(
                            businessPath(
                              business.id,
                              `office-tasks/${note.id}/done`,
                            ),
                            { method: "POST" },
                          );
                          setNotesRevision((r) => r + 1);
                        } catch (e) {
                          setError(errorText(e));
                        }
                      }}
                    />
                    <div className="t">{note.content}</div>
                  </div>
                ))}
                {!source?.tasks.length && !notes.data?.length && (
                  <div className="empty">Открытых задач нет</div>
                )}
                <form
                  className="task-add"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const form = e.currentTarget;
                    const content = new FormData(form).get("content");
                    try {
                      await request(businessPath(business.id, "office-tasks"), {
                        method: "POST",
                        body: JSON.stringify({ content }),
                      });
                      form.reset();
                      setNotesRevision((r) => r + 1);
                    } catch (e) {
                      setError(errorText(e));
                    }
                  }}
                >
                  <input
                    name="content"
                    required
                    maxLength={500}
                    placeholder="Своя задача, Enter чтобы добавить"
                    aria-label="Новая задача"
                  />
                </form>
              </div>
            </div>
          </aside>
        )}
      </div>
    </section>
  );
}
