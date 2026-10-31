import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { submitLogin } from "./login";

let account: { username: string; password: string; business_id: string };
let seeded: { chat_id: string; customer_id: string };
const python = resolve("../backend/.venv/bin/python"),
  fixture = resolve("../backend/tests/browser_fixture.py"),
  chats = resolve("../backend/tests/chat_browser_fixture.py");
test.beforeEach(() => {
  account = JSON.parse(
    execFileSync(python, [fixture, "create"], { encoding: "utf8" }),
  );
  seeded = JSON.parse(
    execFileSync(python, [chats, "seed"], {
      input: JSON.stringify(account),
      encoding: "utf8",
    }),
  );
});
test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "wait" });
  execFileSync(python, [fixture, "delete"], { input: JSON.stringify(account) });
});
const chatUrl = () =>
  `/?view=chats&business=${account.business_id}&chat=${seeded.chat_id}`;
async function api(page: Page, suffix: string, method = "GET", data?: unknown) {
  return page.evaluate(
    async ({ business, suffix, method, data }) => {
      const csrf = await (await fetch("/api/v1/auth/csrf/")).json();
      const response = await fetch(`/api/v1/businesses/${business}/${suffix}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf.csrf_token,
        },
        ...(data ? { body: JSON.stringify(data) } : {}),
      });
      if (!response.ok) throw new Error(await response.text());
      return response.json();
    },
    { business: account.business_id, suffix, method, data },
  );
}
async function login(page: Page) {
  await page.goto("/");
  await submitLogin(page, account.username, account.password);
  await api(page, "products/", "POST", {
    name: "Нежный букет",
    price: "3200.00",
  });
  await page.goto(chatUrl());
  await expect(page.getByRole("log")).toContainText("Сообщение 65");
}
async function editor(page: Page, mobile = false) {
  if (mobile)
    await page
      .getByRole("group", { name: "Клиент и черновик", exact: true })
      .getByRole("button", { name: "Черновик заказа", exact: true })
      .click();
  await page
    .getByRole("button", { name: "Создать черновик", exact: true })
    .click();
  await expect(page.locator("dialog[open] h2")).toHaveText("Черновик заказа");
  await page
    .getByRole("button", { name: "Добавить позицию в черновик" })
    .click();
  await page
    .getByLabel("Дата получения", { exact: true })
    .fill(new Date(Date.now() + 4 * 86400000).toISOString().slice(0, 10));
  await page
    .getByLabel("Окно получения", { exact: true })
    .selectOption("10:00|12:00");
  await page
    .getByLabel("Адрес доставки", { exact: true })
    .fill("Бишкек, Токтогула 125");
  await page
    .getByLabel("Текст открытки", { exact: true })
    .fill("Маме с любовью");
}

for (const mobile of [false, true])
  test(`черновик в чате, обновление страницы, pending и подтверждение ${mobile ? "390" : "1440"}`, async ({
    page,
  }, info) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    await login(page);
    await editor(page, mobile);
    await page
      .getByRole("button", { name: "Сохранить черновик", exact: true })
      .click();
    await expect(page.getByRole("status")).toContainText("Черновик сохранён");
    await page.screenshot({
      path: `/tmp/tapme-${info.project.name}-order-draft-${mobile ? 390 : 1440}.png`,
      fullPage: true,
    });
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(mobile ? 390 : 1440);
    await page.reload();
    if (mobile)
      await page
        .getByRole("group", { name: "Клиент и черновик", exact: true })
        .getByRole("button", { name: "Черновик заказа", exact: true })
        .click();
    await page
      .getByRole("button", { name: "Открыть черновик", exact: true })
      .click();
    await expect(
      page.getByLabel("Текст открытки", { exact: true }),
    ).toHaveValue("Маме с любовью");
    await page
      .getByRole("button", {
        name: "Создать заказ · ждёт подтверждения",
        exact: true,
      })
      .click();
    await expect(
      page.getByLabel("Подтверждение заказа", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Подтвердить заказ", exact: true }),
    ).toBeDisabled();
    await page
      .getByLabel("Подтверждение заказа", { exact: true })
      .scrollIntoViewIfNeeded();
    await page.screenshot({
      path: `/tmp/tapme-${info.project.name}-pending-order-${mobile ? 390 : 1440}.png`,
      fullPage: true,
    });
    await expect(
      page.getByRole("button", { name: "Назначить сотрудников", exact: true }),
    ).toHaveCount(0);
    const pending = await api(page, "orders/desk/?scope=pending");
    expect(pending.count).toBe(1);
    expect(pending.summary.build).toBe(0);
    const orderId = pending.results[0].id;
    if (!mobile) {
      const deskPage = await page.context().newPage();
      await deskPage.goto(`/?view=orders&business=${account.business_id}`);
      await deskPage
        .getByRole("button", { name: /Ждут подтверждения.*1/ })
        .click();
      await expect(deskPage.locator(".tiles article")).toHaveCount(1);
      await deskPage
        .getByRole("button", { name: "Доска", exact: true })
        .click();
      await expect(deskPage.locator(".kcol")).toHaveCount(1);
      await expect(deskPage.locator(".kcol-hd")).toContainText(
        "Ждёт подтверждения",
      );
      await deskPage.locator(".kcard").click();
      await expect(
        deskPage.getByLabel("Подтверждение заказа", { exact: true }),
      ).toBeVisible();
      await deskPage.goto(chatUrl());
      await expect(
        deskPage.getByRole("article", { name: "Системное сообщение" }),
      ).toContainText("ждёт подтверждения");
      await deskPage.close();
    }
    const share = await api(page, `orders/${orderId}/share/`, "POST", {
      revoke: false,
    });
    const publicPage = await page.context().newPage();
    await publicPage.goto(`/track/${share.token}`);
    await expect(
      publicPage.getByRole("heading", {
        name: "Ожидаем подтверждение магазина",
      }),
    ).toBeVisible();
    await publicPage.close();
    await page
      .getByLabel("Причина подтверждения без предоплаты", { exact: true })
      .fill("Постоянный клиент, оплатит при вручении");
    await page
      .getByRole("button", { name: "Подтвердить заказ", exact: true })
      .click();
    await expect(
      page.getByLabel("Подтверждение заказа", { exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Назначить сотрудников", exact: true }),
    ).toBeVisible();
    expect((await api(page, `orders/${orderId}/`)).status).toBe("new");
  });

test("два менеджера: конфликт сохраняет правки и позволяет загрузить актуальный черновик", async ({
  page,
}) => {
  await login(page);
  await editor(page);
  await page
    .getByRole("button", { name: "Сохранить черновик", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Черновик сохранён");
  const other = await page.context().newPage();
  await other.goto(chatUrl());
  await other
    .getByRole("button", { name: "Открыть черновик", exact: true })
    .click();
  await other.getByLabel("Пожелания к заказу").fill("Правка второго менеджера");
  await page.getByLabel("Пожелания к заказу").fill("Без лилий");
  await page
    .getByRole("button", { name: "Сохранить черновик", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Черновик сохранён");
  await other
    .getByRole("button", { name: "Сохранить черновик", exact: true })
    .click();
  await expect(other.locator("dialog [role=alert]")).toContainText(
    "другой вкладке",
  );
  await expect(other.getByLabel("Пожелания к заказу")).toHaveValue(
    "Правка второго менеджера",
  );
  other.once("dialog", (d) => d.accept());
  await other
    .getByRole("button", { name: "Загрузить актуальный черновик" })
    .click();
  await expect(other.getByLabel("Пожелания к заказу")).toHaveValue("Без лилий");
  await other.close();
});

test("потерянный ответ создания не дублирует заказ из черновика", async ({
  page,
}) => {
  await login(page);
  await editor(page);
  await page.route(
    "**/order-draft/convert/",
    async (route) => {
      await route.fetch();
      await route.abort("failed");
    },
    { times: 1 },
  );
  await page
    .getByRole("button", {
      name: "Создать заказ · ждёт подтверждения",
      exact: true,
    })
    .click();
  await expect(page.locator("dialog [role=alert]")).toContainText(
    "Не удалось связаться",
  );
  await page
    .getByRole("button", {
      name: "Создать заказ · ждёт подтверждения",
      exact: true,
    })
    .click();
  await expect(
    page.getByLabel("Подтверждение заказа", { exact: true }),
  ).toBeVisible();
  expect((await api(page, "orders/desk/?scope=all")).count).toBe(1);
});

test("букет по бюджету, неполный черновик и отложенный заказ", async ({
  page,
}) => {
  await login(page);
  await page
    .getByRole("button", { name: "Создать черновик", exact: true })
    .click();
  await page.getByLabel("Пожелания к заказу").fill("Пока уточняем адрес");
  await page
    .getByRole("button", { name: "Сохранить черновик", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Черновик сохранён");
  await page
    .locator("dialog")
    .getByRole("button", { name: "Закрыть", exact: true })
    .click();
  page.once("dialog", (d) => d.accept());
  await page
    .getByRole("button", { name: "Отложить черновик", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Восстановить черновик", exact: true })
    .click();
  await expect(page.getByLabel("Пожелания к заказу")).toHaveValue(
    "Пока уточняем адрес",
  );
  await page.getByText("Букет по бюджету", { exact: true }).click();
  await page.getByLabel("Бюджет", { exact: true }).fill("5000");
  await page
    .getByLabel("Описание букета", { exact: true })
    .fill("Пионы без лилий");
  await page.getByRole("button", { name: "Добавить букет по бюджету" }).click();
  await page
    .getByLabel("Способ получения", { exact: true })
    .selectOption("pickup");
  await page
    .getByLabel("Дата получения", { exact: true })
    .fill(new Date(Date.now() + 4 * 86400000).toISOString().slice(0, 10));
  await page
    .getByLabel("Окно получения", { exact: true })
    .selectOption("10:00|12:00");
  await page
    .locator("dialog")
    .getByRole("button", { name: "Создать заказ", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Назначить сотрудников", exact: true }),
  ).toBeVisible();
  const orders = await api(page, "orders/desk/?scope=all");
  expect(orders.results[0].total).toBe("5000.00");
  expect(orders.results[0].status).toBe("new");
  expect(orders.results[0].lines[0].name).toContain("Пионы без лилий");
});
