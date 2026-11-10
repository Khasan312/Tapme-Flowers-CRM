import {
  Fragment,
  useCallback,
  useEffect,
  useState,
  type FormEvent,
} from "react";
import {
  ClipboardList,
  Users,
  Flower2,
  Plus,
  LogOut,
  Truck,
  Bell,
  MessageCircle,
  Settings as SettingsIcon,
} from "lucide-react";
import { ApiError, businessPath, errorText, request } from "./api";
import { Notice } from "./components";
import { CustomerForm, OrderForm } from "./forms";
import type { Business, Customer, Order, User, Reminder, Point } from "./types";

import { OrderPanel, TaskBoard } from "./orders";
import { Settings, type SettingsTab } from "./settings";
import { GlobalSearch } from "./global-search";
import { Avatar, BrandMark, shopDay } from "./ui";
import { useRemote } from "./hooks";
import type { ShopSettings } from "./types";
import { CustomerTransfer } from "./customers";
import { Reminders } from "./reminders";
import { Chats } from "./chats";
import { ChatChannelPicker } from "./chat-channels";
import { InstagramInbox } from "./instagram-inbox";
import { useChatChannelNavigation } from "./chat-channel-navigation";
import type { ChatChannel } from "./chat-types";
import { useChatNotifications, ChatNotificationControls } from "./chat-extras";
import { clearChatDrafts } from "./chat-drafts";
import { PasswordPanel } from "./account";
import { FirstPasswordPage, SignInPage, platformUrl } from "./auth";
import PlatformApp from "./platform";
import { CustomerDirectory } from "./customer-directory";
import { CustomerPage } from "./customer-page";
import { DeliveryDesk } from "./deliveries";
import { PointSwitcher } from "./point-switcher";
import { OrderDesk } from "./order-desk";
import { startChatViewport } from "./chat-keyboard";
import { newUuid } from "./uuid";
import {
  accessibleRoute,
  homeRoute,
  routeUrl,
  useWorkspaceRoute,
  type View,
} from "./navigation";

