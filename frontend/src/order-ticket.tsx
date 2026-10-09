import { createPortal } from "react-dom";
import type { Business, Order } from "./types";
import "./order-ticket.css";

export function OrderTicket({
  order,
  business,
  status,
}: {
  order: Order;
  business: Business;
  status: string;
}) {
  const date = new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(`${order.delivery_date}T12:00:00`));
  return createPortal(
    <section className="print-ticket" aria-label="Талон заказа">
      <header className="ticket-header">
        <div>
          <p className="ticket-store">{business.name}</p>
          <h1>Талон заказа №{order.number}</h1>
        </div>
        <span className="ticket-status">{status}</span>
      </header>
      <section className="ticket-section">
        <h2>{order.fulfillment === "courier" ? "Доставка" : "Самовывоз"}</h2>
        <p className="ticket-schedule">
          {date} · {order.window_start.slice(0, 5)}–
          {order.window_end.slice(0, 5)}
        </p>
        <dl className="ticket-details">
          <div>
            <dt>Получатель</dt>
            <dd>{order.recipient_name}</dd>
          </div>
          {order.recipient_phone && (
            <div>
              <dt>Телефон</dt>
              <dd>{order.recipient_phone}</dd>
            </div>
          )}
          {order.fulfillment === "courier" && order.address && (
            <div>
              <dt>Адрес</dt>
              <dd>{order.address}</dd>
            </div>
          )}
        </dl>
      </section>
      <section className="ticket-section">
        <h2>Состав букета</h2>
        <table>
          <thead>
            <tr>
              <th scope="col">Позиция</th>
              <th scope="col">Кол-во</th>
            </tr>
          </thead>
          <tbody>
            {order.lines.map((line) => (
              <tr key={line.product_id}>
                <td>{line.name}</td>
                <td>{line.quantity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      {order.card && (
        <section className="ticket-section">
          <h2>Открытка</h2>
          <p>{order.card}</p>
        </section>
      )}
      {order.notes && (
        <section className="ticket-section">
          <h2>Для команды</h2>
          <p>{order.notes}</p>
        </section>
      )}
    </section>,
    document.body,
  );
}
