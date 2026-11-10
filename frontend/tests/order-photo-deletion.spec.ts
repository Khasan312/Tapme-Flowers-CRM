import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";
import { submitLogin } from "./login";

let account: { username: string; password: string; business_id: string };
const python = resolve("../backend/.venv/bin/python");
const fixture = resolve("../backend/tests/browser_fixture.py");
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

async function login(page: Page, username: string) {
  await page.goto("/login");
  await submitLogin(page, username, account.password);
}
async function logout(page: Page) {
  await page.getByRole("button", { name: "Меню пользователя" }).click();
  await page.getByRole("menuitem", { name: "Выйти", exact: true }).click();
  await expect(page.getByLabel("Логин", { exact: true })).toBeVisible();
}
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

test("удаление фото: подтверждение, ошибка и повтор, сохранность остальных и права курьера", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await login(page, account.username);
  const staff = [];
  for (const role of ["florist", "courier"]) {
    staff.push(
      await post(page, "staff", {
        username: `${account.username}_${role}`,
        password: account.password,
        name: `Проверка фото ${role}`,
        role,
      }),
    );
  }
  const customer = await post(page, "customers", {
    name: "Клиент фото",
    phone: "+12025550123",
  });
  const product = await post(page, "products", {
    name: "Букет фото",
    price: "1000",
  });
  const order = await post(page, "orders", {
    customer_id: customer.id,
    items: [{ product_id: product.id, quantity: 1 }],
    recipient_name: "Получатель фото",
    fulfillment: "courier",
    delivery_date: "2030-01-10",
    window_start: "10:00",
    window_end: "12:00",
    address: "Шукурова, тестовый адрес",
  });
  await post(page, `orders/${order.id}/assignment`, {
    version: order.version,
    florist_id: staff[0].id,
    courier_id: staff[1].id,
  });
  const photosUrl = `/api/v1/businesses/${account.business_id}/orders/${order.id}/photos/`;
  const buffer = execFileSync(python, [
    "-c",
    "import sys; from PIL import Image; Image.new('RGB', (80, 80), 'pink').save(sys.stdout.buffer, 'PNG')",
  ]);
  const csrf = await (await page.request.get("/api/v1/auth/csrf/")).json();
  for (const kind of ["bouquet", "bouquet", "bouquet", "bouquet", "delivery"]) {
    const response = await page.request.post(photosUrl, {
      headers: { "X-CSRFToken": csrf.csrf_token },
      multipart: {
        kind,
        file: { name: "flower.png", mimeType: "image/png", buffer },
      },
    });
    expect(response.status()).toBe(201);
  }
  await logout(page);
  await login(page, staff[0].username);
  const task = page.locator(".m-card");
  await expect(task.locator(".order-photo")).toHaveCount(5);
  await expect(task.locator(".photo-remove")).toHaveCount(4);
  const firstUrl = await task
    .locator(".order-photo a")
    .first()
    .getAttribute("href");
  await task.locator(".photo-remove").first().click();
  await page.getByRole("button", { name: "Отмена", exact: true }).click();
  await expect(task.locator(".order-photo")).toHaveCount(5);
  await task.locator(".photo-remove").first().click();
  await page.setViewportSize({ width: 320, height: 800 });
  await page.locator(".photo-delete-confirm").scrollIntoViewIfNeeded();
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-photo-delete-phone.png`,
  });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(320);
  await page.route("**/photos/*/", async (route) => {
    if (route.request().method() === "DELETE")
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: "{}",
      });
    else await route.continue();
  });
  const confirm = page.getByRole("button", {
    name: "Удалить фото",
    exact: true,
  });
  await confirm.click();
  await expect(page.getByRole("alert")).toContainText(
    "Сервер не смог выполнить запрос",
  );
  await expect(task.locator(".order-photo")).toHaveCount(5);
  await page.unroute("**/photos/*/");
  await confirm.click();
  await expect(
    page.getByRole("status").filter({ hasText: "Фотография удалена" }),
  ).toBeVisible();
  await expect(task.locator(".order-photo")).toHaveCount(4);
  expect((await page.request.get(firstUrl!)).status()).toBe(404);
  await page.reload();
  await expect(task.locator(".order-photo")).toHaveCount(4);
  await expect(task.locator(".photo-remove")).toHaveCount(3);
  await logout(page);
  await login(page, staff[1].username);
  await expect(
    page.getByRole("heading", {
      name: "Адрес: Шукурова, тестовый адрес",
      exact: true,
    }),
  ).toBeVisible();
  await expect(task.locator(".order-photo")).toHaveCount(4);
  await expect(task.locator(".photo-remove")).toHaveCount(1);
  await expect(task.locator(".photo-remove")).toHaveAccessibleName(/вручение/);
  await task.locator(".photo-remove").click();
  await confirm.click();
  await expect(task.locator(".order-photo")).toHaveCount(3);
  await expect(task.locator(".photo-remove")).toHaveCount(0);
  expect(errors).toEqual([]);
});
