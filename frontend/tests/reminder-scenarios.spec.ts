import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { randomUUID } from "node:crypto";
import { submitLogin } from "./login";
let account: { username: string; password: string; business_id: string };
const python = resolve("../backend/.venv/bin/python"),
  fixture = resolve("../backend/tests/browser_fixture.py");
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
async function login(page: Page) {
  await page.goto("/");
  await submitLogin(page, account.username, account.password);
  await expect(page.locator(".app-shell")).toBeVisible();
}
async function api(
  page: Page,
  path: string,
  data?: unknown,
  method = data ? "POST" : "GET",
) {
  const csrf = await (await page.request.get("/api/v1/auth/csrf/")).json();
  const response = await page.request.fetch(
    `/api/v1/businesses/${account.business_id}/${path.includes("?") ? path : path + "/"}`,
    {
      method,
      data,
      headers: {
        "X-CSRFToken": csrf.csrf_token,
        "Idempotency-Key": randomUUID(),
      },
    },
  );
  expect(response.ok(), `${path}: ${await response.text()}`).toBeTruthy();
  return response.status() === 204 ? null : response.json();
}
async function goQueue(page: Page) {
  await page.getByRole("button", { name: "Напоминания", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Кому написать сегодня" }),
  ).toBeVisible();
}
async function scenarioSettings(page: Page) {
  await goQueue(page);
  await page
    .getByRole("button", { name: "Настройки напоминаний", exact: true })
    .click();
  await expect(
    page.getByLabel("Название сценария", { exact: true }),
  ).toHaveValue("День рождения");
}
async function customer(page: Page, name: string, index: number, days: number) {
  const c = await api(page, "customers", {
    name,
    phone: `+99655512${String(index).padStart(4, "0")}`,
    consent: true,
  });
  const profile = await api(page, `customers/${c.id}`);
  const target = await page.evaluate((days) => {
    const today = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Bishkek",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
    const date = new Date(today + "T12:00:00Z");
    date.setUTCDate(date.getUTCDate() + days);
    return { day: date.getUTCDate(), month: date.getUTCMonth() + 1 };
  }, days);
  const { id, code, created_at, ...input } = profile;
  void id;
  void code;
  void created_at;
  await api(
    page,
    `customers/${c.id}`,
    {
      ...input,
      dates: [{ label: "День рождения", person: "Айжан", ...target }],
    },
    "PUT",
  );
  return c;
}
async function seed(page: Page, count = 3) {
  const config = await api(page, "reminder-scenarios");
  await api(
    page,
    "reminder-scenarios",
    { ...config, start_hour: 0, end_hour: 24, min_days_between: 0 },
    "PUT",
  );
  const clients = [];
  for (let i = 0; i < count; i++)
    clients.push(
      await customer(
        page,
        [
          "Алина Садыкова",
          "Тимур Осмонов",
          "Мария Ким",
          "Данияр Исаев",
          "Айдана Каримова",
          "Руслан Абдраев",
        ][i % 6] + (i > 5 ? ` ${i}` : ""),
        i,
        [1, 3, 7][i % 3],
      ),
    );
  await api(page, "reminders", {});
  return clients;
}

test("сценарии сохраняются, предпросмотр и мобильная версия соответствуют редактору", async ({
  page,
}, info) => {
  await login(page);
  await scenarioSettings(page);
  await expect(
    page.getByLabel("Список сценариев").locator(".rm-scenario"),
  ).toHaveCount(6);
  await page.getByRole("tab", { name: "За 1 дн.", exact: true }).click();
  await page
    .getByLabel("Текст шага", { exact: true })
    .fill(
      "{имя}, здравствуйте! {магазин}. Завтра {повод} у {получатель}. Подобрать букет?",
    );
  await expect(page.locator(".rm-bubble")).toContainText(
    "Алина, здравствуйте!",
  );
  await page.getByLabel("Минимум дней между сообщениями").fill("2");
  await page.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Настройки напоминаний сохранены",
  );
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-scenarios-desktop.png`,
    fullPage: true,
  });
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Настройки напоминаний", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Минимум дней между сообщениями")).toHaveValue(
    "2",
  );
  await page.getByRole("button", { name: "Новый", exact: true }).click();
  await page.getByLabel("Название нового сценария").fill("День учителя");
  await page.getByLabel("Когда напоминать").selectOption("holiday");
  await page
    .getByRole("button", { name: "Добавить сценарий", exact: true })
    .click();
  await page.getByLabel("День праздника").fill("5");
  await page.getByLabel("Месяц", { exact: true }).selectOption("10");
  await page
    .getByLabel("Текст шага", { exact: true })
    .fill("{имя}, скоро День учителя. Выбрать букет? {магазин}");
  await page.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Настройки напоминаний сохранены",
  );
  const config = await api(page, "reminder-scenarios");
  expect(config.scenarios.at(-1).holiday_month).toBe(10);
  for (const width of [390, 768]) {
    await page.setViewportSize({ width, height: 844 });
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await expect(
      page.getByRole("button", { name: "Сохранить", exact: true }),
    ).toBeVisible();
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-scenarios-mobile.png`,
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "К напоминаниям", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Кому написать сегодня" }),
  ).toBeVisible();
  await page.goBack();
  await expect(
    page.getByRole("heading", { name: "Настройки напоминаний", exact: true }),
  ).toBeVisible();
});

