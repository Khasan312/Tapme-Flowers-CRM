import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { submitLogin } from "./login";

let account: { username: string; password: string; business_id: string };
const python = resolve("../backend/.venv/bin/python"),
  fixture = resolve("../backend/tests/browser_fixture.py");
test.beforeEach(() => {
  account = JSON.parse(
    execFileSync(python, [fixture, "create"], { encoding: "utf8" }),
  );
});
test.afterEach(() => {
  if (account)
    execFileSync(python, [fixture, "delete"], {
      input: JSON.stringify(account),
    });
});
async function login(page: Page) {
  await page.goto("/");
  await submitLogin(page, account.username, account.password);
}
async function settings(page: Page, tab: string) {
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await page.getByRole("tab", { name: tab, exact: true }).click();
}
async function api(page: Page, path: string, body?: unknown, method = "GET") {
  return page.evaluate(
    async ({ path, body, method }) => {
      const csrf = decodeURIComponent(
        document.cookie
          .split("; ")
          .find((c) => c.startsWith("csrftoken="))
          ?.split("=")[1] || "",
      );
      const response = await fetch(path, {
        method,
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const data = response.status === 204 ? null : await response.json();
      if (!response.ok) throw Error(JSON.stringify(data));
      return data;
    },
    {
      path: `/api/v1/businesses/${account.business_id}/${path}/`,
      body,
      method,
    },
  );
}

test("две вкладки сохраняют настройки и шаблоны без потери изменений", async ({
  page,
  context,
}) => {
  await login(page);
  const second = await context.newPage();
  await second.goto("/");
  await settings(page, "Магазин");
  await settings(second, "Магазин");
  await page
    .getByLabel("Адрес", { exact: true })
    .fill("Новый адрес первой вкладки");
  await second
    .getByLabel("Город", { exact: true })
    .fill("Черновик второй вкладки");
  await page.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Сохранено");
  await second.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(second.getByRole("alert")).toContainText("другой вкладке");
  await expect(second.getByLabel("Город", { exact: true })).toHaveValue(
    "Черновик второй вкладки",
  );
  expect((await api(page, "settings")).address).toBe(
    "Новый адрес первой вкладки",
  );
  await second
    .getByRole("button", { name: "Загрузить актуальные настройки" })
    .click();
  await expect(second.getByLabel("Адрес", { exact: true })).toHaveValue(
    "Новый адрес первой вкладки",
  );
  await second.getByLabel("Город", { exact: true }).fill("Бишкек");
  await second.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(second.getByRole("status")).toHaveText("Сохранено");
  await settings(page, "Шаблоны");
  await settings(second, "Шаблоны");
  await expect(
    second.getByRole("textbox", { name: "Дата через 7 дней", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Добавить шаблон" }).click();
  await page
    .getByLabel("Название шаблона", { exact: true })
    .fill("Сохранённый шаблон");
  await page
    .getByLabel("Текст шаблона", { exact: true })
    .fill("Спасибо, {имя}!");
  await page.getByRole("button", { name: "Сохранить шаблоны" }).first().click();
  await expect(page.getByRole("status")).toHaveText("Шаблоны сохранены");
  await second
    .getByRole("textbox", { name: "Дата через 7 дней", exact: true })
    .fill("Мой черновик {имя}");
  await second
    .getByRole("button", { name: "Сохранить шаблоны" })
    .first()
    .click();
  await expect(second.getByRole("alert")).toContainText("другой вкладке");
  await expect(
    second.getByRole("textbox", { name: "Дата через 7 дней", exact: true }),
  ).toHaveValue("Мой черновик {имя}");
  expect((await api(page, "reminder-rules")).custom_templates[0].name).toBe(
    "Сохранённый шаблон",
  );
  await second
    .getByRole("button", { name: "Загрузить актуальные настройки" })
    .click();
  await expect(
    second.getByLabel("Название шаблона", { exact: true }),
  ).toHaveValue("Сохранённый шаблон");
  await second
    .getByRole("button", { name: "Напоминания", exact: true })
    .click();
  await second.getByRole("button", { name: "Правила", exact: true }).click();
  await second.getByLabel("Давний клиент — без покупок, дней").fill("120");
  await page
    .getByLabel("Текст шаблона", { exact: true })
    .fill("Ждём вас, {имя}!");
  await page.getByRole("button", { name: "Сохранить шаблоны" }).first().click();
  await expect(page.getByRole("status")).toHaveText("Шаблоны сохранены");
  await second
    .getByRole("button", { name: "Сохранить напоминания", exact: true })
    .click();
  await expect(second.getByRole("alert")).toContainText("другой вкладке");
  await expect(
    second.getByLabel("Давний клиент — без покупок, дней"),
  ).toHaveValue("120");
  await second
    .getByRole("button", { name: "Загрузить актуальные настройки" })
    .click();
  await expect(
    second.getByLabel("Давний клиент — без покупок, дней"),
  ).toHaveValue("90");
  await second.close();
});

test("старое окно редактируется, отключённого курьера можно заменить в пути", async ({
  page,
}) => {
  await login(page);
  const config = await api(page, "settings");
  await api(
    page,
    "settings",
    {
      ...config,
      enforce_capacity: true,
      windows: [
        { start: "10:00", end: "12:00", capacity: 1, price: "300.00" },
        { start: "12:00", end: "14:00", capacity: 1, price: "500.00" },
      ],
    },
    "PUT",
  );
  const customer = await api(
    page,
    "customers",
    { name: "Клиент проверки", phone: "555123456" },
    "POST",
  );
  const product = await api(
    page,
    "products",
    { name: "Букет проверки", price: "1000" },
    "POST",
  );
  const staff = [];
  for (const [role, name, suffix] of [
    ["florist", "Флорист", "florist"],
    ["courier", "Первый курьер", "old"],
    ["courier", "Новый курьер", "new"],
  ]) {
    staff.push(
      await api(
        page,
        "staff",
        {
          role,
          name,
          username: account.username + "_" + suffix,
          password: account.password,
        },
        "POST",
      ),
    );
  }
  const today = await page.evaluate(() =>
    new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Bishkek",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date()),
  );
  let order = await api(
    page,
    "orders",
    {
      customer_id: customer.id,
      items: [{ product_id: product.id, quantity: 1 }],
      recipient_name: "Получатель",
      fulfillment: "courier",
      delivery_date: today,
      window_start: "10:00",
      window_end: "12:00",
      address: "Тестовый адрес",
    },
    "POST",
  );
  const current = await api(page, "settings");
  await api(
    page,
    "settings",
    { ...current, windows: current.windows.slice(1) },
    "PUT",
  );
  await page.reload();
  await page
    .getByRole("button", { name: "Открыть заказ №1", exact: true })
    .click();
  await page.getByRole("button", { name: "Редактировать заказ" }).click();
  await expect(
    page.getByText(/Прежнее окно удалено из настроек/),
  ).toBeVisible();
  await expect(
    page.getByText("Доставка: 300 сом", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Заметка к заказу", { exact: true })
    .fill("Уточнён подъезд");
  await page
    .getByRole("button", { name: "Сохранить изменения", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Редактировать заказ" }),
  ).toBeVisible();
  order = await api(page, `orders/${order.id}`);
  expect(order.delivery_fee).toBe("300.00");
  expect(order.notes).toBe("Уточнён подъезд");
  order = await api(
    page,
    `orders/${order.id}/assignment`,
    {
      version: order.version,
      florist_id: staff[0].id,
      courier_id: staff[1].id,
    },
    "POST",
  );
  for (const status of ["work", "ready", "route"])
    order = await api(
      page,
      `orders/${order.id}/transition`,
      { version: order.version, status },
      "POST",
    );
  await api(
    page,
    `staff/${staff[1].id}`,
    { role: "courier", is_active: false },
    "PUT",
  );
  await page.reload();
  await page
    .getByRole("button", { name: "Открыть заказ №1", exact: true })
    .click();
  await expect(page.getByLabel("Флорист", { exact: true })).toBeDisabled();
  await expect(page.getByLabel("Курьер", { exact: true })).toHaveValue(
    staff[1].id,
  );
  await expect(
    page.getByLabel("Курьер", { exact: true }).locator("option:checked"),
  ).toHaveText("Первый курьер — недоступен");
  await page.getByLabel("Курьер", { exact: true }).selectOption(staff[2].id);
  await page
    .getByRole("button", { name: "Заменить курьера", exact: true })
    .click();
  await expect(page.getByLabel("Курьер", { exact: true })).toHaveValue(
    staff[2].id,
  );
  await expect(
    page.getByText("Курьер заменён. Статус «В пути» сохранён."),
  ).toBeVisible();
  order = await api(page, `orders/${order.id}`);
  expect(order.status).toBe("route");
  expect(order.courier_id).toBe(staff[2].id);
});
