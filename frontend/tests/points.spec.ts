import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { submitLogin } from "./login";

const python = resolve("../backend/.venv/bin/python"),
  fixture = resolve("../backend/tests/browser_fixture.py");
let account: { username: string; password: string; business_id: string };
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
  await page.goto("/?view=settings&tab=points");
  await submitLogin(page, account.username, account.password);
  await expect(
    page.getByRole("heading", { name: "Точки магазина" }),
  ).toBeVisible();
}
async function api(
  page: Page,
  resource: string,
  data: object,
  method = "POST",
) {
  const csrf = await (await page.request.get("/api/v1/auth/csrf/")).json();
  const response = await page.request.fetch(
    `/api/v1/businesses/${account.business_id}/${resource}/`,
    {
      method,
      data,
      headers: {
        "X-CSRFToken": csrf.csrf_token,
        "Idempotency-Key": crypto.randomUUID(),
      },
    },
  );
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}
function pointSwitcher(page: Page) {
  return page.getByRole("button", { name: /, филиал: / });
}
async function selectPoint(page: Page, name: string) {
  await pointSwitcher(page).click();
  await page.getByRole("option", { name, exact: true }).click();
  await expect(pointSwitcher(page)).toHaveAccessibleName(
    new RegExp(`, филиал: ${name}$`),
  );
  await expect(
    page.getByRole("listbox", { name: "Выберите филиал" }),
  ).toBeHidden();
}
async function add(page: Page, name: string, address: string) {
  await page
    .getByRole("button", { name: "Добавить точку", exact: true })
    .click();
  await page
    .getByLabel("Название точки", { exact: true })
    .fill(`Филиал ${name}`);
  await page.getByLabel("Короткое название", { exact: true }).fill(name);
  await page.getByLabel("Адрес точки", { exact: true }).fill(address);
  await page
    .getByRole("button", { name: "Сохранить точку", exact: true })
    .click();
  await expect(
    page.getByText("Точка сохранена", { exact: true }),
  ).toBeVisible();
}

