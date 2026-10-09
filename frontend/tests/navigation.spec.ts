import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";
import { submitLogin } from "./login";

let account: { username: string; password: string; business_id: string };
const python = resolve("../backend/.venv/bin/python");
const fixture = resolve("../backend/tests/browser_fixture.py");
const base = () => `/api/v1/businesses/${account.business_id}`;
const link = (params: Record<string, string>) =>
  `/?${new URLSearchParams({ business: account.business_id, ...params })}`;

test.beforeEach(() => {
  account = JSON.parse(
    execFileSync(python, [fixture, "create"], { encoding: "utf8" }),
  );
});
test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "wait" });
  if (account)
    execFileSync(python, [fixture, "delete"], {
      input: JSON.stringify(account),
    });
});

async function login(page: Page, url = "/", username = account.username) {
  await page.goto(url);
  await submitLogin(page, username, account.password);
  await expect(page.locator(".app-shell")).toBeVisible();
}
async function section(page: Page, name: string) {
  await page.getByRole("button", { name, exact: true }).click();
  await expect(page.locator(".nav [aria-current=page]")).toHaveText(
    new RegExp(name),
  );
}
async function params(page: Page, wanted: Record<string, string | null>) {
  await expect
    .poll(() => {
      const query = new URL(page.url()).searchParams;
      return Object.fromEntries(
        Object.keys(wanted).map((key) => [key, query.get(key)]),
      );
    })
    .toEqual(wanted);
}
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

test("разделы и все вкладки настроек остаются на месте после обновления", async ({
  page,
}, info) => {
  await login(page);
  for (const [view, label] of [
    ["customers", "Клиенты"],
    ["reminders", "Напоминания"],
    ["deliveries", "Доставка"],
    ["orders", "Заказы"],
  ]) {
    await section(page, label);
    await page.reload();
    await expect(page.locator(".nav [aria-current=page]")).toHaveText(
      new RegExp(label),
    );
    await params(page, { view, business: account.business_id });
  }
  await section(page, "Настройки");
  for (const [tab, label] of [
    ["windows", "Окна доставки"],
    ["templates", "Шаблоны"],
    ["prices", "Прайс"],
    ["shop", "Магазин"],
    ["staff", "Сотрудники"],
  ]) {
    await page.getByRole("tab", { name: label, exact: true }).click();
    if (tab === "windows") {
      await page.getByLabel("Вместимость окна 1", { exact: true }).fill("9");
      await page
        .getByRole("button", { name: "Сохранить окна", exact: true })
        .click();
      await expect(page.getByRole("status")).toContainText("Сохранено");
    }
    await page.reload();
    await expect(
      page.getByRole("tab", { name: label, exact: true }),
    ).toHaveAttribute("aria-selected", "true");
    await params(page, { view: "settings", tab });
    if (tab === "windows") {
      await expect(
        page.getByLabel("Вместимость окна 1", { exact: true }),
      ).toHaveValue("9");
      await page.screenshot({
        path: `/tmp/tapme-${info.project.name}-navigation-reload.png`,
      });
    }
  }
});

