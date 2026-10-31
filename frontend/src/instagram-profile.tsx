import { useState, type Ref } from "react";
import {
  CalendarDays,
  ClipboardList,
  Plus,
  ShoppingBag,
  X,
} from "lucide-react";
import { price } from "./api";
import { Modal } from "./components";
import { Avatar, shortDate } from "./ui";
import { newUuid } from "./uuid";
import type {
  InstagramPreviewChat,
  InstagramPreviewOrder,
} from "./instagram-preview";
import "./instagram-profile.css";

type Editor =
  | { kind: "customer" }
  | { kind: "draft" | "order" }
  | { kind: "view"; order: InstagramPreviewOrder };

export function InstagramProfile({
  chat,
  panelRef,
  open,
  close,
  change,
}: {
  chat: InstagramPreviewChat;
  panelRef?: Ref<HTMLElement>;
  open: boolean;
  close: () => void;
  change: (patch: Partial<InstagramPreviewChat>) => void;
}) {
  const [name, setName] = useState("");
  const [editor, setEditor] = useState<Editor | null>(null);
  const orders = chat.orders || [];
  return (
    <>
      <aside
        ref={panelRef}
        className={`ig-profile ig-customer-panel ${open ? "is-open" : ""}`}
        aria-label="Клиент в Instagram"
      >
        <header>
          <h2>Клиент</h2>
          <button
            className="chat-icon"
            aria-label="Закрыть карточку Instagram"
            onClick={close}
          >
            <X size={19} />
          </button>
        </header>
        <div className="chat-profile-card">
          <Avatar name={chat.name} />
          <h3>{chat.name}</h3>
          <p className="ig-customer-handle">@{chat.handle}</p>
          <div className="chat-tags">
            {chat.tags.map((tag) => (
              <span key={tag}>{tag}</span>
            ))}
          </div>
          <button
            className="btn"
            onClick={() => setEditor({ kind: "customer" })}
          >
            Открыть карточку
          </button>
        </div>
        {chat.nameConfirmed === false && (
          <form
            className="chat-name-card"
            onSubmit={(e) => {
              e.preventDefault();
              if (!name.trim()) return;
              change({
                name: name.trim(),
                nameConfirmed: true,
                tags: chat.tags.filter((tag) => tag !== "Новый клиент"),
              });
            }}
          >
            <span className="chat-mini ig-source-tag">
              Новый клиент · из Instagram
            </span>
            <h3>Как зовут клиента?</h3>
            <p>
              Ник профиля уже сохранён. Уточните имя, чтобы быстрее найти
              клиента в следующий раз.
            </p>
            <input
              aria-label="Имя клиента Instagram"
              required
              maxLength={150}
              placeholder={chat.name}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <button className="btn primary" disabled={!name.trim()}>
              Сохранить имя
            </button>
          </form>
        )}
        <section
          className="chat-profile-card ig-draft-card"
          aria-label="Черновик заказа в Instagram"
        >
          <h3>
            <ClipboardList size={18} />
            Черновик заказа
          </h3>
          {chat.draft ? (
            <>
              <p className="ig-order-description">{chat.draft.description}</p>
              <OrderDetails order={chat.draft} />
              <button
                className="btn primary"
                onClick={() => setEditor({ kind: "draft" })}
              >
                Открыть черновик
              </button>
            </>
          ) : (
            <>
              <p>Заполняет менеджер</p>
              <p>
                Сохраняйте состав, время и пожелания по ходу переписки. Заказ
                появится после подтверждения формы.
              </p>
              <button
                className="btn primary"
                onClick={() => setEditor({ kind: "draft" })}
              >
                <Plus size={16} />
                Создать черновик
              </button>
            </>
          )}
        </section>
        <section
          className="chat-profile-card"
          aria-label="Заказы клиента Instagram"
        >
          <h3>
            <ShoppingBag size={17} />
            Заказы <span>{orders.length}</span>
          </h3>
          {!orders.length && <p>Заказов пока нет</p>}
          {orders.map((order, index) => (
            <button
              key={order.id}
              className="ig-order-link"
              onClick={() => setEditor({ kind: "view", order })}
            >
              <strong>№{index + 1}</strong>
              <span>{order.description}</span>
              {order.amount && <b>{price(order.amount)}</b>}
            </button>
          ))}
          <button
            className="btn primary"
            onClick={() => setEditor({ kind: "order" })}
          >
            Создать заказ
          </button>
          <button
            className="btn"
            disabled
            title="Отправка QR станет доступна после подключения Instagram"
          >
            Отправить QR для оплаты
          </button>
        </section>
        <section className="chat-profile-card">
          <h3>
            <CalendarDays size={17} />
            Важные даты
          </h3>
          <p>Пока не добавлены</p>
        </section>
        <section className="chat-profile-card">
          <h3>Заметки</h3>
          <p className="chat-notes">
            {chat.note || "Здесь появятся заметки из карточки клиента."}
          </p>
        </section>
        <p className="ig-profile-example">Карточка и заказы — часть примера.</p>
      </aside>
      {editor?.kind === "customer" && (
        <CustomerEditor
          chat={chat}
          close={() => setEditor(null)}
          save={(patch) => {
            change(patch);
            setEditor(null);
          }}
        />
      )}
      {(editor?.kind === "draft" || editor?.kind === "order") && (
        <OrderEditor
          mode={editor.kind}
          initial={chat.draft}
          close={() => setEditor(null)}
          save={(order) => {
            change(
              editor.kind === "draft"
                ? { draft: order }
                : {
                    orders: [...orders, { ...order, id: newUuid() }],
                    draft: undefined,
                  },
            );
            setEditor(null);
          }}
        />
      )}
      {editor?.kind === "view" && (
        <Modal title="Заказ в примере Instagram" close={() => setEditor(null)}>
          <div className="modal-body ig-profile-editor">
            <p>{editor.order.description}</p>
            <OrderDetails order={editor.order} />
            <p className="muted">
              Это пример. Настоящий заказ в CRM не создавался.
            </p>
            <button className="primary" onClick={() => setEditor(null)}>
              Понятно
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}

function OrderDetails({ order }: { order: InstagramPreviewOrder }) {
  return (
    <dl className="ig-order-details">
      {order.date && (
        <div>
          <dt>Дата</dt>
          <dd>{shortDate(order.date)}</dd>
        </div>
      )}
      {order.time && (
        <div>
          <dt>Время</dt>
          <dd>{order.time}</dd>
        </div>
      )}
      {order.amount && (
        <div>
          <dt>Сумма</dt>
          <dd>{price(order.amount)}</dd>
        </div>
      )}
    </dl>
  );
}

function CustomerEditor({
  chat,
  close,
  save,
}: {
  chat: InstagramPreviewChat;
  close: () => void;
  save: (patch: Partial<InstagramPreviewChat>) => void;
}) {
  const [name, setName] = useState(chat.name);
  const [note, setNote] = useState(chat.note);
  return (
    <Modal title="Карточка клиента Instagram" close={close}>
      <form
        className="modal-body ig-profile-editor"
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim())
            save({
              name: name.trim(),
              note,
              nameConfirmed: true,
              tags: chat.tags.filter((tag) => tag !== "Новый клиент"),
            });
        }}
      >
        <p className="muted">Изменения останутся только в этом примере.</p>
        <label>
          Имя клиента
          <input
            autoFocus
            required
            maxLength={150}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label>
          Instagram
          <input readOnly value={`@${chat.handle}`} />
        </label>
        <label>
          Заметки
          <textarea
            rows={4}
            maxLength={2000}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </label>
        <button className="primary" type="submit" disabled={!name.trim()}>
          Сохранить карточку
        </button>
      </form>
    </Modal>
  );
}

