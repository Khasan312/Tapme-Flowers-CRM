import { useEffect, useState } from "react";
import { ClipboardList, Pencil, Plus, Trash2 } from "lucide-react";
import { ApiError, businessPath, errorText, price, request } from "./api";
import { Modal, Notice } from "./components";
import { useRemote } from "./hooks";
import { ProductPicker } from "./product-picker";
import { shopDay, shortDate } from "./ui";
import type { Business, Order, Product, ShopSettings } from "./types";
import "./order-draft.css";

type DraftItem =
  | { kind: "product"; product_id: string; quantity: number }
  | { kind: "budget"; amount: string; description: string };
type Fields = {
  point_id: string;
  items: DraftItem[];
  fulfillment: "pickup" | "courier";
  date: string;
  window: { start: string; end: string };
  recipient_name: string;
  recipient_phone: string;
  occasion: string;
  requested_time_text: string;
  address: string;
  address_details: string;
  card_text: string;
  notes: string;
};
type Draft = {
  id: string;
  version: number;
  status: "active" | "converted" | "abandoned";
  fields: Fields;
  total: string;
  delivery_fee: string;
  prepayment_percent: number;
  missing: string[];
  order_id: string | null;
  updated_at: string;
  lines: { name: string; price: string; quantity: number; total: string }[];
};
type Result = { draft: Draft | null };

