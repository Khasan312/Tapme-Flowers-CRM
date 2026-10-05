import { useEffect, useState, type FormEvent } from "react";
import { businessPath, errorText, price, request } from "./api";
import { Modal, Notice } from "./components";
import { useRemote } from "./hooks";
import { Status } from "./orders";
import type { Business, CustomerProfile } from "./types";

export function CustomerPanel({
  business,
  customerId,
  close,
  changed,
}: {
  business: Business;
  customerId: string;
  close: () => void;
  changed: () => void;
}) {
  const path = businessPath(business.id, `customers/${customerId}`);
  const [revision, setRevision] = useState(0),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  const source = useRemote<CustomerProfile>(path, revision);
  const activity = useRemote<{
    order_count: number;
    orders: {
      id: string;
      number: number;
      status: string;
      total: string;
      delivery_date: string;
    }[];
    feedback: {
      id: string;
      message: string;
      outcome: string;
      status: string;
    }[];
    reminders: { id: string; state: string; event: string; message: string }[];
  }>(path + "activity/", revision);
  const [draft, setDraft] = useState<CustomerProfile | null>(null);
  useEffect(() => {
    if (source.data) setDraft(source.data);
  }, [source.data]);
  async function save(e: FormEvent) {
    e.preventDefault();
    if (!draft) return;
    setBusy(true);
    setError("");
    try {
      const { id: _id, code: _code, created_at: _created, ...body } = draft;
      const result = await request<CustomerProfile>(path, {
        method: "PUT",
        body: JSON.stringify(body),
      });
      setDraft(result);
      setNotice("Карточка сохранена");
      changed();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title={draft?.name || "Клиент"} close={close} busy={busy}>
      <form onSubmit={save}>
        <div className="modal-body stack">
          {(error || source.error) && <Notice>{error || source.error}</Notice>}
          {notice && (
            <p role="status" className="selection">
              {notice}
            </p>
          )}
          {activity.error && <Notice>{activity.error}</Notice>}
          {draft && (
            <>
              <div className="form-grid">
                <label>
                  Имя клиента
                  <input
                    required
                    value={draft.name}
                    onChange={(e) =>
                      setDraft({ ...draft, name: e.target.value })
                    }
                  />
                </label>
                <label>
                  Телефон клиента
                  <input
                    required
                    type="tel"
                    value={draft.phone}
                    onChange={(e) =>
                      setDraft({ ...draft, phone: e.target.value })
                    }
                  />
                </label>
              </div>
              <div className="fgrid">
                <label>
                  Источник клиента
                  <input
                    value={draft.source || ""}
                    maxLength={80}
                    onChange={(e) =>
                      setDraft({ ...draft, source: e.target.value })
                    }
                  />
                </label>
                <label>
                  Метки клиента
                  <input
                    value={(draft.tags || []).join(", ")}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        tags: e.target.value
                          .split(",")
                          .map((t) => t.trim())
                          .filter(Boolean),
                      })
                    }
                  />
                  <span className="hint">Например: VIP, Корпоративный</span>
                </label>
              </div>
              <label>
                Заметка клиента
                <textarea
                  value={draft.notes}
                  onChange={(e) =>
                    setDraft({ ...draft, notes: e.target.value })
                  }
                />
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={draft.consent}
                  onChange={(e) =>
                    setDraft({ ...draft, consent: e.target.checked })
                  }
                />
                Клиент согласился получать сообщения
              </label>
              <section className="stack">
                <h3>Получатели</h3>
                {draft.recipients.map((r, i) => (
                  <div className="detail-box stack" key={r.id}>
                    <div className="form-grid">
                      {(
                        [
                          ["name", "Имя получателя"],
                          ["relation", "Кем приходится"],
                          ["phone", "Телефон получателя"],
                          ["address", "Адрес получателя"],
                          ["notes", "Заметка получателя"],
                        ] as const
                      ).map(([field, label]) => (
                        <label key={field}>
                          {label}
                          <input
                            required={field === "name"}
                            value={r[field]}
                            onChange={(e) =>
                              setDraft({
                                ...draft,
                                recipients: draft.recipients.map((v, j) =>
                                  i === j
                                    ? { ...v, [field]: e.target.value }
                                    : v,
                                ),
                              })
                            }
                          />
                        </label>
                      ))}
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        setDraft({
                          ...draft,
                          recipients: draft.recipients.filter(
                            (_, j) => i !== j,
                          ),
                        })
                      }
                    >
                      Убрать получателя
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() =>
                    setDraft({
                      ...draft,
                      recipients: [
                        ...draft.recipients,
                        {
                          id: crypto.randomUUID(),
                          name: "",
                          relation: "",
                          phone: "",
                          address: "",
                          notes: "",
                        },
                      ],
                    })
                  }
                >
                  Добавить получателя
                </button>
              </section>
              <section className="stack">
                <h3>Важные даты</h3>
                {draft.dates.map((d, i) => (
                  <div className="detail-box stack" key={d.id}>
                    <div className="form-grid">
                      <label>
                        Событие
                        <input
                          required
                          value={d.label}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              dates: draft.dates.map((v, j) =>
                                i === j ? { ...v, label: e.target.value } : v,
                              ),
                            })
                          }
                        />
                      </label>
                      <label>
                        У кого
                        <input
                          required
                          value={d.person}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              dates: draft.dates.map((v, j) =>
                                i === j ? { ...v, person: e.target.value } : v,
                              ),
                            })
                          }
                        />
                      </label>
                      <label>
                        День
                        <input
                          type="number"
                          min={1}
                          max={31}
                          required
                          value={d.day}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              dates: draft.dates.map((v, j) =>
                                i === j
                                  ? { ...v, day: Number(e.target.value) }
                                  : v,
                              ),
                            })
                          }
                        />
                      </label>
                      <label>
                        Месяц
                        <input
                          type="number"
                          min={1}
                          max={12}
                          required
                          value={d.month}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              dates: draft.dates.map((v, j) =>
                                i === j
                                  ? { ...v, month: Number(e.target.value) }
                                  : v,
                              ),
                            })
                          }
                        />
                      </label>
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        setDraft({
                          ...draft,
                          dates: draft.dates.filter((_, j) => i !== j),
                        })
                      }
                    >
                      Убрать дату
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() =>
                    setDraft({
                      ...draft,
                      dates: [
                        ...draft.dates,
                        {
                          id: crypto.randomUUID(),
                          label: "День рождения",
                          person: "",
                          month: 1,
                          day: 1,
                        },
                      ],
                    })
                  }
                >
                  Добавить дату
                </button>
              </section>
            </>
          )}
          {activity.data && (
            <>
              <section className="stack">
                <h3>История заказов · {activity.data.order_count}</h3>
                <p className="muted">Последние 50 заказов</p>
                {activity.data.orders.map((o) => (
                  <div className="detail-line" key={o.id}>
                    <span>
                      №{o.number} · {o.delivery_date}
                    </span>
                    <Status value={o.status} />
                    <strong>{price(o.total)}</strong>
                  </div>
                ))}
              </section>
              <section className="stack">
                <h3>Отзывы и жалобы</h3>
                {activity.data.feedback.map((f) => (
                  <div className="detail-box" key={f.id}>
                    <p>{f.message}</p>
                    {f.outcome && <p>Решение: {f.outcome}</p>}
                  </div>
                ))}
              </section>
              <section className="stack">
                <h3>Напоминания и сообщения</h3>
                {activity.data.reminders.map((r) => (
                  <div className="detail-box" key={r.id}>
                    <strong>
                      {r.event} ·{" "}
                      {
                        (
                          {
                            wait: "В очереди",
                            sent: "Написали",
                            answered: "Ответили",
                            ordered: "Заказали",
                            skipped: "Пропущено",
                          } as Record<string, string>
                        )[r.state]
                      }
                    </strong>
                    <p>{r.message}</p>
                  </div>
                ))}
              </section>
            </>
          )}
        </div>
        <footer className="modal-footer">
          <button
            type="button"
            disabled={busy}
            onClick={() => setRevision((r) => r + 1)}
          >
            Обновить карточку
          </button>
          <button disabled={busy || !draft} className="primary">
            Сохранить клиента
          </button>
        </footer>
      </form>
    </Modal>
  );
}

