import { useEffect, useState, type FormEvent } from "react";
import {
  Building2,
  Check,
  Copy,
  Flower2,
  History,
  LogOut,
  Plus,
  RefreshCw,
  Search,
} from "lucide-react";
import { ApiError, errorText, request } from "./api";
import { crmUrl, FirstPasswordPage, platformUrl, SignInPage } from "./auth";
import { Modal, Notice } from "./components";
import type { User } from "./types";
import "./platform.css";

type Owner = {
  id: string;
  username: string;
  name: string;
  is_active: boolean;
  last_login: string | null;
  must_change_password: boolean;
};
type Company = {
  id: string;
  name: string;
  currency: string;
  timezone: string;
  point_count: number;
  member_count: number;
  owners: Owner[];
};
type Credentials = { username: string; temporary_password: string };
type Access = { company: string; credentials: Credentials };
type AuditEvent = {
  id: number;
  action: string;
  created_at: string;
  actor: string;
  business: string;
  owner: string;
};
const date = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat("ru-RU", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value))
    : "Ещё не входил";
const plural = new Intl.PluralRules("ru-RU");
function count(value: number, one: string, few: string, many: string) {
  const form = plural.select(value);
  return `${value} ${form === "one" ? one : form === "few" ? few : many}`;
}

function NewCompany({
  close,
  created,
}: {
  close: () => void;
  created: (value: Access) => void;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const data = new FormData(e.currentTarget);
    try {
      const result = await request<{
        business: Company;
        credentials: Credentials;
      }>("/platform/businesses/", {
        method: "POST",
        body: JSON.stringify({
          name: data.get("name"),
          owner_name: data.get("owner_name"),
          owner_username: data.get("owner_username"),
        }),
      });
      created({
        company: result.business.name,
        credentials: result.credentials,
      });
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Подключить магазин" close={close} busy={busy}>
      <form className="modal-body stack" onSubmit={submit}>
        <p className="muted">
          Создадим компанию, основную точку и первую учётную запись владельца.
        </p>
        {error && <Notice>{error}</Notice>}
        <label>
          Название компании
          <input
            name="name"
            placeholder="Dion Flowers"
            maxLength={150}
            required
            autoFocus
          />
        </label>
        <label>
          Имя владельца
          <input
            name="owner_name"
            maxLength={150}
            required
            autoComplete="name"
          />
        </label>
        <label>
          Логин владельца
          <input
            name="owner_username"
            placeholder="dion.aigul"
            pattern="[a-zA-Z0-9][a-zA-Z0-9._@+\-]*"
            maxLength={150}
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            autoComplete="off"
            required
          />
        </label>
        <p className="muted">
          Временный пароль создадим автоматически. При первом входе владелец
          задаст свой и сможет добавить сотрудников.
        </p>
        <button className="primary" disabled={busy}>
          {busy ? "Создаём…" : "Создать магазин и доступ"}
        </button>
      </form>
    </Modal>
  );
}

function AccessDetails({ value, close }: { value: Access; close: () => void }) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const url = `${location.origin}${crmUrl()}`;
  const message = `${value.company} — доступ в TapMe Flowers\n${url}\nЛогин: ${value.credentials.username}\nВременный пароль: ${value.credentials.temporary_password}\nПри первом входе задайте свой пароль.`;
  async function copy() {
    try {
      await navigator.clipboard.writeText(message);
      setCopied(true);
      setError("");
    } catch {
      setError(
        "Не удалось скопировать автоматически. Выделите и скопируйте доступ вручную.",
      );
    }
  }
  return (
    <Modal title="Доступ владельца готов" close={close}>
      <div className="modal-body stack">
        <p>
          <strong>{value.company}</strong> · Владелец магазина
        </p>
        <p className="muted">
          Передайте эти данные владельцу лично. Пароль показывается только
          сейчас; при потере можно выдать новый.
        </p>
        <dl className="platform-credentials">
          <dt>Вход в CRM</dt>
          <dd>
            <a href={url}>{url}</a>
          </dd>
          <dt>Логин</dt>
          <dd>{value.credentials.username}</dd>
          <dt>Временный пароль</dt>
          <dd>{value.credentials.temporary_password}</dd>
        </dl>
        {error && <Notice>{error}</Notice>}
        <button className="primary" onClick={() => void copy()}>
          {copied ? <Check size={16} /> : <Copy size={16} />}
          {copied ? "Доступ скопирован" : "Скопировать доступ"}
        </button>
        <button onClick={close}>Доступ сохранён, закрыть</button>
      </div>
    </Modal>
  );
}