test("создание трёх точек, выбор и сохранение после обновления", async ({
  page,
}, info) => {
  await login(page);
  await expect(pointSwitcher(page)).toHaveCount(0);
  await add(page, "Чуй", "Чуй, 12");
  await add(page, "Юг", "Южная, 7");
  const selector = pointSwitcher(page);
  const company = selector.locator("strong");
  await expect(company).toContainText("Цветочная мастерская");
  await expect(page.locator(".rail-foot .shop-n")).toHaveCount(0);
  const settingsUrl = page.url();
  await company.click();
  await expect(
    page.getByRole("listbox", { name: "Выберите филиал" }),
  ).toBeVisible();
  await expect(page).toHaveURL(settingsUrl);
  await page.keyboard.press("Escape");
  await selector.focus();
  await page.keyboard.press("ArrowDown");
  const list = page.getByRole("listbox", { name: "Выберите филиал" });
  await expect(list.getByRole("option")).toHaveCount(4);
  await expect(list).toBeFocused();
  await page.keyboard.press("End");
  await page.keyboard.press("ArrowUp");
  await page.keyboard.press("Enter");
  await expect(selector).toHaveAccessibleName(/, филиал: Юг$/);
  await expect(page.getByLabel("Адрес точки", { exact: true })).toHaveValue(
    "Южная, 7",
  );
  const url = page.url();
  await selector.click();
  await expect(
    page.getByRole("option", { name: "Юг", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await expect(list).toContainText("Южная, 7");
  await expect(page.locator(".point-switch-popup")).toHaveCSS("opacity", "1");
  await page.screenshot({
    path: `/tmp/tapme-point-switch-open-${info.project.name}.png`,
  });
  // Opening, dismissing and moving focus must not change the current branch.
  await selector.click();
  await expect(list).toBeHidden();
  await selector.click();
  await page.keyboard.press("Home");
  await page.keyboard.press("Escape");
  await expect(selector).toBeFocused();
  await expect(page).toHaveURL(url);
  await selector.click();
  await page.getByRole("heading", { name: "Точки магазина" }).click();
  await expect(list).toBeHidden();
  await expect(page).toHaveURL(url);
  await page.reload();
  await expect(page).toHaveURL(url);
  await expect(selector).toHaveAccessibleName(/, филиал: Юг$/);
  await page.screenshot({
    path: `/tmp/tapme-points-${info.project.name}.png`,
    fullPage: true,
  });
  await selectPoint(page, "Все точки");
  await expect(page).toHaveURL(/point=all/);
  await page.goBack();
  await expect(selector).toHaveAccessibleName(/, филиал: Юг$/);
  await page.setViewportSize({ width: 820, height: 900 });
  const triggerBox = await selector.boundingBox();
  expect(triggerBox!.width).toBeGreaterThan(150);
  expect(triggerBox!.x).toBeGreaterThanOrEqual(0);
  expect(triggerBox!.x + triggerBox!.width).toBeLessThanOrEqual(192);
  expect(triggerBox!.y + triggerBox!.height).toBeLessThanOrEqual(900);
  await selector.click();
  await expect(page.locator(".point-switch-popup")).toHaveCSS("opacity", "1");
  await page.screenshot({
    path: `/tmp/tapme-point-switch-tablet-${info.project.name}.png`,
  });
});

test("переключение точки меняет доставки, напоминания и их счётчики", async ({
  page,
}) => {
  await login(page);
  await add(page, "Чуй", "Чуй, 12");
  const base = `/api/v1/businesses/${account.business_id}`;
  const points = await (await page.request.get(base + "/points/")).json();
  const product = await api(page, "products", {
    name: "Букет филиала",
    price: "1000.00",
  });
  const today = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Bishkek",
  }).format(new Date());
  const next = new Date(today + "T12:00:00Z");
  next.setUTCDate(next.getUTCDate() + 1);
  for (const [index, point] of points.entries()) {
    const customer = await api(page, "customers", {
      name: `Клиент ${point.short_name}`,
      phone: `+99655512345${index}`,
      consent: true,
    });
    const profile = await (
      await page.request.get(`${base}/customers/${customer.id}/`)
    ).json();
    const { id, code, created_at, ...input } = profile;
    void id;
    void code;
    void created_at;
    await api(
      page,
      `customers/${customer.id}`,
      {
        ...input,
        dates: [
          {
            label: "День рождения",
            person: "Мама",
            month: next.getUTCMonth() + 1,
            day: next.getUTCDate(),
          },
        ],
      },
      "PUT",
    );
    await api(page, "orders", {
      point_id: point.id,
      customer_id: customer.id,
      items: [{ product_id: product.id, quantity: 1 }],
      recipient_name: `Получатель ${point.short_name}`,
      recipient_phone: "+996555123456",
      fulfillment: "courier",
      address: `Адрес ${point.short_name}`,
      delivery_date: today,
      window_start: "10:00",
      window_end: "12:00",
    });
  }
  await api(page, "reminders", {});
  const selector = pointSwitcher(page);
  await selectPoint(page, "Все точки");
  await page.getByRole("button", { name: "Напоминания", exact: true }).click();
  await expect(page.locator("article.rm-reminder")).toHaveCount(2);
  for (const point of points) {
    await selectPoint(page, point.short_name);
    await expect(page.locator("article.rm-reminder")).toHaveCount(1);
    await expect(page.locator("article.rm-reminder")).toContainText(
      `Клиент ${point.short_name}`,
    );
    await page.getByRole("button", { name: "Доставка", exact: true }).click();
    await expect(page.locator(".window-group")).toHaveCount(1);
    await expect(
      page.getByText(
        `№${points.indexOf(point) + 1} · Получатель ${point.short_name}`,
        { exact: true },
      ),
    ).toBeVisible();
    await page.reload();
    await expect(selector).toHaveAccessibleName(
      new RegExp(`, филиал: ${point.short_name}$`),
    );
    await expect(page.locator(".window-group")).toHaveCount(1);
    await page
      .getByRole("button", { name: "Напоминания", exact: true })
      .click();
  }
  await selectPoint(page, "Все точки");
  await expect(page.locator("article.rm-reminder")).toHaveCount(2);
  await page.getByRole("button", { name: "Доставка", exact: true }).click();
  await expect(page.locator(".window-group")).toHaveCount(2);
  await expect(page.locator(".window-group .point-badge")).toHaveCount(2);
});

test("заказы и окна доставки разделены по точкам, клиенты общие", async ({
  page,
}) => {
  await login(page);
  await add(page, "Чуй", "Чуй, 12");
  const base = `/api/v1/businesses/${account.business_id}`;
  const points = await (await page.request.get(base + "/points/")).json();
  const primary = points.find((p: { is_primary: boolean }) => p.is_primary),
    second = points.find((p: { short_name: string }) => p.short_name === "Чуй");
  const customer = await api(page, "customers", {
    name: "Клиент обеих точек",
    phone: "+996555123456",
  });
  const product = await api(page, "products", {
    name: "Букет для филиалов",
    price: "2500.00",
  });
  for (const point of [primary, second])
    await api(page, "orders", {
      point_id: point.id,
      customer_id: customer.id,
      items: [{ product_id: product.id, quantity: 1 }],
      recipient_name: "Получатель " + point.short_name,
      fulfillment: "pickup",
      delivery_date: new Intl.DateTimeFormat("en-CA", {
        timeZone: "Asia/Bishkek",
      }).format(new Date()),
      window_start: "10:00",
      window_end: "12:00",
    });
  await page.getByRole("button", { name: "Заказы", exact: true }).click();
  await selectPoint(page, "Все точки");
  await expect(page.locator("article.tk")).toHaveCount(2);
  await expect(
    page.locator("article.tk .point-badge", { hasText: "Чуй" }),
  ).toBeVisible();
  await selectPoint(page, "Чуй");
  await expect(page.locator("article.tk")).toHaveCount(1);
  await expect(page.locator("article.tk")).toContainText("Получатель Чуй");
  await page.getByRole("button", { name: "Клиенты", exact: true }).click();
  await expect(
    page.getByText("Клиент обеих точек", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Новый заказ", exact: true }).click();
  await expect(
    page.getByRole("combobox", { name: "Точка заказа" }),
  ).toHaveValue(second.id);
  await page.getByRole("button", { name: "Отмена", exact: true }).click();
  await selectPoint(page, "Все точки");
  await page.getByRole("button", { name: "Новый заказ", exact: true }).click();
  await expect(
    page.getByRole("combobox", { name: "Точка заказа" }),
  ).toHaveValue("");
});

test("мобильные настройки филиала и архив без потери истории", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await add(page, "Чуй", "Чуй, 12");
  await page
    .getByRole("navigation", { name: "Филиалы" })
    .getByRole("button", { name: /Чуй/ })
    .click();
  await expect(page.getByLabel("Адрес точки", { exact: true })).toHaveValue(
    "Чуй, 12",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: `/tmp/tapme-points-mobile-${info.project.name}.png`,
    fullPage: true,
  });
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await pointSwitcher(page).click();
    const popup = page.locator(".point-switch-popup");
    await expect(popup).toBeVisible();
    await expect(popup).toHaveCSS("opacity", "1");
    const box = await popup.boundingBox();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(width);
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.y + box!.height).toBeLessThanOrEqual(844);
    await page.screenshot({
      path: `/tmp/tapme-point-switch-mobile-${width}-${info.project.name}.png`,
    });
    await page.getByRole("option", { name: "Чуй", exact: true }).click();
    await expect(pointSwitcher(page)).toContainText("Филиал: Чуй");
  }
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Архивировать точку" }).click();
  // Archiving the selected point returns to the combined workspace.
  await expect(pointSwitcher(page)).toHaveAccessibleName(
    /, филиал: Все точки$/,
  );
  await expect(page.getByRole("navigation", { name: "Филиалы" })).toContainText(
    "В архиве",
  );
  const selector = pointSwitcher(page);
  await selectPoint(page, "Все точки");
  await page.reload();
  await expect(selector).toHaveAccessibleName(/, филиал: Все точки$/);
  await selector.click();
  await expect(
    page.getByRole("option", { name: "Чуй", exact: true }),
  ).toHaveCount(0);
});
