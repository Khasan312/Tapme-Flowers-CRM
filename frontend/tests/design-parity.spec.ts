import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { submitLogin } from "./login";
let account: { username: string; password: string; business_id: string };
const python = resolve("../backend/.venv/bin/python"),
  fixture = resolve("../backend/tests/browser_fixture.py");
test.beforeAll(() => {
  account = JSON.parse(
    execFileSync(python, [fixture, "create"], { encoding: "utf8" }),
  );
});
test.afterAll(() => {
  if (account)
    execFileSync(python, [fixture, "delete"], {
      input: JSON.stringify(account),
    });
});
test("макет: настройки, общий поиск, виды заказов и размеры экранов", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/login");
  await submitLogin(page, account.username, account.password);
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await expect(
    page.getByRole("cell", { name: account.username, exact: true }),
  ).toBeVisible();
  const tabs = ["Сотрудники", "Окна доставки", "Шаблоны", "Прайс", "Магазин"];
  for (const name of tabs)
    await expect(page.getByRole("tab", { name, exact: true })).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: "Поиск", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-settings-staff.png`,
    fullPage: true,
  });
  await page.getByRole("tab", { name: "Окна доставки" }).click();
  await page.getByLabel("Вместимость окна 1", { exact: true }).fill("4");
  await page.getByLabel("Стоимость окна 1", { exact: true }).fill("300");
  await page
    .getByLabel("Не принимать заказ в окно, если оно заполнено")
    .check();
  await page.getByRole("button", { name: "Сохранить окна" }).click();
  await expect(page.getByRole("status")).toContainText("Сохранено");
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-settings-windows.png`,
    fullPage: true,
  });
  await page.getByRole("tab", { name: "Шаблоны", exact: true }).click();
  await expect(page.locator("textarea")).toHaveCount(10);
  await page
    .getByRole("textbox", { name: "Дата через 7 дней", exact: true })
    .fill("{имя}, через неделю {повод}. {магазин}");
  await page.getByRole("button", { name: "Сохранить шаблоны" }).first().click();
  await expect(page.getByRole("status")).toContainText("Шаблоны сохранены");
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-settings-templates.png`,
    fullPage: true,
  });
  await page.getByRole("tab", { name: "Магазин", exact: true }).click();
  await page.getByLabel("Город", { exact: true }).fill("Бишкек");
  await page.getByLabel("Адрес", { exact: true }).fill("Улица цветов, 12");
  await page.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Сохранено");
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-settings-shop.png`,
    fullPage: true,
  });
  async function api(path: string, body: unknown, method = "POST") {
    return page.evaluate(
      async ({ path, body, method }) => {
        const csrf = decodeURIComponent(
          document.cookie
            .split("; ")
            .find((c) => c.startsWith("csrftoken="))
            ?.split("=")[1] || "",
        );
        const r = await fetch(path, {
          method,
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
          body: JSON.stringify(body),
        });
        const data = await r.json();
        if (!r.ok) throw Error(JSON.stringify(data));
        return data;
      },
      {
        path: `/api/v1/businesses/${account.business_id}/${path}/`,
        body,
        method,
      },
    );
  }
  const c = await api("customers", {
    name: "Алия Тестовая",
    phone: "+996555444333",
    consent: true,
    source: "Instagram",
    tags: ["VIP"],
  });
  const product = await api("products", {
    name: "Авторский букет",
    price: "2500",
  });
  await page.getByRole("button", { name: "Клиенты", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /Алия Тестовая/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: "VIP", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /Алия Тестовая/ }),
  ).toBeVisible();
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-clients.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: /Алия Тестовая/ }).click();
  await expect(
    page.getByRole("heading", { name: /Алия Тестовая/ }),
  ).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-client.png`,
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Новый заказ", exact: true })
    .last()
    .click();
  await expect(
    page.getByText("Выбран: Алия Тестовая", { exact: false }),
  ).toBeVisible();
  await expect(page.getByLabel("Получатель", { exact: true })).toHaveValue(
    "Алия Тестовая",
  );
  await expect(
    page.getByLabel("Телефон получателя", { exact: true }),
  ).toHaveValue("+996555444333");
  await page
    .getByRole("button", { name: "Добавить в заказ", exact: true })
    .click();
  await page.getByLabel("Получение", { exact: true }).selectOption("courier");
  await page.getByLabel("Адрес доставки").fill("Улица цветов, 15");
  await expect(
    page.getByText("Доставка: 300 сом", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Создать заказ", exact: true })
    .click();
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await page.getByRole("combobox", { name: "Поиск", exact: true }).fill("Алия");
  await page.getByRole("option", { name: /Клиент/ }).click();
  await expect(
    page.getByRole("heading", { name: /Алия Тестовая/ }),
  ).toBeVisible();
  await page.getByRole("combobox", { name: "Поиск", exact: true }).fill("#1");
  await page.getByRole("option", { name: /Заказ/ }).click();
  await expect(page.getByRole("dialog")).toHaveClass(/order-drawer/);
  await expect(
    page.getByRole("heading", { name: "Заказ №1", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Закрыть", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "Заказы", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Открыть заказ №1" }),
  ).toBeVisible();
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-tiles.png`,
    fullPage: true,
  });
  for (const mode of ["Доска", "Список", "Календарь", "Плитки"]) {
    await page.getByRole("button", { name: mode, exact: true }).click();
    await expect(
      page.getByRole("button", { name: mode, exact: true }),
    ).toHaveClass(/is-on/);
  }
  await page
    .getByLabel("Новая задача", { exact: true })
    .fill("Проверить упаковку");
  await page.getByLabel("Новая задача", { exact: true }).press("Enter");
  await expect(
    page.getByRole("button", { name: "Завершить: Проверить упаковку" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Завершить: Проверить упаковку" })
    .click();
  await expect(
    page.getByRole("button", { name: "Завершить: Проверить упаковку" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await page.getByRole("tab", { name: "Прайс", exact: true }).click();
  await page.getByRole("button", { name: "Скрыть Авторский букет" }).click();
  await expect(
    page.getByRole("button", { name: "Авторский букет", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Архив", exact: true }).click();
  await page.getByRole("button", { name: "Вернуть Авторский букет" }).click();
  await expect(
    page.getByRole("button", { name: "Скрыть Авторский букет" }),
  ).toBeVisible();
  const courier = await api("staff", {
    name: "Курьер проверки",
    username: account.username + "_delivery",
    password: account.password,
    role: "courier",
    staff_phone: "+996700222111",
  });
  await page.getByRole("button", { name: "Доставка", exact: true }).click();
  await expect(page.getByRole("heading", { name: "По окнам" })).toBeVisible();
  await page.getByLabel("Курьер заказа №1").selectOption(courier.id);
  await expect(page.getByText("Алия Тестовая", { exact: true })).toBeVisible();
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-deliveries.png`,
    fullPage: true,
  });
  const profile = await api(`customers/${c.id}`, undefined, "GET");
  const next = await page.evaluate(() => {
    const day = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Bishkek",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
    const date = new Date(day + "T12:00:00Z");
    date.setUTCDate(date.getUTCDate() + 7);
    return { day: date.getUTCDate(), month: date.getUTCMonth() + 1 };
  });
  await api(
    `customers/${c.id}`,
    {
      ...profile,
      id: undefined,
      code: undefined,
      created_at: undefined,
      dates: [{ label: "День рождения", person: "Мама", ...next }],
    },
    "PUT",
  );
  await api("reminders", {});
  await page.getByRole("button", { name: "Напоминания", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Алия Тестовая", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(/Алия Тестовая, через неделю День рождения/),
  ).toBeVisible();
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-reminders.png`,
    fullPage: true,
  });
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    for (const nav of [
      "Заказы",
      "Клиенты",
      "Напоминания",
      "Доставка",
      "Настройки",
    ]) {
      await page.getByRole("button", { name: nav, exact: true }).click();
      await expect(
        page.getByRole("combobox", { name: "Поиск", exact: true }),
      ).toBeVisible();
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(width);
    }
    if (width === 390)
      await page.screenshot({
        path: `/tmp/tapme-${info.project.name}-mobile-settings.png`,
        fullPage: true,
      });
  }
  expect(errors).toEqual([]);
});