function OwnerAccess({
  company,
  close,
  reset,
}: {
  company: Company;
  close: () => void;
  reset: (value: Access) => void;
}) {
  const [selected, setSelected] = useState<Owner | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function restore() {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      const credentials = await request<Credentials>(
        `/platform/businesses/${company.id}/owners/${selected.id}/reset-password/`,
        { method: "POST" },
      );
      reset({ company: company.name, credentials });
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title={`Владелец · ${company.name}`} close={close} busy={busy}>
      <div className="modal-body stack">
        {error && <Notice>{error}</Notice>}
        {selected ? (
          <>
            <h3>Выдать новый временный пароль?</h3>
            <p>
              Учётная запись: <strong>{selected.username}</strong>. Текущий
              пароль перестанет работать, открытые сессии завершатся. При
              следующем входе потребуется смена пароля.
            </p>
            <button
              className="primary"
              disabled={busy}
              onClick={() => void restore()}
            >
              {busy ? "Восстанавливаем…" : "Выдать новый пароль"}
            </button>
            <button disabled={busy} onClick={() => setSelected(null)}>
              Назад
            </button>
          </>
        ) : (
          <>
            {company.owners.length === 0 && (
              <p>
                У компании нет активного назначения владельца. Проверьте учётные
                записи перед восстановлением.
              </p>
            )}
            {company.owners.map((owner) => (
              <section className="platform-owner" key={owner.id}>
                <h3>{owner.name || owner.username}</h3>
                <p className="platform-mono">{owner.username}</p>
                <p className="muted">
                  Последний вход: {date(owner.last_login)}
                </p>
                <p>
                  {!owner.is_active
                    ? "Учётная запись отключена"
                    : owner.must_change_password
                      ? "Ожидает смены временного пароля"
                      : "Доступ готов"}
                </p>
                <button
                  disabled={!owner.is_active}
                  onClick={() => setSelected(owner)}
                >
                  Восстановить доступ
                </button>
              </section>
            ))}
            <p className="muted">
              Менеджеров, флористов и курьеров владелец добавляет
              самостоятельно: CRM → Настройки → Сотрудники.
            </p>
          </>
        )}
      </div>
    </Modal>
  );
}