export function OrderDraftCard({
  business,
  chatId,
  userId,
  canEdit,
  openOrder,
  changed,
}: {
  business: Business;
  chatId: string;
  userId: string;
  canEdit: boolean;
  openOrder: (id: string) => void;
  changed: () => void;
}) {
  const path = businessPath(business.id, `chats/${chatId}/order-draft`);
  const [revision, setRevision] = useState(0);
  const source = useRemote<Result>(path, revision);
  const [editing, setEditing] = useState<Draft | null>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const draft = source.data?.draft;
  async function abandon() {
    if (
      !draft ||
      !window.confirm(
        "Отложить черновик? Сохранённые данные останутся, несохранённые правки будут убраны.",
      )
    )
      return;
    setBusy(true);
    setError("");
    try {
      await request(path, {
        method: "DELETE",
        body: JSON.stringify({ draft_id: draft.id, version: draft.version }),
      });
      try {
        sessionStorage.removeItem(
          `tapme-order-draft:${userId}:${business.id}:${chatId}`,
        );
      } catch {
        /* Optional storage. */
      }
      setRevision((v) => v + 1);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function start(restore = false) {
    setBusy(true);
    setError("");
    try {
      const result = await request<Result>(path + (restore ? "restore/" : ""), {
        method: "POST",
        body: JSON.stringify(
          restore && draft
            ? { draft_id: draft.id, version: draft.version }
            : {},
        ),
      });
      setEditing(result.draft);
      setRevision((v) => v + 1);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <section
        className="chat-profile-card order-draft-card"
        aria-label="Черновик заказа в чате"
      >
        <h3>
          <ClipboardList size={18} />
          Черновик заказа
        </h3>
        <span className="draft-caption">Заполняет менеджер</span>
        {(error || source.error) && <Notice>{error || source.error}</Notice>}
        {source.error && (
          <button className="btn" onClick={() => setRevision((v) => v + 1)}>
            Повторить загрузку черновика
          </button>
        )}
        {draft?.status === "active" ? (
          <>
            <div className="draft-summary">
              {draft.lines.map((line, i) => (
                <div key={i}>
                  <span>
                    {line.name} × {line.quantity}
                  </span>
                  <b>{price(line.total)}</b>
                </div>
              ))}
              {!draft.lines.length && (
                <p>Добавьте букет из прайса или укажите бюджет.</p>
              )}
              <p>
                {draft.fields.fulfillment === "courier"
                  ? "Доставка"
                  : "Самовывоз"}
                {draft.fields.date && ` · ${shortDate(draft.fields.date)}`}{" "}
                {draft.fields.window.start &&
                  `· ${draft.fields.window.start}–${draft.fields.window.end}`}
              </p>
              <p>{draft.fields.recipient_name || "Получатель ещё не указан"}</p>
              <div className="draft-total">
                <span>Итого</span>
                <strong>{price(draft.total)}</strong>
              </div>
            </div>
            {draft.missing.length > 0 && (
              <p className="draft-missing">
                Уточнить: {draft.missing.join(", ").toLowerCase()}
              </p>
            )}
            <button
              className="btn primary"
              disabled={!canEdit || busy}
              onClick={() => setEditing(draft)}
            >
              <Pencil size={15} />
              Открыть черновик
            </button>
            <button
              className="btn"
              disabled={busy}
              onClick={() => void abandon()}
            >
              Отложить черновик
            </button>
          </>
        ) : draft?.status === "converted" ? (
          <>
            <p>Из этого черновика уже создан заказ.</p>
            {draft.order_id && (
              <button
                className="btn"
                onClick={() => openOrder(draft.order_id!)}
              >
                Открыть созданный заказ
              </button>
            )}
            <button
              className="btn"
              disabled={!canEdit || busy}
              onClick={() => void start()}
            >
              Новый черновик
            </button>
          </>
        ) : draft?.status === "abandoned" ? (
          <>
            <p>Черновик отложен. Его можно восстановить или начать новый.</p>
            <button
              className="btn"
              disabled={!canEdit || busy}
              onClick={() => void start(true)}
            >
              Восстановить черновик
            </button>
            <button
              className="btn"
              disabled={!canEdit || busy}
              onClick={() => void start()}
            >
              Новый черновик
            </button>
          </>
        ) : (
          <>
            <p>
              Сохраняйте состав, время и пожелания по ходу переписки. Заказ
              появится после подтверждения формы.
            </p>
            <button
              className="btn primary"
              disabled={!canEdit || busy || source.loading || !!source.error}
              onClick={() => void start()}
            >
              <Plus size={16} />
              Создать черновик
            </button>
          </>
        )}
        {!canEdit && (
          <p>
            Откройте диалог и выберите клиента, чтобы работать с черновиком.
          </p>
        )}
      </section>
      {editing && (
        <DraftEditor
          key={editing.id}
          draft={editing}
          business={business}
          path={path}
          cacheKey={`tapme-order-draft:${userId}:${business.id}:${chatId}`}
          close={() => {
            setEditing(null);
            setRevision((v) => v + 1);
          }}
          saved={() => {
            setRevision((v) => v + 1);
            changed();
          }}
          created={(order) => {
            setEditing(null);
            setRevision((v) => v + 1);
            changed();
            openOrder(order.id);
          }}
        />
      )}
    </>
  );
}

function DraftEditor({
  draft,
  business,
  path,
  cacheKey,
  close,
  saved,
  created,
}: {
  draft: Draft;
  business: Business;
  path: string;
  cacheKey: string;
  close: () => void;
  saved: () => void;
  created: (order: Order) => void;
}) {
  const [initial] = useState(() => {
    try {
      const cached = JSON.parse(sessionStorage.getItem(cacheKey) || "null");
      if (cached?.id === draft.id && cached.fields && cached.version)
        return cached as { fields: Fields; version: number };
    } catch {
      /* Optional local recovery. */
    }
    return { fields: draft.fields, version: draft.version };
  });
  const [fields, setFields] = useState<Fields>(initial.fields);
  const [version, setVersion] = useState(initial.version);
  const [dirty, setDirty] = useState(initial.fields !== draft.fields);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [conflict, setConflict] = useState(false),
    [busy, setBusy] = useState(false);
  const [product, setProduct] = useState<Product | null>(null);
  const [budget, setBudget] = useState(""),
    [description, setDescription] = useState("");
  const [without, setWithout] = useState(false),
    [reason, setReason] = useState("");
  const [deadline, setDeadline] = useState("");
  const points = useRemote<import("./types").Point[]>(
    businessPath(business.id, "points"),
  );
  const shop = useRemote<ShopSettings>(
    fields.point_id
      ? businessPath(business.id, `points/${fields.point_id}`)
      : businessPath(business.id, "settings"),
  );
  const [names, setNames] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      draft.fields.items.flatMap((item, i) =>
        item.kind === "product"
          ? [[item.product_id, draft.lines[i]?.name || "Позиция прайса"]]
          : [],
      ),
    ),
  );
  useEffect(() => {
    try {
      if (dirty)
        sessionStorage.setItem(
          cacheKey,
          JSON.stringify({ id: draft.id, fields, version }),
        );
      else sessionStorage.removeItem(cacheKey);
    } catch {
      /* Storage may be unavailable. */
    }
  }, [fields, version, dirty, cacheKey, draft.id]);
  function edit<K extends keyof Fields>(key: K, value: Fields[K]) {
    setFields((old) => ({ ...old, [key]: value }));
    setDirty(true);
    setNotice("");
  }
  function addProduct() {
    if (!product) return;
    const existing = fields.items.find(
      (i) => i.kind === "product" && i.product_id === product.id,
    );
    if (existing && existing.kind === "product")
      edit(
        "items",
        fields.items.map((i) =>
          i === existing
            ? { ...existing, quantity: Math.min(999, existing.quantity + 1) }
            : i,
        ),
      );
    else
      edit("items", [
        ...fields.items,
        { kind: "product", product_id: product.id, quantity: 1 },
      ]);
    setNames((old) => ({ ...old, [product.id]: product.name }));
  }
  async function persist() {
    const response = await request<Result>(path, {
      method: "PUT",
      body: JSON.stringify({ draft_id: draft.id, version, fields }),
    });
    const result = response.draft!;
    setVersion(result.version);
    setFields(result.fields);
    setDirty(false);
    setNotice("Черновик сохранён");
    saved();
    return result;
  }
  async function act(convert: boolean) {
    if (busy || conflict) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const current = dirty ? await persist() : { ...draft, fields, version };
      if (convert) {
        const order = await request<Order>(path + "convert/", {
          method: "POST",
          body: JSON.stringify({
            draft_id: draft.id,
            version: current.version,
            without_prepayment: without && fields.fulfillment === "courier",
            reason,
            ...(deadline && fields.fulfillment === "courier" && !without
              ? { payment_due_at: new Date(deadline).toISOString() }
              : {}),
          }),
        });
        try {
          sessionStorage.removeItem(cacheKey);
        } catch {
          /* Optional storage. */
        }
        created(order);
      } else if (!dirty) setNotice("Черновик сохранён");
    } catch (e) {
      setError(errorText(e));
      if (e instanceof ApiError && e.status === 409) setConflict(true);
    } finally {
      setBusy(false);
    }
  }
  async function refresh() {
    if (
      dirty &&
      !window.confirm("Заменить правки в форме сохранённым черновиком?")
    )
      return;
    setBusy(true);
    try {
      const response = await request<Result>(path);
      if (
        !response.draft ||
        response.draft.status !== "active" ||
        response.draft.id !== draft.id
      ) {
        close();
        return;
      }
      setFields(response.draft.fields);
      setVersion(response.draft.version);
      setDirty(false);
      setConflict(false);
      setError("");
      setNames(
        Object.fromEntries(
          response.draft.fields.items.flatMap((item, i) =>
            item.kind === "product"
              ? [
                  [
                    item.product_id,
                    response.draft!.lines[i]?.name || "Позиция прайса",
                  ],
                ]
              : [],
          ),
        ),
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  const courier = fields.fulfillment === "courier";
  return (
    <Modal title="Черновик заказа" close={close} busy={busy}>
      <form
        className="draft-editor"
        onSubmit={(e) => {
          e.preventDefault();
          void act(false);
        }}
      >
        <p className="draft-intro">
          Заполняйте по ходу переписки. Сохранённый черновик доступен менеджерам
          магазина и пока не является заказом.
        </p>
        {error && <Notice>{error}</Notice>}
        {conflict && (
          <button
            type="button"
            className="btn"
            disabled={busy}
            onClick={() => void refresh()}
          >
            Загрузить актуальный черновик
          </button>
        )}
        {notice && (
          <p role="status" className="draft-saved">
            {notice}
          </p>
        )}
        <fieldset disabled={busy || conflict}>
          <legend>Состав заказа</legend>
          <div className="draft-picker">
            <ProductPicker
              businessId={business.id}
              value={product}
              onChange={setProduct}
            />
            <button
              type="button"
              className="btn"
              disabled={!product || fields.items.length >= 50}
              onClick={addProduct}
              aria-label="Добавить позицию в черновик"
            >
              <Plus size={18} />
            </button>
          </div>
          <div className="draft-items">
            {fields.items.map((item, index) => (
              <div
                className="draft-item"
                key={item.kind === "product" ? item.product_id : "budget"}
              >
                <span>
                  {item.kind === "product"
                    ? names[item.product_id] || "Позиция прайса"
                    : `Букет на ${price(item.amount)}${item.description ? ` · ${item.description}` : ""}`}
                </span>
                {item.kind === "product" && (
                  <input
                    aria-label={`Количество ${names[item.product_id] || "позиции"}`}
                    type="number"
                    min="1"
                    max="999"
                    value={item.quantity}
                    onChange={(e) =>
                      edit(
                        "items",
                        fields.items.map((i, n) =>
                          n === index
                            ? { ...item, quantity: Number(e.target.value) }
                            : i,
                        ),
                      )
                    }
                  />
                )}
                <button
                  type="button"
                  className="icon-button"
                  aria-label={`Убрать позицию ${index + 1}`}
                  onClick={() =>
                    edit(
                      "items",
                      fields.items.filter((_, n) => n !== index),
                    )
                  }
                >
                  <Trash2 size={17} />
                </button>
              </div>
            ))}
          </div>
          {!fields.items.some((i) => i.kind === "budget") && (
            <details className="draft-budget">
              <summary>Букет по бюджету</summary>
              <label>
                Бюджет
                <input
                  inputMode="decimal"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  placeholder="Например, 5000"
                />
              </label>
              <label>
                Описание букета
                <input
                  maxLength={150}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Пионы, без лилий"
                />
              </label>
              <button
                type="button"
                className="btn"
                disabled={
                  !Number(budget) ||
                  Number(budget) <= 0 ||
                  fields.items.length >= 50
                }
                onClick={() => {
                  edit("items", [
                    ...fields.items,
                    { kind: "budget", amount: budget, description },
                  ]);
                  setBudget("");
                  setDescription("");
                }}
              >
                Добавить букет по бюджету
              </button>
            </details>
          )}
          <p className="draft-caption">
            Цены из прайса и доставка пересчитываются сервером при сохранении и
            создании заказа.
          </p>
        </fieldset>
        <fieldset disabled={busy || conflict}>
          <legend>Получение</legend>
          {points.data && points.data.filter((p) => p.active).length > 1 && (
            <label>
              Точка заказа
              <select
                value={fields.point_id || ""}
                onChange={(e) => edit("point_id", e.target.value)}
              >
                <option value="">Выберите точку</option>
                {points.data
                  .filter((p) => p.active)
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.short_name}
                    </option>
                  ))}
              </select>
            </label>
          )}
          <div className="form-grid">
            <label>
              Способ получения
              <select
                aria-label="Способ получения"
                value={fields.fulfillment}
                onChange={(e) =>
                  edit("fulfillment", e.target.value as Fields["fulfillment"])
                }
              >
                <option value="courier">Доставка</option>
                <option value="pickup">Самовывоз</option>
              </select>
            </label>
            <label>
              Дата получения
              <input
                type="date"
                min={shopDay(business.timezone)}
                value={fields.date}
                onChange={(e) => edit("date", e.target.value)}
              />
            </label>
          </div>
          <label>
            Окно получения
            <select
              aria-label="Окно получения"
              value={`${fields.window.start}|${fields.window.end}`}
              onChange={(e) => {
                const [start, end] = e.target.value.split("|");
                edit("window", { start, end });
              }}
            >
              <option value="|">Выберите окно</option>
              {shop.data?.windows.map((w) => (
                <option key={w.start + w.end} value={`${w.start}|${w.end}`}>
                  {w.start}–{w.end}
                  {courier ? ` · ${price(w.price)}` : ""}
                </option>
              ))}
            </select>
          </label>
          {shop.error && <Notice>{shop.error}</Notice>}
          <label>
            Пожелание по времени
            <input
              value={fields.requested_time_text}
              maxLength={100}
              placeholder="Например, к 15:00 — согласовать с клиентом"
              onChange={(e) => edit("requested_time_text", e.target.value)}
            />
          </label>
          {courier && (
            <div className="form-grid">
              <label>
                Адрес доставки
                <input
                  maxLength={400}
                  value={fields.address}
                  onChange={(e) => edit("address", e.target.value)}
                />
              </label>
              <label>
                Квартира, домофон
                <input
                  maxLength={90}
                  value={fields.address_details}
                  onChange={(e) => edit("address_details", e.target.value)}
                />
              </label>
            </div>
          )}
          <div className="form-grid">
            <label>
              Имя получателя
              <input
                maxLength={150}
                value={fields.recipient_name}
                onChange={(e) => edit("recipient_name", e.target.value)}
              />
            </label>
            <label>
              Телефон получателя
              <input
                type="tel"
                value={fields.recipient_phone || "+996"}
                onChange={(e) => edit("recipient_phone", e.target.value)}
              />
            </label>
          </div>
        </fieldset>
        <fieldset disabled={busy || conflict}>
          <legend>Пожелания</legend>
          <label>
            Повод
            <input
              value={fields.occasion}
              maxLength={100}
              onChange={(e) => edit("occasion", e.target.value)}
            />
          </label>
          <label>
            Текст открытки
            <textarea
              aria-label="Текст открытки"
              value={fields.card_text}
              maxLength={1000}
              onChange={(e) => edit("card_text", e.target.value)}
            />
          </label>
          <label>
            Пожелания к заказу
            <textarea
              aria-label="Пожелания к заказу"
              value={fields.notes}
              maxLength={1700}
              onChange={(e) => edit("notes", e.target.value)}
            />
          </label>
        </fieldset>
        <fieldset disabled={busy || conflict} className="draft-confirmation">
          <legend>Перед созданием</legend>
          {courier ? (
            <>
              <p>
                Для доставки требуется полная предоплата. Заказ будет ждать
                подтверждения менеджера; флорист его пока не увидит. Обычно на
                оплату даётся до 60 минут с запасом 2 часа на сборку.
              </p>
              <label className="draft-check">
                <input
                  type="checkbox"
                  checked={without}
                  onChange={(e) => setWithout(e.target.checked)}
                />
                Подтвердить без предоплаты
              </label>
              {without ? (
                <label>
                  Причина подтверждения
                  <input
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    maxLength={1000}
                  />
                </label>
              ) : (
                <label>
                  Срок оплаты для срочного заказа{" "}
                  <small>Необязательно · местное время вашего устройства</small>
                  <input
                    type="datetime-local"
                    value={deadline}
                    onChange={(e) => setDeadline(e.target.value)}
                  />
                </label>
              )}
            </>
          ) : (
            <p>
              Самовывоз без обязательной предоплаты: после создания заказ сразу
              появится у флориста.
            </p>
          )}
        </fieldset>
        <div className="draft-actions">
          <span>
            {dirty
              ? "Есть несохранённые правки"
              : `Сохранённая версия ${version}`}
          </span>
          <button className="btn" disabled={busy || conflict}>
            Сохранить черновик
          </button>
          <button
            type="button"
            className="btn primary"
            disabled={
              busy ||
              conflict ||
              !fields.items.length ||
              (courier && without && !reason.trim())
            }
            onClick={() => void act(true)}
          >
            {busy
              ? "Сохраняем…"
              : courier && !without
                ? "Создать заказ · ждёт подтверждения"
                : "Создать заказ"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
