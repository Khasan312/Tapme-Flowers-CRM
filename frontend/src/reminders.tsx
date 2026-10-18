import { useEffect, useState } from "react";
import {
  Bell,
  Check,
  Clock3,
  Info,
  MessageCircle,
  MoreHorizontal,
  Settings2,
  ShoppingBag,
} from "lucide-react";
import { businessPath, errorText, price, request } from "./api";
import { Modal, Notice, Pager, RefreshIndicator } from "./components";
import { useRemote } from "./hooks";
import { Avatar, shopDay, shortDate } from "./ui";
import type { Business, Order, Page, Reminder, ReminderPage } from "./types";
import "./reminders.css";

const tabs = {
  wait: "Написать",
  sent: "Ждём ответа",
  answered: "Ответили",
  ordered: "Заказали",
  skipped: "Пропущено",
};
function dateTone(row: Reminder, today: string) {
  if (!row.event_date) return "";
  const days = (Date.parse(row.event_date) - Date.parse(today)) / 86400000;
  return days <= 1 ? "urgent" : days <= 3 ? "soon" : "";
}
function group(row: Reminder, today: string) {
  if (row.kind === "after_last_order")
    return { title: "Давно не заказывали", rank: 1000 };
  if (row.kind === "after_delivery")
    return { title: "После доставки", rank: 1001 };
  if (row.kind === "holiday")
    return { title: `Праздник: ${row.event}`, rank: 999 };
  if (!row.event_date) return { title: "Важные даты", rank: 998 };
  const days = Math.round(
    (Date.parse(row.event_date) - Date.parse(today)) / 86400000,
  );
  return {
    title:
      days < 0
        ? "Событие уже прошло"
        : days === 0
          ? "Сегодня событие"
          : days === 1
            ? "Завтра"
            : days === 7
              ? "Через неделю"
              : days === 14
                ? "Через 2 недели"
                : `Через ${days} дн.`,
    rank: days,
  };
}

