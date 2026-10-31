import { useState } from "react";
import {
  CheckCircle2,
  Circle,
  MessageCircle,
  QrCode,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { businessPath, errorText, request } from "./api";
import { Modal, Notice } from "./components";
import { useRemote } from "./hooks";
import type { Business } from "./types";
import type { AutoReply, Channel, PaymentSettings } from "./chat-types";
import "./chats.css";
import { CopyField } from "./channel-copy-field";
import { InstagramChannelSettings } from "./instagram-channel-settings";

const checklist = {
  token_checked_at: "Токен работает",
  registered_at: "Номер зарегистрирован",
  webhook_verified_at: "Вебхук подтверждён",
  subscribed_at: "Подписка на сообщения",
  last_inbound_at: "Первое входящее получено",
};
export function Channels({ business }: { business: Business }) {
  const [revision, refresh] = useState(0);
  const channel = useRemote<Channel>(
    businessPath(business.id, "channels/whatsapp"),
    revision,
    { refreshOnAppear: false },
  );
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [disconnect, setDisconnect] = useState(false);
  const owner = business.role === "owner";
  const data = channel.data;
  async function action(resource: string, body?: unknown, method = "POST") {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await request(businessPath(business.id, resource), {
        method,
        ...(body
          ? { body: body instanceof FormData ? body : JSON.stringify(body) }
          : {}),
      });
      refresh((v) => v + 1);
      setNotice("Сохранено");
      return true;
    } catch (e) {
      setError(errorText(e));
      return false;
    } finally {
      setBusy(false);
    }
  }
  if (!data)
    return <Notice>{channel.error || "Загружаем настройки канала…"}</Notice>;
  const connected = data.status === "active";
  const ready =
    connected && Object.keys(checklist).every((k) => data.checks[k]);
  return (
    <section className="chat-channel-page">
      <div className="chat-channel-intro">
        <div>
          <h2>Каналы общения</h2>
          <p>Подключите WhatsApp и Instagram — переписка появится в «Чатах».</p>
        </div>
        <span className="chat-mini">WhatsApp · Instagram</span>
      </div>
      {data.server_mode === "fake" && (
        <div className="chat-test-banner">
          <Zap size={18} />
          <span>
            <strong>Тестовый режим</strong> · Сообщения моделируются внутри CRM.
            Клиентам ничего не отправляется.
          </span>
        </div>
      )}
      {(error || channel.error) && <Notice>{error || channel.error}</Notice>}
      {notice && (
        <p role="status" className="chat-save-notice">
          {notice}
        </p>
      )}
      <div className="chat-channel-grid">
        <div className="stack">
          <article className="chat-settings-card">
            <header>
              <span className="chat-channel-logo">
                <MessageCircle size={22} />
              </span>
              <div>
                <h3>WhatsApp · номер для заказов</h3>
                <p>Подключение вручную · приложение Meta магазина</p>
              </div>
              <span className={`chat-mini ${ready ? "green" : "amber"}`}>
                {ready
                  ? "Подключён"
                  : connected
                    ? "Завершите подключение"
                    : "Не подключён"}
              </span>
            </header>
            <div className="chat-settings-body stack">
              {!data.configured && (
                <Notice>
                  Администратору нужно задать ключ шифрования и версию Meta API
                  на сервере.
                </Notice>
              )}
              {owner ? (
                <form
                  className="stack"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const form = e.currentTarget;
                    const f = new FormData(form);
                    if (
                      await action("channels/whatsapp", {
                        phone_number_id: f.get("phone_number_id"),
                        waba_id: f.get("waba_id"),
                        token: f.get("token"),
                        app_secret: f.get("app_secret"),
                        version: data.version,
                      })
                    ) {
                      (
                        form.elements.namedItem("token") as HTMLInputElement
                      ).value = "";
                      (
                        form.elements.namedItem(
                          "app_secret",
                        ) as HTMLInputElement
                      ).value = "";
                    }
                  }}
                >
                  <div className="chat-fields">
                    <label>
                      Phone Number ID
                      <input
                        name="phone_number_id"
                        defaultValue={data.phone_number_id}
                        inputMode="numeric"
                        pattern="[0-9]{5,80}"
                        required
                      />
                      <small>Meta → WhatsApp → Настройка API</small>
                    </label>
                    <label>
                      WhatsApp Business Account ID
                      <input
                        name="waba_id"
                        defaultValue={data.waba_id}
                        inputMode="numeric"
                        pattern="[0-9]{5,80}"
                        required
                      />
                      <small>Идентификатор аккаунта магазина</small>
                    </label>
                  </div>
                  <div className="chat-fields">
                    <label>
                      Access token
                      <input
                        name="token"
                        type="password"
                        autoComplete="new-password"
                        required
                        placeholder={
                          connected
                            ? "Новый токен для переподключения"
                            : "Вставьте токен доступа"
                        }
                      />
                    </label>
                    <label>
                      App Secret
                      <input
                        name="app_secret"
                        type="password"
                        autoComplete="new-password"
                        required
                        placeholder="Секрет приложения Meta"
                      />
                      <small>Meta → Настройки приложения → Основное</small>
                    </label>
                  </div>
                  <p className="chat-security">
                    <ShieldCheck size={15} /> Секреты шифруются. После
                    сохранения они не отображаются.
                  </p>
                  {data.simulator && (
                    <button
                      type="button"
                      className="btn"
                      disabled={busy}
                      onClick={(e) => {
                        const form = e.currentTarget.form!;
                        const values: Record<string, string> = {
                          phone_number_id:
                            data.phone_number_id || String(Date.now()),
                          waba_id: "987654321",
                          token: "fake-local-token",
                          app_secret: "fake-local-secret",
                        };
                        for (const [key, value] of Object.entries(values))
                          (
                            form.elements.namedItem(key) as HTMLInputElement
                          ).value = value;
                      }}
                    >
                      Заполнить тестовые данные
                    </button>
                  )}
                  <button
                    className="btn primary"
                    disabled={busy || !data.configured}
                  >
                    {busy ? "Проверяем…" : "Проверить и подключить"}
                  </button>
                </form>
              ) : (
                <p>
                  Подключать номер и менять настройки канала может владелец
                  магазина.
                </p>
              )}
              {connected && (
                <>
                  <div className="chat-channel-info">
                    <strong>
                      {data.display_name} · {data.display_phone}
                    </strong>
                    <small>
                      Качество номера: {data.quality_rating || "нет данных"}
                    </small>
                  </div>
                  {data.connection_error && (
                    <Notice>{data.connection_error}</Notice>
                  )}
                  {owner && (
                    <>
                      <h4>Приём сообщений</h4>
                      <CopyField
                        label="Callback URL"
                        value={location.origin + data.webhook_path}
                      />
                      <CopyField
                        label="Verify token"
                        value={data.verify_token || ""}
                      />
                      <p className="muted">
                        Вставьте их в Meta → WhatsApp → Конфигурация. Для
                        реальных сообщений нужен публичный HTTPS-адрес.
                      </p>
                      {!data.checks.registered_at && (
                        <form
                          className="chat-fields"
                          onSubmit={(e) => {
                            e.preventDefault();
                            const form = e.currentTarget;
                            void action("channels/whatsapp/register", {
                              pin: new FormData(form).get("pin"),
                            }).then((ok) => {
                              if (ok) form.reset();
                            });
                          }}
                        >
                          <label>
                            PIN регистрации
                            <input
                              type="password"
                              name="pin"
                              inputMode="numeric"
                              pattern="[0-9]{6}"
                              maxLength={6}
                              required
                              autoComplete="new-password"
                            />
                          </label>
                          <button className="btn" disabled={busy}>
                            Зарегистрировать номер
                          </button>
                        </form>
                      )}
                      <div className="chat-button-row">
                        <button
                          className="btn"
                          disabled={busy}
                          onClick={() =>
                            void action("channels/whatsapp/subscribe")
                          }
                        >
                          Подписать на сообщения
                        </button>
                        <button
                          className="btn"
                          disabled={busy}
                          onClick={() => void action("channels/whatsapp/check")}
                        >
                          Проверить статус
                        </button>
                      </div>
                    </>
                  )}
                  <ul className="chat-checklist">
                    {Object.entries(checklist).map(([key, label]) => (
                      <li key={key} className={data.checks[key] ? "done" : ""}>
                        {data.checks[key] ? (
                          <CheckCircle2 size={18} />
                        ) : (
                          <Circle size={18} />
                        )}{" "}
                        {label}
                      </li>
                    ))}
                  </ul>
                  {owner && (
                    <button
                      className="chat-disconnect"
                      disabled={busy}
                      onClick={() => setDisconnect(true)}
                    >
                      Отключить WhatsApp
                    </button>
                  )}
                </>
              )}
            </div>
          </article>

          {owner && data.simulator && connected && (
            <article className="chat-settings-card">
              <header>
                <Zap size={21} />
                <div>
                  <h3>Симулятор входящего сообщения</h3>
                  <p>Только тестовый режим · без отправки в WhatsApp</p>
                </div>
              </header>
              <form
                className="chat-settings-body stack"
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  void action(
                    "channels/whatsapp/simulate",
                    Object.fromEntries(f),
                  );
                }}
              >
                <div className="chat-fields">
                  <label>
                    Имя клиента
                    <input
                      name="name"
                      required
                      defaultValue="Тестовый клиент"
                    />
                  </label>
                  <label>
                    Номер клиента
                    <input
                      name="phone"
                      required
                      defaultValue="+996700555011"
                      pattern="\+[1-9][0-9]{7,14}"
                    />
                  </label>
                </div>
                <label>
                  Входящее сообщение
                  <textarea
                    name="text"
                    required
                    defaultValue="Здравствуйте! Хочу заказать букет."
                  />
                </label>
                <div className="chat-button-row">
                  <button className="btn primary" disabled={busy}>
                    Создать входящее
                  </button>
                  <button
                    type="button"
                    className="btn"
                    disabled={busy}
                    onClick={() =>
                      void action("channels/whatsapp/simulate-verify")
                    }
                  >
                    Проверить тестовый вебхук
                  </button>
                </div>
                <small>
                  Разговор появится в «Чатах» после обработки очереди, обычно до
                  10 секунд.
                </small>
              </form>
            </article>
          )}
        </div>
        <div className="stack">
          <InstagramChannelSettings business={business} />
          <PaymentForm
            key={`payment-${data.payment.version}`}
            data={data.payment}
            owner={owner}
            busy={busy}
            save={(f) => action("channels/payment-qr", f)}
          />
          <AutoReplyForm
            key={`auto-${data.version}`}
            value={data.autoreply}
            owner={owner}
            busy={busy}
            connected={connected}
            timezone={business.timezone}
            save={(v) =>
              action("channels/whatsapp/autoreply", {
                ...v,
                version: data.version,
              })
            }
          />
          <article className="chat-settings-card">
            <header>
              <MessageCircle size={21} />
              <div>
                <h3>Основной WhatsApp магазина</h3>
                <p>Ваш привычный номер остаётся на телефоне</p>
              </div>
              <span className="chat-mini">На телефоне</span>
            </header>
            <div className="chat-settings-body stack">
              <strong>
                {data.main_phone || "Укажите номер в настройках магазина"}
              </strong>
              <p>
                Попросите клиента написать на номер для заказов. Тогда менеджер
                увидит сообщение и сможет ответить здесь.
              </p>
              {connected && (
                <CopyField
                  label="Приглашение в чат"
                  value={`Здравствуйте! Это ${business.name} 🌷 Заказ быстрее оформить здесь: https://wa.me/${data.display_phone.replace(/\D/g, "")}`}
                />
              )}
            </div>
          </article>
          <div className="chat-pilot-note">
            <ShieldCheck size={20} />
            <div>
              <strong>Ответы остаются за сотрудниками</strong>
              <p>
                Автоответ только приветствует клиента. Он не закрывает диалог и
                не снимает отметку «Ждёт ответа».
              </p>
            </div>
          </div>
        </div>
      </div>
      {disconnect && (
        <Modal
          title="Отключить WhatsApp?"
          close={() => setDisconnect(false)}
          busy={busy}
        >
          <div className="modal-body stack">
            <p>
              Новые сообщения перестанут поступать. История сохранится, токен и
              секрет подключения будут удалены.
            </p>
            <button
              className="btn primary"
              disabled={busy}
              onClick={() =>
                void action("channels/whatsapp", undefined, "DELETE").then(
                  (ok) => {
                    if (ok) setDisconnect(false);
                  },
                )
              }
            >
              Отключить
            </button>
          </div>
        </Modal>
      )}
    </section>
  );
}
function PaymentForm({
  data,
  owner,
  busy,
  save,
}: {
  data: PaymentSettings;
  owner: boolean;
  busy: boolean;
  save: (f: FormData) => Promise<boolean>;
}) {
  const [file, setFile] = useState<File | null>(null),
    [remove, setRemove] = useState(false);
  return (
    <article className="chat-settings-card">
      <header>
        <QrCode size={21} />
        <div>
          <h3>QR для оплаты</h3>
          <p>Менеджер отправит его из чата</p>
        </div>
      </header>
      <form
        className="chat-settings-body stack"
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          f.set("version", String(data.version));
          f.set("remove", String(remove));
          if (file) f.set("file", file);
          void save(f);
        }}
      >
        <div className="chat-qr-preview">
          {data.image_url && !remove ? (
            <img
              src={`${data.image_url}?v=${data.version}`}
              alt="QR для оплаты магазина"
            />
          ) : (
            <>
              <QrCode size={46} />
              <span>Загрузите QR вашего банка</span>
            </>
          )}
        </div>
        {owner && (
          <>
            <label className="chat-upload">
              PNG, JPG или WebP · до 5 МБ
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => {
                  setFile(e.target.files?.[0] || null);
                  setRemove(false);
                }}
              />
              {file && <small>{file.name}</small>}
            </label>
            {data.image_url && (
              <label className="chat-checkbox">
                <input
                  type="checkbox"
                  checked={remove}
                  onChange={(e) => {
                    setRemove(e.target.checked);
                    setFile(null);
                  }}
                />
                Удалить текущий QR
              </label>
            )}
          </>
        )}
        <label>
          Подпись для сотрудников
          <input
            name="note"
            defaultValue={data.note}
            disabled={!owner}
            maxLength={150}
            placeholder="Например, MBANK · ИП Айгуль"
          />
        </label>
        <label>
          Сообщение вместе с QR
          <textarea
            name="text"
            required
            maxLength={1024}
            defaultValue={data.text}
            disabled={!owner}
          />
        </label>
        <small>
          Переменные: {"{номер}"} — заказ, {"{сумма}"} — сумма оплаты. Перед
          отправкой менеджер проверит сумму.
        </small>
        {owner && (
          <button className="btn" disabled={busy}>
            Сохранить QR и подпись
          </button>
        )}
      </form>
    </article>
  );
}
function AutoReplyForm({
  value,
  owner,
  busy,
  connected,
  timezone,
  save,
}: {
  value: AutoReply | null;
  owner: boolean;
  busy: boolean;
  connected: boolean;
  timezone: string;
  save: (v: AutoReply) => Promise<boolean>;
}) {
  const [v, setV] = useState<AutoReply>(
    value || {
      enabled: true,
      start: "09:00",
      end: "20:00",
      open_text: "Здравствуйте! Мы получили ваше сообщение и скоро ответим 🌸",
      closed_text:
        "Здравствуйте! Сейчас магазин закрыт. Ответим в рабочее время 🌸",
    },
  );
  return (
    <article className="chat-settings-card">
      <header>
        <Zap size={21} />
        <div>
          <h3>Автоответ</h3>
          <p>Клиент сразу узнает, что сообщение получено</p>
        </div>
      </header>
      <form
        className="chat-settings-body stack"
        onSubmit={(e) => {
          e.preventDefault();
          void save(v);
        }}
      >
        <label className="chat-checkbox">
          <input
            type="checkbox"
            disabled={!owner}
            checked={v.enabled}
            onChange={(e) => setV({ ...v, enabled: e.target.checked })}
          />
          Включить автоответ
        </label>
        <div className="chat-fields">
          <label>
            Работаем с
            <input
              type="time"
              required
              disabled={!owner}
              value={v.start}
              onChange={(e) => setV({ ...v, start: e.target.value })}
            />
          </label>
          <label>
            До
            <input
              type="time"
              required
              disabled={!owner}
              value={v.end}
              onChange={(e) => setV({ ...v, end: e.target.value })}
            />
          </label>
        </div>
        <small>Часовой пояс магазина: {timezone}</small>
        <label>
          В рабочее время
          <textarea
            required
            maxLength={4096}
            disabled={!owner}
            value={v.open_text}
            onChange={(e) => setV({ ...v, open_text: e.target.value })}
          />
        </label>
        <label>
          В нерабочее время
          <textarea
            required
            maxLength={4096}
            disabled={!owner}
            value={v.closed_text}
            onChange={(e) => setV({ ...v, closed_text: e.target.value })}
          />
        </label>
        <p className="muted">
          В рабочее время — на первое сообщение и после суток тишины, не чаще
          одного раза за 12 часов. В нерабочее время — один ответ за период
          закрытия, даже если клиент уже писал днём. После полуночи ответ не
          повторяется. {"{магазин}"} заменится названием магазина.
        </p>
        {owner && (
          <button className="btn" disabled={busy || !connected}>
            Сохранить автоответ
          </button>
        )}
      </form>
    </article>
  );
}