const labels = {
  orders: "Заказы",
  chats: "Чаты",
  customers: "Клиенты",
  reminders: "Напоминания",
  deliveries: "Доставка",
  settings: "Настройки",
};
const icons = {
  orders: ClipboardList,
  chats: MessageCircle,
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
const signOutEvent = "tapme-sign-out";

function Workspace() {
  const measureTopbar = useCallback((node: HTMLElement | null) => {
    if (!node) return;
    const update = () =>
      node
        .closest<HTMLElement>(".app-shell")
        ?.style.setProperty(
          "--workspace-header-height",
          `${node.getBoundingClientRect().height}px`,
        );
    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  const [newOrderCustomer, setNewOrderCustomer] = useState<Customer | null>(
    null,
  );
  const [newOrderReminder, setNewOrderReminder] = useState<Pick<
    Reminder,
    "person" | "event"
  > | null>(null);
  const [user, setUser] = useState<User | null>(null),
    [businesses, setBusinesses] = useState<Business[]>([]);
  const [starting, setStarting] = useState(true),
    [loginBusy, setLoginBusy] = useState(false);
  const { route: requestedRoute, go } = useWorkspaceRoute();
  const route = user
    ? accessibleRoute(requestedRoute, businesses)
    : requestedRoute;
  const {
    view,
    settingsTab,
    businessId,
    pointId,
    customerId: customerDetail,
    orderId,
    chatId,
    chatChannel,
  } = route;
  const chatDestination = useChatChannelNavigation(user?.id || "", route);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [settingsRevision, setSettingsRevision] = useState(0);
  const [form, setForm] = useState<"orders" | "customers" | null>(null);
  const [notice, setNotice] = useState("");
  const [importOpen, setImportOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const selectedBusiness = businesses.find((b) => b.id === businessId);
  const business = selectedBusiness
    ? { ...selectedBusiness, point_id: pointId }
    : undefined;
  const points = useRemote<Point[]>(
    user && businessId ? businessPath(businessId, "points") : null,
    settingsRevision,
  );
  const [pointContextReady, setPointContextReady] = useState("");
  useEffect(() => {
    if (!user || !businessId) setPointContextReady("");
    else if (points.data || points.error) setPointContextReady(businessId);
  }, [user, businessId, points.data, points.error]);
  useEffect(() => {
    if (!user || !businessId || !points.data) return;
    const active = points.data.filter((p) => p.active);
    const key = `tapme.point.${user.id}.${businessId}`;
    let stored = "";
    try {
      stored = localStorage.getItem(key) || "";
    } catch {
      /* private storage */
    }
    const wanted = pointId || stored;
    const valid = wanted === "all" || active.some((p) => p.id === wanted);
    const next =
      active.length === 1 && points.data.length === 1
        ? active[0].id
        : valid
          ? wanted
          : "all";
    if (next !== pointId) go({ ...route, pointId: next }, "replace");
    try {
      localStorage.setItem(key, next);
    } catch {
      /* private storage */
    }
  }, [user, businessId, pointId, points.data, go, route]);
  const office = business && ["owner", "manager"].includes(business.role);
  useEffect(() => {
    if (office && view === "chats") return startChatViewport(window, document);
  }, [office, view]);
  useEffect(() => {
    if (user && !starting) go(route, "replace");
  }, [user, starting, route, go]);
  useEffect(() => {
    setForm(null);
    setImportOpen(false);
    setPasswordOpen(false);
    setMenuOpen(false);
    setNewOrderCustomer(null);
    setNewOrderReminder(null);
    setError("");
    setNotice("");
  }, [requestedRoute]);
  const shop = useRemote<ShopSettings>(
    office && businessId && pointId && pointId !== "all"
      ? businessPath(businessId, `points/${pointId}`)
      : null,
    settingsRevision,
  );
  const overview = useRemote<{
    pending: number;
    in_progress: number;
    deliveries: number;
    reminders: number;
  }>(
    office && business
      ? businessPath(business.id, "overview") +
          `?day=${shopDay(business.timezone)}&point=${pointId || "all"}`
      : null,
    revision + settingsRevision,
  );
  const chatNotifications = useChatNotifications(
    office ? businessId : null,
    user?.id || "",
    view === "chats" ? chatId : null,
  );
  const navCounts: Record<string, number | undefined> = {
    chats: chatNotifications.waiting,
    orders: overview.data
      ? overview.data.in_progress + overview.data.pending
      : undefined,
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
        setNewOrderReminder(null);
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
        if (current.is_platform_admin) {
          location.replace(platformUrl());
          return;
        }
        const choices = current.must_change_password
          ? []
          : await request<Business[]>("/businesses/");
        if (live) {
          setUser(current);
          setBusinesses(choices);
        }
      } catch (e) {
        if (live) {
          if (e instanceof ApiError && e.status === 403) clearChatDrafts();
          else setError(errorText(e));
        }
      } finally {
        if (live) setStarting(false);
      }
    })();
    return () => {
      live = false;
    };
  }, []);
  useEffect(() => {
    function onStorage(event: StorageEvent) {
      if (event.key !== signOutEvent) return;
      clearChatDrafts();
      window.location.reload();
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
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
      if (result.user.is_platform_admin) {
        location.assign(platformUrl());
        return;
      }
      const choices = result.user.must_change_password
        ? []
        : await request<Business[]>("/businesses/");
      setUser(result.user);
      setBusinesses(choices);
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
      clearChatDrafts();
      try {
        localStorage.setItem(signOutEvent, newUuid());
      } catch {
        /* Storage may be unavailable. */
      }
      setUser(null);
      setBusinesses([]);
      go(homeRoute, "replace");

      setError("");
      setForm(null);

      setPasswordOpen(false);
      setImportOpen(false);
      setMenuOpen(false);
      setNewOrderCustomer(null);
      setNewOrderReminder(null);
    } catch (e) {
      setError(errorText(e));
    }
  }
  function navigate(
    next: View,
    tab: SettingsTab = next === "settings" && settingsTab === "reminders"
      ? "staff"
      : settingsTab,
  ) {
    setMenuOpen(false);
    window.scrollTo(0, 0);
    if (next === "chats") {
      go(chatDestination());
      return;
    }
    const destination = {
      ...route,
      view: next,
      orderSection: "orders" as const,
      settingsTab: tab,
      customerId: null,
      orderId: null,
      chatId: null,
    };
    if (routeUrl(destination) === routeUrl(route)) {
      setRevision((r) => r + 1);
      return;
    }
    go(destination);
  }
  function openCustomer(id: string) {
    go({ ...route, view: "customers", customerId: id, orderId: null });
  }
  function selectChatChannel(channel: ChatChannel) {
    go(chatDestination(channel));
  }
  async function openChat(customerId: string) {
    if (!business) return;
    try {
      const chat = await request<{ id: string }>(
        businessPath(business.id, "chats"),
        {
          method: "POST",
          body: JSON.stringify({ customer_id: customerId }),
        },
      );
      go({
        ...route,
        view: "chats",
        chatChannel: "whatsapp",
        chatId: chat.id,
        customerId: null,
        orderId: null,
      });
    } catch (e) {
      setError(errorText(e));
    }
  }
  function openOrder(order: Order) {
    go({ ...route, orderId: order.id });
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
    return <SignInPage onSubmit={signIn} error={error} busy={loginBusy} />;
  if (user.must_change_password)
    return (
      <FirstPasswordPage
        signedOut={() => void signOut()}
        changed={() => location.reload()}
      />
    );

  if (business && pointContextReady !== business.id)
    return (
      <div className="loading-screen">
        <p>Загружаем точки магазина…</p>
      </div>
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

        <nav className="nav" aria-label="Основные разделы">
          {(office
            ? ([
                "orders",
                "chats",
                "customers",
                "reminders",
                "deliveries",
                "settings",
              ] as View[])
            : (["orders"] as View[])
          ).map((key) => {
            const Icon = icons[key];
            return (
              <Fragment key={key}>
                <button
                  className="nav-item"
                  aria-current={view === key ? "page" : undefined}
                  onClick={() => navigate(key)}
                  title={labels[key]}
                  aria-label={office ? labels[key] : "Мои задания"}
                >
                  <Icon size={16} />
                  <span className="nav-label-full">
                    {office ? labels[key] : "Мои задания"}
                  </span>
                  {office && key === "reminders" && (
                    <span className="nav-label-short" aria-hidden="true">
                      Напом.
                    </span>
                  )}
                  {office && Boolean(navCounts[key]) && (
                    <span className="cnt" aria-hidden="true">
                      {navCounts[key]}
                    </span>
                  )}
                </button>
                {key === "chats" && office && (
                  <ChatChannelPicker
                    placement="sidebar"
                    value={view === "chats" ? chatChannel : null}
                    unread={
                      chatNotifications.unread -
                      chatNotifications.instagramUnread
                    }
                    instagramUnread={chatNotifications.instagramUnread}
                    select={selectChatChannel}
                  />
                )}
              </Fragment>
            );
          })}
        </nav>
        <div className="rail-foot">
          {!(points.data && points.data.length > 1) && (
            <Avatar name={business?.name || "Магазин"} />
          )}
          <div className="shop-switch">
            {points.data && points.data.length > 1 ? (
              <PointSwitcher
                key={businessId}
                businessName={business?.name || "Магазин"}
                points={points.data}
                value={pointId || "all"}
                onChange={(id) =>
                  go({
                    ...route,
                    pointId: id,
                    orderId: null,
                    customerId: null,
                    chatId: null,
                  })
                }
              />
            ) : (
              <>
                <button
                  className="plain-button shop-n"
                  onClick={() => {
                    if (office) {
                      navigate("settings", "shop");
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
              </>
            )}
            {businesses.length > 1 && (
              <select
                aria-label="Магазин"
                value={businessId}
                onChange={(e) => {
                  go(
                    accessibleRoute(
                      {
                        ...route,
                        businessId: e.target.value,
                        chatChannel: "whatsapp",
                        pointId: "",
                        customerId: null,
                        orderId: null,
                        chatId: null,
                      },
                      businesses,
                    ),
                  );
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
        <header className="topbar" ref={measureTopbar}>
          <div className="topbar-title">
            <h1>{office ? labels[view] : "Мои задания"}</h1>
            {points.data && points.data.length > 1 && (
              <span className="point-badge">
                {pointId === "all"
                  ? "Все точки"
                  : points.data.find((p) => p.id === pointId)?.short_name}
              </span>
            )}
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
              key={business.id + pointId}
              business={business}
              openCustomer={openCustomer}
              openOrder={openOrder}
            />
          )}
          {office && (
            <ChatNotificationControls
              state={chatNotifications}
              open={(id, channel) =>
                go({
                  ...route,
                  view: "chats",
                  chatChannel: channel,
                  chatId: id,
                  customerId: null,
                  orderId: null,
                })
              }
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
                setNewOrderReminder(null);
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
        <div
          className={`page-content${office && view === "chats" ? " chat-inbox-content" : ""}`}
          key={businessId + pointId}
        >
          {view === "settings" && settingsTab !== "reminders" && (
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
                close={() => navigate("customers")}
                changed={() => setRevision((r) => r + 1)}
                openOrder={openOrder}
                newOrder={(c) => {
                  setNewOrderCustomer(c);
                  setNewOrderReminder(null);
                  setForm("orders");
                }}
                openChat={() => void openChat(customerDetail)}
              />
            ) : (
              <CustomerDirectory
                business={business}
                revision={revision}
                openCustomer={openCustomer}
                add={() => setForm("customers")}
                importClients={() => setImportOpen(true)}
              />
            )
          ) : office && view === "chats" ? (
            <div className="chat-inbox-page" data-channel={chatChannel}>
              <ChatChannelPicker
                placement="mobile"
                value={chatChannel}
                unread={
                  chatNotifications.unread - chatNotifications.instagramUnread
                }
                instagramUnread={chatNotifications.instagramUnread}
                select={selectChatChannel}
              />
              {chatChannel === "instagram" ? (
                <InstagramInbox
                  userId={user.id}
                  activityRevision={chatNotifications.activityRevision}
                  workspaceRevision={revision}
                  key={business.id}
                  business={business}
                  chatId={chatId}
                  select={(id) => go({ ...route, chatId: id })}
                  settings={() => navigate("settings", "channels")}
                  openCustomer={openCustomer}
                  openOrder={(id) => go({ ...route, orderId: id })}
                  newOrder={(c) => {
                    setNewOrderCustomer(c);
                    setNewOrderReminder(null);
                    setForm("orders");
                  }}
                />
              ) : (
                <Chats
                  userId={user.id}
                  activityRevision={chatNotifications.activityRevision}
                  workspaceRevision={revision}
                  key={business.id}
                  business={business}
                  chatId={chatId}
                  select={(id) => go({ ...route, chatId: id })}
                  settings={() => navigate("settings", "channels")}
                  openCustomer={openCustomer}
                  openOrder={(id) => go({ ...route, orderId: id })}
                  newOrder={(c) => {
                    setNewOrderCustomer(c);
                    setNewOrderReminder(null);
                    setForm("orders");
                  }}
                />
              )}
            </div>
          ) : office && view === "orders" ? (
            <OrderDesk
              key={business.id}
              business={business}
              revision={revision}
              openOrder={openOrder}
              section={route.orderSection}
              chooseSection={(orderSection) => {
                go({ ...route, orderSection, orderId: null });
                window.scrollTo(0, 0);
              }}
            />
          ) : office && view === "deliveries" ? (
            <DeliveryDesk
              business={business}
              revision={revision}
              openOrder={openOrder}
            />
          ) : !office && points.data?.filter((p) => p.active).length === 0 ? (
            <div className="card empty">
              Владелец ещё не назначил вам точку. Обратитесь к владельцу
              магазина.
            </div>
          ) : !office ? (
            <TaskBoard
              key={business.id + business.role}
              business={business}
              openOrder={openOrder}
              refresh={revision}
            />
          ) : view === "settings" ? (
            <Settings
              key={business.id}
              business={business}
              tab={settingsTab}
              setTab={(tab: SettingsTab) => navigate("settings", tab)}
              importClients={() => setImportOpen(true)}
              openReminders={() => navigate("reminders")}
              changed={() => {
                setRevision((r) => r + 1);
                setSettingsRevision((r) => r + 1);
                void request<Business[]>("/businesses/")
                  .then(setBusinesses)
                  .catch((e) => setError(errorText(e)));
              }}
            />
          ) : view === "reminders" ? (
            <Reminders
              key={business.id}
              business={business}
              settings={() => navigate("settings", "reminders")}
              openOrder={(id) => go({ ...route, orderId: id })}
              createOrder={(row) => {
                void request<Customer>(
                  businessPath(business.id, `customers/${row.customer_id}`),
                )
                  .then((customer) => {
                    setNewOrderCustomer(customer);
                    setNewOrderReminder(row);
                    setForm("orders");
                  })
                  .catch((e) => setError(errorText(e)));
              }}
              openCustomer={openCustomer}
              openChat={(id) => void openChat(id)}
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
          initialSource={
            view === "chats" && newOrderCustomer ? "WhatsApp" : undefined
          }
          initialReminder={newOrderReminder || undefined}
          close={() => setForm(null)}
          saved={saved}
        />
      )}
      {passwordOpen && <PasswordPanel close={() => setPasswordOpen(false)} />}
      {business && orderId && (
        <OrderPanel
          key={business.id + orderId}
          business={business}
          orderId={orderId}
          close={() => go({ ...route, orderId: null })}
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
  if (
    location.pathname === platformUrl() ||
    location.pathname === platformUrl().replace(/\/$/, "")
  )
    return <PlatformApp />;
  return <Workspace />;
}
