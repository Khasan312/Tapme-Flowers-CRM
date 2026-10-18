import { newUuid } from "./uuid";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Check, X } from "lucide-react";
import { ApiError, businessPath, errorText, price, request } from "./api";
import { Modal, Notice, Pager, RefreshIndicator } from "./components";
import { OrderForm } from "./forms";
import { ProductPhoto } from "./product-photo";
import { OrderTicket } from "./order-ticket";
import { useRemote } from "./hooks";
import type {
  Business,
  Feedback,
  HistoryEvent,
  Order,
  Page,
  Payment,
  Photo,
  Staff,
  Task,
} from "./types";

export const statusNames: Record<string, string> = {
  pending: "Ждёт подтверждения",
  new: "Новый",
  work: "У флориста",
  ready: "Собран",
  route: "В пути",
  done: "Вручён",
  cancelled: "Отменён",
};
const actionNames: Record<string, string> = {
  work: "Взять в работу",
  ready: "Букет готов",
  route: "Передать курьеру",
  done: "Заказ вручён",
  cancelled: "Отменить заказ",
};
const eventNames: Record<string, string> = {
  ...statusNames,
  created: "Заказ принят",
  confirmed: "Заказ подтверждён",
  confirmed_without_prepayment: "Подтверждён без предоплаты",
  payment_extended: "Срок оплаты продлён",
  payment_deadline_review: "Проверить оплату",
  edited: "Заказ изменён",
  assigned: "Назначены сотрудники",
  courier_reassigned: "Курьер заменён",
  payment: "Оплата",
  refund: "Возврат",
  photo: "Добавлено фото",
  photo_deleted: "Удалено фото",
  public_link: "Ссылка клиенту",
  complaint: "Жалоба",
  review: "Отзыв",
  complaint_resolved: "Жалоба решена",
  delivery_issue: "Проблема доставки",
};
export function Status({ value }: { value: string }) {
  return (
    <span className={`badge status-${value}`}>
      {statusNames[value] || value}
    </span>
  );
}
function transitions(order: { status: string; fulfillment: string }) {
  return (
    (
      {
        pending: ["cancelled"],
        new: ["work", "cancelled"],
        work: ["ready", "cancelled"],
        ready: [
          order.fulfillment === "courier" ? "route" : "done",
          "cancelled",
        ],
        route: ["done", "cancelled"],
      } as Record<string, string[]>
    )[order.status] || []
  );
}

function PaymentForm({ path, changed }: { path: string; changed: () => void }) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [uncertain, setUncertain] = useState(false);
  const attempt = useRef<{ key: string; body: string } | null>(null);
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    if (!attempt.current) {
      const data = new FormData(form);
      attempt.current = {
        key: newUuid(),
        body: JSON.stringify(Object.fromEntries(data)),
      };
    }
    setBusy(true);
    setError("");
    try {
      await request(path, {
        method: "POST",
        body: attempt.current.body,
        headers: { "Idempotency-Key": attempt.current.key },
      });
      attempt.current = null;
      setUncertain(false);
      form.reset();
      changed();
    } catch (e) {
      const unknown =
        !(e instanceof ApiError) || e.status === 0 || e.status >= 500;
      setUncertain(unknown);
      if (!unknown) attempt.current = null;
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={save} className="stack">
      {error && <Notice>{error}</Notice>}
      <fieldset disabled={busy || uncertain} className="form-grid">
        <label>
          Операция
          <select aria-label="Операция" name="kind">
            <option value="payment">Оплата</option>
            <option value="refund">Возврат</option>
          </select>
        </label>
        <label>
          Сумма, сом
          <input name="amount" type="number" step="0.01" min="0.01" required />
        </label>
        <label>
          Способ
          <select aria-label="Способ" name="method">
            <option value="cash">Наличные</option>
            <option value="transfer">Перевод</option>
            <option value="card">Карта</option>
          </select>
        </label>
        <label>
          Комментарий к операции
          <input
            name="note"
            maxLength={1000}
            placeholder="Для возврата обязателен"
          />
        </label>
      </fieldset>
      <button disabled={busy} className="primary">
        {uncertain ? "Повторить ту же операцию" : "Записать оплату или возврат"}
      </button>
    </form>
  );
}

