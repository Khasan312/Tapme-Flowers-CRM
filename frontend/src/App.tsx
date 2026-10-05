import { useEffect, useState, type FormEvent } from "react";
import {
  ClipboardList,
  Users,
  Flower2,
  Plus,
  LogOut,
  Truck,
  ArrowUpRight,
  Bell,
  Settings as SettingsIcon,
} from "lucide-react";
import { ApiError, businessPath, errorText, request } from "./api";
import { Notice } from "./components";
import { CustomerForm, OrderForm } from "./forms";
import type { Business, Customer, Order, User } from "./types";

import { OrderPanel, TaskBoard } from "./orders";
import { Settings, type SettingsTab } from "./settings";
import { GlobalSearch } from "./global-search";
import { Avatar, BrandMark, shopDay } from "./ui";
import { useRemote } from "./hooks";
import type { ShopSettings } from "./types";
import { CustomerTransfer } from "./customers";
import { Reminders } from "./reminders";
import { PublicOrderPage } from "./public";
import { PasswordPanel } from "./account";
import { CustomerDirectory } from "./customer-directory";
import { CustomerPage } from "./customer-page";
import { DeliveryDesk } from "./deliveries";
import { OrderDesk } from "./order-desk";

type View = "orders" | "customers" | "reminders" | "deliveries" | "settings";
const labels = {
  orders: "Заказы",
  customers: "Клиенты",
  reminders: "Напоминания",
  deliveries: "Доставка",
  settings: "Настройки",
};
const icons = {
  orders: ClipboardList,
  customers: Users,
  reminders: Bell,
  deliveries: Truck,
  settings: SettingsIcon,
};
const roles: Record<string, string> = {
  owner: "Владелец",
  manager: "Менеджер",
  florist: "Флорист",
  courier: "Курьер",
};

