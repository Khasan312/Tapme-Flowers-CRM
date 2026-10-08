import { useEffect, useState } from "react";
import { ApiError, businessPath, errorText, request } from "./api";
import { Avatar } from "./ui";
import { Notice, Pager, Modal, SettingsConflict } from "./components";
import { useRemote } from "./hooks";
import type { Business, Page, Reminder, ReminderRules } from "./types";

const stateNames: Record<string, string> = {
  wait: "Очередь",
  sent: "Написали",
  skipped: "Пропущено",
  answered: "Ответили",
  ordered: "Заказали",
};
export function Reminders({
  business,
  templates,
  openCustomer,
}: {
  business: Business;
  templates: () => void;
  openCustomer: (id: string) => void;
}) {
  const [conflict, setConflict] = useState(false);
  const [kind, setKind] = useState("all");
  const [tab, setTab] = useState("queue"),
    [state, setState] = useState("wait"),
    [offset, setOffset] = useState(0),
    [revision, setRevision] = useState(0);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState<{
      id: string;
      message: string;
      url: string;
    } | null>(null);
  const source = useRemote<ReminderRules>(
    businessPath(business.id, "reminder-rules"),
    revision,
  );
  const [rules, setRules] = useState<ReminderRules | null>(null);
  useEffect(() => {
    if (source.data) setRules(source.data);
  }, [source.data]);
  const page = useRemote<Page<Reminder> & { stats: Record<string, number> }>(
    businessPath(business.id, "reminders") +
      `?state=${state}&kind=${kind}&limit=50&offset=${offset}`,
    revision,
  );
  async function generate() {
    setBusy(true);
    setError("");
    try {
      const r = await request<{ created: number }>(
        businessPath(business.id, "reminders"),
        { method: "POST" },
      );
      setNotice(`Добавлено напоминаний: ${r.created}`);
      setRevision((v) => v + 1);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function act(id: string, action: string) {
    setBusy(true);
    setError("");
    try {
      await request(businessPath(business.id, `reminders/${id}/action`), {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      setMessage(null);
      setRevision((v) => v + 1);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function prepare(id: string) {
    setError("");
    try {
      setMessage({
        id,
        ...(await request<{ message: string; url: string }>(
          businessPath(business.id, `reminders/${id}/message`),
        )),
      });
    } catch (e) {
      setError(errorText(e));
    }
  }
  async function save() {
    if (!rules) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const saved = await request<ReminderRules>(
        businessPath(business.id, "reminder-rules"),
        {
          method: "PUT",
          body: JSON.stringify(rules),
        },
      );
      setRules(saved);
      setConflict(false);
      setRevision((v) => v + 1);
      setNotice("Настройки напоминаний сохранены");
    } catch (e) {
      setError(errorText(e));
      setConflict(e instanceof ApiError && e.status === 409);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="stack reminders-screen">
      <div className="page-hd">
        <div>
          <h1>Напоминания</h1>
          <div className="sub">
            Даты за {rules?.offsets.join(", ") || "14, 7, 3, 1"} дней · клиенты
            без заказов {rules?.inactive_days || 90}+ дней
          </div>
        </div>
        <span className="spacer" />
        <button className="btn" onClick={templates}>
          Шаблоны
        </button>
        <button
          className="btn"
          onClick={() => setTab(tab === "rules" ? "queue" : "rules")}
        >
          {tab === "rules" ? "К очереди" : "Правила"}
        </button>
      </div>
      {(error || source.error || page.error) && (
        <Notice>{error || source.error || page.error}</Notice>
      )}
      {conflict && (
        <SettingsConflict
          busy={busy || source.loading}
          reload={() => {
            setRevision((r) => r + 1);
            setConflict(false);
            setError("");
          }}
        />
      )}
      {notice && (
        <p role="status" className="selection">
          {notice}
        </p>
      )}
      {tab === "queue" && (
        <>
          <div className="kpis reminder-kpis">
            {[
              ["wait", "Ждут сообщения", "на сегодня"],
              ["sent", "Написали", "ждём ответа"],
              ["ordered", "Превратились в заказ", "за всё время"],
            ].map(([key, label, sub]) => (
              <button
                key={key}
                className="kpi"
                onClick={() => {
                  setState(key);
                  setKind("all");
                  setOffset(0);
                }}
              >
                <span className="kl">{label}</span>
                <span className="kv">{page.data?.stats[key] || 0}</span>
                <span className="kf">{sub}</span>
              </button>
            ))}
          </div>
          <div className="row reminder-controls">
            <div className="pills">
              {[
                ["all", "Все"],
                ["date", "Даты"],
                ["inactive", "Давно не заказывали"],
                ["sent", "Отправлено"],
              ].map(([key, label]) => (
                <button
                  key={key}
                  className={`pill${(key === "sent" ? state === "sent" : state === "wait" && kind === key) ? " is-on" : ""}`}
                  onClick={() => {
                    setState(key === "sent" ? "sent" : "wait");
                    setKind(key === "sent" ? "all" : key);
                    setOffset(0);
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            <span className="spacer" />
            <select
              className="btn sm"
              aria-label="Состояние напоминаний"
              value={state}
              onChange={(e) => {
                setState(e.target.value);
                setOffset(0);
              }}
            >
              {Object.entries(stateNames).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
            <button
              className="btn sm"
              disabled={busy}
              onClick={() => void generate()}
            >
              Сформировать очередь на сегодня
            </button>
          </div>
          {["date", "inactive"]
            .filter((k) => kind === "all" || k === kind)
            .map((k) => (
              <section className="card" key={k}>
                <div className="card-hd">
                  <h2>
                    {k === "date" ? "Важные даты" : "Давно не заказывали"}
                  </h2>
                  {k === "inactive" && (
                    <span className="small muted">
                      {rules?.inactive_days || 90} дней и больше
                    </span>
                  )}
                </div>
                <div className="card-bd tight">
                  {page.data?.results
                    .filter((r) => r.kind === k)
                    .map((r) => (
                      <div className="lrow reminder-row" key={r.id}>
                        <Avatar name={r.customer_name} />
                        <div>
                          <div className="t">
                            <button
                              className="plain-button"
                              onClick={() => openCustomer(r.customer_id)}
                            >
                              {r.customer_name}
                            </button>
                            <span className="muted">
                              {" "}
                              · {r.event} у {r.person}
                            </span>
                          </div>
                          <div className="s">
                            {r.message || r.preview || r.phone}
                          </div>
                          {r.recovered && (
                            <span className="tag">
                              Восстановлено после перерыва
                            </span>
                          )}
                          {r.paused && (
                            <span className="tag crit">
                              Приостановлено: согласие, жалоба или правила
                            </span>
                          )}
                        </div>
                        <div className="r row nowrap">
                          {state === "wait" ? (
                            <>
                              <button
                                className="btn sm wa"
                                disabled={busy || r.paused}
                                onClick={() => void prepare(r.id)}
                              >
                                WhatsApp
                              </button>
                              <details className="reminder-more">
                                <summary className="btn sm">⋯</summary>
                                <div className="reminder-actions">
                                  <button
                                    className="btn xs"
                                    disabled={busy}
                                    onClick={() => void act(r.id, "tomorrow")}
                                  >
                                    Напомнить завтра
                                  </button>
                                  <button
                                    className="btn xs"
                                    disabled={busy}
                                    onClick={() => void act(r.id, "skipped")}
                                  >
                                    Пропустить этот повод
                                  </button>
                                </div>
                              </details>
                            </>
                          ) : (
                            <>
                              <span className="tag wa">
                                {stateNames[state]}
                              </span>
                              {state === "sent" && (
                                <button
                                  className="btn xs"
                                  disabled={busy || r.paused}
                                  onClick={() => void act(r.id, "answered")}
                                >
                                  Отметить ответ
                                </button>
                              )}
                              {["sent", "answered"].includes(state) && (
                                <button
                                  className="btn xs"
                                  disabled={busy || r.paused}
                                  onClick={() => void act(r.id, "ordered")}
                                >
                                  Отметить заказ
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  {!page.data?.results.some((r) => r.kind === k) && (
                    <div className="empty">
                      {page.loading
                        ? "Загружаем…"
                        : "Напоминаний с этим фильтром нет"}
                    </div>
                  )}
                </div>
              </section>
            ))}
          <Pager
            count={page.data?.count || 0}
            offset={offset}
            setOffset={setOffset}
          />
          {message && (
            <Modal
              title="Сообщение клиенту"
              close={() => setMessage(null)}
              busy={busy}
            >
              <div className="modal-body stack">
                <p className="preserve">{message.message}</p>
                <a
                  className="btn wa"
                  target="_blank"
                  rel="noopener noreferrer"
                  href={message.url}
                >
                  Открыть WhatsApp
                </a>
                <p className="muted">
                  Отправьте сообщение в WhatsApp, затем отметьте действие здесь.
                </p>
                <button
                  className="btn primary"
                  disabled={busy}
                  onClick={() => void act(message.id, "sent")}
                >
                  Я написал клиенту
                </button>
              </div>
            </Modal>
          )}
        </>
      )}
      {(tab === "rules" || tab === "template") && rules && (
        <form
          className="panel stack"
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
        >
          <fieldset
            disabled={business.role !== "owner" || busy}
            className="stack"
          >
            {tab === "template" ? (
              <>
                <label>
                  Важные даты — текст сообщения
                  <textarea
                    rows={6}
                    value={rules.template}
                    onChange={(e) =>
                      setRules({ ...rules, template: e.target.value })
                    }
                  />
                </label>
                <label>
                  Давние клиенты — текст сообщения
                  <textarea
                    rows={4}
                    value={rules.inactive_template}
                    onChange={(e) =>
                      setRules({ ...rules, inactive_template: e.target.value })
                    }
                  />
                </label>
                <p className="muted">
                  Подстановки: {"{name}"} — имя, {"{person}"} — получатель,{" "}
                  {"{event}"} — повод, {"{shop}"} — магазин.
                </p>
              </>
            ) : (
              <>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={rules.enabled}
                    onChange={(e) =>
                      setRules({ ...rules, enabled: e.target.checked })
                    }
                  />
                  Напоминания включены
                </label>
                <label>
                  За сколько дней напоминать (через запятую)
                  <input
                    value={rules.offsets.join(", ")}
                    onChange={(e) =>
                      setRules({
                        ...rules,
                        offsets: e.target.value
                          .split(",")
                          .map((v) => Number(v.trim())),
                      })
                    }
                  />
                </label>
                <label>
                  Давний клиент — без покупок, дней
                  <input
                    type="number"
                    min={30}
                    max={730}
                    value={rules.inactive_days}
                    onChange={(e) =>
                      setRules({
                        ...rules,
                        inactive_days: Number(e.target.value),
                      })
                    }
                  />
                </label>
                <div className="form-grid">
                  <label>
                    Сообщения с часа
                    <input
                      type="number"
                      min={0}
                      max={23}
                      value={rules.start_hour}
                      onChange={(e) =>
                        setRules({
                          ...rules,
                          start_hour: Number(e.target.value),
                        })
                      }
                    />
                  </label>
                  <label>
                    До часа
                    <input
                      type="number"
                      min={1}
                      max={24}
                      value={rules.end_hour}
                      onChange={(e) =>
                        setRules({ ...rules, end_hour: Number(e.target.value) })
                      }
                    />
                  </label>
                </div>
                <p className="muted">
                  Используется часовой пояс магазина. Сообщения разрешены только
                  при согласии клиента; открытая жалоба ставит их на паузу.
                </p>
              </>
            )}
            <button className="primary">Сохранить напоминания</button>
          </fieldset>
        </form>
      )}
    </section>
  );
}
