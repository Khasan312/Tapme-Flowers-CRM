import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";
import { submitLogin } from "./login";

let account: { username: string; password: string; business_id: string };
let workerPage: Page | undefined;
const python = resolve("../backend/.venv/bin/python");
const fixture = resolve("../backend/tests/browser_fixture.py");
test.beforeEach(() => {
  account = JSON.parse(
    execFileSync(python, [fixture, "create"], { encoding: "utf8" }),
  );
});
test.afterEach(async () => {
  await workerPage?.context().close();
  workerPage = undefined;
  if (account)
    execFileSync(python, [fixture, "delete"], {
      input: JSON.stringify(account),
    });
});

async function post(page: Page, path: string, data: object) {
  const csrf = await (await page.request.get("/api/v1/auth/csrf/")).json();
  const response = await page.request.post(
    `/api/v1/businesses/${account.business_id}/${path}/`,
    {
      headers: {
        "X-CSRFToken": csrf.csrf_token,
        "Idempotency-Key": randomUUID(),
      },
      data,
    },
  );
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}
async function prepare(page: Page, role: "florist" | "courier", count: number) {
  await page.goto("/login");
  await submitLogin(page, account.username, account.password);
  const staff = await post(page, "staff", {
    username: `${account.username}_${role}`,
    password: account.password,
    name: "Сотрудник проверки страниц",
    role,
  });
  const customer = await post(page, "customers", {
    name: "Клиент проверки страниц",
    phone: "+12025550123",
  });
  const product = await post(page, "products", {
    name: "Букет проверки страниц",
    price: "1500.00",
  });
  const orders = [];
  for (let i = 0; i < count; i++) {
    const order = await post(page, "orders", {
      customer_id: customer.id,
      items: [{ product_id: product.id, quantity: 1 }],
      recipient_name: `Получатель ${i + 1}`,
      fulfillment: role === "courier" ? "courier" : "pickup",
      delivery_date: i === 12 ? "2030-01-11" : "2030-01-10",
      window_start: "10:00",
      window_end: "12:00",
      address: role === "courier" ? `Тестовая улица, ${i + 1}` : "",
    });
    orders.push(order);
    if (role === "courier") {
      await post(page, `orders/${order.id}/assignment`, {
        version: order.version,
        florist_id: null,
        courier_id: staff.id,
      });
    }
  }
  return { staff, orders };
}

test("флорист: страницы, размер, дата и исчезновение последнего задания", async ({
  page,
  browser,
}, info) => {
  const { staff, orders } = await prepare(page, "florist", 13);
  const other = await post(page, "staff", {
    username: `${account.username}_other`,
    password: account.password,
    name: "Другой флорист",
    role: "florist",
  });
  workerPage = await browser.newPage({
    baseURL: "http://127.0.0.1:5173",
    viewport: { width: 1440, height: 1000 },
  });
  const worker = workerPage;
  await worker.goto("/login");
  await submitLogin(worker, staff.username, account.password);
  const top = worker.getByRole("navigation", {
    name: "Страницы заданий сверху",
  });
  const bottom = worker.getByRole("navigation", {
    name: "Страницы заданий снизу",
  });
  const cards = worker.locator(".task-grid > article");
  await expect(top).toContainText("1–6 из 13");
  await expect(top).toContainText("Страница 1 из 3");
  await expect(cards).toHaveCount(6);
  await expect(
    top.getByRole("button", { name: "Предыдущая страница" }),
  ).toBeDisabled();
  await top.getByRole("button", { name: "Следующая страница" }).click();
  await expect(top).toContainText("7–12 из 13");
  await expect(cards.first()).toContainText("Получатель 7");
  await cards
    .first()
    .getByRole("button", { name: "Взять в работу", exact: true })
    .click();
  await expect(
    cards.first().getByRole("button", { name: "Букет готов" }),
  ).toBeVisible();
  await expect(top).toContainText("Страница 2 из 3");
  await bottom.getByRole("button", { name: "Следующая страница" }).click();
  await expect(top).toContainText("13–13 из 13");
  await expect(cards).toHaveCount(1);
  await expect(
    top.getByRole("button", { name: "Следующая страница" }),
  ).toBeDisabled();
  await expect(top).toBeInViewport();

  // Another florist can take the only unassigned order on the last page.
  await post(page, `orders/${orders[12].id}/assignment`, {
    version: orders[12].version,
    florist_id: other.id,
    courier_id: null,
  });
  await worker.getByRole("button", { name: "Обновить задания" }).click();
  await expect(top).toContainText("Страница 2 из 2");
  await expect(top).toContainText("7–12 из 12");
  await expect(cards).toHaveCount(6);

  await worker.getByLabel("Дата получения", { exact: true }).fill("2030-01-11");
  await expect(
    worker.getByText("Заданий пока нет", { exact: true }),
  ).toBeVisible();
  await expect(top).toContainText("Нет записей");
  await expect(
    top.getByRole("button", { name: "Предыдущая страница" }),
  ).toBeDisabled();
  await worker.getByLabel("Дата получения", { exact: true }).fill("2030-01-10");
  await expect(top).toContainText("1–6 из 12");
  await top.getByRole("button", { name: "Следующая страница" }).click();
  await expect(top).toContainText("7–12 из 12");
  await worker.getByLabel("Заданий на странице").selectOption("12");
  await expect(cards).toHaveCount(12);
  await expect(top).toContainText("Страница 1 из 1");
  await worker.getByLabel("Заданий на странице").selectOption("6");
  await expect(cards).toHaveCount(6);
  await worker.setViewportSize({ width: 390, height: 844 });
  await worker.screenshot({
    path: `/tmp/tapme-${info.project.name}-task-pagination-phone.png`,
  });
  expect(
    await worker.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await top.getByRole("button", { name: "Следующая страница" }).click();
  await expect(top).toContainText("Страница 2 из 2");
  await bottom.getByRole("button", { name: "Предыдущая страница" }).click();
  await expect(top).toContainText("Страница 1 из 2");
  await expect(top).toBeInViewport();
});

test("курьер: страницы содержат только назначенные заказы", async ({
  page,
  browser,
}) => {
  const { staff, orders } = await prepare(page, "courier", 7);
  await post(page, "orders", {
    customer_id: orders[0].customer_id,
    recipient_name: "Не назначен этому курьеру",
    fulfillment: "courier",
    delivery_date: "2030-01-10",
    window_start: "10:00",
    window_end: "12:00",
    address: "Другой адрес",
    items: [{ product_id: orders[0].lines[0].product_id, quantity: 1 }],
  });
  workerPage = await browser.newPage({
    baseURL: "http://127.0.0.1:5173",
    viewport: { width: 390, height: 844 },
  });
  const worker = workerPage;
  await worker.goto("/login");
  await submitLogin(worker, staff.username, account.password);
  const top = worker.getByRole("navigation", {
    name: "Страницы заданий сверху",
  });
  await expect(top).toContainText("1–6 из 7");
  await top.getByRole("button", { name: "Следующая страница" }).click();
  await expect(top).toContainText("7–7 из 7");
  await expect(worker.locator(".task-grid > article")).toHaveCount(1);
  await expect(worker.locator(".task-grid")).toContainText("Тестовая улица, 7");
  await expect(
    worker.getByText("Не назначен этому курьеру", { exact: true }),
  ).toHaveCount(0);
  await worker.getByLabel("Заданий на странице").selectOption("24");
  await expect(worker.locator(".task-grid > article")).toHaveCount(7);
  await expect(top).toContainText("Страница 1 из 1");
});
