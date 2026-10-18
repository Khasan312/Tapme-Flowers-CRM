import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { submitLogin } from "./login";

let account: { username: string; password: string; business_id: string };
const python = resolve("../backend/.venv/bin/python"),
  fixture = resolve("../backend/tests/browser_fixture.py"),
  chats = resolve("../backend/tests/chat_browser_fixture.py");
function scenario(action: string, data: object = {}) {
  return JSON.parse(
    execFileSync(python, [chats, action], {
      input: JSON.stringify({ ...account, ...data }),
      encoding: "utf8",
    }),
  );
}
test.beforeEach(() => {
  account = JSON.parse(
    execFileSync(python, [fixture, "create"], { encoding: "utf8" }),
  );
});
test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "wait" });
  execFileSync(python, [fixture, "delete"], { input: JSON.stringify(account) });
});
async function login(page: Page) {
  await page.goto("/");
  await submitLogin(page, account.username, account.password);
  await expect(page.locator(".app-shell")).toBeVisible();
}

test("чаты по макету: история, ответы, статусы, карточка и телефон", async ({
  page,
}, info) => {
  const seeded = scenario("seed");
  await login(page);
  await page.getByRole("button", { name: "Чаты", exact: true }).click();
  await page.getByRole("button", { name: "Диалог: Алина Садыкова" }).click();
  await expect(page.getByRole("log")).toContainText("Сообщение 65");
  await expect(page.getByLabel("Клиент в переписке")).toContainText(
    "Без лилий",
  );
  await expect(page).toHaveURL(new RegExp("chat=" + seeded.chat_id));
  await page
    .getByLabel("Сообщение в WhatsApp")
    .fill("Да, добавим открытку. Какой текст написать?");
  await page
    .getByRole("button", { name: "Отправить сообщение", exact: true })
    .click();
  await expect(page.getByRole("log")).toContainText("Какой текст написать?");
  scenario("ack", seeded);
  await expect(
    page
      .locator(".chat-bubble")
      .filter({ hasText: "Какой текст написать?" })
      .getByLabel("Прочитано"),
  ).toBeVisible({ timeout: 15000 });
  scenario("inbound", { ...seeded, text: "Напишите: маме с любовью!" });
  await expect(page.getByRole("log")).toContainText("маме с любовью", {
    timeout: 15000,
  });
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-chats-desktop.png`,
    fullPage: true,
  });
  await page.getByRole("log").evaluate((el) => (el.scrollTop = 0));
  await page.getByRole("button", { name: "Предыдущие сообщения" }).click();
  await expect(page.getByRole("log")).toContainText("Сообщение 1.");
  await page.getByRole("log").evaluate((el) => (el.scrollTop = 0));
  scenario("inbound", { ...seeded, text: "Ещё один вопрос" });
  await expect(
    page.getByRole("button", { name: "Новые сообщения" }),
  ).toBeVisible({ timeout: 15000 });
  expect(
    await page.getByRole("log").evaluate((el) => el.scrollTop),
  ).toBeLessThan(60);
  await page.getByRole("button", { name: "Новые сообщения" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByLabel("Сообщение в WhatsApp")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Отправить сообщение", exact: true }),
  ).toBeInViewport();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-chats-mobile.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "Карточка рядом с чатом" }).click();
  await expect(page.getByLabel("Клиент в переписке")).toBeVisible();
  await page.getByRole("button", { name: "Скрыть карточку клиента" }).click();
  await page.getByRole("button", { name: "К списку диалогов" }).click();
  await expect(
    page.getByRole("button", { name: "Диалог: Мария Ким" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Диалог: Мария Ким" }).click();
  await expect(page.locator(".chat-reply-reason")).toContainText("24 часа");
  await expect(
    page.getByRole("button", { name: "Отправить сообщение", exact: true }),
  ).toBeDisabled();
});

test("потерянный ответ не дублирует отправку, черновик сохраняется после обновления", async ({
  page,
}) => {
  const seeded = scenario("seed");
  await login(page);
  await page.goto(
    `/?view=chats&business=${account.business_id}&chat=${seeded.chat_id}`,
  );
  await expect(page.getByRole("log")).toContainText("Сообщение 65");
  const input = page.getByLabel("Сообщение в WhatsApp");
  await input.fill("Черновик сохранён");
  await page.reload();
  await expect(input).toHaveValue("Черновик сохранён");
  await page.route(
    "**/chats/*/messages/",
    async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      await route.fetch();
      await route.abort();
    },
    { times: 1 },
  );
  await page
    .getByRole("button", { name: "Отправить сообщение", exact: true })
    .click();
  await expect(input).toHaveValue("Черновик сохранён");
  await expect(
    page.getByText("Не удалось связаться с сервером.", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Отправить сообщение", exact: true })
    .click();
  await expect(input).toHaveValue("");
  expect(scenario("ack", seeded).count).toBe(1);
  await input.fill("Текст другой карточки");
  await page.getByRole("button", { name: "Диалог: Мария Ким" }).click();
  await expect(input).toHaveValue("");
  await page.goBack();
  await expect(input).toHaveValue("Текст другой карточки");
  await page
    .getByRole("button", { name: "Закрыть диалог", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Открыть диалог", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Открыть диалог", exact: true })
    .click();
  await page.getByLabel("Ответственный за диалог").selectOption({ index: 1 });
  await page.reload();
  await expect(page.getByLabel("Ответственный за диалог")).not.toHaveValue("");
});

test("без подключения показано честное состояние и настройка канала", async ({
  page,
}) => {
  await login(page);
  await page.getByRole("button", { name: "Чаты", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Ваш WhatsApp — в CRM" }),
  ).toBeVisible();
  await expect(page.locator(".chat-row")).toHaveCount(0);
  await page.getByRole("button", { name: "Настроить подключение" }).click();
  await expect(
    page.getByRole("heading", { name: "WhatsApp · номер для заказов" }),
  ).toBeVisible();
  await expect(page.getByText("Не подключён", { exact: true })).toBeVisible();
  await expect(page.getByText("Тестовый режим", { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/tab=channels/);
});

test("фото отправляется только после подтверждения, шаблон вставляется в черновик", async ({
  page,
}) => {
  const seeded = scenario("seed");
  await login(page);
  await page.goto(
    `/?view=chats&business=${account.business_id}&chat=${seeded.chat_id}`,
  );
  await expect(page.getByRole("log")).toContainText("Сообщение 65");
  await page.getByRole("button", { name: "Шаблоны", exact: true }).click();
  await page.getByRole("button", { name: "Приветствие", exact: true }).click();
  await expect(page.getByLabel("Сообщение в WhatsApp")).toHaveValue(
    /Алина Садыкова, здравствуйте/,
  );
  await page.getByLabel("Сообщение в WhatsApp").fill("Вот фотография букета");
  const png = execFileSync(python, [
    "-c",
    "from PIL import Image; import sys; Image.new('RGB',(24,24),'purple').save(sys.stdout.buffer,format='PNG')",
  ]);
  await page
    .getByLabel("Вложение в чат")
    .setInputFiles({ name: "bouquet.png", mimeType: "image/png", buffer: png });
  await expect(page.locator(".chat-file-selected")).toContainText(
    "bouquet.png",
  );
  await expect(
    page.getByRole("log").getByText("Вот фотография букета", { exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Отправить сообщение", exact: true })
    .click();
  const image = page.getByRole("img", { name: "Фото из переписки" });
  await expect(image).toBeVisible();
  expect(
    await image.evaluate((el) => (el as HTMLImageElement).naturalWidth),
  ).toBeGreaterThan(0);
  await expect(page.getByLabel("Сообщение в WhatsApp")).toHaveValue("");
});
