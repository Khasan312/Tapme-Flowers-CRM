import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";
import { submitLogin } from "./login";

let account: { username: string; password: string; business_id: string };
const python = resolve("../backend/.venv/bin/python");
const fixture = resolve("../backend/tests/browser_fixture.py");
const base = () => `/api/v1/businesses/${account.business_id}`;
const today = () =>
  new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Bishkek" }).format(
    new Date(),
  );

test.beforeEach(async ({ page }) => {
  account = JSON.parse(
    execFileSync(python, [fixture, "create"], { encoding: "utf8" }),
  );
  await page.goto("/");
  await submitLogin(page, account.username, account.password);
  await expect(
    page.getByRole("heading", { name: "Заказы", exact: true }),
  ).toBeVisible();
});
test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "wait" });
  if (account)
    execFileSync(python, [fixture, "delete"], {
      input: JSON.stringify(account),
    });
});

async function create(page: Page, path: string, data: object) {
  const csrf = await (await page.request.get("/api/v1/auth/csrf/")).json();
  const response = await page.request.post(`${base()}/${path}/`, {
    headers: {
      "X-CSRFToken": csrf.csrf_token,
      "Idempotency-Key": randomUUID(),
    },
    data,
  });
  expect(response.status()).toBe(201);
  return response.json();
}
async function seedOrder(
  page: Page,
  fulfillment = "pickup",
  phone = "+996555800099",
) {
  const customer = await create(page, "customers", {
    name: "Клиент обновления",
    phone,
  });
  const product = await create(page, "products", {
    name: "Букет обновления",
    price: "1500",
  });
  const order = await create(page, "orders", {
    customer_id: customer.id,
    recipient_name: customer.name,
    recipient_phone: customer.phone,
    fulfillment,
    address: fulfillment === "courier" ? "Тестовый адрес" : "",
    delivery_date: today(),
    window_start: "10:00",
    window_end: "12:00",
    items: [{ product_id: product.id, quantity: 1 }],
  });
  return { customer, order };
}

// Hold a real response until the test has inspected the in-flight UI.
async function holdGet(page: Page, pattern: string, allUntilReleased = false) {
  let held = false;
  let released = false;
  let release!: () => void;
  let arrived!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = () => {
      released = true;
      resolve();
    };
  });
  const entered = new Promise<void>((resolve) => {
    arrived = resolve;
  });
  await page.route(pattern, async (route) => {
    if (
      released ||
      (held && !allUntilReleased) ||
      route.request().method() !== "GET"
    )
      return route.continue();
    held = true;
    const response = await route.fetch();
    arrived();
    await gate;
    await route.fulfill({ response });
  });
  return { entered, release };
}

async function visibility(page: Page, value: "hidden" | "visible") {
  await page.evaluate((value) => {
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value,
    });
    document.dispatchEvent(new Event("visibilitychange"));
  }, value);
}

test("возвращение в CRM обновляет заказы без перезагрузки и повторных запросов", async ({
  page,
}) => {
  await seedOrder(page);
  await page.getByRole("button", { name: "Заказы", exact: true }).click();
  const first = page.getByRole("button", {
    name: "Открыть заказ №1",
    exact: true,
  });
  await expect(first).toBeVisible();
  const original = await first.elementHandle();
  await page.clock.install({ time: new Date() });
  await page.clock.pauseAt(new Date(Date.now() + 1000));
  let requests = 0;
  page.on("request", (r) => {
    if (r.method() === "GET" && r.url().includes("/orders/desk/")) requests++;
  });
  await visibility(page, "hidden");
  await seedOrder(page, "pickup", "+996555800098");
  await page.evaluate(() => {
    window.dispatchEvent(new Event("focus"));
    window.dispatchEvent(new Event("online"));
    window.dispatchEvent(
      new PageTransitionEvent("pageshow", { persisted: true }),
    );
  });
  await page.clock.fastForward(5000);
  expect(requests).toBe(0);

  const pending = await holdGet(page, "**/orders/desk/?*");
  try {
    await visibility(page, "visible");
    await pending.entered;
    await expect(page.locator(".order-main .refresh-indicator")).toHaveText(
      "Обновляем…",
    );
    expect(await original!.evaluate((node) => node.isConnected)).toBe(true);
    await page.clock.fastForward(5000);
    await page.evaluate(() => {
      document.dispatchEvent(new Event("visibilitychange"));
      window.dispatchEvent(new Event("focus"));
      window.dispatchEvent(new Event("online"));
      window.dispatchEvent(
        new PageTransitionEvent("pageshow", { persisted: true }),
      );
    });
    expect(requests).toBe(1);
  } finally {
    pending.release();
  }
  await expect(
    page.getByRole("button", { name: "Открыть заказ №2", exact: true }),
  ).toBeVisible();
  expect(await original!.evaluate((node) => node.isConnected)).toBe(true);
  expect(requests).toBe(1);
});

