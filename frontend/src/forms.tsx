import { useEffect, useRef, useState, type FormEvent } from "react";
import { Plus, Trash2 } from "lucide-react";
import { businessPath, errorText, price, request, ApiError } from "./api";
import { Modal, Notice, Pager } from "./components";
import { useRemote } from "./hooks";
import type {
  Business,
  Customer,
  CustomerProfile,
  ShopSettings,
  Order,
  Page,
  Product,
} from "./types";

type FormProps = { business: Business; close: () => void; saved: () => void };

export function CustomerForm({ business, close, saved }: FormProps) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      await request(businessPath(business.id, "customers"), {
        method: "POST",
        body: JSON.stringify({
          name: data.get("name"),
          phone: data.get("phone"),
          notes: data.get("notes"),
          consent: data.get("consent") === "on",
        }),
      });
      saved();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Новый клиент" close={close} busy={busy}>
      <form onSubmit={submit}>
        <div className="modal-body stack">
          {error && <Notice>{error}</Notice>}
          <label>
            Имя клиента
            <input
              name="name"
              required
              maxLength={150}
              autoFocus
              placeholder="Имя и фамилия"
            />
          </label>
          <label>
            Телефон
            <input
              name="phone"
              type="tel"
              required
              defaultValue="+996"
              maxLength={40}
            />
          </label>
          <label>
            Заметка
            <textarea
              name="notes"
              maxLength={2000}
              placeholder="Предпочтения клиента"
            />
          </label>
          <label className="checkbox">
            <input name="consent" type="checkbox" />
            Клиент согласился получать сообщения
          </label>
        </div>
        <footer className="modal-footer">
          <button type="button" onClick={close} disabled={busy}>
            Отмена
          </button>
          <button className="primary" disabled={busy}>
            {busy ? "Сохраняем…" : "Сохранить клиента"}
          </button>
        </footer>
      </form>
    </Modal>
  );
}

export function ProductForm({
  business,
  close,
  saved,
  initial,
}: FormProps & { initial?: Product }) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      await request(
        businessPath(
          business.id,
          initial ? `products/${initial.id}` : "products",
        ),
        {
          method: initial ? "PUT" : "POST",
          body: JSON.stringify({
            name: data.get("name"),
            price: data.get("price"),
            ...(initial
              ? { version: initial.version, active: initial.active }
              : {}),
          }),
        },
      );
      saved();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={initial ? "Изменение позиции прайса" : "Новая позиция прайса"}
      close={close}
      busy={busy}
    >
      <form onSubmit={submit}>
        <div className="modal-body stack">
          {error && <Notice>{error}</Notice>}
          <label>
            Название
            <input
              autoFocus
              required
              name="name"
              defaultValue={initial?.name}
              maxLength={200}
              placeholder="Например, букет дня"
            />
          </label>
          <label>
            Цена, сом
            <input
              required
              defaultValue={initial?.price}
              name="price"
              type="number"
              min="0"
              max="9999999999.99"
              step="0.01"
              placeholder="2500"
            />
          </label>
        </div>
        <footer className="modal-footer">
          <button type="button" onClick={close} disabled={busy}>
            Отмена
          </button>
          <button className="primary" disabled={busy}>
            {busy
              ? "Сохраняем…"
              : initial
                ? "Сохранить позицию"
                : "Добавить позицию"}
          </button>
        </footer>
      </form>
    </Modal>
  );
}