function OrderEditor({
  mode,
  initial,
  close,
  save,
}: {
  mode: "draft" | "order";
  initial?: InstagramPreviewOrder;
  close: () => void;
  save: (order: InstagramPreviewOrder) => void;
}) {
  const [value, setValue] = useState<InstagramPreviewOrder>(
    () =>
      initial || {
        id: newUuid(),
        description: "",
        date: "",
        time: "",
        amount: "",
      },
  );
  const field = (key: keyof InstagramPreviewOrder, text: string) =>
    setValue((old) => ({ ...old, [key]: text }));
  return (
    <Modal
      title={mode === "draft" ? "Черновик заказа" : "Создать заказ"}
      close={close}
    >
      <form
        className="modal-body ig-profile-editor"
        onSubmit={(e) => {
          e.preventDefault();
          const fields = new FormData(e.currentTarget);
          if (value.description.trim())
            save({
              ...value,
              description: value.description.trim(),
              date: String(fields.get("date") || ""),
              time: String(fields.get("time") || ""),
            });
        }}
      >
        <p className="muted">Это пример. Настоящий заказ в CRM не создаётся.</p>
        <label>
          Состав и пожелания
          <textarea
            autoFocus
            required
            maxLength={2000}
            rows={4}
            placeholder="Например, нежный букет до 5 000 сом, открытка для мамы"
            value={value.description}
            onChange={(e) => field("description", e.target.value)}
          />
        </label>
        <div className="ig-order-fields">
          <label>
            Дата
            <input type="date" name="date" defaultValue={value.date} />
          </label>
          <label>
            Время
            <input type="time" name="time" defaultValue={value.time} />
          </label>
        </div>
        <label>
          Сумма, сом
          <input
            type="number"
            min="0"
            max="99999999"
            step="0.01"
            placeholder="Не указана"
            value={value.amount}
            onChange={(e) => field("amount", e.target.value)}
          />
        </label>
        <button
          className="primary"
          type="submit"
          disabled={!value.description.trim()}
        >
          {mode === "draft" ? "Сохранить черновик" : "Добавить заказ в пример"}
        </button>
      </form>
    </Modal>
  );
}