test("фокус, восстановление сети и истории обновляют карточку и сохраняют ввод при сбое", async ({
  page,
}) => {
  const { order } = await seedOrder(page);
  await page.getByRole("button", { name: "Заказы", exact: true }).click();
  await page
    .getByRole("button", { name: "Открыть заказ №1", exact: true })
    .click();
  const amount = page.getByLabel("Сумма, сом", { exact: true });
  await amount.fill("321");
  const original = await amount.elementHandle();
  await page.clock.install({ time: new Date() });
  await page.clock.pauseAt(new Date(Date.now() + 1000));
  let status = 503;
  let requests = 0;
  await page.route(`**/orders/${order.id}/`, (route) => {
    requests++;
    if (status === 200) return route.continue();
    return route.fulfill({ status, json: {} });
  });
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(page.getByRole("alert")).toContainText("Сервер не смог");
  await expect(amount).toHaveValue("321");
  expect(await original!.evaluate((node) => node.isConnected)).toBe(true);
  await page.evaluate(() => {
    window.dispatchEvent(new Event("focus"));
    document.dispatchEvent(new Event("visibilitychange"));
  });
  expect(requests).toBe(1);

  status = 200;
  await page.clock.fastForward(1000);
  await page.evaluate(() => {
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: false,
    });
    window.dispatchEvent(new Event("offline"));
  });
  await visibility(page, "hidden");
  await visibility(page, "visible");
  expect(requests).toBe(1);
  await page.evaluate(() => {
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: true,
    });
    window.dispatchEvent(new Event("online"));
  });
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Обновить карточку", exact: true }),
  ).toBeEnabled();
  await expect(amount).toHaveValue("321");
  expect(requests).toBe(2);

  status = 403;
  await page.clock.fastForward(1000);
  await page.evaluate(() => {
    window.dispatchEvent(new PageTransitionEvent("pageshow"));
  });
  expect(requests).toBe(2);
  await page.evaluate(() => {
    window.dispatchEvent(
      new PageTransitionEvent("pageshow", { persisted: true }),
    );
  });
  await expect(amount).toHaveCount(0);
  await expect(page.getByRole("alert")).toBeVisible();
  expect(requests).toBe(3);
});

