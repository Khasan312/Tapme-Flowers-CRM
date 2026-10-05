import { useState } from "react";
import { businessPath, errorText, price, request } from "./api";
import { Notice } from "./components";
import { CustomerPanel } from "./customers";
import { useRemote } from "./hooks";
import { Status } from "./orders";
import { Avatar, shortDate, shopDay } from "./ui";
import type { Business, CustomerProfile, Order } from "./types";
type Activity = {
  order_count: number;
  total: string;
  last_order: string | null;
  orders: {
    id: string;
    number: number;
    status: string;
    total: string;
    delivery_date: string;
    recipient_name: string;
  }[];
  feedback: { id: string; message: string; outcome: string; status: string }[];
  reminders: { id: string; event: string; state: string; message: string }[];
};
export function CustomerPage({
  business,
  customerId,
  externalRevision = 0,
  close,
  changed,
  openOrder,
  newOrder,
}: {
  business: Business;
  customerId: string;
  externalRevision?: number;
  close: () => void;
  changed: () => void;
  openOrder: (o: Order) => void;
  newOrder: (c: CustomerProfile) => void;
}) {
  const [revision, setRevision] = useState(0),
    [editing, setEditing] = useState(false),
    [error, setError] = useState("");
  const source = useRemote<CustomerProfile>(
      businessPath(business.id, `customers/${customerId}`),
      revision + externalRevision,
    ),
    activity = useRemote<Activity>(
      businessPath(business.id, `customers/${customerId}/activity`),
      revision + externalRevision,
    );
  const c = source.data,
    a = activity.data;
  const today = shopDay(business.timezone),
    days = (date: string) =>
      Math.floor((Date.parse(today) - Date.parse(date)) / 86400000);
  const next = c?.dates
    .map((d) => {
      const year = Number(today.slice(0, 4));
      let date = new Date(Date.UTC(year, d.month - 1, d.day));
      if (date.toISOString().slice(0, 10) < today)
        date = new Date(Date.UTC(year + 1, d.month - 1, d.day));
      return { ...d, inDays: -days(date.toISOString().slice(0, 10)) };
    })
    .sort((a, b) => a.inDays - b.inDays)[0];
  async function order(id: string) {
    try {
      openOrder(
        await request<Order>(businessPath(business.id, `orders/${id}`)),
      );
    } catch (e) {
      setError(errorText(e));
    }
  }
  return (
    <>
      <div className="page-hd">
        <button className="btn ghost sm" onClick={close}>
          ← Клиенты
        </button>
      </div>
      {(error || source.error || activity.error) && (
        <Notice>{error || source.error || activity.error}</Notice>
      )}
      {!c ? (
        <div className="empty">Загружаем карточку…</div>
      ) : (
        <>
          <section className="card customer-intro">
            <div className="card-bd row">
              <Avatar name={c.name} />
              <div className="customer-identity">
                <h1>
                  {c.name}{" "}
                  {(c.tags || []).map((t) => (
                    <span className="tag acc" key={t}>
                      {t}
                    </span>
                  ))}
                </h1>
                <div className="row small muted">
                  <span className="tag mono">ID {c.code}</span>
                  <span className="mono ink">{c.phone}</span>
                  {c.source && <span>· {c.source}</span>}
                  <span>· клиент с {shortDate(c.created_at.slice(0, 10))}</span>
                </div>
              </div>
              <div className="row">
                <span className={`tag${c.consent ? " ok" : ""}`}>
                  {c.consent ? "Согласие на сообщения" : "Нет согласия"}
                </span>
                <a
                  className="btn wa"
                  target="_blank"
                  rel="noopener noreferrer"
                  href={`https://wa.me/${c.phone.replace(/\D/g, "")}`}
                >
                  WhatsApp
                </a>
                <a className="btn" href={`tel:${c.phone}`}>
                  Позвонить
                </a>
                <button className="btn primary" onClick={() => newOrder(c)}>
                  Новый заказ
                </button>
                <button className="btn sm" onClick={() => setEditing(true)}>
                  Изменить
                </button>
              </div>
            </div>
          </section>
          <div className="kpis customer-kpis">
            {[
              ["Заказов", a?.order_count ?? "—", ""],
              [
                "Сумма покупок",
                a ? price(a.total) : "—",
                a?.order_count
                  ? `Средний чек ${price(Number(a.total) / a.order_count)}`
                  : "",
              ],
              [
                "Последний заказ",
                a?.last_order ? shortDate(a.last_order) : "—",
                a?.last_order
                  ? `${days(a.last_order)} дн. назад`
                  : "заказов пока нет",
              ],
              [
                "Ближайшая дата",
                next ? `${next.inDays} дн.` : "—",
                next?.label || "дат не записано",
              ],
            ].map(([label, value, sub]) => (
              <div className="kpi" key={label}>
                <div className="kl">{label}</div>
                <div className="kv">{value}</div>
                <div className="kf">{sub}</div>
              </div>
            ))}
          </div>
          <div className="g-main">
            <div className="stack">
              <section className="card">
                <div className="card-hd">
                  <h2>Получатели и даты</h2>
                  <span className="spacer" />
                  <button className="btn sm" onClick={() => setEditing(true)}>
                    Добавить получателя
                  </button>
                  <button className="btn sm" onClick={() => setEditing(true)}>
                    Добавить дату
                  </button>
                </div>
                <div className="card-bd tight">
                  {c.recipients.map((r) => (
                    <div className="lrow" key={r.id}>
                      <Avatar name={r.name} />
                      <div>
                        <div className="t">
                          {r.name} <span className="muted">· {r.relation}</span>
                        </div>
                        <div className="s">
                          {r.phone || "телефона нет"}
                          {r.address && ` · ${r.address}`}
                        </div>
                        {r.notes && (
                          <div className="note recipient-note">{r.notes}</div>
                        )}
                      </div>
                      <button
                        className="btn xs"
                        onClick={() => setEditing(true)}
                      >
                        Изменить
                      </button>
                    </div>
                  ))}
                  {c.dates.map((d) => (
                    <div className="lrow" key={d.id}>
                      <span className="mono small">
                        {String(d.day).padStart(2, "0")}.
                        {String(d.month).padStart(2, "0")}
                      </span>
                      <span className="t">
                        {d.label} · {d.person}
                      </span>
                      <button
                        className="btn xs"
                        onClick={() => setEditing(true)}
                      >
                        Изменить
                      </button>
                    </div>
                  ))}
                  {!c.recipients.length && !c.dates.length && (
                    <div className="empty">
                      Получателей пока нет. Добавьте, когда клиент закажет
                      кому-то
                    </div>
                  )}
                </div>
              </section>
              <section className="card">
                <div className="card-hd">
                  <h2>Заказы</h2>
                  <span className="small muted">Последние 50</span>
                </div>
                <div className="tbl-wrap">
                  <table className="tbl">
                    <thead>
                      <tr>
                        <th>№</th>
                        <th>Дата</th>
                        <th>Кому</th>
                        <th className="num">Сумма</th>
                        <th>Статус</th>
                      </tr>
                    </thead>
                    <tbody>
                      {a?.orders.map((o) => (
                        <tr key={o.id} onClick={() => void order(o.id)}>
                          <td>
                            <button
                              className="plain-button mono"
                              onClick={(e) => {
                                e.stopPropagation();
                                void order(o.id);
                              }}
                            >
                              №{o.number}
                            </button>
                          </td>
                          <td className="mono">{shortDate(o.delivery_date)}</td>
                          <td>{o.recipient_name}</td>
                          <td className="num mono">{price(o.total)}</td>
                          <td>
                            <Status value={o.status} />
                          </td>
                        </tr>
                      ))}
                      {!a?.orders.length && (
                        <tr>
                          <td colSpan={5} className="empty">
                            Заказов пока нет
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
            <div className="stack">
              <section className="card">
                <div className="card-hd">
                  <h2>Заметки</h2>
                  <span className="spacer" />
                  <button className="btn xs" onClick={() => setEditing(true)}>
                    Изменить
                  </button>
                </div>
                <div className="card-bd">
                  <p className="note preserve">
                    {c.notes || "Как обращаться, как платит, что не предлагать"}
                  </p>
                </div>
              </section>
              <section className="card">
                <div className="card-hd">
                  <h2>Отзывы</h2>
                </div>
                <div className="card-bd tight">
                  {a?.feedback.map((f) => (
                    <div className="message-row" key={f.id}>
                      <p>{f.message}</p>
                      {f.outcome && (
                        <p className="small muted">Решение: {f.outcome}</p>
                      )}
                    </div>
                  ))}
                  {!a?.feedback.length && (
                    <div className="empty">Отзывов ещё нет</div>
                  )}
                </div>
              </section>
              <section className="card">
                <div className="card-hd">
                  <h2>Сообщения</h2>
                </div>
                <div className="card-bd tight">
                  {a?.reminders.map((r) => (
                    <div className="message-row" key={r.id}>
                      <div className="b">
                        {r.event} ·{" "}
                        {
                          (
                            {
                              wait: "В очереди",
                              sent: "Написали",
                              answered: "Ответили",
                              ordered: "Заказали",
                              skipped: "Пропущено",
                            } as Record<string, string>
                          )[r.state]
                        }
                      </div>
                      <p className="small muted">{r.message}</p>
                    </div>
                  ))}
                  {!a?.reminders.length && (
                    <div className="empty">Сообщений ещё не было</div>
                  )}
                </div>
              </section>
            </div>
          </div>
        </>
      )}
      {editing && (
        <CustomerPanel
          business={business}
          customerId={customerId}
          close={() => setEditing(false)}
          changed={() => {
            setRevision((r) => r + 1);
            changed();
          }}
        />
      )}
    </>
  );
}
