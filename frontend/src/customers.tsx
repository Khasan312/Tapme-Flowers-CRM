import { newUuid } from "./uuid";
import { useEffect, useState, type FormEvent } from "react";
import { businessPath, errorText, price, request } from "./api";
import { Modal, Notice, RefreshIndicator } from "./components";
import { AdditionalPhones, PhoneInput } from "./phone-input";
import { CustomerCategory } from "./customer-category";
import { RecipientHelp } from "./recipient-help";
import { FeedbackHelp } from "./feedback-help";
import { MessagesHelp } from "./messages-help";
import { CustomerFeedback } from "./customer-feedback";
import { useRemote } from "./hooks";
import { Status } from "./orders";
import type { Business, CustomerProfile, Feedback } from "./types";

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
    feedback: Feedback[];
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
                  <PhoneInput
                    required
                    value={draft.phone}
                    onChange={(value) => setDraft({ ...draft, phone: value })}
                  />
                </label>
              </div>
              <AdditionalPhones
                phone={draft.phone}
                values={draft.additional_phones || []}
                disabled={busy}
                onChange={(phone, additional_phones) =>
                  setDraft({ ...draft, phone, additional_phones })
                }
              />
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
                <CustomerCategory
                  tags={draft.tags || []}
                  disabled={busy}
                  onChange={(tags) => setDraft({ ...draft, tags })}
                />
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
                          {field === "phone" ? (
                            <PhoneInput
                              value={r.phone}
                              onChange={(value) =>
                                setDraft({
                                  ...draft,
                                  recipients: draft.recipients.map((v, j) =>
                                    i === j ? { ...v, phone: value } : v,
                                  ),
                                })
                              }
                            />
                          ) : (
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
                          )}
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
                <div className="recipient-help-action">
                  <button
                    type="button"
                    onClick={() =>
                      setDraft({
                        ...draft,
                        recipients: [
                          ...draft.recipients,
                          {
                            id: newUuid(),
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
                  <RecipientHelp />
                </div>
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
                          id: newUuid(),
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
                <FeedbackHelp />
                {activity.data.feedback.map((f) => (
                  <CustomerFeedback
                    key={f.id}
                    feedback={f}
                    timezone={business.timezone}
                  />
                ))}
              </section>
              <section className="stack">
                <h3>Напоминания и сообщения</h3>
                <MessagesHelp />
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
          <RefreshIndicator active={source.refreshing || activity.refreshing} />
          <button
            type="button"
            disabled={busy || source.loading || activity.loading}
            onClick={() => setRevision((r) => r + 1)}
          >
            Обновить карточку
          </button>
          <button disabled={busy || !draft} className="primary">
            {busy ? "Сохраняем…" : "Сохранить клиента"}
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
    additional_phones?: string[];
    status: string;
    error: string;
  }[];
};

function ContactImportHelp() {
  return (
    <details className="import-help">
      <summary>Как перенести контакты с телефона?</summary>
      <div className="stack">
        <p>
          Сначала сохраните телефонную книгу в файл VCF, затем выберите его
          здесь. Кнопка выбора файла открывает «Файлы», а не список контактов.
        </p>
        <section aria-label="Экспорт с iPhone">
          <h3>iPhone</h3>
          <ol>
            <li>Откройте приложение «Контакты» и перейдите в «Списки».</li>
            <li>
              Нажмите и удерживайте нужный список, например «Все iCloud», затем
              выберите «Экспортировать».
            </li>
            <li>
              Оставьте имя, фамилию и все нужные поля телефонов: мобильный,
              домашний и другие. Уберите фотографии, чтобы уменьшить файл, и
              нажмите «Готово».
            </li>
            <li>
              В меню отправки нажмите «Сохранить в Файлы» и запомните папку.
              Если контакты есть в нескольких списках аккаунтов, повторите
              экспорт для каждого.
            </li>
          </ol>
          <a
            href="https://support.apple.com/ru-ru/guide/iphone/iph075ddebf2/ios"
            target="_blank"
            rel="noreferrer"
          >
            Инструкция Apple
          </a>
        </section>
        <section aria-label="Экспорт с Android">
          <h3>Android · Google Контакты</h3>
          <ol>
            <li>Откройте приложение «Контакты» от Google.</li>
            <li>Перейдите в «Управление контактами» → «Экспорт в файл».</li>
            <li>
              Отметьте все нужные аккаунты, выберите экспорт в VCF и сохраните
              файл, например в «Загрузки».
            </li>
          </ol>
          <p className="muted">
            В других приложениях контактов названия пунктов могут отличаться.
          </p>
          <a
            href="https://support.google.com/contacts/answer/7199294?hl=ru&co=GENIE.Platform%3DAndroid"
            target="_blank"
            rel="noreferrer"
          >
            Инструкция Google
          </a>
        </section>
        <section aria-label="Загрузка в CRM">
          <h3>Вернитесь в CRM</h3>
          <ol>
            <li>
              В этом окне выберите сохранённый VCF. Проверка запустится
              автоматически.
            </li>
            <li>
              В появившемся списке отметьте нужные контакты или нажмите «Выбрать
              все готовые».
            </li>
            <li>
              Нажмите «Импортировать выбранные». Только после этого контакты
              сохранятся в базе.
            </li>
          </ol>
          <p className="muted">
            За один раз — до 1000 номеров и 2 МБ. Если контактов больше,
            экспортируйте их отдельными списками. Дубли по телефону пропустим, а
            строки с ошибками покажем перед импортом.
          </p>
        </section>
      </div>
    </details>
  );
}

export function CustomerTransfer({
  business,
  close,
  changed,
}: {
  business: Business;
  close: () => void;
  changed: () => void;
}) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [search, setSearch] = useState("");
  const [file, setFile] = useState<File | null>(null),
    [result, setResult] = useState<ImportResult | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [committed, setCommitted] = useState(false);
  async function send(commit: boolean, upload = file) {
    if (!upload || busy) return;
    setBusy(true);
    setError("");
    if (!commit) setResult(null);
    const controller = new AbortController();
    const timeout = !commit
      ? window.setTimeout(() => controller.abort(), 30000)
      : undefined;
    const data = new FormData();
    data.set("file", upload);
    data.set("commit", String(commit));
    if (commit) data.set("selected_rows", JSON.stringify([...selected]));
    try {
      const response = await request<ImportResult>(
        businessPath(business.id, "customers/import"),
        { method: "POST", body: data, signal: controller.signal },
      );
      setResult(response);
      setSelected(
        new Set(
          response.results
            .filter((r) => r.status === (commit ? "created" : "ready"))
            .map((r) => r.row),
        ),
      );
      setCommitted(commit);
      if (commit) changed();
    } catch (e) {
      setError(
        controller.signal.aborted
          ? "Проверка файла заняла слишком много времени. Проверьте соединение и повторите."
          : errorText(e),
      );
    } finally {
      window.clearTimeout(timeout);
      setBusy(false);
    }
  }
  return (
    <Modal title="Импорт клиентов" close={close} busy={busy}>
      <div className="modal-body stack">
        {error && <Notice>{error}</Notice>}
        <details className="import-file" open={!result && !busy && !error}>
          <summary>
            {file ? `Файл: ${file.name} · изменить` : "Выбор файла контактов"}
          </summary>
          <div className="stack">
            <p>
              Выберите файл контактов VCF с телефона или таблицу CSV / Excel. До
              1000 номеров и 2 МБ. Для таблиц: name — имя, phone — телефон,
              notes — заметка.
            </p>
            <ContactImportHelp />
            <p className="muted">
              После выбора файла список появится автоматически. Имя и фамилия
              сохранятся вместе. Все разные номера одного контакта попадут в
              одну карточку, первый — основной. Пустые поля пропускаем,
              одинаковые номера объединяем. Отметьте нужные контакты и
              подтвердите импорт. Дубли существующих клиентов по любому номеру
              будут пропущены. Согласие на сообщения не импортируется.
            </p>
            <label>
              Файл клиентов
              <input
                type="file"
                accept=".csv,.xlsx,.vcf,.vcard,text/vcard,text/x-vcard"
                disabled={busy}
                onChange={(e) => {
                  const upload = e.target.files?.[0];
                  if (!upload) return;
                  setFile(upload);
                  setResult(null);
                  setSelected(new Set());
                  setSearch("");
                  setError("");
                  setCommitted(false);
                  void send(false, upload);
                }}
              />
            </label>
          </div>
        </details>
        {busy && !result && <p role="status">Проверяем файл контактов…</p>}
        {error && !result && file && (
          <button disabled={busy} onClick={() => void send(false)}>
            Повторить проверку
          </button>
        )}
        {result && (
          <>
            <p role="status">
              Строк: {result.count} · Готово к импорту:{" "}
              {result.results.filter((r) => r.status === "ready").length} ·
              Создано: {result.created}
            </p>
            {!committed && (
              <>
                <label>
                  Найти контакт в файле
                  <input
                    type="search"
                    className="import-search"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Имя или телефон"
                  />
                </label>
                <div className="import-actions">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      setSelected(
                        new Set(
                          result.results
                            .filter((r) => r.status === "ready")
                            .map((r) => r.row),
                        ),
                      )
                    }
                  >
                    Выбрать все готовые
                  </button>
                  <button
                    type="button"
                    disabled={busy || selected.size === 0}
                    onClick={() => setSelected(new Set())}
                  >
                    Снять выбор
                  </button>
                  <span>Выбрано: {selected.size}</span>
                </div>
              </>
            )}
            <div className="import-contacts" aria-label="Контакты из файла">
              {result.results
                .filter(
                  (r) =>
                    committed ||
                    `${r.name} ${r.phone} ${(r.additional_phones || []).join(" ")}`
                      .toLocaleLowerCase()
                      .includes(search.trim().toLocaleLowerCase()),
                )
                .map((r) => (
                  <label className="import-contact" key={r.row}>
                    <input
                      type="checkbox"
                      aria-label={`Выбрать ${r.name || "контакт"} ${r.phone || "без телефона"}`}
                      checked={selected.has(r.row)}
                      disabled={busy || committed || r.status !== "ready"}
                      onChange={(e) => {
                        const next = new Set(selected);
                        if (e.target.checked) next.add(r.row);
                        else next.delete(r.row);
                        setSelected(next);
                      }}
                    />
                    <span className="import-contact-info">
                      <strong>{r.name || "Без имени"}</strong>
                      <span className="mono">{r.phone || "Без телефона"}</span>
                      {(r.additional_phones || []).map((number) => (
                        <span className="mono" key={number}>
                          {number}
                        </span>
                      ))}
                      <span
                        className={
                          r.status === "error" ? "import-error" : "muted"
                        }
                      >
                        {r.error ||
                          (
                            {
                              ready: "Готово к импорту",
                              duplicate: "Дубль — пропускаем",
                              created: "Создан",
                              unselected: "Не выбран",
                            } as Record<string, string>
                          )[r.status]}
                      </span>
                    </span>
                  </label>
                ))}
              {!committed &&
                !result.results.some((r) =>
                  `${r.name} ${r.phone} ${(r.additional_phones || []).join(" ")}`
                    .toLocaleLowerCase()
                    .includes(search.trim().toLocaleLowerCase()),
                ) && <p className="muted">Контакты не найдены.</p>}
            </div>
          </>
        )}
      </div>
      <footer className="modal-footer">
        <button onClick={close} disabled={busy}>
          Закрыть
        </button>
        {result && !committed && (
          <button
            className="primary"
            disabled={busy || selected.size === 0}
            onClick={() => void send(true)}
          >
            {busy
              ? "Импортируем…"
              : `Импортировать выбранные (${selected.size})`}
          </button>
        )}
      </footer>
    </Modal>
  );
}
