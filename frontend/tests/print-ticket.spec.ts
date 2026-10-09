import { test, expect } from "@playwright/test";
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
test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "wait" });
  if (account)
    execFileSync(python, [fixture, "delete"], {
      input: JSON.stringify(account),
    });
});

test("печать талона: только заказ, длинный состав без обрезки и возврат в CRM", async ({
  page,
}, info) => {
  await page.goto("/");
  await submitLogin(page, account.username, account.password);
  const base = `/api/v1/businesses/${account.business_id}`;
  const csrf = await (await page.request.get("/api/v1/auth/csrf/")).json();
  async function create(path: string, data: object) {
    const response = await page.request.post(`${base}/${path}/`, {
      headers: {
        "X-CSRFToken": csrf.csrf_token,
        "Idempotency-Key": randomUUID(),
      },
      data,
    });
    expect(response.status()).toBe(201);
    return response.json();
  }
  const customer = await create("customers", {
    name: "Тестовый покупатель",
    phone: "+996555111222",
  });
  const product = await create("products", {
    name: "Нежность — букет из роз и эвкалипта",
    price: "2500.00",
  });
  const order = await create("orders", {
    customer_id: customer.id,
    recipient_name: "Тестовый получатель",
    recipient_phone: "+996555222333",
    fulfillment: "courier",
    delivery_date: "2026-10-10",
    window_start: "10:00",
    window_end: "12:00",
    address: "Бишкек, Тестовая улица, дом 12, подъезд 2, квартира 25",
    card: "С днём рождения!\nПусть каждый день радует.",
    notes: "Позвонить за десять минут до приезда.\nОткрытку положить внутрь.",
    items: [{ product_id: product.id, quantity: 2 }],
  });
  await page.goto(`/?business=${account.business_id}&order=${order.id}`);
  const print = page.getByRole("button", {
    name: "Печатать талон",
    exact: true,
  });
  await expect(print).toBeVisible();
  await page.evaluate(() => {
    window.print = () => {
      document.documentElement.dataset.printRequested = "true";
    };
  });
  await print.click();
  await expect(page.locator("html")).toHaveAttribute(
    "data-print-requested",
    "true",
  );
  const ticket = page.locator("body > .print-ticket");
  await expect(ticket).toBeHidden();
  await page.emulateMedia({ media: "print" });
  await expect(ticket).toBeVisible();
  await expect(page.locator("#root")).toBeHidden();
  await expect(page.locator("dialog")).toBeHidden();
  await expect(ticket).toContainText(order.address);
  await expect(ticket).toContainText(order.recipient_phone);
  await expect(ticket.getByRole("row")).toHaveCount(2);
  await ticket.screenshot({
    path: `/tmp/tapme-${info.project.name}-print-ticket.png`,
  });
  if (info.project.name === "chromium") {
    const path = "/tmp/tapme-print-ticket.pdf";
    await page.pdf({ path, format: "A4", displayHeaderFooter: false });
    const text = execFileSync("pdftotext", [path, "-"], { encoding: "utf8" });
    expect(text).toContain("Талон заказа №1");
    expect(text).toContain("Нежность");
    expect(text).not.toContain("Печатать талон");
    expect(text).not.toContain("Напоминания");
  }
  await page.emulateMedia({ media: "screen" });
  await expect(print).toBeVisible();
  await expect(ticket).toBeHidden();

  // A read-only response fixture covers the maximum supported order composition.
  const longOrder = {
    ...order,
    fulfillment: "pickup",
    recipient_phone: "",
    address: "",
    lines: Array.from({ length: 50 }, (_, i) => ({
      ...order.lines[0],
      product_id: randomUUID(),
      name: `Позиция ${i + 1}: авторский букет с длинным названием и подарочной упаковкой`,
    })),
    notes: "Завершение длинного талона",
  };
  await page.route(`**${base}/orders/${order.id}/`, (route) =>
    route.fulfill({ json: longOrder }),
  );
  await page.reload();
  await expect(print).toBeVisible();
  await page.emulateMedia({ media: "print" });
  await expect(ticket).toContainText("Самовывоз");
  await expect(ticket).not.toContainText("Телефон");
  await expect(ticket.getByRole("row")).toHaveCount(51);
  if (info.project.name === "chromium") {
    const path = "/tmp/tapme-print-ticket-long.pdf";
    await page.pdf({ path, format: "A4", displayHeaderFooter: false });
    const text = execFileSync("pdftotext", [path, "-"], { encoding: "utf8" });
    for (let i = 1; i <= 50; i++) expect(text).toContain(`Позиция ${i}:`);
    expect(text).toContain("Завершение длинного талона");
    expect(text).not.toContain("Обновить карточку");
  }
  await page.emulateMedia({ media: "screen" });
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByRole("button", { name: "Закрыть", exact: true })
    .first()
    .click();
  await expect(ticket).toHaveCount(0);
});