export function Reminders({
  business,
  settings,
  openCustomer,
  openOrder,
  createOrder,
  openChat,
}: {
  business: Business;
  settings: () => void;
  openCustomer: (id: string) => void;
  openOrder: (id: string) => void;
  createOrder: (row: Reminder) => void;
  openChat: (id: string) => void;
}) {
  const [state, setState] = useState<keyof typeof tabs>("wait");
  const [scenario, setScenario] = useState("");
  const [offset, setOffset] = useState(0),
    [revision, setRevision] = useState(0);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [busy, setBusy] = useState("");
  const [editing, setEditing] = useState<Reminder | null>(null),
    [text, setText] = useState("");
  const [confirm, setConfirm] = useState<{
    row: Reminder;
    action: "skipped" | "opt_out";
  } | null>(null);
  const [linking, setLinking] = useState<Reminder | null>(null);
  const [undo, setUndo] = useState<string | null>(null);
  const page = useRemote<ReminderPage>(
    businessPath(business.id, "reminders") +
      `?state=${state}&limit=50&offset=${offset}${scenario ? `&scenario=${scenario}` : ""}`,
    revision,
  );
  const today = shopDay(business.timezone);
  useEffect(() => {
    const timer = window.setInterval(() => setRevision((v) => v + 1), 60_000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!undo) return;
    const timer = window.setTimeout(() => setUndo(null), 10_000);
    return () => window.clearTimeout(timer);
  }, [undo]);
  useEffect(() => {
    if (page.data && offset >= page.data.count && offset > 0)
      setOffset(Math.max(0, Math.floor((page.data.count - 1) / 50) * 50));
  }, [page.data, offset]);
  async function act(row: Reminder | string, action: string, orderId?: string) {
    const id = typeof row === "string" ? row : row.id;
    setBusy(id);
    setError("");
    try {
      await request(businessPath(business.id, `reminders/${id}/action`), {
        method: "POST",
        body: JSON.stringify({
          action,
          ...(orderId ? { order_id: orderId } : {}),
        }),
      });
      setRevision((v) => v + 1);
      setConfirm(null);
      setLinking(null);
      setNotice(
        action === "tomorrow"
          ? "Отложено на завтра"
          : action === "opt_out"
            ? "Согласие на сообщения отключено в карточке клиента"
            : action === "undo"
              ? "Напоминание возвращено в очередь"
              : "Отметка сохранена",
      );
      if (action === "undo" || id === undo) setUndo(null);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy("");
    }
  }
  async function send(row: Reminder) {
    setBusy(row.id);
    setError("");
    setNotice("");
    // Open within the click gesture so Safari allows the WhatsApp tab after the API check.
    const popup = window.open("about:blank", "_blank");
    if (!popup) {
      setError(
        "Браузер заблокировал новую вкладку. Разрешите всплывающие окна для CRM и попробуйте ещё раз.",
      );
      setBusy("");
      return;
    }
    popup.opener = null;
    try {
      const result = await request<{ url: string }>(
        businessPath(business.id, `reminders/${row.id}/open`),
        { method: "POST" },
      );
      popup.location.href = result.url;
      setUndo(row.id);
      setRevision((v) => v + 1);
    } catch (e) {
      popup.close();
      setError(errorText(e));
      setRevision((v) => v + 1);
    } finally {
      setBusy("");
    }
  }
  async function saveText() {
    if (!editing) return;
    setBusy(editing.id);
    setError("");
    try {
      await request(
        businessPath(business.id, `reminders/${editing.id}/message`),
        { method: "PATCH", body: JSON.stringify({ message: text }) },
      );
      setEditing(null);
      setRevision((v) => v + 1);
      setNotice("Изменён только текст этого сообщения");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy("");
    }
  }
  async function generate() {
    setBusy("refresh");
    setError("");
    try {
      await request(businessPath(business.id, "reminders"), { method: "POST" });
      setRevision((v) => v + 1);
      setNotice("Очередь обновлена");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy("");
    }
  }
  const groups = new Map<string, { rank: number; rows: Reminder[] }>();
  for (const row of page.data?.results || []) {
    const g =
      state === "wait" ? group(row, today) : { title: tabs[state], rank: 0 };
    if (!groups.has(g.title)) groups.set(g.title, { rank: g.rank, rows: [] });
    groups.get(g.title)!.rows.push(row);
  }
  const stats = page.data?.stats || {},
    summary = page.data?.summary;
  const progress = summary?.total_today
    ? Math.min(100, (summary.sent_today / summary.total_today) * 100)
    : 0;
  return (
    <section className="rm-screen stack">
      <div className="page-hd rm-heading">
        <div>
          <h1>Кому написать сегодня</h1>
          <p className="sub rm-date">
            {new Date(today + "T12:00:00").toLocaleDateString("ru-RU", {
              weekday: "long",
              day: "numeric",
              month: "long",
            })}{" "}
            · список собирается автоматически
          </p>
        </div>
        <div className="row">
          <RefreshIndicator active={page.refreshing} />
          <button className="btn" onClick={settings}>
            <Settings2 size={17} />
            Настройки напоминаний
          </button>
          <details className="rm-more">
            <summary className="btn" aria-label="О напоминаниях и обновление">
              <MoreHorizontal size={18} />
            </summary>
            <div className="rm-menu rm-info-menu">
              <strong>Когда появится напоминание?</strong>
              <p>
                За столько дней, сколько указано в сценарии. Очередь формируется
                каждые 15 минут, экран проверяет изменения раз в минуту.
              </p>
              <p>
                WhatsApp открывает готовый текст. Отправку подтверждаете в самом
                WhatsApp; ответы в CRM отмечаются вручную.
              </p>
              {business.role === "owner" && (
                <button disabled={!!busy} onClick={() => void generate()}>
                  Обновить список
                </button>
              )}
            </div>
          </details>
        </div>
      </div>
      {(error || page.error) && <Notice>{error || page.error}</Notice>}
      {notice && (
        <p className="save-notice" role="status">
          {notice}
        </p>
      )}
      {page.data && !page.data.rules.enabled && (
        <div className="rm-banner">
          <Info size={18} />
          Напоминания приостановлены. Включите их в настройках.
        </div>
      )}
      <div className="rm-progress card">
        <div className="rm-progress-number">
          <strong>{summary?.sent_today || 0}</strong>
          <span>
            из {summary?.total_today || 0} отмечено
            <br />
            <small>«Написали» сегодня</small>
          </span>
        </div>
        <div className="rm-progress-main">
          <div
            className="rm-progress-track"
            role="progressbar"
            aria-label="Обработано сегодня"
            aria-valuenow={summary?.sent_today || 0}
            aria-valuemin={0}
            aria-valuemax={summary?.total_today || 1}
          >
            <span style={{ width: `${progress}%` }} />
          </div>
          <div className="rm-progress-facts">
            <span>
              Ждём ответа <b>{stats.sent || 0}</b>
            </span>
            <span>
              Ответили <b>{stats.answered || 0}</b>
            </span>
            <span>
              Заказали за неделю{" "}
              <b>
                {summary?.ordered_week || 0} ·{" "}
                {price(summary?.revenue_week || "0")} сом
              </b>
            </span>
          </div>
        </div>
        <span className="rm-estimate">
          <Clock3 size={15} />{" "}
          {stats.wait
            ? `осталось ≈ ${Math.ceil((stats.wait * 25) / 60)} мин`
            : "всё обработано"}
        </span>
      </div>
      <section className="rm-queue card" aria-label="Очередь напоминаний">
        <div className="rm-toolbar">
          <div
            className="rm-tabs"
            role="tablist"
            aria-label="Состояние напоминаний"
          >
            {Object.entries(tabs).map(([key, title]) => (
              <button
                key={key}
                role="tab"
                aria-selected={state === key}
                onClick={() => {
                  setState(key as keyof typeof tabs);
                  setOffset(0);
                }}
                className={state === key ? "active" : ""}
              >
                {title}
                <span>{stats[key] || 0}</span>
              </button>
            ))}
          </div>
          <select
            aria-label="Повод напоминания"
            value={scenario}
            onChange={(e) => {
              setScenario(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">Все поводы</option>
            {page.data?.scenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        {Array.from(groups.entries())
          .sort((a, b) => a[1].rank - b[1].rank)
          .map(([title, g]) => (
            <div key={title} className="rm-group">
              <h2
                className={`rm-group-title${state === "wait" && (g.rank === 0 || g.rank === 1) ? " urgent" : ""}`}
              >
                {title}
                <span>· {g.rows.length}</span>
              </h2>
              {g.rows.map((row) => (
                <article
                  className="rm-reminder"
                  key={row.id}
                  aria-label={`Напоминание: ${row.customer_name}`}
                >
                  <Avatar name={row.customer_name} />
                  <div className="rm-person">
                    <div className="rm-person-heading">
                      <button
                        className="plain-button"
                        onClick={() => openCustomer(row.customer_id)}
                      >
                        {row.customer_name}
                      </button>
                      {row.event_date && (
                        <span
                          className={`rm-date-chip ${dateTone(row, today)}`}
                        >
                          {shortDate(row.event_date)}
                        </span>
                      )}
                      <span className="rm-event">
                        {row.event}
                        {row.person && row.person !== row.customer_name
                          ? ` · ${row.person}`
                          : ""}
                      </span>
                    </div>
                    <p
                      className="rm-preview"
                      title={row.message || row.preview}
                    >
                      {row.message || row.preview || row.phone}
                    </p>
                    {row.last_year_hint && (
                      <p className="rm-year-hint">
                        Год назад: {row.last_year_hint.items},{" "}
                        {price(row.last_year_hint.total)} сом
                      </p>
                    )}
                    {state === "wait" && row.pause_reason && (
                      <p className="rm-pause">
                        <Clock3 size={13} />
                        {row.pause_reason}
                      </p>
                    )}
                    {state !== "wait" && row.sent_at && (
                      <p className="rm-sent">
                        Отмечено «Написали»{" "}
                        {new Date(row.sent_at).toLocaleString("ru-RU", {
                          timeZone: business.timezone,
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    )}
                    {row.recovered && state === "wait" && (
                      <span className="rm-recovered">
                        Восстановлено после перерыва
                      </span>
                    )}
                  </div>
                  <div className="rm-last">
                    <span>Прошлый заказ</span>
                    {row.last_order ? (
                      <button
                        className="plain-button"
                        onClick={() => openOrder(row.last_order!.id)}
                      >
                        {price(row.last_order.total)} сом ·{" "}
                        {shortDate(row.last_order.date)}
                      </button>
                    ) : (
                      <span>Пока нет</span>
                    )}
                  </div>
                  <div className="rm-row-actions">
                    <button
                      className="btn sm"
                      onClick={() => openChat(row.customer_id)}
                      title="Открыть переписку внутри CRM"
                    >
                      Чат
                    </button>
                    {state === "wait" ? (
                      <>
                        <button
                          className="btn rm-wa"
                          disabled={!!busy || row.paused}
                          title={
                            row.pause_reason ||
                            "Открыть текст в WhatsApp и отметить «Написали»"
                          }
                          onClick={() => void send(row)}
                        >
                          <MessageCircle size={17} />
                          WhatsApp
                        </button>
                        <button
                          className="rm-later"
                          disabled={!!busy}
                          onClick={() => void act(row, "tomorrow")}
                        >
                          <Clock3 size={15} />
                          Позже
                        </button>
                      </>
                    ) : (
                      <>
                        {state === "sent" && (
                          <button
                            className="btn sm"
                            disabled={!!busy}
                            onClick={() => void act(row, "answered")}
                          >
                            <Check size={15} />
                            Ответил(а)
                          </button>
                        )}
                        {["sent", "answered"].includes(state) && (
                          <button
                            className="btn sm"
                            disabled={!!busy}
                            onClick={() => setLinking(row)}
                          >
                            <ShoppingBag size={15} />
                            Заказал(а)
                          </button>
                        )}
                        {row.order_id && (
                          <button
                            className="btn sm"
                            onClick={() => openOrder(row.order_id!)}
                          >
                            Открыть заказ
                          </button>
                        )}
                      </>
                    )}
                    <details className="rm-more">
                      <summary
                        className="btn sm"
                        aria-label={`Действия: ${row.customer_name}`}
                      >
                        <MoreHorizontal size={18} />
                      </summary>
                      <div className="rm-menu">
                        {state === "wait" && (
                          <button
                            onClick={() => {
                              setEditing(row);
                              setText(row.message || row.preview || "");
                            }}
                          >
                            Изменить текст
                          </button>
                        )}
                        <button onClick={() => openCustomer(row.customer_id)}>
                          Открыть карточку
                        </button>
                        {state === "wait" && (
                          <button
                            onClick={() =>
                              setConfirm({ row, action: "skipped" })
                            }
                          >
                            {row.kind === "before_event" ||
                            row.kind === "holiday"
                              ? "Пропустить в этом году"
                              : "Пропустить этот повод"}
                          </button>
                        )}
                        <button
                          onClick={() => setConfirm({ row, action: "opt_out" })}
                        >
                          Не напоминать клиенту
                        </button>
                      </div>
                    </details>
                  </div>
                </article>
              ))}
            </div>
          ))}
        {!page.data?.results.length && (
          <div className="rm-empty">
            <span>
              <Bell size={27} />
            </span>
            <h2>
              {page.loading
                ? "Загружаем напоминания…"
                : "Здесь пока нет напоминаний"}
            </h2>
            <p>
              {state === "wait"
                ? "Подходящие поводы появятся автоматически. Проверьте важные даты клиентов и включённые сценарии."
                : "После обработки сообщения появятся на этой вкладке."}
            </p>
            {!page.loading && state === "wait" && (
              <button className="btn" onClick={settings}>
                Посмотреть сценарии
              </button>
            )}
          </div>
        )}
      </section>
      <Pager
        count={page.data?.count || 0}
        offset={offset}
        setOffset={setOffset}
        disabled={!!busy}
      />
      {undo && (
        <div className="toast rm-undo" role="status">
          <span>Отмечено «Написали». Отправьте текст в WhatsApp.</span>
          <button disabled={!!busy} onClick={() => void act(undo, "undo")}>
            Отменить
          </button>
        </div>
      )}
      {editing && (
        <Modal
          title="Изменить текст сообщения"
          close={() => setEditing(null)}
          busy={!!busy}
        >
          <form
            className="modal-body stack"
            onSubmit={(e) => {
              e.preventDefault();
              void saveText();
            }}
          >
            <p>
              Для {editing.customer_name}. Шаблон сценария останется прежним.
            </p>
            <label>
              Сообщение
              <textarea
                aria-label="Сообщение"
                rows={6}
                maxLength={2000}
                required
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </label>
            {error && <Notice>{error}</Notice>}
            <button className="btn primary" disabled={!!busy}>
              Сохранить текст
            </button>
          </form>
        </Modal>
      )}
      {confirm && (
        <Modal
          title={
            confirm.action === "opt_out"
              ? "Отключить напоминания клиенту?"
              : "Пропустить повод?"
          }
          close={() => setConfirm(null)}
          busy={!!busy}
        >
          <div className="modal-body stack">
            <p>
              {confirm.action === "opt_out"
                ? `У клиента ${confirm.row.customer_name} будет отключено согласие на сообщения. История сохранится.`
                : "Оставшиеся шаги этого повода будут пропущены. История сохранится."}
            </p>
            {error && <Notice>{error}</Notice>}
            <div className="row">
              <button
                className="btn"
                disabled={!!busy}
                onClick={() => setConfirm(null)}
              >
                Отмена
              </button>
              <button
                className="btn primary"
                disabled={!!busy}
                onClick={() => void act(confirm.row, confirm.action)}
              >
                Подтвердить
              </button>
            </div>
          </div>
        </Modal>
      )}
      {linking && (
        <LinkOrder
          business={business}
          row={linking}
          busy={!!busy}
          error={error}
          close={() => setLinking(null)}
          save={(id) => void act(linking, "ordered", id)}
          create={() => {
            createOrder(linking);
            setLinking(null);
          }}
        />
      )}
    </section>
  );
}
function LinkOrder({
  business,
  row,
  close,
  save,
  create,
  busy,
  error,
}: {
  business: Business;
  row: Reminder;
  close: () => void;
  save: (id: string) => void;
  create: () => void;
  busy: boolean;
  error: string;
}) {
  const [offset, setOffset] = useState(0);
  const orders = useRemote<Page<Order>>(
    businessPath(business.id, "orders") +
      `?customer_id=${row.customer_id}&limit=50&offset=${offset}`,
  );
  const available =
    orders.data?.results.filter(
      (o) =>
        o.status !== "cancelled" &&
        (!row.sent_at || o.created_at >= row.sent_at),
    ) || [];
  return (
    <Modal title="Связать напоминание с заказом" close={close} busy={busy}>
      <div className="modal-body stack">
        <p>Выберите заказ {row.customer_name}, созданный после сообщения.</p>
        {(error || orders.error) && <Notice>{error || orders.error}</Notice>}
        {available.map((o) => (
          <button
            className="rm-order-option"
            key={o.id}
            disabled={busy}
            onClick={() => save(o.id)}
          >
            <span>
              Заказ №{o.number} · {shortDate(o.delivery_date)}
            </span>
            <b>{price(o.total)} сом</b>
          </button>
        ))}
        {!available.length && (
          <p className="muted">
            {orders.loading
              ? "Загружаем…"
              : "Подходящих заказов на этой странице нет."}
          </p>
        )}
        <Pager
          count={orders.data?.count || 0}
          offset={offset}
          setOffset={setOffset}
        />
        <button className="btn primary" disabled={busy} onClick={create}>
          Создать заказ
        </button>
        <p className="small muted">
          После создания вернитесь к напоминанию и выберите новый заказ.
        </p>
      </div>
    </Modal>
  );
}
