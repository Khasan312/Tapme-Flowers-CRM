import { useState } from "react";
import { CheckCircle2, Circle, Instagram, ShieldCheck } from "lucide-react";
import { businessPath, errorText, request } from "./api";
import { Modal, Notice } from "./components";
import { CopyField } from "./channel-copy-field";
import { useRemote } from "./hooks";
import type { Business } from "./types";
import type { InstagramChannel } from "./chat-types";

const checks = {
  token_checked_at: "Аккаунт и токен проверены",
  webhook_verified_at: "Вебхук подтверждён Meta",
  subscribed_at: "Подписка на сообщения включена",
  last_inbound_at: "Первое входящее получено",
  first_reply_sent: "Первый ответ отправлен из CRM",
};

export function InstagramChannelSettings({ business }: { business: Business }) {
  const [revision, refresh] = useState(0);
  const channel = useRemote<InstagramChannel>(
    businessPath(business.id, "channels/instagram"),
    revision,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [disconnect, setDisconnect] = useState(false);
  const data = channel.data;
  const owner = business.role === "owner";
  const connected = data?.status === "active";
  async function action(path: string, body?: unknown, method = "POST") {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await request(businessPath(business.id, `channels/instagram${path}`), {
        method,
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      refresh((v) => v + 1);
      setNotice(
        method === "DELETE"
          ? "Instagram отключён. История сохранена."
          : "Настройки Instagram сохранены",
      );
      return true;
    } catch (e) {
      setError(errorText(e));
      return false;
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className="chat-settings-card" aria-label="Подключение Instagram">
      <header>
        <span className="chat-channel-logo">
          <Instagram size={22} />
        </span>
        <div>
          <h3>Instagram · сообщения Direct</h3>
          <p>Профессиональный аккаунт магазина</p>
        </div>
        <span
          className={`chat-mini ${connected && data?.checks.last_inbound_at && !data.connection_error ? "green" : "amber"}`}
        >
          {connected
            ? data?.connection_error
              ? "Ошибка подключения"
              : data?.checks.last_inbound_at
                ? "Сообщения поступают"
                : "Завершите подключение"
            : "Не подключён"}
        </span>
      </header>
      <div className="chat-settings-body stack">
        {(error || channel.error || data?.connection_error) && (
          <Notice>{error || channel.error || data?.connection_error}</Notice>
        )}
        {notice && (
          <p role="status" className="chat-save-notice">
            {notice}
          </p>
        )}
        {!data ? (
          <p>Загружаем настройки Instagram…</p>
        ) : (
          <>
            {data.server_mode === "fake" && (
              <div className="chat-test-banner">
                Тестовый режим: подключение и сообщения моделируются в CRM. В
                Instagram ничего не отправляется.
              </div>
            )}
            {!data.configured && (
              <Notice>
                Администратору нужно настроить ключ шифрования и версию Meta API
                на сервере.
              </Notice>
            )}
            <p className="muted">
              Для первого подключения используйте данные из Meta → Instagram →
              Настройка API с единым входом. Нужны разрешения instagram_basic и
              instagram_manage_messages.
            </p>
            {owner ? (
              <form
                className="stack"
                onSubmit={async (e) => {
                  e.preventDefault();
                  const form = e.currentTarget;
                  const fields = new FormData(form);
                  if (
                    await action("", {
                      ig_user_id: fields.get("ig_user_id"),
                      token: fields.get("token"),
                      app_secret: fields.get("app_secret"),
                      version: data.version,
                    })
                  ) {
                    (
                      form.elements.namedItem("token") as HTMLInputElement
                    ).value = "";
                    (
                      form.elements.namedItem("app_secret") as HTMLInputElement
                    ).value = "";
                  }
                }}
              >
                <label>
                  Instagram Account ID
                  <input
                    name="ig_user_id"
                    inputMode="numeric"
                    pattern="[0-9]{5,80}"
                    required
                    defaultValue={data.ig_user_id}
                  />
                  <small>
                    ID аккаунта Instagram из Meta, а не номер телефона
                  </small>
                </label>
                <div className="chat-fields">
                  <label>
                    Access token Instagram
                    <input
                      name="token"
                      type="password"
                      autoComplete="new-password"
                      required
                      placeholder={
                        connected
                          ? "Новый токен для переподключения"
                          : "Токен из Meta Unified Login"
                      }
                    />
                  </label>
                  <label>
                    App Secret Instagram
                    <input
                      name="app_secret"
                      type="password"
                      autoComplete="new-password"
                      required
                    />
                    <small>
                      Секрет приложения Meta, в котором подключён Instagram
                    </small>
                  </label>
                </div>
                <p className="chat-security">
                  <ShieldCheck size={15} />
                  Секреты шифруются и не показываются после сохранения.
                </p>
                {data.simulator && (
                  <button
                    type="button"
                    className="btn"
                    disabled={busy}
                    onClick={(e) => {
                      const form = e.currentTarget.form!;
                      for (const [key, value] of Object.entries({
                        ig_user_id: data.ig_user_id || String(Date.now()),
                        token: "fake-instagram-token",
                        app_secret: "fake-instagram-secret",
                      }))
                        (
                          form.elements.namedItem(key) as HTMLInputElement
                        ).value = value;
                    }}
                  >
                    Заполнить тестовый Instagram
                  </button>
                )}
                <button
                  className="btn primary"
                  disabled={busy || !data.configured}
                >
                  {busy ? "Проверяем…" : "Проверить и подключить Instagram"}
                </button>
              </form>
            ) : (
              <p>Подключать и отключать Instagram может владелец магазина.</p>
            )}
            {data.version > 0 && (
              <>
                <div className="chat-channel-info">
                  <strong>
                    @{data.ig_username} · {data.display_name}
                  </strong>
                </div>
                {connected && owner && (
                  <>
                    <h4>Приём сообщений Instagram</h4>
                    <CopyField
                      label="Callback URL Instagram"
                      value={location.origin + data.webhook_path}
                    />
                    <CopyField
                      label="Verify token Instagram"
                      value={data.verify_token || ""}
                    />
                    <p className="muted">
                      В Meta укажите публичный HTTPS-адрес этого вебхука и
                      выберите поля messages и messaging_seen. Затем включите
                      подписку ниже. Локальный адрес 127.0.0.1 недоступен Meta.
                    </p>
                    <div className="actions">
                      <button
                        type="button"
                        className="btn"
                        disabled={busy}
                        onClick={() => void action("/check")}
                      >
                        Проверить доступ Instagram
                      </button>
                      <button
                        type="button"
                        className="btn"
                        disabled={busy || !data.checks.webhook_verified_at}
                        onClick={() => void action("/subscribe")}
                      >
                        Включить подписку Instagram
                      </button>
                      <button
                        type="button"
                        className="btn danger"
                        disabled={busy}
                        onClick={() => setDisconnect(true)}
                      >
                        Отключить Instagram
                      </button>
                    </div>
                  </>
                )}
                <ul className="chat-checklist">
                  {Object.entries(checks).map(([key, label]) => (
                    <li
                      key={key}
                      className={connected && data.checks[key] ? "done" : ""}
                    >
                      {connected && data.checks[key] ? (
                        <CheckCircle2 size={18} />
                      ) : (
                        <Circle size={18} />
                      )}
                      <span>{label}</span>
                    </li>
                  ))}
                </ul>
                <p className="muted">
                  Для проверки напишите магазину с другого аккаунта и ответьте
                  из раздела «Чаты → Instagram». Первый запуск поддерживает
                  текстовые ответы; вложения открывайте в Instagram.
                </p>
              </>
            )}
          </>
        )}
      </div>
      {disconnect && (
        <Modal
          title="Отключить Instagram?"
          close={() => setDisconnect(false)}
          busy={busy}
        >
          <div className="modal-body stack">
            <p>
              Новые сообщения перестанут поступать в CRM. История сохранится,
              токен и секрет подключения будут удалены.
            </p>
            <button
              className="btn primary"
              disabled={busy}
              onClick={() =>
                void action("", undefined, "DELETE").then((ok) => {
                  if (ok) setDisconnect(false);
                })
              }
            >
              Отключить Instagram
            </button>
          </div>
        </Modal>
      )}
    </article>
  );
}