test("возвращение сохраняет черновики клиента, заказа и настроек", async ({
  page,
}) => {
  const { customer } = await seedOrder(page);
  await page.getByRole("button", { name: "Клиенты", exact: true }).click();
  await page.getByRole("button", { name: customer.name, exact: false }).click();
  await page
    .getByRole("button", { name: "Добавить дату", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  const notes = dialog.getByRole("textbox", {
    name: "Заметка клиента",
    exact: true,
  });
  await notes.fill("Несохранённая заметка");
  await visibility(page, "hidden");
  const activity = page.waitForResponse((r) =>
    r.url().includes(`/customers/${customer.id}/activity/`),
  );
  await visibility(page, "visible");
  await activity;
  await expect(notes).toHaveValue("Несохранённая заметка");
  await dialog.getByLabel("Закрыть", { exact: true }).click();

  await page.getByRole("button", { name: "Заказы", exact: true }).click();
  await page
    .getByRole("button", { name: "Открыть заказ №1", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Редактировать заказ", exact: true })
    .click();
  const recipient = page.getByLabel("Получатель", { exact: true });
  await recipient.fill("Несохранённый получатель");
  await visibility(page, "hidden");
  const payments = page.waitForResponse((r) => r.url().includes("/payments/"));
  await visibility(page, "visible");
  await payments;
  await expect(recipient).toHaveValue("Несохранённый получатель");
  await page.getByRole("dialog").getByLabel("Закрыть", { exact: true }).click();
  await page.getByRole("dialog").getByLabel("Закрыть", { exact: true }).click();

  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await page.getByRole("tab", { name: "Магазин", exact: true }).click();
  const name = page.getByLabel("Название магазина", { exact: true });
  await name.fill("Несохранённое название");
  await visibility(page, "hidden");
  const staff = page.waitForResponse((r) => r.url().endsWith("/staff/"));
  await visibility(page, "visible");
  await staff;
  await expect(name).toHaveValue("Несохранённое название");
});

test("новый заказ и фоновые задачи не убирают существующие карточки", async ({
  page,
}, info) => {
  await seedOrder(page);
  await page.getByRole("button", { name: "Заказы", exact: true }).click();
  const first = page.getByRole("button", {
    name: "Открыть заказ №1",
    exact: true,
  });
  await expect(first).toBeVisible();
  const original = await first.elementHandle();
  await page.getByRole("button", { name: "Новый заказ", exact: true }).click();
  await page.getByRole("button", { name: /Клиент обновления/ }).click();
  await page
    .getByRole("button", { name: "Добавить в заказ", exact: true })
    .click();
  await page.getByLabel("Получение", { exact: true }).selectOption("pickup");
  const requests: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "GET") requests.push(r.url());
  });
  const pending = await holdGet(page, "**/orders/desk/?*");
  try {
    await page
      .getByRole("button", { name: "Создать заказ", exact: true })
      .click();
    await pending.entered;
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(
      page.getByText("Загружаем заказы…", { exact: true }),
    ).toHaveCount(0);
    await expect(page.locator(".order-main .refresh-indicator")).toHaveText(
      "Обновляем…",
    );
    expect(await original!.evaluate((node) => node.isConnected)).toBe(true);
    await expect(first).toBeVisible();
    expect(
      requests.some((url) => /\/(settings|staff|office-tasks)\/$/.test(url)),
    ).toBe(false);
    await page.screenshot({
      path: `/tmp/tapme-${info.project.name}-background-refresh.png`,
    });
  } finally {
    pending.release();
  }
  await expect(
    page.getByRole("button", { name: "Открыть заказ №2", exact: true }),
  ).toBeVisible();
  expect(await original!.evaluate((node) => node.isConnected)).toBe(true);
  await page.unroute("**/orders/desk/?*");
  requests.length = 0;
  await page
    .getByLabel("Новая задача", { exact: true })
    .fill("Проверка локального обновления");
  await page.getByLabel("Новая задача", { exact: true }).press("Enter");
  await expect(
    page.getByRole("button", {
      name: "Завершить: Проверка локального обновления",
    }),
  ).toBeVisible();
  expect(requests.some((url) => url.includes("/orders/desk/"))).toBe(false);
});

test("сохранение даты оставляет карточку, прокрутку и новый черновик на месте", async ({
  page,
}) => {
  const { customer } = await seedOrder(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Клиенты", exact: true }).click();
  await page.getByRole("button", { name: customer.name, exact: false }).click();
  const heading = page.getByRole("heading", {
    name: customer.name,
    exact: true,
  });
  await expect(heading).toBeVisible();
  const original = await heading.elementHandle();
  await page
    .getByRole("button", { name: "Добавить дату", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByLabel("Имя клиента", { exact: true })).toHaveValue(
    customer.name,
  );
  await dialog
    .getByRole("button", { name: "Добавить дату", exact: true })
    .click();
  await dialog.getByLabel("Событие", { exact: true }).fill("Проверка даты");
  await dialog.getByLabel("У кого", { exact: true }).fill("Мама");
  await dialog.getByLabel("День", { exact: true }).fill("10");
  await dialog.getByLabel("Месяц", { exact: true }).fill("10");
  const pending = await holdGet(page, `**/customers/${customer.id}/`);
  try {
    await dialog
      .getByRole("button", { name: "Сохранить клиента", exact: true })
      .click();
    await pending.entered;
    expect(await original!.evaluate((node) => node.isConnected)).toBe(true);
    await expect(
      page.getByText("Загружаем карточку…", { exact: true }),
    ).toHaveCount(0);
    await dialog
      .getByLabel("Заметка клиента", { exact: true })
      .fill("Черновик после сохранения");
    const scroll = await dialog.evaluate((el) => el.scrollTop);
    pending.release();
    await expect(page.locator(".page-hd .refresh-indicator")).toHaveText("");
    await expect(
      dialog.getByRole("textbox", { name: "Заметка клиента", exact: true }),
    ).toHaveValue("Черновик после сохранения");
    expect(await dialog.evaluate((el) => el.scrollTop)).toBe(scroll);
    expect(await original!.evaluate((node) => node.isConnected)).toBe(true);
  } finally {
    pending.release();
  }
  const saved = await (
    await page.request.get(`${base()}/customers/${customer.id}/`)
  ).json();
  expect(saved.dates[0].label).toBe("Проверка даты");
  expect(saved.notes).not.toBe("Черновик после сохранения");
});

test("обновление заказа сохраняет черновик оплаты и переживает временную ошибку", async ({
  page,
}) => {
  const { order } = await seedOrder(page);
  await page.getByRole("button", { name: "Заказы", exact: true }).click();
  await page
    .getByRole("button", { name: "Открыть заказ №1", exact: true })
    .click();
  const amount = page.getByLabel("Сумма, сом", { exact: true });
  await amount.fill("123");
  const original = await amount.elementHandle();
  const path = `**/orders/${order.id}/`;
  const pending = await holdGet(page, path);
  try {
    await page
      .getByRole("button", { name: "Обновить карточку", exact: true })
      .click();
    await pending.entered;
    expect(await original!.evaluate((node) => node.isConnected)).toBe(true);
    await expect(amount).toHaveValue("123");
  } finally {
    pending.release();
  }
  await expect(
    page.getByRole("button", { name: "Обновить карточку", exact: true }),
  ).toBeEnabled();
  await expect(amount).toHaveValue("123");
  await page.unroute(path);
  await page.route(path, (route) => route.fulfill({ status: 503, json: {} }));
  await page
    .getByRole("button", { name: "Обновить карточку", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Сервер не смог");
  await expect(amount).toHaveValue("123");
  expect(await original!.evaluate((node) => node.isConnected)).toBe(true);
  await page.unroute(path);
  await page
    .getByRole("button", { name: "Обновить карточку", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Обновить карточку", exact: true }),
  ).toBeEnabled();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(amount).toHaveValue("123");
  await page.route(path, (route) =>
    route.fulfill({ status: 403, json: { detail: "Доступ отозван" } }),
  );
  await page
    .getByRole("button", { name: "Обновить карточку", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Доступ отозван");
  await expect(amount).toHaveCount(0);
});

test("другая дата не показывает прежние заказы и опоздавший ответ не заменяет текущий", async ({
  page,
}) => {
  await seedOrder(page);
  await page.getByRole("button", { name: "Заказы", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Открыть заказ №1", exact: true }),
  ).toBeVisible();
  const pending = await holdGet(page, "**/orders/desk/?*scope=tomorrow*");
  try {
    await page.getByRole("button", { name: /^Завтра / }).click();
    await pending.entered;
    await expect(
      page.getByRole("button", { name: "Открыть заказ №1", exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByText("Загружаем заказы…", { exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: /^Сегодня / }).click();
    await expect(
      page.getByRole("button", { name: "Открыть заказ №1", exact: true }),
    ).toBeVisible();
    pending.release();
    await page.unrouteAll({ behavior: "wait" });
    await expect(
      page.getByRole("button", { name: "Открыть заказ №1", exact: true }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: /^Сегодня / })).toHaveClass(
      /is-on/,
    );
  } finally {
    pending.release();
  }
});

test("при смене магазина старые клиенты сразу скрываются даже при отказе доступа", async ({
  page,
}) => {
  const { customer } = await seedOrder(page);
  const shops = await (await page.request.get("/api/v1/businesses/")).json();
  const otherId = randomUUID();
  // Only the switcher is mocked; the real API must reject this unavailable business.
  await page.route("**/api/v1/businesses/", (route) =>
    route.fulfill({
      json: [
        ...shops,
        { ...shops[0], id: otherId, name: "Недоступный тестовый магазин" },
      ],
    }),
  );
  await page.reload();
  await page.getByRole("button", { name: "Клиенты", exact: true }).click();
  const customerButton = page.getByRole("button", {
    name: customer.name,
    exact: false,
  });
  await expect(customerButton).toBeVisible();
  const pending = await holdGet(
    page,
    `**/businesses/${otherId}/customers/directory/?*`,
    // A new point/business mounts a new screen. StrictMode may abort its first
    // GET and start another; both must wait for the simulated slow connection.
    true,
  );
  try {
    await page
      .getByRole("combobox", { name: "Магазин", exact: true })
      .selectOption(otherId);
    await pending.entered;
    await expect(customerButton).toHaveCount(0);
    await expect(
      page.getByText("Загружаем клиентов…", { exact: true }),
    ).toBeVisible();
    pending.release();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(customerButton).toHaveCount(0);
    await page
      .getByRole("combobox", { name: "Магазин", exact: true })
      .selectOption(account.business_id);
    await expect(customerButton).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
  } finally {
    pending.release();
  }
});

test("после редактирования назначение ждёт свежую версию и сохраняет выбранного курьера", async ({
  page,
}) => {
  const { order } = await seedOrder(page, "courier");
  const courier = await create(page, "staff", {
    username: `${account.username}_courier`,
    name: "Курьер обновления",
    role: "courier",
    password: account.password,
  });
  await page.getByRole("button", { name: "Заказы", exact: true }).click();
  await page
    .getByRole("button", { name: "Открыть заказ №1", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Редактировать заказ", exact: true })
    .click();
  await page
    .getByLabel("Получатель", { exact: true })
    .fill("Обновлённый получатель");
  const pending = await holdGet(page, `**/orders/${order.id}/`);
  try {
    await page
      .getByRole("button", { name: "Сохранить изменения", exact: true })
      .click();
    await pending.entered;
    await expect(
      page.getByRole("combobox", { name: "Курьер", exact: true }),
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Назначить сотрудников", exact: true }),
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Редактировать заказ", exact: true }),
    ).toBeVisible();
    pending.release();
    await page
      .getByRole("combobox", { name: "Курьер", exact: true })
      .selectOption({ label: "Курьер обновления" });
    await Promise.all([
      page.waitForResponse(
        (r) =>
          r.url().endsWith(`/orders/${order.id}/assignment/`) &&
          r.request().method() === "POST",
      ),
      page
        .getByRole("button", { name: "Назначить сотрудников", exact: true })
        .click(),
    ]);
    const saved = await (
      await page.request.get(`${base()}/orders/${order.id}/`)
    ).json();
    expect(saved.recipient_name).toBe("Обновлённый получатель");
    expect(saved.courier_id).toBe(courier.id);
  } finally {
    pending.release();
  }
});
