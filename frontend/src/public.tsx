import { useState, type FormEvent } from "react";
import { errorText, request } from "./api";
import { Notice } from "./components";
import { useRemote } from "./hooks";
import { Status } from "./orders";
import { Avatar, shortDate } from "./ui";
import { Check, Flower2, Truck } from "lucide-react";

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
export function PublicOrderPage({ token }: { token: string }) {
  const [revision, setRevision] = useState(0),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const path = `/public/orders/${encodeURIComponent(token)}/`;
  const source = useRemote<PublicOrder>(path, revision);
  async function review(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const d = new FormData(e.currentTarget);
    try {
      await request(path, {
        method: "POST",
        body: JSON.stringify({
          rating: Number(d.get("rating")),
          message: d.get("message"),
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
  return (
    <main className="crm public-page">
      <section className="public-status-page stack">
        {(error || source.error) && <Notice>{error || source.error}</Notice>}
        {notice && <p role="status">{notice}</p>}
        {source.loading ? (
          <p>Загружаем заказ…</p>
        ) : (
          o && (
            <>
              <div className="m-brand">
                <Avatar name={o.shop_name} />
                <div>
                  <div className="n">{o.shop_name}</div>
                  <div className="s">
                    Заказ №{o.number} · {shortDate(o.delivery_date)}
                  </div>
                </div>
              </div>
              <div className="big-state">
                <div className="ic">
                  {o.status === "done" ? (
                    <Check size={26} />
                  ) : o.status === "route" ? (
                    <Truck size={26} />
                  ) : (
                    <Flower2 size={26} />
                  )}
                </div>
                <h1 className="st">
                  {
                    (
                      {
                        new: "Заказ принят",
                        work: "Собираем букет",
                        ready: "Букет собран",
                        route: "Курьер уже едет",
                        done: "Букет вручён",
                        cancelled: "Заказ отменён",
                      } as Record<string, string>
                    )[o.status]
                  }
                </h1>
                <div className="ss">
                  {o.status === "done"
                    ? `Спасибо, что выбрали ${o.shop_name}`
                    : `${shortDate(o.delivery_date)}, ${o.window_start.slice(0, 5)}–${o.window_end.slice(0, 5)}`}
                </div>
              </div>
              <div className="m-card">
                <Status value={o.status} />
                <div className="tl">
                  {[
                    "new",
                    "ready",
                    ...(o.fulfillment === "courier" ? ["route"] : []),
                    "done",
                  ].map((s, i, steps) => (
                    <div
                      className={`tl-i ${i < steps.indexOf(o.status === "work" ? "new" : o.status) ? "done" : s === (o.status === "work" ? "new" : o.status) ? "cur" : "todo"}`}
                      key={s}
                    >
                      <div className="dot" />
                      <div className="tt">
                        {
                          (
                            {
                              new: "Принят",
                              ready: "Собран",
                              route: "В пути",
                              done:
                                o.fulfillment === "pickup"
                                  ? "Выдан"
                                  : "Доставлен",
                            } as Record<string, string>
                          )[s]
                        }
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <p>
                {o.fulfillment === "courier" ? "Доставка" : "Самовывоз"}:{" "}
                {o.delivery_date}
              </p>
              <p>
                {o.window_start.slice(0, 5)}–{o.window_end.slice(0, 5)}
              </p>
              <button onClick={() => setRevision((v) => v + 1)}>
                Обновить статус
              </button>
              {o.shop_phone && (
                <div className="inline-form">
                  <a href={`tel:${o.shop_phone}`}>Позвонить магазину</a>
                  <a
                    href={`https://wa.me/${o.shop_phone.replace(/\D/g, "")}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Написать магазину
                  </a>
                </div>
              )}
              {o.can_review && (
                <form onSubmit={review} className="m-card stack">
                  <h2>Как вам букет?</h2>
                  <label>
                    Оценка
                    <select aria-label="Оценка" name="rating" defaultValue="5">
                      {[5, 4, 3, 2, 1].map((n) => (
                        <option key={n} value={n}>
                          {n} из 5
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Ваш отзыв
                    <textarea name="message" maxLength={2000} />
                  </label>
                  <button disabled={busy} className="primary">
                    Отправить отзыв
                  </button>
                </form>
              )}
            </>
          )
        )}
      </section>
    </main>
  );
}