test("история проходит по разделам и вкладкам без лишних шагов", async ({
  page,
}) => {
  await login(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await section(page, "Клиенты");
  await section(page, "Настройки");
  await page.getByRole("tab", { name: "Окна доставки", exact: true }).click();
  const windowsUrl = page.url();
  const historyLength = await page.evaluate(() => history.length);
  await section(page, "Настройки");
  await page.getByRole("tab", { name: "Окна доставки", exact: true }).click();
  expect(await page.evaluate(() => history.length)).toBe(historyLength);
  await section(page, "Доставка");
  await page.goBack();
  await expect(page).toHaveURL(windowsUrl);
  await expect(
    page.getByRole("tab", { name: "Окна доставки", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await page.goBack();
  await expect(
    page.getByRole("tab", { name: "Сотрудники", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await page.goBack();
  await expect(page.locator(".nav [aria-current=page]")).toHaveText("Клиенты");
  await page.goForward();
  await page.goForward();
  await expect(page).toHaveURL(windowsUrl);
  await page.reload();
  await expect(
    page.getByRole("tab", { name: "Окна доставки", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await expect(
    page.getByLabel("Вместимость окна 1", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.getByRole("tab", { name: "Сотрудники", exact: true }).click();
  await page.getByRole("button", { name: "Пригласить", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.goBack();
  await expect(
    page.getByRole("tab", { name: "Окна доставки", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("карточки клиента и заказа восстанавливаются, Назад закрывает заказ", async ({
  page,
}) => {
  await login(page);
  const customer = await create(page, "customers", {
    name: "Клиент навигации",
    phone: "+996555890012",
  });
  const product = await create(page, "products", {
    name: "Букет навигации",
    price: "1500",
  });
  const order = await create(page, "orders", {
    customer_id: customer.id,
    recipient_name: customer.name,
    recipient_phone: customer.phone,
    fulfillment: "pickup",
    delivery_date: new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Bishkek",
    }).format(new Date()),
    window_start: "10:00",
    window_end: "12:00",
    items: [{ product_id: product.id, quantity: 1 }],
  });
  await section(page, "Клиенты");
  await page.getByRole("button", { name: customer.name, exact: false }).click();
  await params(page, { view: "customers", customer: customer.id });
  await page.reload();
  await expect(
    page.getByRole("heading", { name: customer.name, exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "№1", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await params(page, { customer: customer.id, order: order.id });
  await page.reload();
  await expect(
    page
      .getByRole("dialog")
      .getByRole("heading", { name: "Заказ №1", exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: customer.name, exact: true }),
  ).toBeVisible();
  await page.goForward();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByRole("button", { name: "Закрыть", exact: true })
    .first()
    .click();
  await params(page, { customer: customer.id, order: null });
  await page.getByRole("button", { name: "← Клиенты", exact: true }).click();
  await params(page, { customer: null, order: null });
  await expect(
    page.getByRole("button", { name: customer.name, exact: false }),
  ).toBeVisible();
});

test("прямая ссылка продолжается после входа, выход очищает текущий адрес", async ({
  page,
}) => {
  await login(page, link({ view: "settings", tab: "windows" }));
  await expect(
    page.getByRole("tab", { name: "Окна доставки", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await expect(
    page.getByLabel("Вместимость окна 1", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Меню пользователя" }).click();
  await page.getByRole("menuitem", { name: "Выйти", exact: true }).click();
  await expect(page.getByLabel("Логин", { exact: true })).toBeVisible();
  await params(page, { view: "orders", business: null, tab: null });
  await page.reload();
  await expect(page.getByLabel("Логин", { exact: true })).toBeVisible();
});

test("ошибочные и недоступные ссылки дают безопасный раздел и выход из карточки", async ({
  page,
}) => {
  await login(
    page,
    "/?view=unknown&tab=unknown&business=bad&customer=bad&order=bad",
  );
  await params(page, {
    view: "orders",
    business: account.business_id,
    tab: null,
    customer: null,
    order: null,
  });
  await page.goto(link({ view: "settings", tab: "unknown" }));
  await expect(
    page.getByRole("tab", { name: "Сотрудники", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  const requested: string[] = [];
  page.on("request", (r) => requested.push(r.url()));
  const unavailable = randomUUID(),
    missing = randomUUID();
  await page.goto(
    link({
      view: "customers",
      business: unavailable,
      customer: missing,
      order: missing,
    }),
  );
  await params(page, {
    business: account.business_id,
    customer: null,
    order: null,
  });
  await expect(
    page.getByRole("button", { name: "Новый клиент", exact: true }),
  ).toBeVisible();
  expect(
    requested.some((url) => url.includes(unavailable) && url.includes("/api/")),
  ).toBe(false);
  await page.goto(link({ view: "customers", customer: missing }));
  await expect(
    page.getByText("Не удалось открыть карточку клиента.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText("Загружаем карточку…", { exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "← Клиенты", exact: true }).click();
  await page.goto(link({ view: "orders", order: missing }));
  await expect(
    page.getByText("Не удалось открыть заказ.", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Закрыть", exact: true })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await params(page, { order: null });
});

test("ссылка владельца не открывает настройки и карточки флористу", async ({
  page,
}) => {
  await login(page);
  const florist = `${account.username}_florist`;
  await create(page, "staff", {
    username: florist,
    name: "Флорист навигации",
    role: "florist",
    password: account.password,
  });
  await page.context().clearCookies();
  const requested: string[] = [];
  page.on("request", (r) => requested.push(r.url()));
  await login(
    page,
    link({
      view: "settings",
      tab: "windows",
      customer: randomUUID(),
      order: randomUUID(),
    }),
    florist,
  );
  await expect(
    page.getByRole("heading", { name: "Мои задания", exact: true }),
  ).toBeVisible();
  await params(page, {
    view: "orders",
    tab: null,
    customer: null,
    order: null,
  });
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Мои задания", exact: true }),
  ).toBeVisible();
  expect(
    requested.some((url) =>
      /\/(settings|customers|orders)\//.test(new URL(url).pathname),
    ),
  ).toBe(false);
  await expect(
    page.getByRole("button", { name: "Настройки", exact: true }),
  ).toHaveCount(0);
});

test("выбранный второй магазин сохраняется после обновления и в истории", async ({
  page,
}) => {
  await login(page);
  const shops = await (await page.request.get("/api/v1/businesses/")).json();
  const second = randomUUID();
  // Model a second membership only in the browser. Read responses are snapshots;
  // there is no fake server-side access and no mutation of either shop.
  const responses: Record<string, unknown> = {};
  for (const endpoint of ["settings/", "overview/", "customers/directory/"])
    responses[endpoint] = await (
      await page.request.get(`${base()}/${endpoint}`)
    ).json();
  await page.route("**/api/v1/businesses/", (route) =>
    route.fulfill({
      json: [
        ...shops,
        { ...shops[0], id: second, name: "Второй тестовый магазин" },
      ],
    }),
  );
  await page.route(`**/api/v1/businesses/${second}/**`, (route) => {
    const endpoint = new URL(route.request().url()).pathname.split(
      `${second}/`,
    )[1];
    expect(route.request().method()).toBe("GET");
    expect(responses[endpoint]).toBeDefined();
    return route.fulfill({ json: responses[endpoint] });
  });
  await page.reload();
  await section(page, "Клиенты");
  const selector = page.getByRole("combobox", { name: "Магазин", exact: true });
  await selector.selectOption(second);
  await page.reload();
  await expect(selector).toHaveValue(second);
  await params(page, { view: "customers", business: second });
  await selector.selectOption(account.business_id);
  await page.goBack();
  await expect(selector).toHaveValue(second);
  await page.goForward();
  await expect(selector).toHaveValue(account.business_id);
});