function Workspace() {
  const [newOrderCustomer, setNewOrderCustomer] = useState<Customer | null>(
    null,
  );
  const [user, setUser] = useState<User | null>(null),
    [businesses, setBusinesses] = useState<Business[]>([]);
  const [businessId, setBusinessId] = useState(""),
    [starting, setStarting] = useState(true),
    [loginBusy, setLoginBusy] = useState(false);
  const [view, setView] = useState<View>("orders"),
    [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [form, setForm] = useState<"orders" | "customers" | null>(null);
  const [detail, setDetail] = useState<Order | null>(null),
    [notice, setNotice] = useState("");
  const [customerDetail, setCustomerDetail] = useState<string | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState<SettingsTab>("staff");
  const [menuOpen, setMenuOpen] = useState(false);
  const business = businesses.find((b) => b.id === businessId);
  const office = business && ["owner", "manager"].includes(business.role);
  const shop = useRemote<ShopSettings>(
    office && businessId ? businessPath(businessId, "settings") : null,
    revision,
  );
  const overview = useRemote<{
    in_progress: number;
    deliveries: number;
    reminders: number;
  }>(
    office && business
      ? businessPath(business.id, "overview") +
          `?day=${shopDay(business.timezone)}`
      : null,
    revision,
  );
  const navCounts: Record<string, number | undefined> = {
    orders: overview.data?.in_progress,
    deliveries: overview.data?.deliveries,
    reminders: overview.data?.reminders,
  };
  useEffect(() => {
    function shortcut(e: KeyboardEvent) {
      if (
        (e.key.toLowerCase() === "n" || e.key.toLowerCase() === "т") &&
        office &&
        !(e.target as HTMLElement).closest(
          "input,textarea,select,dialog,[contenteditable]",
        )
      ) {
        e.preventDefault();
        setNewOrderCustomer(null);
        setForm("orders");
      }
    }
    document.addEventListener("keydown", shortcut);
    return () => document.removeEventListener("keydown", shortcut);
  }, [office]);
  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const current = await request<User>("/auth/me/");
        const choices = await request<Business[]>("/businesses/");
        if (live) {
          setUser(current);
          setBusinesses(choices);
          setBusinessId(choices[0]?.id || "");
        }
      } catch (e) {
        if (live && !(e instanceof ApiError && e.status === 403))
          setError(errorText(e));
      } finally {
        if (live) setStarting(false);
      }
    })();
    return () => {
      live = false;
    };
  }, []);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 5000);
    return () => clearTimeout(timer);
  }, [notice]);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoginBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const result = await request<{ user: User }>("/auth/login/", {
        method: "POST",
        body: JSON.stringify({
          username: data.get("username"),
          password: data.get("password"),
        }),
      });
      const choices = await request<Business[]>("/businesses/");
      setUser(result.user);
      setBusinesses(choices);
      setBusinessId(choices[0]?.id || "");
      setRevision((r) => r + 1);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setLoginBusy(false);
    }
  }
  async function signOut() {
    try {
      await request("/auth/logout/", { method: "POST" });
      setUser(null);
      setBusinesses([]);
      setBusinessId("");

      setError("");
      setForm(null);
      setDetail(null);
      setCustomerDetail(null);

      setPasswordOpen(false);
      setImportOpen(false);
      setView("orders");
      setMenuOpen(false);
      setNewOrderCustomer(null);
    } catch (e) {
      setError(errorText(e));
    }
  }
  function navigate(next: View) {
    setMenuOpen(false);
    setCustomerDetail(null);
    if (next === view) {
      setRevision((r) => r + 1);
      return;
    }

    setView(next);

    setError("");
  }
  function saved() {
    setForm(null);
    setRevision((r) => r + 1);

    setNotice(form === "orders" ? "Заказ создан" : "Клиент сохранён");
  }

  if (starting)
    return (
      <div className="loading-screen">
        <Flower2 size={36} />
        <p>Открываем рабочее пространство…</p>
      </div>
    );
  if (!user)
    return (
      <main className="login-page">
        <section className="login-story">
          <div className="brand">
            <span className="brand-mark">
              <Flower2 />
            </span>
            <span>
              tapme<small>Flowers</small>
            </span>
          </div>
          <div>
            <span className="eyebrow">КАЖДЫЙ БУКЕТ — ВАЖЕН</span>
            <h1>
              Больше внимания
              <br />
              цветам и людям.
            </h1>
            <p>
              Заказы, клиенты и команда вашего магазина
              <br />в одном рабочем пространстве.
            </p>
          </div>
          <span className="login-foot">Tapme Flowers · Бишкек</span>
        </section>
        <section className="login-panel">
          <form className="login-card" onSubmit={signIn}>
            <span className="eyebrow">ВАШ МАГАЗИН</span>
            <h2>С возвращением</h2>
            <p className="muted">Войдите, чтобы начать рабочий день.</p>
            {error && <Notice>{error}</Notice>}
            <label>
              Логин
              <input
                name="username"
                required
                autoComplete="username"
                autoFocus
              />
            </label>
            <label>
              Пароль
              <input
                name="password"
                type="password"
                required
                autoComplete="current-password"
              />
            </label>
            <button className="primary" disabled={loginBusy}>
              {loginBusy ? "Входим…" : "Войти в CRM"}
              <ArrowUpRight size={18} />
            </button>
            <p className="login-hint">
              Доступ сотрудникам выдаёт владелец магазина.
            </p>
          </form>
        </section>
      </main>
    );

  return (
    <div className="app-shell crm">
      <aside className="rail">
        <button
          className="brand plain-button"
          onClick={() => navigate("orders")}
          aria-label="На главную"
        >
          <span className="brand-mark">
            <BrandMark />
          </span>
          <span>
            <span className="brand-name">Tapme Flowers</span>
            <span className="brand-sub">Кабинет магазина</span>
          </span>
        </button>
        <nav className="nav">
          {(office
            ? ([
                "orders",
                "customers",
                "reminders",
                "deliveries",
                "settings",
              ] as View[])
            : (["orders"] as View[])
          ).map((key) => {
            const Icon = icons[key];
            return (
              <button
                className="nav-item"
                key={key}
                aria-current={view === key ? "page" : undefined}
                onClick={() => navigate(key)}
                title={labels[key]}
                aria-label={office ? labels[key] : "Мои задания"}
              >
                <Icon size={16} />
                {office ? labels[key] : "Мои задания"}
                {office && Boolean(navCounts[key]) && (
                  <span className="cnt" aria-hidden="true">
                    {navCounts[key]}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
        <div className="rail-foot">
          <Avatar name={business?.name || "Магазин"} />
          <div className="shop-switch">
            <button
              className="plain-button shop-n"
              onClick={() => {
                if (office) {
                  setSettingsTab("shop");
                  navigate("settings");
                }
              }}
            >
              {business?.name || "Магазин"}
            </button>
            <div className="shop-c">
              {[shop.data?.city, shop.data?.address]
                .filter(Boolean)
                .join(" · ") || "Контакты магазина"}
            </div>
            {businesses.length > 1 && (
              <select
                aria-label="Магазин"
                value={businessId}
                onChange={(e) => {
                  setBusinessId(e.target.value);
                  setForm(null);
                  setDetail(null);
                  setCustomerDetail(null);
                  setImportOpen(false);
                  setPasswordOpen(false);
                }}
              >
                {businesses.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>
      </aside>
      <main className="workspace">
        <header className="topbar">
          <div className="topbar-title">
            <h1>{office ? labels[view] : "Мои задания"}</h1>
            {view === "orders" && (
              <div className="sub">
                {new Intl.DateTimeFormat("ru-RU", {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                  timeZone: business?.timezone || "Asia/Bishkek",
                }).format(new Date())}
              </div>
            )}
          </div>
          {office && business && (
            <GlobalSearch
              key={business.id}
              business={business}
              openCustomer={(id) => {
                navigate("customers");
                setCustomerDetail(id);
              }}
              openOrder={setDetail}
            />
          )}
          <span className="spacer" />
          {office && (
            <button
              className="btn primary"
              aria-label="Новый заказ"
              title="Новый заказ · N"
              onClick={() => {
                setNewOrderCustomer(null);
                setForm("orders");
              }}
            >
              <Plus size={15} />
              Заказ
            </button>
          )}
          <div className="usermenu">
            <button
              className="ubtn"
              aria-label="Меню пользователя"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen(!menuOpen)}
            >
              <Avatar name={user.username} />
              <span>
                <span className="un">{user.username}</span>
                <span className="ur">
                  {business ? roles[business.role] : "Сотрудник"}
                </span>
              </span>
              <span aria-hidden="true">⌄</span>
            </button>
            {menuOpen && (
              <div className="menu" role="menu">
                <div className="lab">Учётная запись</div>
                <button
                  role="menuitem"
                  onClick={() => {
                    setMenuOpen(false);
                    setPasswordOpen(true);
                  }}
                >
                  Сменить личный пароль
                </button>
                {office && (
                  <button
                    role="menuitem"
                    onClick={() => {
                      setMenuOpen(false);
                      setImportOpen(true);
                    }}
                  >
                    Импорт клиентов
                  </button>
                )}
                <div className="sep" />
                <button
                  role="menuitem"
                  onClick={() => {
                    setMenuOpen(false);
                    void signOut();
                  }}
                >
                  <LogOut size={16} />
                  Выйти
                </button>
              </div>
            )}
          </div>
        </header>
        <div className="page-content">
          {view === "settings" && (
            <div className="page-hd">
              <h1>Настройки</h1>
            </div>
          )}
          {error && <Notice>{error}</Notice>}
          {!business ? (
            <div className="empty">
              <Flower2 size={38} />
              <h2>Магазин ещё не назначен</h2>
              <p>Обратитесь к владельцу, чтобы получить доступ.</p>
            </div>
          ) : office && view === "customers" ? (
            customerDetail ? (
              <CustomerPage
                key={customerDetail}
                business={business}
                customerId={customerDetail}
                externalRevision={revision}
                close={() => setCustomerDetail(null)}
                changed={() => setRevision((r) => r + 1)}
                openOrder={setDetail}
                newOrder={(c) => {
                  setNewOrderCustomer(c);
                  setForm("orders");
                }}
              />
            ) : (
              <CustomerDirectory
                business={business}
                revision={revision}
                openCustomer={setCustomerDetail}
                add={() => setForm("customers")}
                importClients={() => setImportOpen(true)}
              />
            )
          ) : office && view === "orders" ? (
            <OrderDesk
              key={business.id}
              business={business}
              revision={revision}
              openOrder={setDetail}
            />
          ) : office && view === "deliveries" ? (
            <DeliveryDesk
              business={business}
              revision={revision}
              openOrder={setDetail}
            />
          ) : !office ? (
            <TaskBoard
              key={business.id + business.role}
              business={business}
              openOrder={setDetail}
              refresh={revision}
            />
          ) : view === "settings" ? (
            <Settings
              key={business.id}
              business={business}
              tab={settingsTab}
              setTab={setSettingsTab}
              importClients={() => setImportOpen(true)}
              changed={() => {
                setRevision((r) => r + 1);
                void request<Business[]>("/businesses/")
                  .then(setBusinesses)
                  .catch((e) => setError(errorText(e)));
              }}
            />
          ) : view === "reminders" ? (
            <Reminders
              key={business.id}
              business={business}
              templates={() => {
                setSettingsTab("templates");
                navigate("settings");
              }}
              openCustomer={(id) => {
                navigate("customers");
                setCustomerDetail(id);
              }}
            />
          ) : null}
        </div>
      </main>
      {notice && (
        <div className="toast" role="status">
          {notice}
        </div>
      )}
      {business && form === "customers" && (
        <CustomerForm
          business={business}
          close={() => setForm(null)}
          saved={saved}
        />
      )}
      {business && form === "orders" && (
        <OrderForm
          business={business}
          initialCustomer={newOrderCustomer || undefined}
          close={() => setForm(null)}
          saved={saved}
        />
      )}
      {passwordOpen && <PasswordPanel close={() => setPasswordOpen(false)} />}
      {business && detail && (
        <OrderPanel
          key={detail.id}
          business={business}
          orderId={detail.id}
          close={() => setDetail(null)}
          changed={() => setRevision((r) => r + 1)}
        />
      )}
      {business && importOpen && (
        <CustomerTransfer
          business={business}
          close={() => setImportOpen(false)}
          changed={() => setRevision((r) => r + 1)}
        />
      )}
    </div>
  );
}

export default function App() {
  const match = location.pathname.match(/^\/track\/([^/]+)\/?$/);
  return match ? <PublicOrderPage token={match[1]} /> : <Workspace />;
}