export function OrderForm({
  business,
  close,
  saved,
  initial,
  initialCustomer,
}: FormProps & { initial?: Order; initialCustomer?: Customer }) {
  const [customers, setCustomers] = useState<Page<Customer>>({
    count: 0,
    results: [],
  });
  const [products, setProducts] = useState<Page<Product>>({
    count: 0,
    results: [],
  });
  const [query, setQuery] = useState(""),
    [customerOffset, setCustomerOffset] = useState(0),
    [productOffset, setProductOffset] = useState(0);
  const [customer, setCustomer] = useState<Customer | null>(
    initial
      ? {
          id: initial.customer_id,
          name: initial.customer_name,
          phone: initial.customer_phone,
          notes: "",
          consent: false,
        }
      : initialCustomer || null,
  );
  const [recipient, setRecipient] = useState(
      initial?.recipient_name || initialCustomer?.name || "",
    ),
    [fulfillment, setFulfillment] = useState(initial?.fulfillment || "pickup");
  const [lines, setLines] = useState<{ product: Product; quantity: number }[]>(
    initial?.lines.map((line) => ({
      product: { id: line.product_id, name: line.name, price: line.unit_price },
      quantity: line.quantity,
    })) || [],
  );
  const [recipientPhone, setRecipientPhone] = useState(
    initial?.recipient_phone || "",
  );
  const [address, setAddress] = useState(initial?.address || "");
  const [windowStart, setWindowStart] = useState(
    initial?.window_start.slice(0, 5) || "10:00",
  );
  const [windowEnd, setWindowEnd] = useState(
    initial?.window_end.slice(0, 5) || "12:00",
  );
  const settings = useRemote<ShopSettings>(
    businessPath(business.id, "settings"),
  );
  const profile = useRemote<CustomerProfile>(
    customer ? businessPath(business.id, `customers/${customer.id}`) : null,
  );
  const [productId, setProductId] = useState("");
  const [quickName, setQuickName] = useState("");
  const [quickPhone, setQuickPhone] = useState("");
  async function createCustomerHere() {
    setBusy(true);
    setError("");
    try {
      const created = await request<Customer>(
        businessPath(business.id, "customers"),
        {
          method: "POST",
          body: JSON.stringify({ name: quickName, phone: quickPhone }),
        },
      );
      setCustomer(created);
      setQuery(created.name);
      if (!recipient) setRecipient(created.name);
      setQuickName("");
      setQuickPhone("");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [optionError, setOptionError] = useState(""),
    [customerLoading, setCustomerLoading] = useState(true),
    [productLoading, setProductLoading] = useState(true);
  const [uncertain, setUncertain] = useState(false);
  // Preserve both key and payload after a transport failure: the first request may have committed.
  const attempt = useRef<{ key: string; body: string } | null>(null);
  useEffect(() => {
    const abort = new AbortController();
    setCustomerLoading(true);
    setOptionError("");
    const timer = setTimeout(
      () =>
        request<Page<Customer>>(
          businessPath(business.id, "customers") +
            `?limit=10&offset=${customerOffset}&search=${encodeURIComponent(query)}`,
          { signal: abort.signal },
        )
          .then(setCustomers)
          .catch((e) => {
            if (!abort.signal.aborted) setOptionError(errorText(e));
          })
          .finally(() => {
            if (!abort.signal.aborted) setCustomerLoading(false);
          }),
      200,
    );
    return () => {
      clearTimeout(timer);
      abort.abort();
    };
  }, [business.id, query, customerOffset]);
  useEffect(() => {
    const abort = new AbortController();
    setProductLoading(true);
    request<Page<Product>>(
      businessPath(business.id, "products") +
        `?limit=20&offset=${productOffset}`,
      { signal: abort.signal },
    )
      .then((data) => {
        setProducts(data);
        setProductId(data.results[0]?.id || "");
      })
      .catch((e) => {
        if (!abort.signal.aborted) setOptionError(errorText(e));
      })
      .finally(() => {
        if (!abort.signal.aborted) setProductLoading(false);
      });
    return () => abort.abort();
  }, [business.id, productOffset]);
  const today = new Intl.DateTimeFormat("en-CA", {
    timeZone: business.timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
  const [deliveryDate, setDeliveryDate] = useState(
    initial?.delivery_date || today,
  );
  const deliveryFee =
    fulfillment === "pickup"
      ? 0
      : initial &&
          deliveryDate === initial.delivery_date &&
          windowStart === initial.window_start.slice(0, 5) &&
          windowEnd === initial.window_end.slice(0, 5) &&
          fulfillment === initial.fulfillment
        ? Number(initial.delivery_fee)
        : Number(
            settings.data?.windows.find(
              (w) => w.start === windowStart && w.end === windowEnd,
            )?.price || 0,
          );
  function addLine() {
    const product = products.results.find((p) => p.id === productId);
    if (!product) return;
    setLines((current) =>
      current.some((line) => line.product.id === product.id)
        ? current.map((line) =>
            line.product.id === product.id
              ? { ...line, quantity: Math.min(999, line.quantity + 1) }
              : line,
          )
        : [...current, { product, quantity: 1 }],
    );
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!attempt.current) {
      if (!customer || !lines.length) {
        setError(
          !customer
            ? "Нажмите на найденного клиента, чтобы выбрать его, или создайте нового ниже."
            : "Добавьте товар кнопкой «Добавить в заказ» в разделе состава.",
        );
        return;
      }
      const data = new FormData(event.currentTarget);
      attempt.current = {
        key: crypto.randomUUID(),
        body: JSON.stringify({
          ...(initial ? { version: initial.version } : {}),
          customer_id: customer.id,
          items: lines.map((line) => ({
            product_id: line.product.id,
            quantity: line.quantity,
          })),
          recipient_name: recipient,
          recipient_phone: data.get("recipient_phone"),
          fulfillment,
          delivery_date: data.get("delivery_date"),
          occasion: data.get("occasion"),
          source: data.get("source"),
          relation: data.get("relation"),
          window_start: data.get("window_start"),
          window_end: data.get("window_end"),
          address: data.get("address") || "",
          notes: data.get("notes"),
          card: data.get("card"),
        }),
      };
    }
    setBusy(true);
    setError("");
    try {
      await request<Order>(
        businessPath(
          business.id,
          initial ? `orders/${initial.id}/edit` : "orders",
        ),
        {
          method: initial ? "PUT" : "POST",
          body: attempt.current.body,
          headers: { "Idempotency-Key": attempt.current.key },
        },
      );
      saved();
    } catch (e) {
      const unknown =
        !(e instanceof ApiError) || e.status === 0 || e.status >= 500;
      setUncertain(unknown);
      if (!unknown) attempt.current = null;
      setError(
        unknown
          ? "Ответ сервера не получен. Повторите сохранение — повторный запрос не создаст второй заказ."
          : errorText(e),
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={
        initial ? `Редактирование заказа №${initial.number}` : "Новый заказ"
      }
      close={close}
      busy={busy || uncertain}
    >
      <form onSubmit={submit}>
        <div className="modal-body stack">
          {error && <Notice>{error}</Notice>}
          {optionError && <Notice>{optionError}</Notice>}
          {(settings.error || profile.error) && (
            <Notice>{settings.error || profile.error}</Notice>
          )}
          <fieldset disabled={busy || uncertain} className="stack">
            <div>
              <h3>Клиент</h3>
              <label>
                Поиск по имени или телефону
                <input
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setCustomerOffset(0);
                  }}
                  placeholder="Найти клиента"
                />
              </label>
              <div className="customer-options" aria-busy={customerLoading}>
                {customerLoading ? (
                  <p className="muted">Ищем…</p>
                ) : (
                  customers.results.map((c) => (
                    <button
                      type="button"
                      key={c.id}
                      className={customer?.id === c.id ? "selected" : ""}
                      onClick={() => {
                        setCustomer(c);
                        if (!recipient) setRecipient(c.name);
                      }}
                    >
                      {c.name}
                      <span>{c.phone}</span>
                    </button>
                  ))
                )}
                {!customerLoading && !customers.count && (
                  <p className="muted">
                    Клиенты не найдены. Добавьте клиента в разделе «Клиенты».
                  </p>
                )}
              </div>
              {customers.count > 10 && (
                <Pager
                  count={customers.count}
                  offset={customerOffset}
                  setOffset={setCustomerOffset}
                  limit={10}
                />
              )}
              <details>
                <summary>Новый клиент — создать прямо в заказе</summary>
                <div className="form-grid">
                  <label>
                    Имя нового клиента
                    <input
                      value={quickName}
                      onChange={(e) => setQuickName(e.target.value)}
                    />
                  </label>
                  <label>
                    Телефон нового клиента
                    <input
                      type="tel"
                      value={quickPhone}
                      onChange={(e) => setQuickPhone(e.target.value)}
                    />
                  </label>
                </div>
                <button
                  type="button"
                  disabled={busy || !quickName || !quickPhone}
                  onClick={createCustomerHere}
                >
                  Создать и выбрать клиента
                </button>
              </details>
              {customer && (
                <p className="selection">
                  Выбран: {customer.name} · {customer.phone}
                </p>
              )}
            </div>
            <div>
              <h3>Состав заказа</h3>
              <div className="add-line">
                <label>
                  Позиция прайса
                  <select
                    aria-label="Позиция прайса"
                    disabled={productLoading}
                    value={productId}
                    onChange={(e) => setProductId(e.target.value)}
                  >
                    {products.results.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} · {price(p.price)}
                      </option>
                    ))}
                    {!products.results.length && (
                      <option value="">
                        Добавьте товары в разделе «Прайс»
                      </option>
                    )}
                  </select>
                </label>
                <button
                  type="button"
                  onClick={addLine}
                  disabled={!productId || productLoading || lines.length >= 50}
                  aria-label="Добавить в заказ"
                >
                  <Plus size={18} /> Добавить в заказ
                </button>
              </div>
              {products.count > 20 && (
                <Pager
                  count={products.count}
                  offset={productOffset}
                  setOffset={setProductOffset}
                  limit={20}
                />
              )}
              {lines.map((line) => (
                <div className="order-line" key={line.product.id}>
                  <span>
                    {line.product.name}
                    <small>{price(line.product.price)} за шт.</small>
                  </span>
                  <input
                    aria-label={`Количество ${line.product.name}`}
                    type="number"
                    min="1"
                    max="999"
                    step="1"
                    required
                    value={line.quantity}
                    onChange={(e) =>
                      setLines((current) =>
                        current.map((l) =>
                          l.product.id === line.product.id
                            ? { ...l, quantity: Number(e.target.value) }
                            : l,
                        ),
                      )
                    }
                  />
                  <button
                    type="button"
                    className="icon-button"
                    aria-label={`Убрать ${line.product.name}`}
                    onClick={() =>
                      setLines((current) =>
                        current.filter((l) => l.product.id !== line.product.id),
                      )
                    }
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
            {profile.data && profile.data.recipients.length > 0 && (
              <label>
                Получатель из карточки
                <select
                  aria-label="Получатель из карточки"
                  defaultValue=""
                  onChange={(e) => {
                    const r = profile.data?.recipients.find(
                      (r) => r.id === e.target.value,
                    );
                    if (r) {
                      setRecipient(r.name);
                      setRecipientPhone(r.phone);
                      setAddress(r.address);
                    }
                  }}
                >
                  <option value="">Указать вручную</option>
                  {profile.data.recipients.map((r) => (
                    <option value={r.id} key={r.id}>
                      {r.name} · {r.relation}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {settings.data && (
              <label>
                Окно магазина
                <select
                  aria-label="Окно магазина"
                  value={`${windowStart}|${windowEnd}`}
                  onChange={(e) => {
                    const [start, end] = e.target.value.split("|");
                    if (start && end) {
                      setWindowStart(start);
                      setWindowEnd(end);
                    }
                  }}
                >
                  <option value={`${windowStart}|${windowEnd}`}>
                    {windowStart}–{windowEnd}
                  </option>
                  {settings.data.windows
                    .filter(
                      (w) => w.start !== windowStart || w.end !== windowEnd,
                    )
                    .map((w) => (
                      <option
                        key={`${w.start}|${w.end}`}
                        value={`${w.start}|${w.end}`}
                      >
                        {w.start}–{w.end}
                      </option>
                    ))}
                </select>
              </label>
            )}
            <div className="form-grid">
              <label>
                Получатель
                <input
                  required
                  maxLength={150}
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                />
              </label>
              <label>
                Телефон получателя
                <input
                  value={recipientPhone}
                  onChange={(e) => setRecipientPhone(e.target.value)}
                  name="recipient_phone"
                  type="tel"
                  maxLength={40}
                  placeholder="+996"
                />
              </label>
              <label>
                Получение
                <select
                  aria-label="Получение"
                  value={fulfillment}
                  onChange={(e) =>
                    setFulfillment(e.target.value as "pickup" | "courier")
                  }
                >
                  <option value="pickup">Самовывоз</option>
                  <option value="courier">Доставка курьером</option>
                </select>
              </label>
              <label>
                Дата
                <input
                  name="delivery_date"
                  type="date"
                  required
                  value={deliveryDate}
                  onChange={(e) => setDeliveryDate(e.target.value)}
                />
              </label>
              <label>
                Время с
                <input
                  type="time"
                  name="window_start"
                  value={windowStart}
                  onChange={(e) => setWindowStart(e.target.value)}
                  required
                />
              </label>
              <label>
                Время до
                <input
                  type="time"
                  name="window_end"
                  value={windowEnd}
                  onChange={(e) => setWindowEnd(e.target.value)}
                  required
                />
              </label>
            </div>
            {fulfillment === "courier" && (
              <label>
                Адрес доставки
                <input
                  name="address"
                  required
                  maxLength={500}
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                />
              </label>
            )}
            <div className="fgrid">
              {(
                [
                  [
                    "relation",
                    "Кто это клиенту",
                    [
                      "себе",
                      "мама",
                      "супруга",
                      "девушка",
                      "коллега",
                      "офис",
                      "друг",
                    ],
                  ],
                  [
                    "occasion",
                    "Повод",
                    [
                      "День рождения",
                      "Просто так",
                      "Годовщина",
                      "Выписка из роддома",
                      "Извинения",
                      "Свадьба",
                      "Юбилей",
                      "Корпоративный",
                    ],
                  ],
                  [
                    "source",
                    "Источник",
                    ["WhatsApp", "Instagram", "Звонок", "Прилавок"],
                  ],
                ] as const
              ).map(([key, label, choices]) => (
                <label className="field" key={key}>
                  {label}
                  <select
                    name={key}
                    defaultValue={
                      initial?.[key] ||
                      (key === "source" ? customer?.source : "") ||
                      ""
                    }
                  >
                    <option value="">Не указан</option>
                    {Array.from(
                      new Set([
                        ...choices,
                        initial?.[key] || "",
                        key === "source" ? customer?.source || "" : "",
                      ]),
                    )
                      .filter(Boolean)
                      .map((value) => (
                        <option key={value}>{value}</option>
                      ))}
                  </select>
                </label>
              ))}
            </div>
            <label>
              Текст открытки
              <textarea
                name="card"
                maxLength={1000}
                defaultValue={initial?.card}
              />
            </label>
            <label>
              Заметка к заказу
              <textarea
                name="notes"
                maxLength={2000}
                defaultValue={initial?.notes}
              />
            </label>
          </fieldset>
        </div>
        <footer className="modal-footer">
          <span className="total">
            {deliveryFee > 0 && (
              <small className="delivery-price">
                Доставка: {price(deliveryFee)}
              </small>
            )}
            Итого:{" "}
            {price(
              lines.reduce(
                (sum, line) =>
                  sum +
                  Math.round(Number(line.product.price) * 100) * line.quantity,
                0,
              ) /
                100 +
                deliveryFee,
            )}
          </span>
          <button type="button" disabled={busy || uncertain} onClick={close}>
            Отмена
          </button>
          <button className="primary" disabled={busy}>
            {busy
              ? "Сохраняем…"
              : uncertain
                ? "Повторить сохранение"
                : initial
                  ? "Сохранить изменения"
                  : "Создать заказ"}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