export default function PlatformApp() {
  useEffect(() => {
    const previous = document.title;
    document.title = "Панель TapMe — Магазины";
    return () => {
      document.title = previous;
    };
  }, []);
  const [user, setUser] = useState<User | null>(null);
  const [starting, setStarting] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [companies, setCompanies] = useState<Company[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [view, setView] = useState<"companies" | "events">("companies");
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [newCompany, setNewCompany] = useState(false);
  const [access, setAccess] = useState<Access | null>(null);
  const [selected, setSelected] = useState<Company | null>(null);
  useEffect(() => {
    let live = true;
    request<User>("/auth/me/")
      .then((value) => {
        if (live) setUser(value);
      })
      .catch((e) => {
        if (live && !(e instanceof ApiError && e.status === 403))
          setError(errorText(e));
      })
      .finally(() => {
        if (live) setStarting(false);
      });
    return () => {
      live = false;
    };
  }, []);
  async function refresh() {
    setLoading(true);
    setError("");
    try {
      if (view === "companies")
        setCompanies(await request<Company[]>("/platform/businesses/"));
      else setEvents(await request<AuditEvent[]>("/platform/events/"));
    } catch (e) {
      setError(errorText(e));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    if (user?.is_platform_admin && !user.must_change_password) void refresh();
  }, [user, view]);
  async function signIn(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(e.currentTarget);
    try {
      const result = await request<{ user: User }>("/auth/login/", {
        method: "POST",
        body: JSON.stringify({
          username: data.get("username"),
          password: data.get("password"),
        }),
      });
      setUser(result.user);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function signOut() {
    setBusy(true);
    try {
      await request("/auth/logout/", { method: "POST" });
      setUser(null);
      setCompanies([]);
      setEvents([]);
      setAccess(null);
      setSelected(null);
      setNewCompany(false);
      setError("");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  function issued(value: Access) {
    setNewCompany(false);
    setSelected(null);
    setAccess(value);
    void refresh();
  }
  if (starting)
    return (
      <div className="loading-screen">
        <Flower2 size={36} />
        <p>Открываем панель TapMe…</p>
      </div>
    );
  if (!user)
    return <SignInPage platform onSubmit={signIn} busy={busy} error={error} />;
  if (user.must_change_password)
    return (
      <FirstPasswordPage
        signedOut={() => void signOut()}
        changed={() => location.reload()}
      />
    );
  if (!user.is_platform_admin)
    return (
      <main className="platform-denied">
        <Flower2 size={32} />
        <h1>Панель команды TapMe</h1>
        <p>
          Вы вошли как {user.username}. Эта учётная запись предназначена для
          работы в магазине.
        </p>
        <a className="primary" href={crmUrl()}>
          Открыть CRM магазина
        </a>
        <button disabled={busy} onClick={() => void signOut()}>
          Войти другой учётной записью
        </button>
        {error && <Notice>{error}</Notice>}
      </main>
    );
  const filtered = companies.filter((c) =>
    `${c.name} ${c.owners.map((o) => `${o.username} ${o.name}`).join(" ")}`
      .toLocaleLowerCase()
      .includes(search.toLocaleLowerCase()),
  );
  return (
    <div className="crm platform-shell">
      <aside className="platform-sidebar">
        <a className="platform-brand" href={platformUrl()}>
          <Flower2 size={30} />
          <span>
            TapMe<small>Управление платформой</small>
          </span>
        </a>
        <nav aria-label="Панель TapMe">
          <button
            className={view === "companies" ? "active" : ""}
            onClick={() => setView("companies")}
          >
            <Building2 size={18} />
            Магазины<span>{companies.length}</span>
          </button>
          <button
            className={view === "events" ? "active" : ""}
            onClick={() => setView("events")}
          >
            <History size={18} />
            Журнал действий
          </button>
        </nav>
        <footer>
          <span>
            {user.username}
            <small>Администратор TapMe</small>
          </span>
          <button
            aria-label="Выйти"
            disabled={busy}
            onClick={() => void signOut()}
          >
            <LogOut size={18} />
          </button>
        </footer>
      </aside>
      <main className="platform-main">
        <header className="platform-heading">
          <div>
            <p className="eyebrow">ПЛАТФОРМА TAPME</p>
            <h1>{view === "companies" ? "Магазины" : "Журнал действий"}</h1>
            <p className="muted">
              {view === "companies"
                ? "Подключение компаний и первый доступ владельцев."
                : "Последние 100 действий администраторов платформы."}
            </p>
          </div>
          <div className="platform-actions">
            <button
              aria-label="Обновить"
              disabled={loading}
              onClick={() => void refresh()}
            >
              <RefreshCw size={17} />
            </button>
            {view === "companies" && (
              <button className="primary" onClick={() => setNewCompany(true)}>
                <Plus size={17} />
                Подключить магазин
              </button>
            )}
          </div>
        </header>
        {error && <Notice>{error}</Notice>}
        {view === "companies" ? (
          <>
            <div className="platform-toolbar">
              <p>
                {count(companies.length, "компания", "компании", "компаний")} ·{" "}
                {count(
                  companies.reduce((n, c) => n + c.point_count, 0),
                  "точка",
                  "точки",
                  "точек",
                )}{" "}
                ·{" "}
                {count(
                  companies.reduce((n, c) => n + c.member_count, 0),
                  "пользователь",
                  "пользователя",
                  "пользователей",
                )}
              </p>
              <label className="platform-search">
                <Search size={17} />
                <input
                  aria-label="Найти магазин или владельца"
                  placeholder="Магазин или владелец"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </label>
            </div>
            <div className="platform-table-wrap">
              <table className="platform-table">
                <thead>
                  <tr>
                    <th>Компания</th>
                    <th>Точки</th>
                    <th>Сотрудники</th>
                    <th>Владелец</th>
                    <th>Первый доступ</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((company) => (
                    <tr key={company.id}>
                      <td data-label="Компания">
                        <strong>{company.name}</strong>
                        <small>
                          {company.currency} · {company.timezone}
                        </small>
                      </td>
                      <td data-label="Точки">{company.point_count}</td>
                      <td data-label="Сотрудники">{company.member_count}</td>
                      <td data-label="Владелец">
                        {company.owners.length ? (
                          company.owners.map((owner) => (
                            <div key={owner.id}>
                              <span>{owner.name || owner.username}</span>
                              {owner.name && (
                                <small className="platform-mono">
                                  {owner.username}
                                </small>
                              )}
                            </div>
                          ))
                        ) : (
                          <span className="muted">Не назначен</span>
                        )}
                      </td>
                      <td data-label="Первый доступ">
                        <button onClick={() => setSelected(company)}>
                          Доступ владельца
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!filtered.length && (
                <div className="platform-empty">
                  <Building2 size={28} />
                  <h2>
                    {loading
                      ? "Загружаем магазины…"
                      : search
                        ? "Ничего не найдено"
                        : "Подключите первый магазин"}
                  </h2>
                  <p className="muted">
                    {search
                      ? "Попробуйте другое название или логин владельца."
                      : "Создайте компанию и передайте первый доступ её владельцу."}
                  </p>
                </div>
              )}
            </div>
            <p className="platform-help">
              Мы выдаём доступ владельцу. Командой и ролями внутри магазина он
              управляет самостоятельно.
            </p>
          </>
        ) : (
          <div className="platform-table-wrap">
            <table className="platform-table">
              <thead>
                <tr>
                  <th>Когда</th>
                  <th>Действие</th>
                  <th>Компания</th>
                  <th>Владелец</th>
                  <th>Администратор</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.id}>
                    <td data-label="Когда">{date(event.created_at)}</td>
                    <td data-label="Действие">
                      {event.action === "business_created"
                        ? "Магазин подключён"
                        : "Доступ восстановлен"}
                    </td>
                    <td data-label="Компания">{event.business}</td>
                    <td data-label="Владелец">{event.owner}</td>
                    <td data-label="Администратор">{event.actor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!events.length && (
              <p className="platform-empty">
                {loading ? "Загружаем журнал…" : "Действий пока нет."}
              </p>
            )}
          </div>
        )}
      </main>
      {newCompany && (
        <NewCompany close={() => setNewCompany(false)} created={issued} />
      )}
      {selected && (
        <OwnerAccess
          company={selected}
          close={() => setSelected(null)}
          reset={issued}
        />
      )}
      {access && <AccessDetails value={access} close={() => setAccess(null)} />}
    </div>
  );
}
