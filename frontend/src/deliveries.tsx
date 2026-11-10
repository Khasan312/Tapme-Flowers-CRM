import { useState } from "react";
import { businessPath, errorText, request } from "./api";
import { Notice, Pager, RefreshIndicator } from "./components";
import { DeliveryWindowHelp } from "./delivery-window-help";
import { useRemote } from "./hooks";
import { Status } from "./orders";
import { Avatar, shopDay } from "./ui";
import type { Business, Order, Page, Point, Staff } from "./types";
type DeliveryDeskData = Page<Order> & {
  summary?: { done: number; route: number };
  window_load?: {
    point_id: string;
    window_start: string;
    window_end: string;
    occupied: number;
  }[];
};

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
  const source = useRemote<DeliveryDeskData>(
      businessPath(business.id, "orders/desk") +
        `?scope=date&day=${day}&status=courier&limit=50&offset=${offset}`,
      revision + refresh,
    ),
    staff = useRemote<Staff[]>(businessPath(business.id, "staff"), revision),
    points = useRemote<Point[]>(businessPath(business.id, "points"), revision);
  const orders = source.data?.results || [],
    couriers =
      staff.data?.filter(
        (s) =>
          s.role === "courier" &&
          (business.point_id === "all" ||
            !s.point_ids?.length ||
            s.point_ids.includes(business.point_id || "")),
      ) || [];
  const windowKey = (o: Order) =>
    `${o.point_id}|${o.window_start.slice(0, 5)}–${o.window_end.slice(0, 5)}`;
  const byWindow = new Map<string, Order[]>();
  for (const order of orders) {
    const key = windowKey(order);
    if (!byWindow.has(key)) byWindow.set(key, []);
    byWindow.get(key)!.push(order);
  }
  const windowLoad = new Map(
    source.data?.window_load?.map((row) => [
      `${row.point_id}|${row.window_start}–${row.window_end}`,
      row.occupied,
    ]),
  );
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
            {source.data?.summary &&
              ` · ${source.data.summary.done} вручено · ${source.data.summary.route} в пути`}
          </div>
        </div>
        <span className="spacer" />
        <RefreshIndicator active={source.refreshing} />
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
            setDay(e.target.value || shopDay(business.timezone));
            setOffset(0);
          }}
        />
      </div>
      {(error || source.error || staff.error || points.error) && (
        <Notice>{error || source.error || staff.error || points.error}</Notice>
      )}
      <div className="g-main">
        <section className="card">
          <div className="card-hd">
            <h2>По окнам</h2>
          </div>
          <DeliveryWindowHelp />
          <div className="card-bd tight">
            {[...byWindow]
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([key, rows]) => {
                const [pointId, time] = key.split("|");
                const point = points.data?.find((p) => p.id === pointId);
                const capacity = point?.windows.find(
                  (w) => `${w.start}–${w.end}` === time,
                )?.capacity;
                const occupied =
                  windowLoad.get(key) ??
                  (source.data?.window_load ? 0 : undefined);
                const extra =
                  capacity !== undefined && occupied !== undefined
                    ? occupied - capacity
                    : 0;
                return (
                  <div key={key}>
                    <div
                      className={`card-hd window-group${extra > 0 ? " is-over-capacity" : ""}`}
                    >
                      <span className="mono b ink">
                        {business.point_id === "all" && point && (
                          <span className="point-badge">
                            {point.short_name}
                          </span>
                        )}
                        {time}
                      </span>
                      <span className="small muted">
                        {occupied !== undefined && capacity !== undefined
                          ? `Мест занято: ${occupied} из ${capacity}`
                          : capacity !== undefined
                            ? `Вместимость: ${capacity}`
                            : "Вместимость не задана"}
                      </span>
                      {extra > 0 && (
                        <span className="tag crit">Сверх лимита: {extra}</span>
                      )}
                    </div>
                    {rows.map((o) => (
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
                              disabled={busy || source.loading}
                              onChange={(e) => void assign(o, e.target.value)}
                            >
                              <option value="">Назначить</option>
                              {couriers
                                .filter(
                                  (c) =>
                                    c.is_active &&
                                    (!c.point_ids?.length ||
                                      c.point_ids.includes(o.point_id)),
                                )
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
                );
              })}
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
                        {business.point_id === "all" && o.point_name && (
                          <span className="point-badge">{o.point_name}</span>
                        )}
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