test("очередь: группы, правка сообщения, WhatsApp, отмена и результат с реальным заказом", async ({
  page,
  context,
}, info) => {
  await login(page);
  const clients = await seed(page, 6);
  await goQueue(page);
  await expect(page.getByRole("heading", { name: /^Завтра/ })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /^Через 3 дн/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /^Через неделю/ }),
  ).toBeVisible();
  const row = () =>
    page.getByRole("article", {
      name: "Напоминание: Алина Садыкова",
      exact: true,
    });
  await row().getByLabel("Действия: Алина Садыкова").click();
  await row().getByRole("button", { name: "Изменить текст" }).click();
  await page
    .getByLabel("Сообщение", { exact: true })
    .fill("Алина, приготовим для Айжан красивый букет?");
  await page.getByRole("button", { name: "Сохранить текст" }).click();
  await expect(row().locator(".rm-preview")).toHaveText(
    "Алина, приготовим для Айжан красивый букет?",
  );
  await context.route("https://wa.me/**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "text/html",
      body: "<p>WhatsApp test. No message sent.</p>",
    }),
  );
  const popupPromise = context.waitForEvent("page");
  await row().getByRole("button", { name: "WhatsApp", exact: true }).click();
  const popup = await popupPromise;
  await expect(
    page.getByRole("button", { name: "Отменить", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Отменить", exact: true }).click();
  await expect(row()).toBeVisible();
  await popup.close();
  const secondPopup = context.waitForEvent("page");
  await row().getByRole("button", { name: "WhatsApp", exact: true }).click();
  const whatsapp = await secondPopup;
  await expect.poll(() => whatsapp.url()).toContain("https://wa.me/");
  expect(decodeURIComponent(whatsapp.url())).toContain("приготовим для Айжан");
  await page.getByRole("tab", { name: /Ждём ответа/ }).click();
  await row().getByRole("button", { name: "Ответил(а)", exact: true }).click();
  await page.getByRole("tab", { name: /^Ответили/ }).click();
  await row().getByRole("button", { name: "Заказал(а)", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Создать заказ", exact: true })
    .click();
  await expect(
    page.getByRole("dialog").getByLabel("Получатель", { exact: true }),
  ).toHaveValue("Айжан");
  await expect(
    page
      .getByRole("dialog")
      .getByRole("combobox", { name: "Повод", exact: true }),
  ).toHaveValue("День рождения");
  await expect(
    page.getByRole("dialog").getByLabel("Телефон получателя", { exact: true }),
  ).toHaveValue("+996");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Закрыть", exact: true })
    .click();
  const product = await api(page, "products", {
    name: "Нежность",
    price: "3500.00",
  });
  const today = await page.evaluate(() =>
    new Date().toISOString().slice(0, 10),
  );
  const order = await api(page, "orders", {
    customer_id: clients[0].id,
    items: [{ product_id: product.id, quantity: 1 }],
    recipient_name: "Айжан",
    fulfillment: "pickup",
    delivery_date: today,
    window_start: "10:00",
    window_end: "12:00",
  });
  await row().getByRole("button", { name: "Заказал(а)", exact: true }).click();
  await page.getByRole("button", { name: /Заказ №1/ }).click();
  await page.getByRole("tab", { name: /^Заказали/ }).click();
  await expect(
    row().getByRole("button", { name: "Открыть заказ" }),
  ).toBeVisible();
  expect(
    (await api(page, "reminders/?state=ordered")).results[0].order_id,
  ).toBe(order.id);
  await page.getByRole("tab", { name: /^Написать/ }).click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-reminder-queue-desktop.png`,
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-reminder-queue-mobile.png`,
    fullPage: true,
  });
  await whatsapp.close();
  await context.unrouteAll({ behavior: "wait" });
});

test("настройки в двух вкладках сохраняют черновик при конфликте", async ({
  page,
  context,
}) => {
  await login(page);
  await scenarioSettings(page);
  const second = await context.newPage();
  await second.goto(page.url());
  await expect(
    second.getByLabel("Название сценария", { exact: true }),
  ).toHaveValue("День рождения");
  await page
    .getByLabel("Текст шага", { exact: true })
    .fill("Первый текст {имя}");
  await second
    .getByLabel("Текст шага", { exact: true })
    .fill("Черновик второй вкладки {имя}");
  await page.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Настройки напоминаний сохранены",
  );
  await second.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(second.getByRole("alert")).toContainText("другой вкладке");
  await expect(second.getByLabel("Текст шага", { exact: true })).toHaveValue(
    "Черновик второй вкладки {имя}",
  );
  await second
    .getByRole("button", { name: "Загрузить актуальные настройки" })
    .click();
  await expect(second.getByLabel("Текст шага", { exact: true })).toHaveValue(
    "Первый текст {имя}",
  );
  await second.close();
});

