import { useEffect, useRef, useState } from "react";
import {
  Bell,
  Volume2,
  VolumeX,
  Pencil,
  Trash2,
  Plus,
  QrCode,
} from "lucide-react";
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
type Summary = {
  waiting: number;
  unread: number;
  latest_inbound_id: string;
  items: { id: string; chat_id: string; name: string; text: string }[];
};
export function useChatNotifications(
  businessId: string | null,
  userId: string,
  activeChat: string | null,
) {
  const [waiting, setWaiting] = useState(0),
    [toast, setToast] = useState<Summary["items"][number] | null>(null);
  const [sound, setSound] = useState(false);
  const audio = useRef<AudioContext | null>(null),
    soundRef = useRef(sound),
    activeRef = useRef(activeChat);
  soundRef.current = sound;
  activeRef.current = activeChat;
  useEffect(() => {
    setWaiting(0);
    setToast(null);
    if (!businessId) return;
    let cancelled = false;
    let cursor = "0";
    let initialized = false;
    let unread = 0,
      blink = false;
    let timer: number;
    const controller = new AbortController();
    const title = document.title;
    async function poll() {
      try {
        const data = await request<Summary>(
          businessPath(businessId!, "chats/summary") + `?after=${cursor}`,
          { signal: controller.signal },
        );
        if (cancelled) return;
        setWaiting(data.waiting);
        unread = data.unread;
        document.title = (unread ? `(${unread}) ` : "") + title;
        const item = data.items.find(
          (i) => i.chat_id !== activeRef.current || document.hidden,
        );
        if (initialized && item) {
          setToast(item);
          if (soundRef.current && audio.current) {
            const oscillator = audio.current.createOscillator(),
              gain = audio.current.createGain();
            oscillator.connect(gain);
            gain.connect(audio.current.destination);
            gain.gain.setValueAtTime(0.06, audio.current.currentTime);
            gain.gain.exponentialRampToValueAtTime(
              0.001,
              audio.current.currentTime + 0.25,
            );
            oscillator.frequency.value = 700;
            oscillator.start();
            oscillator.stop(audio.current.currentTime + 0.25);
          }
        }
        if (BigInt(data.latest_inbound_id) > BigInt(cursor))
          cursor = data.latest_inbound_id;
        initialized = true;
      } catch {
        /* Next poll retries without clearing the unread count. */
      } finally {
        if (!cancelled)
          timer = window.setTimeout(
            () => void poll(),
            document.hidden ? 60000 : 10000,
          );
      }
    }
    const titleTimer = window.setInterval(() => {
      blink = !blink;
      document.title =
        (unread && (!document.hidden || blink) ? `(${unread}) ` : "") + title;
    }, 1000);
    void poll();
    return () => {
      cancelled = true;
      controller.abort();
      clearTimeout(timer);
      clearInterval(titleTimer);
      document.title = title;
    };
  }, [businessId, userId]);
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 8000);
    return () => clearTimeout(timer);
  }, [toast]);
  function toggle() {
    if (!sound) {
      audio.current ??= new AudioContext();
      void audio.current.resume();
    }
    setSound((v) => !v);
  }
  return { waiting, toast, dismiss: () => setToast(null), sound, toggle };
}
export function ChatNotificationControls({
  state,
  open,
}: {
  state: ReturnType<typeof useChatNotifications>;
  open: (id: string) => void;
}) {
  return (
    <>
      <button
        className="chat-icon"
        aria-label={
          state.sound ? "Выключить звук чатов" : "Включить звук чатов"
        }
        title={state.sound ? "Звук чатов включён" : "Включить звук чатов"}
        onClick={state.toggle}
      >
        {state.sound ? <Volume2 size={18} /> : <VolumeX size={18} />}
      </button>
      {state.toast && (
        <div role="status" className="chat-toast">
          <Bell size={18} />
          <button
            onClick={() => {
              open(state.toast!.chat_id);
              state.dismiss();
            }}
          >
            <strong>{state.toast.name}</strong>
            <span>{state.toast.text}</span>
          </button>
          <button aria-label="Закрыть уведомление" onClick={state.dismiss}>
            ×
          </button>
        </div>
      )}
    </>
  );
}