export function Photos({
  business,
  orderId,
  kind,
  refresh = 0,
}: {
  business: Business;
  orderId: string;
  kind?: string;
  refresh?: number;
}) {
  const [revision, setRevision] = useState(0),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const path = businessPath(business.id, `orders/${orderId}/photos`);
  const photos = useRemote<Photo[]>(path, revision + refresh);
  const [pendingDelete, setPendingDelete] = useState<Photo | null>(null);
  const [removed, setRemoved] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const actionBusy = busy || photos.loading;
  async function remove() {
    if (!pendingDelete || actionBusy) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await request(`${path}${pendingDelete.id}/`, { method: "DELETE" });
      setRemoved((ids) => [...ids, pendingDelete.id]);
      setPendingDelete(null);
      setMessage("Фотография удалена.");
      setRevision((r) => r + 1);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function upload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (actionBusy) return;
    const form = e.currentTarget;
    setBusy(true);
    setError("");
    setMessage("");
    setPendingDelete(null);
    try {
      await request(path, { method: "POST", body: new FormData(form) });
      form.reset();
      setRevision((r) => r + 1);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="stack">
      <h3>Фотографии</h3>
      {(error || photos.error) && <Notice>{error || photos.error}</Notice>}
      {message && <p role="status">{message}</p>}
      <div className="photo-grid">
        {photos.data
          ?.filter((p) => !removed.includes(p.id))
          .map((p, index) => (
            <div className="order-photo" key={p.id}>
              <a
                href={`/api/v1${path}${p.id}/`}
                target="_blank"
                rel="noreferrer"
              >
                <img
                  src={`/api/v1${path}${p.id}/`}
                  alt={p.kind === "bouquet" ? "Фото букета" : "Фото вручения"}
                />
                <small>{p.kind === "bouquet" ? "Букет" : "Вручение"}</small>
              </a>
              {p.can_delete && (
                <button
                  type="button"
                  className="photo-remove"
                  aria-label={`Удалить фото ${index + 1}: ${p.kind === "bouquet" ? "букет" : "вручение"}`}
                  title="Удалить фотографию"
                  disabled={actionBusy}
                  onClick={() => {
                    setPendingDelete(p);
                    setError("");
                    setMessage("");
                  }}
                >
                  <X size={18} aria-hidden="true" />
                </button>
              )}
            </div>
          ))}
      </div>
      {pendingDelete && (
        <div
          className="photo-delete-confirm"
          role="group"
          aria-label="Удаление фотографии"
        >
          <img
            src={`/api/v1${path}${pendingDelete.id}/`}
            alt="Фото для удаления"
          />
          <div className="stack">
            <p>Удалить выбранную фотографию?</p>
            <div className="photo-delete-actions">
              <button
                type="button"
                disabled={actionBusy}
                onClick={() => void remove()}
              >
                {busy ? "Удаляем…" : "Удалить фото"}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => setPendingDelete(null)}
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
      <form onSubmit={upload} className="inline-form">
        <label>
          Этап фото
          <select
            aria-label="Этап фото"
            name="kind"
            defaultValue={kind || "bouquet"}
          >
            {(!kind || kind === "bouquet") && (
              <option value="bouquet">Букет</option>
            )}
            {(!kind || kind === "delivery") && (
              <option value="delivery">Вручение</option>
            )}
          </select>
        </label>
        <label>
          Файл фотографии
          <input
            type="file"
            name="file"
            accept="image/jpeg,image/png,image/webp"
            required
          />
        </label>
        <button disabled={actionBusy}>Загрузить фото</button>
      </form>
    </section>
  );
}

export function OrderPanel({
  business,
  orderId,
  close,
  changed,
}: {
  business: Business;
  orderId: string;
  close: () => void;
  changed: () => void;
}) {
  const [revision, setRevision] = useState(0),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [editing, setEditing] = useState(false);
  const [share, setShare] = useState("");
  const [confirmationReason, setConfirmationReason] = useState("");
  const base = businessPath(business.id, `orders/${orderId}`);
  const order = useRemote<Order>(base, revision, {
    refreshOnAppear: !editing,
  });
  const actionBusy = busy || order.loading;
  const staff = useRemote<Staff[]>(
    businessPath(business.id, "staff"),
    revision,
  );
  const payments = useRemote<Payment[]>(base + "payments/", revision);
  const history = useRemote<HistoryEvent[]>(base + "history/", revision);
  const feedback = useRemote<Feedback[]>(base + "feedback/", revision);
  function reload() {
    setRevision((r) => r + 1);
    changed();
  }
  async function act(path: string, data: object) {
    if (actionBusy) return;
    setBusy(true);
    setError("");
    try {
      await request(path, { method: "POST", body: JSON.stringify(data) });
      reload();
    } catch (e) {
      setError(errorText(e));
      if (e instanceof ApiError && e.status === 409) reload();
    } finally {
      setBusy(false);
    }
  }
  async function shareLink(revoke: boolean) {
    setBusy(true);
    setError("");
    try {
      const result = await request<{ token: string }>(base + "share/", {
        method: "POST",
        body: JSON.stringify({ revoke }),
      });
      setShare(result.token ? `${location.origin}/track/${result.token}` : "");
      reload();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  const o = order.data;
  if (editing && o)
    return (
      <OrderForm
        business={business}
        initial={o}
        close={() => setEditing(false)}
        saved={() => {
          setEditing(false);
          reload();
        }}
      />
    );
  const balance =
    (payments.data || []).reduce(
      (sum, p) =>
        sum +
        Math.round(Number(p.amount) * 100) * (p.kind === "payment" ? 1 : -1),
      0,
    ) / 100;
  return (
    <Modal
      drawer
      title={o ? `Заказ №${o.number}` : "Заказ"}
      close={close}
      busy={busy}
    >
      {o && (
        <OrderTicket
          order={o}
          business={business}
          status={statusNames[o.status]}
        />
      )}
      <div className="modal-body stack">
        {[
          error,
          order.error,
          staff.error,
          payments.error,
          history.error,
          feedback.error,
        ]
          .filter(Boolean)
          .map((m, i) => (
            <Notice key={i}>{m}</Notice>
          ))}
        {!o ? (
          <p>
            {order.loading
              ? "Загружаем карточку…"
              : "Не удалось открыть заказ. Закройте карточку и попробуйте ещё раз."}
          </p>
        ) : (
          <>
            <div className="timeline">
              {[
                ...(o.status === "pending" ? ["pending"] : []),
                "new",
                "work",
                "ready",
                ...(o.fulfillment === "courier" ? ["route"] : []),
                "done",
              ].map((status, i, steps) => {
                const completed =
                  o.status === "done" || i < steps.indexOf(o.status);
                const active = !completed && status === o.status;
                return (
                  <div
                    className={`tl-i ${completed ? "done" : active ? "cur" : "todo"}`}
                    key={status}
                    aria-current={active ? "step" : undefined}
                  >
                    <div className="dot" aria-hidden="true">
                      {completed && <Check size={12} strokeWidth={3} />}
                    </div>
                    <div>
                      <div className="tt">{statusNames[status]}</div>
                      <div className="ts">
                        {active
                          ? "сейчас"
                          : status === "done" && completed
                            ? "заказ выполнен"
                            : ""}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="section-heading">
              <Status value={o.status} />
              <strong className="total">{price(o.total)}</strong>
            </div>
            <div className="form-grid">
              <div>
                <small>Клиент</small>
                <h3>{o.customer_name}</h3>
                <p>{o.customer_phone}</p>
              </div>
              <div>
                <small>Получатель</small>
                <h3>{o.recipient_name}</h3>
                <p>{o.recipient_phone || "Телефон не указан"}</p>
              </div>
            </div>
            <div className="detail-box">
              <strong>
                {o.fulfillment === "courier" ? "Доставка" : "Самовывоз"} ·{" "}
                {o.delivery_date}
              </strong>
              <p>
                {o.window_start.slice(0, 5)}–{o.window_end.slice(0, 5)} ·{" "}
                {o.address}
              </p>
            </div>
            {o.lines.map((l) => (
              <div className="detail-line" key={l.product_id}>
                <span className="product-name">
                  <ProductPhoto url={l.photo_url} name={l.name} />
                  {l.name} × {l.quantity}
                </span>
                <strong>{price(l.total)}</strong>
              </div>
            ))}
            {Number(o.delivery_fee) > 0 && (
              <div className="detail-line">
                <span>Доставка</span>
                <strong>{price(o.delivery_fee)}</strong>
              </div>
            )}
            {(o.occasion || o.source || o.relation) && (
              <div className="row small muted">
                {[o.occasion, o.relation, o.source].filter(Boolean).join(" · ")}
              </div>
            )}
            {o.card && <p className="preserve">Открытка: {o.card}</p>}
            {o.notes && <p className="preserve">{o.notes}</p>}
            {o.delivery_issue && (
              <Notice>
                Проблема доставки: {o.delivery_issue}{" "}
                <button
                  disabled={actionBusy}
                  onClick={() =>
                    void act(base + "resolve-delivery-issue/", {
                      version: o.version,
                    })
                  }
                >
                  Проблема решена
                </button>
              </Notice>
            )}
            {o.cancellation_reason && (
              <Notice>Причина отмены: {o.cancellation_reason}</Notice>
            )}
            <div className="inline-form">
              {["pending", "new", "work"].includes(o.status) && (
                <button disabled={actionBusy} onClick={() => setEditing(true)}>
                  Редактировать заказ
                </button>
              )}
              <button onClick={() => window.print()}>Печатать талон</button>
            </div>
            {o.status === "pending" && (
              <section
                className="pending-confirmation"
                aria-label="Подтверждение заказа"
              >
                <strong>Заказ ждёт подтверждения</strong>
                <p>
                  Флорист и курьер пока не видят этот заказ. Место в окне
                  доставки занято.
                </p>
                <p>
                  Предоплата: {price(o.prepayment_required)} · внесено{" "}
                  {price(o.paid_amount)}
                </p>
                {o.payment_due_at && (
                  <p>
                    Оплатить до{" "}
                    {new Date(o.payment_due_at).toLocaleString("ru-RU", {
                      timeZone: business.timezone,
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                    . При отсутствии оплаты и вложений клиента заказ отменится
                    автоматически.
                  </p>
                )}
                {Number(o.paid_amount) < Number(o.prepayment_required) && (
                  <label>
                    Причина подтверждения без предоплаты
                    <input
                      maxLength={1000}
                      value={confirmationReason}
                      onChange={(e) => setConfirmationReason(e.target.value)}
                      placeholder="Например, согласовано с постоянным клиентом"
                    />
                  </label>
                )}
                <div className="inline-form">
                  <button
                    className="primary"
                    disabled={
                      actionBusy ||
                      (Number(o.paid_amount) < Number(o.prepayment_required) &&
                        !confirmationReason.trim())
                    }
                    onClick={() =>
                      void act(base + "transition/", {
                        version: o.version,
                        status: "new",
                        reason: confirmationReason,
                      })
                    }
                  >
                    Подтвердить заказ
                  </button>
                  <button
                    disabled={actionBusy}
                    onClick={() =>
                      void act(base + "extend-payment/", { version: o.version })
                    }
                  >
                    Продлить оплату на 30 минут
                  </button>
                </div>
              </section>
            )}
            {!["pending", "done", "cancelled"].includes(o.status) &&
              staff.data && (
                <form
                  key={`assign-${o.version}`}
                  className="inline-form assignment-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const d = new FormData(e.currentTarget);
                    void act(base + "assignment/", {
                      version: o.version,
                      florist_id:
                        o.status === "route"
                          ? o.florist_id
                          : d.get("florist") || null,
                      courier_id: d.get("courier") || null,
                    });
                  }}
                >
                  <label>
                    Флорист
                    <select
                      aria-label="Флорист"
                      name="florist"
                      defaultValue={o.florist_id || ""}
                      disabled={
                        actionBusy || staff.loading || o.status === "route"
                      }
                    >
                      <option value="">Не назначен</option>
                      {staff.data
                        ?.filter(
                          (s) =>
                            (s.role === "florist" && s.is_active) ||
                            s.id === o.florist_id,
                        )
                        .map((s) => (
                          <option
                            key={s.id}
                            value={s.id}
                            disabled={!s.is_active || s.role !== "florist"}
                          >
                            {s.name}
                            {(!s.is_active || s.role !== "florist") &&
                              " — недоступен"}
                          </option>
                        ))}
                    </select>
                  </label>
                  <label className="courier-field">
                    Курьер
                    <select
                      aria-label="Курьер"
                      aria-describedby={
                        o.fulfillment === "pickup"
                          ? `courier-pickup-${o.id}`
                          : undefined
                      }
                      name="courier"
                      defaultValue={o.courier_id || ""}
                      disabled={
                        actionBusy ||
                        staff.loading ||
                        o.fulfillment === "pickup"
                      }
                      required={o.status === "route"}
                    >
                      <option value="">
                        {o.fulfillment === "pickup"
                          ? "Не требуется"
                          : "Не назначен"}
                      </option>
                      {staff.data
                        ?.filter(
                          (s) =>
                            (s.role === "courier" && s.is_active) ||
                            s.id === o.courier_id,
                        )
                        .map((s) => (
                          <option
                            key={s.id}
                            value={s.id}
                            disabled={!s.is_active || s.role !== "courier"}
                          >
                            {s.name}
                            {(!s.is_active || s.role !== "courier") &&
                              " — недоступен"}
                          </option>
                        ))}
                    </select>
                    {o.fulfillment === "pickup" && (
                      <span
                        className="field-hint"
                        id={`courier-pickup-${o.id}`}
                      >
                        Самовывоз — клиент заберёт заказ в магазине.
                      </span>
                    )}
                    {o.status === "route" && (
                      <span className="field-hint">
                        Можно передать доставку другому курьеру. Заказ останется
                        в пути.
                      </span>
                    )}
                  </label>
                  <button disabled={actionBusy || staff.loading}>
                    {o.status === "route"
                      ? "Заменить курьера"
                      : "Назначить сотрудников"}
                  </button>
                </form>
              )}
            <div className="inline-form">
              {transitions(o)
                .filter((s) => s !== "cancelled")
                .map((s) => (
                  <button
                    key={s}
                    className="primary"
                    disabled={actionBusy}
                    onClick={() =>
                      void act(base + "transition/", {
                        status: s,
                        version: o.version,
                      })
                    }
                  >
                    {actionNames[s]}
                  </button>
                ))}
            </div>
            {transitions(o).includes("cancelled") && (
              <details>
                <summary>Отмена заказа</summary>
                <form
                  className="inline-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void act(base + "transition/", {
                      status: "cancelled",
                      version: o.version,
                      reason: new FormData(e.currentTarget).get("reason"),
                    });
                  }}
                >
                  <label>
                    Причина отмены
                    <input name="reason" required maxLength={1000} />
                  </label>
                  <button disabled={actionBusy} className="danger">
                    Отменить заказ
                  </button>
                </form>
              </details>
            )}
            <section className="stack">
              <h3>Оплаты и возвраты</h3>
              {payments.data && (
                <p>
                  Внесено: <strong>{price(balance)}</strong> · Остаток:{" "}
                  <strong>{price(Number(o.total) - balance)}</strong>
                </p>
              )}
              {payments.data?.map((p) => (
                <div className="detail-line" key={p.id}>
                  <span>
                    {p.kind === "refund" ? "Возврат" : "Оплата"} ·{" "}
                    {p.method === "cash"
                      ? "наличные"
                      : p.method === "card"
                        ? "карта"
                        : "перевод"}
                    <small>{p.note}</small>
                  </span>
                  <strong>{price(p.amount)}</strong>
                </div>
              ))}
              <PaymentForm path={base + "payments/"} changed={reload} />
            </section>
            <Photos business={business} orderId={orderId} />
            <section className="stack">
              <h3>Страница для клиента</h3>
              <p className="muted">
                Только статус и время получения. Новая ссылка отменяет
                предыдущую.
              </p>
              <div className="inline-form">
                <button disabled={busy} onClick={() => void shareLink(false)}>
                  Создать ссылку
                </button>
                <button disabled={busy} onClick={() => void shareLink(true)}>
                  Отозвать ссылку
                </button>
              </div>
              {share && (
                <label>
                  Ссылка клиенту
                  <input
                    readOnly
                    aria-label="Ссылка клиенту"
                    value={share}
                    onFocus={(e) => e.target.select()}
                  />
                  <a href={share} target="_blank" rel="noreferrer">
                    Открыть страницу клиента
                  </a>
                </label>
              )}
            </section>
            <section className="stack">
              <h3>Отзывы и жалобы</h3>
              {feedback.data?.map((f) => (
                <div className="detail-box" key={f.id}>
                  <strong>
                    {f.kind === "complaint" ? "Жалоба" : "Отзыв"}
                    {f.rating ? ` · ${f.rating}/5` : ""}
                  </strong>
                  <p>{f.message}</p>
                  {f.outcome && <p>Решение: {f.outcome}</p>}
                  {f.kind === "complaint" && f.status === "open" && (
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        void act(
                          businessPath(business.id, `feedback/${f.id}/resolve`),
                          {
                            outcome: new FormData(e.currentTarget).get(
                              "outcome",
                            ),
                          },
                        );
                      }}
                    >
                      <label>
                        Результат решения
                        <input name="outcome" required />
                      </label>
                      <button disabled={busy}>Закрыть жалобу</button>
                    </form>
                  )}
                </div>
              ))}
              <form
                className="stack"
                onSubmit={(e) => {
                  e.preventDefault();
                  const d = new FormData(e.currentTarget);
                  void act(base + "feedback/", {
                    kind: d.get("kind"),
                    message: d.get("message"),
                    rating: null,
                  });
                }}
              >
                <label>
                  Вид обращения
                  <select aria-label="Вид обращения" name="kind">
                    <option value="complaint">Жалоба</option>
                    <option value="review">Отзыв</option>
                  </select>
                </label>
                <label>
                  Текст обращения
                  <textarea name="message" required maxLength={2000} />
                </label>
                <button disabled={busy}>Записать обращение</button>
              </form>
            </section>
            <section className="stack">
              <h3>История заказа</h3>
              {history.data?.map((h) => (
                <div className="history-row" key={h.id}>
                  <span className="history-dot" />
                  <div>
                    <strong>{eventNames[h.kind] || h.kind}</strong>
                    {h.detail && <p>{h.detail}</p>}
                    <small>
                      {new Date(h.created_at).toLocaleString("ru-RU", {
                        timeZone: business.timezone,
                      })}{" "}
                      · {h.actor__username}
                    </small>
                  </div>
                </div>
              ))}
            </section>
          </>
        )}
      </div>
      <footer className="modal-footer">
        <RefreshIndicator
          active={
            order.refreshing ||
            payments.refreshing ||
            history.refreshing ||
            feedback.refreshing
          }
        />
        <button onClick={reload} disabled={busy || order.loading}>
          Обновить карточку
        </button>
        <button onClick={close} disabled={busy}>
          Закрыть
        </button>
      </footer>
    </Modal>
  );
}

export function TaskBoard({
  business,
  openOrder,
  refresh = 0,
}: {
  business: Business;
  openOrder: (order: Order) => void;
  refresh?: number;
}) {
  const [revision, setRevision] = useState(0),
    [day, setDay] = useState(""),
    [limit, setLimit] = useState(6),
    [offset, setOffset] = useState(0),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const board = useRef<HTMLElement>(null);
  const office = ["owner", "manager"].includes(business.role);
  const page = useRemote<Page<Task | Order>>(
    businessPath(business.id, "tasks") +
      `?limit=${limit}&offset=${offset}${day ? `&day=${day}` : ""}`,
    revision + refresh,
  );
  useEffect(() => {
    if (page.loading || !page.data) return;
    const lastOffset = Math.max(
      0,
      (Math.ceil(page.data.count / limit) - 1) * limit,
    );
    if (offset > lastOffset) setOffset(lastOffset);
  }, [page.data, page.loading, limit, offset]);
  function changePage(next: number) {
    setOffset(next);
    board.current?.scrollIntoView({ block: "start" });
  }
  function pagination(position: string) {
    return page.data ? (
      <nav
        className="task-pagination"
        aria-label={`Страницы заданий ${position}`}
      >
        <Pager
          count={page.data.count}
          offset={offset}
          setOffset={changePage}
          limit={limit}
          disabled={busy || page.loading}
          showPageNumber
        />
      </nav>
    ) : null;
  }
  async function transition(o: Task | Order, status: string) {
    setBusy(true);
    setError("");
    try {
      await request(businessPath(business.id, `orders/${o.id}/transition`), {
        method: "POST",
        body: JSON.stringify({ version: o.version, status }),
      });
      setRevision((r) => r + 1);
    } catch (e) {
      setError(errorText(e));
      setRevision((r) => r + 1);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="stack worker-tasks" ref={board}>
      <div className="toolbar">
        <label>
          Дата получения
          <input
            type="date"
            value={day}
            onChange={(e) => {
              setDay(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <label>
          Заданий на странице
          <select
            value={limit}
            disabled={busy}
            onChange={(event) => {
              setLimit(Number(event.target.value));
              setOffset(0);
            }}
          >
            {[6, 12, 24].map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </label>
        <button
          disabled={page.loading}
          onClick={() => setRevision((r) => r + 1)}
        >
          Обновить задания
        </button>
        <RefreshIndicator active={page.refreshing} />
      </div>
      {pagination("сверху")}
      {(error || page.error) && <Notice>{error || page.error}</Notice>}
      {page.initialLoading ? (
        <p>Загружаем задания…</p>
      ) : !page.data?.count ? (
        <div className="empty">
          <h2>{office ? "Доставок пока нет" : "Заданий пока нет"}</h2>
          <p>Здесь появятся заказы вашего магазина.</p>
        </div>
      ) : (
        <div className="task-grid">
          {page.data.results.map((o) => (
            <article className="m-card stack" key={o.id}>
              <div className="section-heading">
                <strong>№{o.number}</strong>
                <Status value={o.status} />
              </div>
              <h3 className="mb">
                {business.role === "courier"
                  ? `Адрес: ${o.address}`
                  : o.recipient_name}
              </h3>
              <p>
                {o.delivery_date} · {o.window_start.slice(0, 5)}–
                {o.window_end.slice(0, 5)}
              </p>
              {o.delivery_issue && <Notice>{o.delivery_issue}</Notice>}
              {o.address && (
                <p className="ms">
                  {business.role === "courier" ? o.recipient_name : o.address}
                </p>
              )}
              {o.recipient_phone && (
                <a href={`tel:${o.recipient_phone}`}>{o.recipient_phone}</a>
              )}
              {("lines" in o ? o.lines : o.items).map((l, i) => (
                <div className="product-name" key={i}>
                  <ProductPhoto url={l.photo_url} name={l.name} />
                  {l.name} × {l.quantity}
                </div>
              ))}
              {o.card && <p>Открытка: {o.card}</p>}
              {office ? (
                <button onClick={() => openOrder(o as Order)}>
                  Открыть заказ
                </button>
              ) : (
                <>
                  <div className="inline-form">
                    {transitions(o)
                      .filter((s) =>
                        business.role === "florist"
                          ? ["work", "ready"].includes(s)
                          : ["route", "done"].includes(s),
                      )
                      .map((s) => (
                        <button
                          className="primary"
                          key={s}
                          disabled={busy || page.loading}
                          onClick={() => void transition(o, s)}
                        >
                          {actionNames[s]}
                        </button>
                      ))}
                  </div>
                  {business.role === "courier" && o.status === "route" && (
                    <form
                      onSubmit={async (e) => {
                        e.preventDefault();
                        const text = new FormData(e.currentTarget).get(
                          "detail",
                        );
                        setBusy(true);
                        try {
                          await request(
                            businessPath(
                              business.id,
                              `orders/${o.id}/delivery-issue`,
                            ),
                            {
                              method: "POST",
                              body: JSON.stringify({
                                version: o.version,
                                detail: text,
                              }),
                            },
                          );
                          setRevision((r) => r + 1);
                        } catch (e) {
                          setError(errorText(e));
                        } finally {
                          setBusy(false);
                        }
                      }}
                    >
                      <label>
                        Проблема доставки
                        <input
                          name="detail"
                          placeholder="Не дозвонился, нужен другой адрес…"
                          required
                        />
                      </label>
                      <button disabled={busy || page.loading}>
                        Сообщить менеджеру
                      </button>
                    </form>
                  )}
                  <Photos
                    business={business}
                    orderId={o.id}
                    kind={business.role === "florist" ? "bouquet" : "delivery"}
                  />
                </>
              )}
            </article>
          ))}
        </div>
      )}
      {pagination("снизу")}
    </section>
  );
}
