import { newUuid } from "./uuid";
import { messageTemplates } from "./message-templates";
import { useEffect, useState, type FormEvent } from "react";
import { ApiError, businessPath, errorText, price, request } from "./api";
import { Modal, Notice, Pager, SettingsConflict } from "./components";
import { PhoneInput } from "./phone-input";
import { ProductForm } from "./forms";
import { ProductPhoto } from "./product-photo";
import { Pencil } from "lucide-react";
import { useRemote } from "./hooks";
import { Avatar, roleNames, roleAccess, Toggle } from "./ui";
import type {
  Business,
  ShopSettings,
  Staff,
  Product,
  Page,
  ReminderRules,
} from "./types";

export type SettingsTab = "staff" | "windows" | "templates" | "prices" | "shop";
const tabs: Record<SettingsTab, string> = {
  staff: "Сотрудники",
  windows: "Окна доставки",
  templates: "Шаблоны",
  prices: "Прайс",
  shop: "Магазин",
};
export function Settings({
  business,
  changed,
  tab,
  setTab,
  importClients,
}: {
  business: Business;
  changed: () => void;
  tab: SettingsTab;
  setTab: (tab: SettingsTab) => void;
  importClients: () => void;
}) {
  const [revision, setRevision] = useState(0),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [conflict, setConflict] = useState(false);
  const source = useRemote<ShopSettings>(
    businessPath(business.id, "settings"),
    revision,
  );
  const staff = useRemote<Staff[]>(
    businessPath(business.id, "staff"),
    revision,
  );
  const [draft, setDraft] = useState<ShopSettings | null>(null),
    [staffEditor, setStaffEditor] = useState<Staff | "new" | null>(null);
  useEffect(() => {
    if (source.data) setDraft(source.data);
  }, [source.data]);
  const owner = business.role === "owner";
  async function write(path: string, method: string, body: object) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await request(path, { method, body: JSON.stringify(body) });
      setConflict(false);
      setNotice("Сохранено");
      setRevision((r) => r + 1);
      changed();
      return true;
    } catch (e) {
      setError(errorText(e));
      setConflict(
        path === businessPath(business.id, "settings") &&
          e instanceof ApiError &&
          e.status === 409,
      );
      return false;
    } finally {
      setBusy(false);
    }
  }
  function saveSettings(e: FormEvent) {
    e.preventDefault();
    if (draft) void write(businessPath(business.id, "settings"), "PUT", draft);
  }
  return (
    <>
      <div className="tabs" role="tablist" aria-label="Разделы настроек">
        {Object.entries(tabs).map(([key, label]) => (
          <button
            className="tab"
            role="tab"
            key={key}
            aria-selected={tab === key}
            onClick={() => {
              setTab(key as SettingsTab);
              setNotice("");
              setError("");
            }}
          >
            {label}
          </button>
        ))}
      </div>
      {(error || source.error || staff.error) && (
        <Notice>{error || source.error || staff.error}</Notice>
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
        <p role="status" className="save-notice">
          {notice}
        </p>
      )}
      {tab === "staff" && (
        <section className="card">
          <div className="card-hd">
            <h2>Сотрудники</h2>
            <span className="spacer" />
            {owner && (
              <button
                className="btn sm primary"
                onClick={() => setStaffEditor("new")}
              >
                Пригласить
              </button>
            )}
          </div>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Имя</th>
                  <th>Роль</th>
                  <th>Телефон</th>
                  <th>Что видит</th>
                  <th>Доступ</th>
                </tr>
              </thead>
              <tbody>
                {staff.data?.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <button
                        className="plain-button row nowrap"
                        onClick={() =>
                          owner && s.role !== "owner" && setStaffEditor(s)
                        }
                        disabled={!owner || s.role === "owner"}
                      >
                        <Avatar name={s.name} />
                        <span className="b ink">{s.name}</span>
                      </button>
                    </td>
                    <td>{roleNames[s.role]}</td>
                    <td className="mono">{s.phone || "—"}</td>
                    <td className="small muted">{roleAccess[s.role]}</td>
                    <td>
                      <Toggle
                        checked={s.is_active}
                        disabled={!owner || busy || s.role === "owner"}
                        onChange={(active) =>
                          void write(
                            businessPath(business.id, `staff/${s.id}`),
                            "PUT",
                            { role: s.role, is_active: active },
                          )
                        }
                      >
                        {s.is_active ? "Активен" : "Отключён"}
                      </Toggle>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {staff.loading && <div className="empty">Загружаем сотрудников…</div>}
        </section>
      )}
      {tab === "windows" && draft && (
        <form onSubmit={saveSettings} className="card">
          <div className="card-hd">
            <h2>Окна доставки</h2>
            <span className="small muted">
              Сколько доставок берёт магазин в каждое окно
            </span>
          </div>
          <fieldset disabled={!owner || busy}>
            <div className="tbl-wrap">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Окно</th>
                    <th>Вместимость</th>
                    <th>Стоимость</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {draft.windows.map((w, i) => (
                    <tr key={i}>
                      <td>
                        <div className="window-times">
                          <input
                            aria-label={`Начало окна ${i + 1}`}
                            type="time"
                            required
                            value={w.start}
                            onChange={(e) =>
                              setDraft({
                                ...draft,
                                windows: draft.windows.map((v, j) =>
                                  i === j ? { ...v, start: e.target.value } : v,
                                ),
                              })
                            }
                          />
                          <span>–</span>
                          <input
                            aria-label={`Конец окна ${i + 1}`}
                            type="time"
                            required
                            value={w.end}
                            onChange={(e) =>
                              setDraft({
                                ...draft,
                                windows: draft.windows.map((v, j) =>
                                  i === j ? { ...v, end: e.target.value } : v,
                                ),
                              })
                            }
                          />
                        </div>
                      </td>
                      <td>
                        <input
                          className="compact-number mono"
                          type="number"
                          min={1}
                          max={999}
                          required
                          aria-label={`Вместимость окна ${i + 1}`}
                          value={w.capacity}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              windows: draft.windows.map((v, j) =>
                                i === j
                                  ? { ...v, capacity: Number(e.target.value) }
                                  : v,
                              ),
                            })
                          }
                        />
                      </td>
                      <td>
                        <div className="row nowrap">
                          <input
                            className="compact-number mono"
                            aria-label={`Стоимость окна ${i + 1}`}
                            type="number"
                            min={0}
                            step="0.01"
                            required
                            value={w.price}
                            onChange={(e) =>
                              setDraft({
                                ...draft,
                                windows: draft.windows.map((v, j) =>
                                  i === j ? { ...v, price: e.target.value } : v,
                                ),
                              })
                            }
                          />
                          <span className="small">сом</span>
                        </div>
                      </td>
                      <td>
                        <button
                          className="iconbtn"
                          type="button"
                          aria-label={`Убрать окно ${i + 1}`}
                          disabled={draft.windows.length <= 1}
                          onClick={() =>
                            setDraft({
                              ...draft,
                              windows: draft.windows.filter((_, j) => i !== j),
                            })
                          }
                        >
                          ×
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="card-bd stack">
              <div className="row">
                <Toggle
                  checked={draft.pickup_unlimited}
                  onChange={(pickup_unlimited) =>
                    setDraft({ ...draft, pickup_unlimited })
                  }
                >
                  Самовывоз без ограничений
                </Toggle>
                <Toggle
                  checked={draft.enforce_capacity}
                  onChange={(enforce_capacity) =>
                    setDraft({ ...draft, enforce_capacity })
                  }
                >
                  Не принимать заказ в окно, если оно заполнено
                </Toggle>
              </div>
              <div className="row">
                <button
                  className="btn"
                  type="button"
                  disabled={draft.windows.length >= 24}
                  onClick={() =>
                    setDraft({
                      ...draft,
                      windows: [
                        ...draft.windows,
                        {
                          start: "18:00",
                          end: "20:00",
                          capacity: 6,
                          price: "0.00",
                        },
                      ],
                    })
                  }
                >
                  Добавить окно
                </button>
                <button className="btn primary">Сохранить окна</button>
              </div>
            </div>
          </fieldset>
        </form>
      )}
      {tab === "templates" && <MessageTemplates business={business} />}
      {tab === "prices" && <PriceSettings business={business} />}
      {tab === "shop" && draft && (
        <form onSubmit={saveSettings} className="card">
          <div className="card-hd">
            <h2>Магазин</h2>
          </div>
          <div className="card-bd">
            <fieldset disabled={!owner || busy}>
              <div className="fgrid">
                {(
                  [
                    ["name", "Название"],
                    ["city", "Город"],
                    ["address", "Адрес"],
                    ["phone", "Телефон"],
                    ["whatsapp", "WhatsApp магазина"],
                  ] as const
                ).map(([key, label]) => (
                  <label className="field" key={key}>
                    {label}
                    {key === "phone" || key === "whatsapp" ? (
                      <PhoneInput
                        aria-label={label}
                        value={draft[key]}
                        onChange={(value) =>
                          setDraft({ ...draft, [key]: value })
                        }
                      />
                    ) : (
                      <input
                        aria-label={
                          key === "name" ? "Название магазина" : label
                        }
                        required={key === "name"}
                        value={draft[key]}
                        onChange={(e) =>
                          setDraft({ ...draft, [key]: e.target.value })
                        }
                      />
                    )}
                    {key === "whatsapp" && (
                      <span className="hint">
                        С этого номера пишут клиентам
                      </span>
                    )}
                  </label>
                ))}
                <label className="field">
                  Валюта
                  <select aria-label="Валюта" value="KGS" disabled>
                    <option value="KGS">сом (KGS)</option>
                  </select>
                </label>
                <label className="field">
                  Часы работы
                  <input
                    value={draft.opening_hours}
                    onChange={(e) =>
                      setDraft({ ...draft, opening_hours: e.target.value })
                    }
                  />
                </label>
                <label className="field">
                  Ссылка для клиентов
                  <input readOnly value={location.origin} />
                  <span className="hint">
                    Персональная ссылка на статус создаётся в заказе.
                  </span>
                </label>
                <details className="full">
                  <summary>Дополнительно</summary>
                  <label className="field">
                    Часовой пояс
                    <select
                      aria-label="Часовой пояс"
                      value={draft.timezone}
                      onChange={(e) =>
                        setDraft({ ...draft, timezone: e.target.value })
                      }
                    >
                      {Array.from(
                        new Set([
                          draft.timezone,
                          "Asia/Bishkek",
                          "Asia/Almaty",
                          "Asia/Tashkent",
                          "Europe/Moscow",
                        ]),
                      ).map((z) => (
                        <option key={z}>{z}</option>
                      ))}
                    </select>
                  </label>
                </details>
              </div>
              <div className="row section-actions">
                <button className="btn primary">Сохранить</button>
                <button className="btn" type="button" onClick={importClients}>
                  Импорт клиентов
                </button>
                <a
                  className="btn"
                  href={`/api/v1${businessPath(business.id, "customers/export")}?kind=xlsx`}
                >
                  Выгрузить всех клиентов
                </a>
              </div>
            </fieldset>
          </div>
        </form>
      )}
      {staffEditor && (
        <StaffEditor
          business={business}
          initial={staffEditor}
          close={() => setStaffEditor(null)}
          saved={(message) => {
            setStaffEditor(null);
            setNotice(message || "Сохранено");
            setRevision((r) => r + 1);
            changed();
          }}
        />
      )}
    </>
  );
}
function StaffEditor({
  business,
  initial,
  close,
  saved,
}: {
  business: Business;
  initial: Staff | "new";
  close: () => void;
  saved: (message?: string) => void;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [confirmDelete, setConfirmDelete] = useState(false);
  const existing = initial !== "new" ? initial : null;
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const d = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await request(
        businessPath(business.id, existing ? `staff/${existing.id}` : "staff"),
        {
          method: existing ? "PUT" : "POST",
          body: JSON.stringify(
            existing
              ? {
                  role: d.get("role"),
                  is_active: existing.is_active,
                  staff_phone: d.get("staff_phone"),
                }
              : Object.fromEntries(d),
          ),
        },
      );
      saved();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  if (existing && confirmDelete) {
    return (
      <Modal title="Удалить сотрудника?" close={close} busy={busy}>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError("");
            try {
              await request(businessPath(business.id, `staff/${existing.id}`), {
                method: "DELETE",
              });
              saved("Сотрудник удалён из магазина");
            } catch (e) {
              setError(errorText(e));
            } finally {
              setBusy(false);
            }
          }}
        >
          <div className="modal-body stack">
            {error && <Notice>{error}</Notice>}
            <p>
              <strong>{existing.name}</strong> потеряет доступ к этому магазину
              и исчезнет из списка сотрудников. История заказов и оплат
              сохранится.
            </p>
            <p className="muted">
              Если на сотруднике есть незавершённые заказы, сначала передайте их
              другому сотруднику или завершите. Курьера можно заменить и в
              заказе в пути.
            </p>
          </div>
          <footer className="modal-footer">
            <button
              type="button"
              autoFocus
              disabled={busy}
              onClick={() => {
                setConfirmDelete(false);
                setError("");
              }}
            >
              Отмена
            </button>
            <button className="staff-delete-button" disabled={busy}>
              {busy ? "Удаление…" : "Да, удалить сотрудника"}
            </button>
          </footer>
        </form>
      </Modal>
    );
  }
  return (
    <Modal
      title={existing ? existing.name : "Пригласить сотрудника"}
      close={close}
      busy={busy}
    >
      <form onSubmit={submit}>
        <div className="modal-body stack">
          {error && <Notice>{error}</Notice>}
          {!existing && (
            <>
              <label>
                Имя сотрудника
                <input name="name" required />
              </label>
              <label>
                Логин сотрудника
                <input name="username" required autoComplete="off" />
              </label>
              <label>
                Начальный пароль
                <input
                  name="password"
                  type="password"
                  required
                  minLength={12}
                  maxLength={128}
                  autoComplete="new-password"
                />
              </label>
            </>
          )}
          <label>
            Телефон сотрудника
            <PhoneInput
              name="staff_phone"
              defaultValue={existing?.phone || ""}
            />
          </label>
          <label>
            Роль сотрудника
            <select
              aria-label="Роль сотрудника"
              name="role"
              defaultValue={existing?.role || "manager"}
            >
              {["manager", "florist", "courier"].map((role) => (
                <option value={role} key={role}>
                  {roleNames[role]}
                </option>
              ))}
            </select>
          </label>
          {!existing && (
            <p className="muted">Передайте логин и пароль сотруднику лично.</p>
          )}
        </div>
        <footer className="modal-footer">
          <button type="button" onClick={close} disabled={busy}>
            Отмена
          </button>
          <button className="primary" disabled={busy}>
            {existing ? "Сохранить сотрудника" : "Создать сотрудника"}
          </button>
        </footer>
      </form>
      {existing && (
        <form
          className="modal-body stack"
          onSubmit={async (e) => {
            e.preventDefault();
            const form = e.currentTarget;
            setBusy(true);
            setError("");
            try {
              await request(
                businessPath(
                  business.id,
                  `staff/${existing.id}/reset-password`,
                ),
                {
                  method: "POST",
                  body: JSON.stringify({
                    password: new FormData(form).get("password"),
                  }),
                },
              );
              saved();
            } catch (e) {
              setError(errorText(e));
            } finally {
              setBusy(false);
            }
          }}
        >
          <h3>Восстановить доступ</h3>
          <label>
            Новый пароль сотрудника
            <input
              name="password"
              type="password"
              required
              minLength={12}
              maxLength={128}
              autoComplete="new-password"
            />
          </label>
          <button disabled={busy}>Восстановить доступ</button>
        </form>
      )}
      {existing && (
        <section className="modal-body stack staff-removal">
          <h3>Удалить сотрудника</h3>
          <p className="muted">
            Уберите сотрудника из магазина и закройте ему доступ к CRM. История
            его работы сохранится.
          </p>
          <button
            type="button"
            className="staff-delete-button"
            disabled={busy}
            onClick={() => {
              setError("");
              setConfirmDelete(true);
            }}
          >
            Удалить сотрудника
          </button>
        </section>
      )}
    </Modal>
  );
}
function PriceSettings({ business }: { business: Business }) {
  const [showHidden, setShowHidden] = useState(false);
  const [revision, setRevision] = useState(0),
    [offset, setOffset] = useState(0),
    [editor, setEditor] = useState<Product | "new" | null>(null),
    [error, setError] = useState("");
  const page = useRemote<Page<Product>>(
    businessPath(business.id, "products") +
      `?limit=50&offset=${offset}&include_hidden=${showHidden}`,
    revision,
  );
  async function update(product: Product, value: string) {
    if (value === product.price) return;
    try {
      await request(businessPath(business.id, `products/${product.id}`), {
        method: "PUT",
        body: JSON.stringify({
          name: product.name,
          price: value,
          version: product.version,
          active: product.active,
        }),
      });
      setRevision((r) => r + 1);
    } catch (e) {
      setError(errorText(e));
      setRevision((r) => r + 1);
    }
  }
  return (
    <>
      <section className="card">
        <div className="card-hd">
          <h2>Прайс</h2>
          <span className="small muted">
            Подсказки в форме заказа, цену можно менять в заказе
          </span>
          <span className="spacer" />
          <button
            className="btn xs"
            onClick={() => {
              setShowHidden(!showHidden);
              setOffset(0);
            }}
          >
            {showHidden ? "Скрыть архив" : "Архив"}
          </button>
          <button className="btn sm" onClick={() => setEditor("new")}>
            Добавить позицию
          </button>
        </div>
        {(error || page.error) && <Notice>{error || page.error}</Notice>}
        <div className="tbl-wrap">
          <table className="tbl price-table">
            <thead>
              <tr>
                <th>Позиция</th>
                <th className="num">Цена, сом</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {page.data?.results.map((p) => (
                <tr key={`${p.id}-${p.version}`}>
                  <td className="ink">
                    <div className="product-name">
                      <ProductPhoto url={p.photo_url} name={p.name} />
                      <button
                        className="plain-button"
                        onClick={() => setEditor(p)}
                      >
                        {p.name}
                      </button>
                    </div>
                  </td>
                  <td className="num">
                    <input
                      className="compact-number mono"
                      aria-label={`Цена ${p.name}`}
                      type="number"
                      min={0}
                      step="0.01"
                      defaultValue={p.price}
                      onBlur={(e) => {
                        if (e.target.validity.valid)
                          void update(p, e.target.value);
                      }}
                    />
                  </td>
                  <td>
                    <div className="product-actions">
                      <button
                        className="iconbtn"
                        aria-label={`${p.active === false ? "Вернуть" : "Скрыть"} ${p.name}`}
                        onClick={async () => {
                          try {
                            await request(
                              businessPath(business.id, `products/${p.id}`),
                              {
                                method: "PUT",
                                body: JSON.stringify({
                                  name: p.name,
                                  price: p.price,
                                  version: p.version,
                                  active: p.active === false,
                                }),
                              },
                            );
                            setRevision((r) => r + 1);
                          } catch (e) {
                            setError(errorText(e));
                          }
                        }}
                      >
                        {p.active === false ? "↶" : "×"}
                      </button>
                      <button
                        className="iconbtn"
                        aria-label={`Изменить ${p.name}`}
                        title="Изменить позицию"
                        onClick={() => setEditor(p)}
                      >
                        <Pencil size={16} aria-hidden="true" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!page.loading && !page.data?.count && (
          <div className="empty">
            Добавьте букеты, упаковку и услуги в прайс
          </div>
        )}
        <Pager
          count={page.data?.count || 0}
          offset={offset}
          setOffset={setOffset}
        />
      </section>
      {editor && (
        <ProductForm
          business={business}
          initial={editor === "new" ? undefined : editor}
          close={() => setEditor(null)}
          saved={() => {
            setEditor(null);
            setRevision((r) => r + 1);
          }}
        />
      )}
    </>
  );
}
function MessageTemplates({ business }: { business: Business }) {
  const [revision, setRevision] = useState(0),
    [conflict, setConflict] = useState(false);
  const source = useRemote<ReminderRules>(
    businessPath(business.id, "reminder-rules"),
    revision,
  );
  const [draft, setDraft] = useState<ReminderRules | null>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    if (source.data)
      setDraft({
        ...source.data,
        custom_templates: source.data.custom_templates || [],
        templates: Object.fromEntries(
          messageTemplates.map((t) => [
            t.id,
            source.data!.templates?.[t.id] ||
              (t.id === "lapsed"
                ? source.data!.inactive_template
                : ["d14", "d7", "d3", "d1"].includes(t.id)
                  ? source.data!.template
                  : t.text),
          ]),
        ),
      });
  }, [source.data]);
  return (
    <form
      className="stack"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!draft) return;
        setBusy(true);
        setError("");
        setNotice("");
        try {
          const saved = await request<ReminderRules>(
            businessPath(business.id, "reminder-rules"),
            {
              method: "PUT",
              body: JSON.stringify(draft),
            },
          );
          setDraft(saved);
          setConflict(false);
          setNotice("Шаблоны сохранены");
        } catch (e) {
          setError(errorText(e));
          setConflict(e instanceof ApiError && e.status === 409);
        } finally {
          setBusy(false);
        }
      }}
    >
      {(error || source.error) && <Notice>{error || source.error}</Notice>}
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
        <p role="status" className="save-notice">
          {notice}
        </p>
      )}
      {draft && (
        <>
          <section className="card">
            <div className="card-hd">
              <h2>Свои шаблоны</h2>
              <span className="spacer" />
              <button
                type="button"
                className="btn sm"
                disabled={
                  busy ||
                  business.role !== "owner" ||
                  draft.custom_templates.length >= 50
                }
                onClick={() => {
                  setDraft({
                    ...draft,
                    custom_templates: [
                      ...draft.custom_templates,
                      { id: newUuid(), name: "", text: "" },
                    ],
                  });
                  setNotice("");
                }}
              >
                Добавить шаблон
              </button>
              <button
                className="btn sm primary"
                disabled={busy || business.role !== "owner"}
              >
                Сохранить шаблоны
              </button>
            </div>
            <div className="card-bd">
              <p className="muted">
                Создайте текст для своего повода. Сохранённые шаблоны доступны
                команде магазина.
              </p>
              {!draft.custom_templates.length && (
                <p className="hint">Своих шаблонов пока нет.</p>
              )}
            </div>
          </section>
          {draft.custom_templates.map((template, index) => (
            <section className="card custom-template" key={template.id}>
              <div className="card-hd">
                <h2>{template.name || "Новый шаблон"}</h2>
                <span className="spacer" />
                {business.role === "owner" && (
                  <button
                    type="button"
                    className="btn sm danger"
                    disabled={busy}
                    onClick={() => {
                      setDraft({
                        ...draft,
                        custom_templates: draft.custom_templates.filter(
                          (t) => t.id !== template.id,
                        ),
                      });
                      setNotice("");
                    }}
                  >
                    Убрать шаблон
                  </button>
                )}
              </div>
              <div className="card-bd stack">
                <label className="field">
                  Название шаблона
                  <input
                    required
                    maxLength={100}
                    autoFocus={!template.name}
                    disabled={busy || business.role !== "owner"}
                    value={template.name}
                    onChange={(e) => {
                      setDraft({
                        ...draft,
                        custom_templates: draft.custom_templates.map((t, i) =>
                          i === index ? { ...t, name: e.target.value } : t,
                        ),
                      });
                      setNotice("");
                    }}
                  />
                </label>
                <label className="field">
                  Текст шаблона
                  <textarea
                    aria-label="Текст шаблона"
                    aria-describedby={`template-hint-${template.id}`}
                    required
                    rows={3}
                    maxLength={2000}
                    disabled={busy || business.role !== "owner"}
                    value={template.text}
                    onChange={(e) => {
                      setDraft({
                        ...draft,
                        custom_templates: draft.custom_templates.map((t, i) =>
                          i === index ? { ...t, text: e.target.value } : t,
                        ),
                      });
                      setNotice("");
                    }}
                  />
                  <span className="hint" id={`template-hint-${template.id}`}>
                    Подстановки:{" "}
                    {
                      "{имя}, {магазин}, {повод}, {получатель}, {номер}, {состав}, {дата}, {окно}, {адрес}, {сумма}, {ссылка}"
                    }
                  </span>
                </label>
              </div>
            </section>
          ))}
        </>
      )}
      {draft &&
        messageTemplates.map(({ id: key, name }) => (
          <section className="card" key={key}>
            <div className="card-hd">
              <h2>{name}</h2>
            </div>
            <div className="card-bd">
              <label className="field">
                <span className="sr-only">{name}</span>
                <textarea
                  aria-label={name}
                  rows={3}
                  disabled={business.role !== "owner"}
                  value={draft.templates[key]}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      templates: { ...draft.templates, [key]: e.target.value },
                    })
                  }
                />
                <span className="hint">
                  Подстановки:{" "}
                  {
                    "{имя}, {магазин}, {повод}, {получатель}, {номер}, {состав}, {дата}, {окно}, {адрес}, {сумма}, {ссылка}"
                  }
                </span>
              </label>
            </div>
          </section>
        ))}
      <div>
        <button
          className="btn primary"
          disabled={!draft || busy || business.role !== "owner"}
        >
          Сохранить шаблоны
        </button>
      </div>
    </form>
  );
}
