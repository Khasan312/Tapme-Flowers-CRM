import { businessPath, price } from "./api";
import { Notice } from "./components";
import { useRemote } from "./hooks";
import { Status, statusNames } from "./orders";
import type { Business, Order } from "./types";

type Summary = {
  deliveries_completed: number;
  deliveries_on_time: number;
  orders: number;
  completed: number;
  in_progress: number;
  total: string;
  payments: string;
  refunds: string;
  complaints: number;
};
export function OrderSummary({
  business,
  day,
  revision,
}: {
  business: Business;
  day: string;
  revision: number;
}) {
  const stats = useRemote<Summary>(
    businessPath(business.id, "overview") + (day ? `?day=${day}` : ""),
    revision,
  );
  if (stats.error) return <Notice>{stats.error}</Notice>;
  return (
    <div className="metrics order-metrics">
      {stats.data && (
        <>
          <div className="metric">
            <small>Активных заказов</small>
            <strong>{stats.data.in_progress}</strong>
          </div>
          <div className="metric">
            <small>Вручено</small>
            <strong>{stats.data.completed}</strong>
          </div>
          <div className="metric">
            <small>Получено по этим заказам</small>
            <strong>
              {price(Number(stats.data.payments) - Number(stats.data.refunds))}
            </strong>
          </div>
          <div className="metric">
            <small>Доставлено вовремя</small>
            <strong>
              {stats.data.deliveries_on_time} /{" "}
              {stats.data.deliveries_completed}
            </strong>
          </div>
          <div className="metric">
            <small>Открытые жалобы</small>
            <strong>{stats.data.complaints}</strong>
          </div>
        </>
      )}
    </div>
  );
}

export function OrderViews({
  orders,
  mode,
  open,
}: {
  orders: Order[];
  mode: string;
  open: (order: Order) => void;
}) {
  const keys =
    mode === "board"
      ? Object.keys(statusNames)
      : [...new Set(orders.map((o) => o.delivery_date))].sort();
  return (
    <div className={mode === "board" ? "order-board" : "calendar-orders"}>
      {keys.map((key) => (
        <section className="board-column stack" key={key}>
          <h3>
            {mode === "board"
              ? statusNames[key]
              : new Date(key + "T12:00:00").toLocaleDateString("ru-RU", {
                  weekday: "short",
                  day: "numeric",
                  month: "long",
                })}
          </h3>
          {orders
            .filter((o) =>
              mode === "board" ? o.status === key : o.delivery_date === key,
            )
            .map((o) => (
              <button className="board-card" key={o.id} onClick={() => open(o)}>
                <div className="section-heading">
                  <strong>№{o.number}</strong>
                  {o.point_name && (
                    <span className="point-badge">{o.point_name}</span>
                  )}
                  <Status value={o.status} />
                </div>
                <strong>{o.customer_name}</strong>
                <p>Для {o.recipient_name}</p>
                <p>
                  {o.window_start.slice(0, 5)}–{o.window_end.slice(0, 5)} ·{" "}
                  {o.fulfillment === "courier" ? "Доставка" : "Самовывоз"}
                </p>
                <small>
                  {o.lines.map((l) => `${l.name} × ${l.quantity}`).join(", ")}
                </small>
                <strong>{price(o.total)}</strong>
              </button>
            ))}
        </section>
      ))}
    </div>
  );
}