type ImportResult = {
  count: number;
  created: number;
  results: {
    row: number;
    name: string;
    phone: string;
    status: string;
    error: string;
  }[];
};
export function CustomerTransfer({
  business,
  close,
  changed,
}: {
  business: Business;
  close: () => void;
  changed: () => void;
}) {
  const [file, setFile] = useState<File | null>(null),
    [result, setResult] = useState<ImportResult | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [committed, setCommitted] = useState(false);
  async function send(commit: boolean) {
    if (!file) return;
    setBusy(true);
    setError("");
    const data = new FormData();
    data.set("file", file);
    data.set("commit", String(commit));
    try {
      setResult(
        await request<ImportResult>(
          businessPath(business.id, "customers/import"),
          { method: "POST", body: data },
        ),
      );
      setCommitted(commit);
      if (commit) changed();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Импорт клиентов" close={close} busy={busy}>
      <div className="modal-body stack">
        <p>
          CSV в UTF-8 или Excel. Колонки: name — имя, phone — телефон, notes —
          заметка. До 1000 строк и 2 МБ.
        </p>
        <p className="muted">
          Дубли по телефону будут пропущены. Согласие на сообщения не
          импортируется.
        </p>
        <label>
          Файл клиентов
          <input
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => {
              setFile(e.target.files?.[0] || null);
              setResult(null);
              setCommitted(false);
            }}
          />
        </label>
        {error && <Notice>{error}</Notice>}
        <button onClick={() => void send(false)} disabled={!file || busy}>
          Проверить файл
        </button>
        {result && (
          <>
            <p role="status">
              Строк: {result.count} · Готово к импорту:{" "}
              {result.results.filter((r) => r.status === "ready").length} ·
              Создано: {result.created}
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Строка</th>
                    <th>Клиент</th>
                    <th>Телефон</th>
                    <th>Результат</th>
                  </tr>
                </thead>
                <tbody>
                  {result.results.map((r) => (
                    <tr key={r.row}>
                      <td>{r.row}</td>
                      <td>{r.name}</td>
                      <td>{r.phone}</td>
                      <td>
                        {r.error ||
                          (
                            {
                              ready: "Готово",
                              duplicate: "Дубль — пропускаем",
                              created: "Создан",
                            } as Record<string, string>
                          )[r.status]}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
      <footer className="modal-footer">
        <button onClick={close}>Закрыть</button>
        {result && !committed && (
          <button
            className="primary"
            disabled={busy || !result.results.some((r) => r.status === "ready")}
            onClick={() => void send(true)}
          >
            Импортировать проверенные строки
          </button>
        )}
      </footer>
    </Modal>
  );
}
