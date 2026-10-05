import { useState } from "react";
import { businessPath, errorText, request } from "./api";
import { Notice, Pager } from "./components";
import { useRemote } from "./hooks";
import { Status } from "./orders";
import { Avatar, shopDay } from "./ui";
import type { Business, Order, Page, ShopSettings, Staff } from "./types";
export function DeliveryDesk({
  business,
  revision,
  openOrder,
}: {
  business: Business;
  revision: number;
  openOrder: (o: Order) => void;
}) {
  const [day, setDay] = useState(shopDay(business.timezone)),
    [offset, setOffset] = useState(0),
    [refresh, setRefresh] = useState(0),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const source = useRemote<Page<Order>>(
      businessPath(business.id, "orders/desk") +
        `?scope=date&day=${day}&status=courier&limit=50&offset=${offset}`,
      revision + refresh,
    ),
    staff = useRemote<Staff[]>(businessPath(business.id, "staff"), revision),
    shop = useRemote<ShopSettings>(
      businessPath(business.id, "settings"),
      revision,
    );
  const orders = source.data?.results || [],
    couriers = staff.data?.filter((s) => s.role === "courier") || [];
  const windowKey = (o: Order) =>
    `${o.window_start.slice(0, 5)}–${o.window_end.slice(0, 5)}`;
  async function assign(o: Order, id: string) {
    setBusy(true);
    setError("");
    try {
      await request(businessPath(business.id, `orders/${o.id}/assignment`), {
        method: "POST",
        body: JSON.stringify({
          version: o.version,
          florist_id: o.florist_id,
          courier_id: id,
        }),
      });
      setRefresh((r) => r + 1);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-hd">
        <div>
          <h1>Доставка</h1>
          <div className="sub">
            {source.data?.count ?? "—"} доставок
            {(
              source.data as unknown as {
                summary?: { done: number; route: number };
              }
            )?.summary &&
              ` · ${(source.data as unknown as { summary: { done: number; route: number } }).summary.done} вручено · ${(source.data as unknown as { summary: { done: number; route: number } }).summary.route} в пути`}
          </div>
        </div>
        <span className="spacer" />
        <div className="seg">
          {[0, 1].map((n) => (
            <button
              key={n}
              className={day === shopDay(business.timezone, n) ? "is-on" : ""}
              onClick={() => {
                setDay(shopDay(business.timezone, n));
                setOffset(0);
              }}
            >
              {n ? "Завтра" : "Сегодня"}
            </button>
          ))}
        </div>
        <input
          className="delivery-date"
          aria-label="Дата доставки"
          type="date"
          value={day}
          onChange={(e) => {
            setDay(e.target.value);
            setOffset(0);
          }}
        />
      </div>
      {(error || source.error || staff.error) && (
        <Notice>{error || source.error || staff.error}</Notice>
      )}
      <div className="g-main">
        <section className="card">
          <div className="card-hd">
            <h2>По окнам</h2>
          </div>
          <div className="card-bd tight">
            {Array.from(new Set(orders.map(windowKey)))
              .sort()
              .map((key) => (
                <div key={key}>
                  <div className="card-hd window-group">
                    <span className="mono b ink">{key}</span>
                    <span className="small muted">
                      {orders.filter((o) => windowKey(o) === key).length}{" "}
                      доставок · вместимость{" "}
                      {shop.data?.windows.find(
                        (w) => `${w.start}–${w.end}` === key,
                      )?.capacity ?? "—"}
                    </span>
                  </div>
                  {orders
                    .filter((o) => windowKey(o) === key)
                    .map((o) => (
                      <div className="lrow" key={o.id}>
                        <Avatar
                          name={
                            staff.data?.find((s) => s.id === o.courier_id)
                              ?.name || "—"
                          }
                        />
                        <button
                          className="plain-button"
                          onClick={() => openOrder(o)}
                        >
                          <span className="t">
                            №{o.number} · {o.recipient_name}
                          </span>
                          <span className="s">
                            {o.address} · {o.recipient_phone}
                            {o.notes && ` · ${o.notes}`}
                          </span>
                        </button>
                        <div className="r">
                          {!o.courier_id &&
                          !["done", "cancelled"].includes(o.status) ? (
                            <select
                              className="btn sm"
                              aria-label={`Курьер заказа №${o.number}`}
                              value=""
                              disabled={busy}
                              onChange={(e) => void assign(o, e.target.value)}
                            >
                              <option value="">Назначить</option>
                              {couriers
                                .filter((c) => c.is_active)
                                .map((c) => (
                                  <option key={c.id} value={c.id}>
                                    {c.name}
                                  </option>
                                ))}
                            </select>
                          ) : (
                            <Status value={o.status} />
                          )}
                        </div>
                      </div>
                    ))}
                </div>
              ))}
            {!orders.length && (
              <div className="empty">
                {source.loading ? "Загружаем доставки…" : "Доставок нет"}
              </div>
            )}
          </div>
          <Pager
            count={source.data?.count || 0}
            offset={offset}
            setOffset={setOffset}
          />
        </section>
        <div className="stack">
          {couriers.map((c) => (
            <section className="card" key={c.id}>
              <div className="card-hd">
                <Avatar name={c.name} />
                <div>
                  <div className="b ink">{c.name}</div>
                  <div className="small muted mono">
                    {c.phone || "Телефон не указан"}
                  </div>
                </div>
                <span className="spacer" />
                {c.phone && (
                  <a className="btn sm" href={`tel:${c.phone}`}>
                    Позвонить
                  </a>
                )}
              </div>
              <div className="card-bd tight">
                {orders
                  .filter((o) => o.courier_id === c.id)
                  .map((o) => (
                    <button
                      className="lrow plain-button"
                      key={o.id}
                      onClick={() => openOrder(o)}
                    >
                      <span className="mono small">
                        {o.window_start.slice(0, 5)}
                      </span>
                      <span>
                        <span className="t">{o.recipient_name}</span>
                        <span className="s">{o.address}</span>
                      </span>
                      <Status value={o.status} />
                    </button>
                  ))}
                {!orders.some((o) => o.courier_id === c.id) && (
                  <div className="empty">Нет доставок на этой странице</div>
                )}
              </div>
            </section>
          ))}
          {!couriers.length && (
            <div className="card empty">
              Добавьте курьера в настройках сотрудников
            </div>
          )}
        </div>
      </div>
    </>
  );
}