test("позже, пропустить и отключить согласие работают из очереди", async ({
  page,
}) => {
  await login(page);
  await seed(page);
  await goQueue(page);
  const alina = page.getByRole("article", {
    name: "Напоминание: Алина Садыкова",
    exact: true,
  });
  await alina.getByRole("button", { name: "Позже", exact: true }).click();
  await expect(alina).toHaveCount(0);
  const timur = page.getByRole("article", {
    name: "Напоминание: Тимур Осмонов",
    exact: true,
  });
  await timur.getByLabel("Действия: Тимур Осмонов").click();
  await timur.getByRole("button", { name: "Пропустить в этом году" }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Подтвердить" })
    .click();
  await expect(timur).toHaveCount(0);
  await page.getByRole("tab", { name: /Пропущено/ }).click();
  await expect(timur).toBeVisible();
  await timur.getByLabel("Действия: Тимур Осмонов").click();
  await timur.getByRole("button", { name: "Не напоминать клиенту" }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Подтвердить" })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Согласие на сообщения отключено",
  );
});

test("тихие часы блокируют отправку, менеджер просматривает сценарии без редактирования", async ({
  page,
}) => {
  await login(page);
  await seed(page, 1);
  const hour = await page.evaluate(() =>
    Number(
      new Intl.DateTimeFormat("en-GB", {
        timeZone: "Asia/Bishkek",
        hour: "2-digit",
        hourCycle: "h23",
      }).format(new Date()),
    ),
  );
  const config = await api(page, "reminder-scenarios");
  const start = (hour + 1) % 24;
  await api(
    page,
    "reminder-scenarios",
    { ...config, start_hour: start, end_hour: start + 1 },
    "PUT",
  );
  const staff = await api(page, "staff", {
    name: "Менеджер сценариев",
    username: account.username + "_manager",
    password: account.password,
    role: "manager",
    staff_phone: "+996700111222",
  });
  await goQueue(page);
  await expect(
    page.getByRole("button", { name: "WhatsApp", exact: true }),
  ).toBeDisabled();
  await expect(page.getByText(/Можно писать с/)).toBeVisible();
  await page.getByRole("button", { name: "Меню пользователя" }).click();
  await page.getByRole("menuitem", { name: "Выйти", exact: true }).click();
  await submitLogin(page, staff.username, account.password);
  await scenarioSettings(page);
  await expect(
    page.getByRole("button", { name: "Сохранить", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByLabel("Название сценария", { exact: true }),
  ).toBeDisabled();
  await page
    .getByLabel("Шаг для просмотра")
    .selectOption(config.scenarios[0].steps.at(-1).id);
  await expect(page.getByLabel("Текст шага", { exact: true })).toHaveValue(
    config.scenarios[0].steps.at(-1).template,
  );
});
