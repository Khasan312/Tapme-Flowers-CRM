import { useEffect, useRef, useState } from "react";
import { Pencil, Trash2, Plus, QrCode } from "lucide-react";
import { businessPath, errorText, price, request } from "./api";
import { Modal, Notice } from "./components";
import { useRemote } from "./hooks";
import { newUuid } from "./uuid";
import type { PaymentSettings, QuickReply } from "./chat-types";

export function PaymentDialog({
  businessId,
  chatId,
  close,
  sent,
}: {
  businessId: string;
  chatId: string;
  close: () => void;
  sent: () => void;
}) {
  const path = businessPath(businessId, `chats/${chatId}/payment-qr`);
  const remote = useRemote<
    PaymentSettings & {
      orders: { id: string; number: number; amount: string }[];
    }
  >(path);
  const [order, setOrder] = useState<string | null>(null),
    [amount, setAmount] = useState<string | null>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const requestId = useRef(newUuid());
  const data = remote.data;
  const selected = order ?? data?.orders[0]?.id ?? "";
  const sum =
    amount ?? data?.orders.find((o) => o.id === selected)?.amount ?? "";
  return (
    <Modal title="Отправить QR для оплаты" close={close} busy={busy}>
      <form
        className="modal-body stack"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            await request(path, {
              method: "POST",
              body: JSON.stringify({
                amount: sum,
                order_id: selected || null,
                request_id: requestId.current,
              }),
            });
            sent();
            close();
          } catch (e) {
            setError(errorText(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        {(error || remote.error) && <Notice>{error || remote.error}</Notice>}
        {data && (
          <>
            {data.image_url ? (
              <img
                className="chat-payment-image"
                src={`${data.image_url}?v=${data.version}`}
                alt="QR для оплаты"
              />
            ) : (
              <Notice>
                Владелец ещё не загрузил QR. Добавьте его в «Настройки →
                Каналы».
              </Notice>
            )}
            <p className="muted">{data.note}</p>
            <label>
              Заказ
              <select
                value={selected}
                onChange={(e) => {
                  setOrder(e.target.value);
                  setAmount(null);
                  requestId.current = newUuid();
                }}
              >
                <option value="">Без привязки к заказу</option>
                {data.orders.map((o) => (
                  <option key={o.id} value={o.id}>
                    №{o.number} · осталось {price(o.amount)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Сумма к оплате, сом
              <input
                type="number"
                required
                min="0.01"
                step="0.01"
                max="9999999999.99"
                value={sum}
                onChange={(e) => {
                  setAmount(e.target.value);
                  requestId.current = newUuid();
                }}
              />
            </label>
            <div className="chat-payment-preview">
              {data.text
                .replaceAll(
                  "{номер}",
                  String(
                    data.orders.find((o) => o.id === selected)?.number ?? "—",
                  ),
                )
                .replaceAll("{сумма}", sum || "…")}
            </div>
            <small>
              QR не подтверждает оплату. После получения денег внесите оплату в
              заказ.
            </small>
            <button
              className="btn primary"
              disabled={busy || !data.image_url || !sum}
            >
              <QrCode size={16} />
              {busy ? "Отправляем…" : "Отправить QR"}
            </button>
          </>
        )}
      </form>
    </Modal>
  );
}
export function QuickReplies({
  businessId,
  insert,
  close,
}: {
  businessId: string;
  insert: (text: string) => void;
  close: () => void;
}) {
  const [revision, setRevision] = useState(0),
    [edit, setEdit] = useState<QuickReply | null | undefined>(undefined);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const replies = useRemote<QuickReply[]>(
    businessPath(businessId, "quick-replies"),
    revision,
  );
  const [deleting, setDeleting] = useState<QuickReply | null>(null);
  async function remove(row: QuickReply) {
    setBusy(true);
    try {
      await request(businessPath(businessId, `quick-replies/${row.id}`), {
        method: "DELETE",
        body: JSON.stringify({ version: row.version }),
      });
      setRevision((r) => r + 1);
      setDeleting(null);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Быстрые ответы" close={close} busy={busy}>
      <div className="modal-body stack">
        {(error || replies.error) && <Notice>{error || replies.error}</Notice>}
        <p className="muted">
          Выберите ответ, чтобы вставить его в поле сообщения. Отправку
          подтверждаете вы.
        </p>
        {replies.data?.map((r) => (
          <div className="chat-quick-row" key={r.id}>
            <button
              className="chat-quick-insert"
              onClick={() => {
                insert(r.text);
                close();
              }}
            >
              <strong>{r.title}</strong>
              <span>{r.text}</span>
            </button>
            <button
              className="chat-icon"
              aria-label={`Изменить ${r.title}`}
              onClick={() => setEdit(r)}
            >
              <Pencil size={16} />
            </button>
            <button
              className="chat-icon"
              aria-label={`Удалить ${r.title}`}
              onClick={() => setDeleting(r)}
            >
              <Trash2 size={16} />
            </button>
          </div>
        ))}
        {deleting && (
          <div className="chat-payment-preview">
            Удалить «{deleting.title}»?
            <div className="chat-button-row">
              <button
                className="btn"
                disabled={busy}
                onClick={() => setDeleting(null)}
              >
                Отмена
              </button>
              <button
                className="btn"
                disabled={busy}
                onClick={() => void remove(deleting)}
              >
                Удалить ответ
              </button>
            </div>
          </div>
        )}
        {edit !== undefined ? (
          <form
            key={edit?.id || "new"}
            className="stack"
            onSubmit={async (e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              setBusy(true);
              setError("");
              try {
                await request(
                  businessPath(
                    businessId,
                    edit ? `quick-replies/${edit.id}` : "quick-replies",
                  ),
                  {
                    method: edit ? "PATCH" : "POST",
                    body: JSON.stringify({
                      title: f.get("title"),
                      text: f.get("text"),
                      ...(edit ? { version: edit.version } : {}),
                    }),
                  },
                );
                setEdit(undefined);
                setRevision((r) => r + 1);
              } catch (e) {
                setError(errorText(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Название ответа
              <input
                name="title"
                required
                maxLength={100}
                defaultValue={edit?.title || ""}
              />
            </label>
            <label>
              Текст ответа
              <textarea
                name="text"
                required
                maxLength={4096}
                defaultValue={edit?.text || ""}
              />
            </label>
            <small>
              Можно использовать {"{имя}"} и {"{магазин}"}
            </small>
            <div className="chat-button-row">
              <button className="btn primary" disabled={busy}>
                Сохранить ответ
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => setEdit(undefined)}
              >
                Отмена
              </button>
            </div>
          </form>
        ) : (
          <button className="btn" onClick={() => setEdit(null)}>
            <Plus size={16} />
            Новый быстрый ответ
          </button>
        )}
      </div>
    </Modal>
  );
}
export {
  useChatNotifications,
  ChatNotificationControls,
} from "./chat-notifications";
