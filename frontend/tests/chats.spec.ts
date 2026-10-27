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

test("каналы чатов: меню, история адресов и сохранение черновика", async ({
  page,
}, info) => {
  const seeded = scenario("seed");
  await login(page);
  const sidebar = page.locator(".chat-channel-picker.is-sidebar");
  const whatsapp = sidebar.getByRole("button", {
    name: "WhatsApp",
    exact: true,
  });
  const instagram = sidebar.getByRole("button", {
    name: "Instagram",
    exact: true,
  });
  await expect(whatsapp.locator(".chat-channel-count")).toBeVisible();
  await expect(instagram.locator(".chat-channel-count")).toHaveCount(0);
  await whatsapp.click();
  await page.getByRole("button", { name: "Диалог: Алина Садыкова" }).click();
  const input = page.getByLabel("Сообщение в WhatsApp");
  await input.fill("Вернусь к этому ответу после Instagram");
  await instagram.click();
  await expect(page).toHaveURL(/channel=instagram/);
  await expect(page).not.toHaveURL(/chat=/);
  await expect(
    page.getByRole("heading", { name: "Ваш Instagram — рядом" }),
  ).toBeVisible();
  await expect(instagram).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("button", { name: "Настройки", exact: true }),
  ).toBeInViewport();
  expect((await sidebar.boundingBox())!.height).toBeLessThan(130);
  await expect(page.getByRole("log")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Отправить сообщение", exact: true }),
  ).toHaveCount(0);
  // A hidden WhatsApp pane must not keep polling and marking messages read.
  let markedRead = 0;
  page.on("request", (request) => {
    if (request.url().includes(`/chats/${seeded.chat_id}/read/`)) markedRead++;
  });
  await page.waitForTimeout(3500);
  expect(markedRead).toBe(0);
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-instagram-channels-desktop.png`,
    fullPage: true,
  });
  await page.goBack();
  await expect(input).toHaveValue("Вернусь к этому ответу после Instagram");
  await page.goForward();
  await expect(instagram).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Ваш Instagram — рядом" }),
  ).toBeVisible();
  await whatsapp.click();
  await expect(page).toHaveURL(new RegExp(`chat=${seeded.chat_id}`));
  await expect(input).toHaveValue("Вернусь к этому ответу после Instagram");
  await instagram.click();
  await page.getByRole("button", { name: "Заказы", exact: true }).click();
  await page.getByRole("button", { name: "Чаты", exact: true }).click();
  await expect(page).toHaveURL(/channel=instagram/);
  await whatsapp.click();
  await expect(input).toHaveValue("Вернусь к этому ответу после Instagram");
});

test("каналы чатов: мобильные вкладки доступны внутри диалога", async ({
  page,
}, info) => {
  scenario("seed");
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await page.getByRole("button", { name: "Чаты", exact: true }).click();
  const tabs = page.locator(".chat-channel-picker.is-mobile");
  await expect(page.locator(".chat-channel-picker.is-sidebar")).toBeHidden();
  await expect(tabs).toBeVisible();
  await page.getByRole("button", { name: "Диалог: Алина Садыкова" }).click();
  await page.getByLabel("Сообщение в WhatsApp").fill("Мобильный черновик");
  await tabs.getByRole("button", { name: "Instagram", exact: true }).click();
  await page.getByText("Что нужно для подключения?", { exact: true }).click();
  await expect(
    page.getByText("Профессиональный аккаунт магазина", { exact: false }),
  ).toBeVisible();
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-instagram-channels-mobile.png`,
    fullPage: true,
  });
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await expect(
      tabs.getByRole("button", { name: "WhatsApp", exact: true }),
    ).toBeVisible();
  }
  await tabs.getByRole("button", { name: "WhatsApp", exact: true }).click();
  await expect(page.getByLabel("Сообщение в WhatsApp")).toHaveValue(
    "Мобильный черновик",
  );
  await expect(page.getByRole("log")).toContainText("Сообщение 65");
  await expect(tabs).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(320);
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-whatsapp-channels-mobile.png`,
    fullPage: true,
  });
});

test("каналы чатов: старые ссылки и несовместимый идентификатор диалога", async ({
  page,
}) => {
  const seeded = scenario("seed");
  await login(page);
  const url = `/?view=chats&business=${account.business_id}&chat=${seeded.chat_id}`;
  await page.goto(url);
  await expect(page.getByRole("log")).toContainText("Сообщение 65");
  await expect(
    page
      .locator(".chat-channel-picker.is-sidebar")
      .getByRole("button", { name: "WhatsApp", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.goto(url + "&channel=instagram");
  await expect(page).not.toHaveURL(/chat=/);
  await expect(page.getByRole("log")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Ваш Instagram — рядом" }),
  ).toBeVisible();
  await page.goto(url + "&channel=unknown");
  await expect(page).not.toHaveURL(/channel=unknown/);
  await expect(page.getByRole("log")).toContainText("Сообщение 65");
});

test("смайлики: курсор, замена выделения, черновик и отправка Unicode", async ({
  page,
}, info) => {
  const seeded = scenario("seed");
  await login(page);
  await page.goto(
    `/?view=chats&business=${account.business_id}&chat=${seeded.chat_id}`,
  );
  await expect(page.getByRole("log")).toContainText("Сообщение 65");
  const input = page.getByLabel("Сообщение в WhatsApp");
  const toggle = page.getByRole("button", { name: "Добавить смайлик" });
  const picker = page.getByRole("dialog", { name: "Выбор смайлика" });
  let sent = 0;
  page.on("request", (request) => {
    if (
      request.method() === "POST" &&
      request.url().endsWith(`/chats/${seeded.chat_id}/messages/`)
    )
      sent++;
  });
  await input.fill("Спасибо за заказ");
  await input.evaluate((node: HTMLTextAreaElement) =>
    node.setSelectionRange(7, 7),
  );
  await toggle.click();
  await picker.getByRole("button", { name: "Цветы", exact: true }).click();
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-emoji-desktop.png`,
    fullPage: true,
    animations: "disabled",
  });
  await picker.getByRole("button", { name: "Букет", exact: true }).click();
  await expect(input).toHaveValue("Спасибо💐 за заказ");
  await expect(input).toBeFocused();
  expect(
    await input.evaluate((node: HTMLTextAreaElement) => node.selectionStart),
  ).toBe(9);
  await input.fill("Для мамы");
  await input.evaluate((node: HTMLTextAreaElement) =>
    node.setSelectionRange(4, 8),
  );
  await toggle.focus();
  await toggle.press("Enter");
  await picker.getByRole("button", { name: "Цветы", exact: true }).click();
  await picker.getByRole("button", { name: "Букет", exact: true }).click();
  await expect(input).toHaveValue("Для 💐");
  await input.press("End");
  await input.pressSequentially(" с любовью");
  await toggle.click();
  await picker.getByRole("button", { name: "Сердца", exact: true }).click();
  await picker
    .getByRole("button", { name: "Красное сердце", exact: true })
    .click();
  const message = "Для 💐 с любовью❤️";
  await expect(input).toHaveValue(message);
  expect(sent).toBe(0);
  await page.reload();
  await expect(input).toHaveValue(message);
  await page
    .getByRole("button", { name: "Отправить сообщение", exact: true })
    .click();
  await expect(input).toHaveValue("");
  await expect(page.getByRole("log")).toContainText(message);
  expect(sent).toBe(1);
  await page.reload();
  await expect(page.getByRole("log")).toContainText(message);
});

test("смайлики: мобильная панель, закрытие и лимиты текста и подписи", async ({
  page,
}, info) => {
  const seeded = scenario("seed");
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await page.goto(
    `/?view=chats&business=${account.business_id}&chat=${seeded.chat_id}`,
  );
  await expect(page.getByRole("log")).toContainText("Сообщение 65");
  const input = page.getByLabel("Сообщение в WhatsApp");
  const toggle = page.getByRole("button", { name: "Добавить смайлик" });
  const picker = page.getByRole("dialog", { name: "Выбор смайлика" });
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await input.fill("Хорошего дня ");
    await toggle.click();
    await expect(picker).toBeVisible();
    const bounds = (await picker.boundingBox())!;
    expect(bounds.x).toBeGreaterThanOrEqual(0);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
    expect(bounds.y).toBeGreaterThanOrEqual(0);
    expect(bounds.y + bounds.height).toBeLessThanOrEqual(844);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await page.screenshot({
      path: `/tmp/tapme-${info.project.name}-emoji-${width}.png`,
      fullPage: true,
      animations: "disabled",
    });
    await picker.getByRole("button", { name: "Улыбка", exact: true }).click();
    await expect(input).toHaveValue("Хорошего дня 😊");
    await expect(input).toBeFocused();
  }
  await toggle.click();
  await page.keyboard.press("Escape");
  await expect(picker).toBeHidden();
  await expect(toggle).toBeFocused();
  await toggle.click();
  await input.click();
  await expect(picker).toBeHidden();
  for (const limit of [4096, 1024]) {
    if (limit === 1024)
      await page.getByLabel("Вложение в чат").setInputFiles({
        name: "test.pdf",
        mimeType: "application/pdf",
        buffer: Buffer.from("%PDF-1.4\n%%EOF"),
      });
    await input.fill("а".repeat(limit - 1));
    await toggle.click();
    await picker.getByRole("button", { name: "Улыбка", exact: true }).click();
    await expect(picker.getByRole("status")).toContainText("Достигнут лимит");
    await expect(input).toHaveValue("а".repeat(limit - 1));
    await picker.getByRole("button", { name: "Закрыть смайлики" }).click();
    await input.evaluate((node: HTMLTextAreaElement) =>
      node.setSelectionRange(0, 1),
    );
    await toggle.click();
    await picker.getByRole("button", { name: "Улыбка", exact: true }).click();
    await expect(input).toHaveValue("😊" + "а".repeat(limit - 2));
  }
  await toggle.click();
  await page
    .locator(".chat-channel-picker.is-mobile")
    .getByRole("button", { name: "Instagram", exact: true })
    .click();
  await expect(picker).toBeHidden();
  await expect(
    page.getByRole("button", { name: "Добавить смайлик" }),
  ).toHaveCount(0);
});

test("меню сообщений: ответ с цитатой, потеря ответа сервера и вложение", async ({
  page,
}, info) => {
  const seeded = scenario("seed");
  await login(page);
  await page.goto(
    `/?view=chats&business=${account.business_id}&chat=${seeded.chat_id}`,
  );
  await expect(page.getByRole("log")).toContainText("Сообщение 65");
  const source = page
    .locator(".chat-bubble")
    .filter({ hasText: "Сообщение 64." });
  const sourceId = await source.getAttribute("data-message-id");
  const menu = page.getByRole("menu", { name: "Действия с сообщением" });
  const preview = page.getByRole("region", {
    name: "Ответ на сообщение",
    exact: true,
  });
  const input = page.getByLabel("Сообщение в WhatsApp");
  await input.fill("Уточним адрес 💐");
  await source.click({ button: "right" });
  await menu.getByRole("menuitem", { name: "Ответить", exact: true }).click();
  await expect(preview).toContainText("Сообщение 64.");
  await expect(input).toHaveValue("Уточним адрес 💐");
  await expect(input).toBeFocused();
  await page.reload();
  await expect(preview).toContainText("Сообщение 64.");
  await expect(input).toHaveValue("Уточним адрес 💐");
  await page.route(
    `**/chats/${seeded.chat_id}/messages/`,
    async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      expect(route.request().postDataJSON().reply_to_id).toBe(sourceId);
      await route.fetch();
      await route.abort();
    },
    { times: 1 },
  );
  const send = page.getByRole("button", {
    name: "Отправить сообщение",
    exact: true,
  });
  await send.click();
  await expect(
    page.getByText("Не удалось связаться с сервером.", { exact: false }),
  ).toBeVisible();
  await expect(preview).toBeVisible();
  await send.click();
  await expect(input).toHaveValue("");
  await expect(preview).toBeHidden();
  await page.reload();
  const reply = page
    .locator(".chat-bubble")
    .filter({ hasText: "Уточним адрес 💐" });
  await expect(reply).toHaveCount(1);
  await expect(reply.locator(".chat-quote")).toContainText("Сообщение 64.");
  await page
    .locator(`[data-message-id="${sourceId}"]`)
    .click({ button: "right" });
  await menu.getByRole("menuitem", { name: "Ответить", exact: true }).click();
  await input.fill("Состав букета");
  await page.getByLabel("Вложение в чат").setInputFiles({
    name: "bouquet.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n%%EOF"),
  });
  await send.click();
  await expect(preview).toBeHidden();
  const attachment = page
    .locator(".chat-bubble")
    .filter({ hasText: "Состав букета" });
  await expect(attachment.locator(".chat-quote")).toContainText(
    "Сообщение 64.",
  );
  await expect(
    attachment.getByRole("link", { name: "bouquet.pdf" }),
  ).toBeVisible();
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-message-reply.png`,
    fullPage: true,
    animations: "disabled",
  });
});

test("меню сообщений: копирование, множественный выбор и порядок", async ({
  page,
}, info) => {
  scenario("seed");
  await page.addInitScript(() => {
    const state = window as unknown as { copied: string[] };
    state.copied = [];
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: async (text: string) => {
          state.copied.push(text);
        },
      },
    });
  });
  await login(page);
  await page.getByRole("button", { name: "Чаты", exact: true }).click();
  await page.getByRole("button", { name: "Диалог: Алина Садыкова" }).click();
  await expect(page.getByRole("log")).toContainText("Сообщение 65");
  const message = (n: number) =>
    page.locator(".chat-bubble").filter({ hasText: `Сообщение ${n}.` });
  const menu = page.getByRole("menu", { name: "Действия с сообщением" });
  await message(64).focus();
  await message(64).press("Shift+F10");
  await expect(
    menu.getByRole("menuitem", { name: "Ответить", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(message(64)).toBeFocused();
  await message(64).click({ button: "right" });
  await menu
    .getByRole("menuitem", { name: "Скопировать", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Сообщение скопировано");
  expect(
    await page.evaluate(() =>
      (window as unknown as { copied: string[] }).copied.at(-1),
    ),
  ).toBe("Сообщение 64. Здравствуйте! Нужен букет из пионов для мамы.");
  await message(64).click({ button: "right" });
  await menu.getByRole("menuitem", { name: "Выбрать", exact: true }).click();
  await message(62).click();
  const selection = page.getByRole("region", { name: "Выбранные сообщения" });
  await expect(selection).toContainText("Выбрано: 2");
  await selection
    .getByRole("button", { name: "Скопировать выбранные" })
    .click();
  const copied = await page.evaluate(() =>
    (window as unknown as { copied: string[] }).copied.at(-1)!,
  );
  expect(copied).toContain("Алина Садыкова:");
  expect(copied).toContain("Сотрудник:");
  expect(copied.indexOf("Сообщение 62.")).toBeLessThan(
    copied.indexOf("Сообщение 64."),
  );
  await message(64).getByRole("checkbox").uncheck();
  await expect(selection).toContainText("Выбрано: 1");
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-message-selection.png`,
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("button", { name: "Диалог: Мария Ким" }).click();
  await expect(selection).toBeHidden();
  await page.getByRole("button", { name: "Диалог: Алина Садыкова" }).click();
  await expect(selection).toBeHidden();
});

test("меню сообщений: удержание, прокрутка и копирование без Clipboard API", async ({
  page,
}, info) => {
  scenario("seed");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: undefined,
    });
    document.addEventListener("copy", (event) => {
      const text = (document.activeElement as HTMLTextAreaElement)?.value || "";
      (window as unknown as { copied: string }).copied = text;
      event.clipboardData?.setData("text/plain", text);
      event.preventDefault();
    });
  });
  await login(page);
  await page.getByRole("button", { name: "Чаты", exact: true }).click();
  await page.getByRole("button", { name: "Диалог: Алина Садыкова" }).click();
  await expect(page.getByRole("log")).toContainText("Сообщение 65");
  const source = page
    .locator(".chat-bubble")
    .filter({ hasText: "Сообщение 64." });
  const menu = page.getByRole("menu", { name: "Действия с сообщением" });
  const touch = {
    pointerId: 7,
    pointerType: "touch",
    isPrimary: true,
    clientX: 388,
    clientY: 830,
  };
  await source.dispatchEvent("pointerdown", touch);
  await source.dispatchEvent("pointermove", { ...touch, clientY: 795 });
  await page.waitForTimeout(600);
  await expect(menu).toBeHidden();
  await source.dispatchEvent("pointercancel", touch);
  await source.dispatchEvent("pointerdown", touch);
  await expect(menu).toBeVisible();
  await source.dispatchEvent("pointerup", touch);
  await source.dispatchEvent("click");
  await expect(menu).toBeVisible();
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-message-menu-mobile.png`,
    fullPage: true,
    animations: "disabled",
  });
  const box = (await menu.boundingBox())!;
  expect(box.x + box.width).toBeLessThanOrEqual(390);
  expect(box.y + box.height).toBeLessThanOrEqual(844);
  await menu
    .getByRole("menuitem", { name: "Скопировать", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Сообщение скопировано");
  expect(
    await page.evaluate(() => (window as unknown as { copied: string }).copied),
  ).toContain("Сообщение 64.");
  await source.click({ button: "right" });
  await menu.getByRole("menuitem", { name: "Выбрать", exact: true }).click();
  await page.setViewportSize({ width: 320, height: 844 });
  const selection = page.getByRole("region", { name: "Выбранные сообщения" });
  await expect(selection).toContainText("Выбрано: 1");
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(320);
  await page.evaluate(() => {
    document.execCommand = () => false;
  });
  await selection
    .getByRole("button", { name: "Скопировать выбранные" })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Не удалось скопировать",
  );
  await expect(selection).toContainText("Выбрано: 1");
  await page.getByRole("button", { name: "Отменить выбор сообщений" }).click();
  await expect(selection).toBeHidden();
});

test("меню чата: правый клик, клавиатура, назначение и архив", async ({
  page,
}, info) => {
  scenario("seed");
  await login(page);
  await page.getByRole("button", { name: "Чаты", exact: true }).click();
  const row = page.getByRole("button", { name: "Диалог: Алина Садыкова" });
  const menu = page.getByRole("menu", {
    name: "Действия с чатом: Алина Садыкова",
  });
  await row.click({ button: "right" });
  await expect(menu).toBeVisible();
  await expect(page).not.toHaveURL(/chat=/);
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-chat-menu.png`,
  });
  await page.keyboard.press("Escape");
  await expect(menu).toBeHidden();
  await expect(row).toBeFocused();
  await row.press("Shift+F10");
  await expect(
    menu.getByRole("menuitem", { name: "Открыть чат" }),
  ).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(
    menu.getByRole("menuitem", { name: "Взять себе" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(menu).toBeHidden();
  await page.getByRole("tab", { name: /^Мои/ }).click();
  await expect(row).toBeVisible();
  await row.click();
  await expect(page.getByLabel("Ответственный за диалог")).not.toContainText(
    "Не назначен",
  );
  await row.click({ button: "right" });
  await menu.getByRole("menuitem", { name: "Снять с себя" }).click();
  await expect(row).toBeHidden();
  await expect(page.getByLabel("Ответственный за диалог")).toContainText(
    "Не назначен",
  );
  await page.getByRole("tab", { name: /^Все/ }).click();
  await row.click({ button: "right" });
  await menu.getByRole("menuitem", { name: "В архив", exact: true }).click();
  await expect(menu).toBeHidden();
  await expect(
    page.getByRole("button", { name: "Открыть диалог", exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: /^Архив/ }).click();
  await row.click({ button: "right" });
  await menu.getByRole("menuitem", { name: "Вернуть из архива" }).click();
  await expect(row).toBeHidden();
  await expect(
    page.getByRole("button", { name: "Закрыть диалог", exact: true }),
  ).toBeVisible();
});

test("меню чата: удержание на телефоне не мешает касанию и прокрутке", async ({
  page,
}, info) => {
  scenario("seed");
  await page.setViewportSize({ width: 390, height: 660 });
  await login(page);
  await page.getByRole("button", { name: "Чаты", exact: true }).click();
  const row = page.getByRole("button", { name: "Диалог: Алина Садыкова" });
  const menu = page.getByRole("menu");
  const touch = {
    pointerId: 7,
    pointerType: "touch",
    isPrimary: true,
    clientX: 300,
    clientY: 260,
  };
  await row.dispatchEvent("pointerdown", touch);
  await row.dispatchEvent("pointermove", { ...touch, clientY: 235 });
  await page.waitForTimeout(650);
  await expect(menu).toBeHidden();
  await row.dispatchEvent("pointercancel", touch);
  await row.dispatchEvent("pointerdown", touch);
  await row.dispatchEvent("pointercancel", touch);
  await page.waitForTimeout(650);
  await expect(menu).toBeHidden();
  await row.click();
  await expect(page.getByRole("log")).toBeVisible();
  await page.getByRole("button", { name: "К списку диалогов" }).click();
  // Deliberately use the viewport edge to exercise the menu's bounds.
  await row.dispatchEvent("pointerdown", {
    ...touch,
    clientX: 388,
    clientY: 650,
  });
  await expect(menu).toBeVisible();
  await row.dispatchEvent("pointerup", touch);
  await row.dispatchEvent("click");
  await expect(page).not.toHaveURL(/chat=/);
  await expect(menu).toBeVisible();
  const bounds = await menu.boundingBox();
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(390);
  expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(660);
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-chat-menu-mobile.png`,
  });
  await page.getByRole("menuitem", { name: "Открыть чат" }).click();
  await expect(page.getByRole("log")).toBeVisible();
});

test("меню чата: ошибка оставляет возможность повторить действие", async ({
  page,
}) => {
  const seeded = scenario("seed");
  await login(page);
  await page.getByRole("button", { name: "Чаты", exact: true }).click();
  const row = page.getByRole("button", { name: "Диалог: Алина Садыкова" });
  await row.click({ button: "right" });
  await page.route(
    `**/chats/${seeded.chat_id}/`,
    async (route) => {
      if (route.request().method() !== "PATCH") return route.continue();
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: "{}",
      });
    },
    { times: 1 },
  );
  const menu = page.getByRole("menu");
  await menu.getByRole("menuitem", { name: "В архив", exact: true }).click();
  await expect(menu.getByRole("alert")).toContainText(
    "Сервер не смог выполнить запрос",
  );
  await expect(
    menu.getByRole("menuitem", { name: "В архив", exact: true }),
  ).toBeEnabled();
  await menu.getByRole("menuitem", { name: "В архив", exact: true }).click();
  await expect(menu).toBeHidden();
  await page.getByRole("tab", { name: /^Архив/ }).click();
  await expect(row).toBeVisible();
  await row.click({ button: "right" });
  await page.getByLabel("Поиск диалогов").click();
  await expect(menu).toBeHidden();
});

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
  const scrollDown = page.getByRole("button", {
    name: "К последним сообщениям",
  });
  await expect(scrollDown).toBeInViewport();
  await scrollDown.click();
  await expect(scrollDown).toBeHidden();
  expect(
    await page
      .getByRole("log")
      .evaluate((el) => el.scrollHeight - el.scrollTop - el.clientHeight),
  ).toBeLessThan(2);
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
  await expect(page.locator(".chat-new-messages")).toBeHidden();
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
  await page.getByRole("log").evaluate((el) => (el.scrollTop = 0));
  await expect(scrollDown).toBeInViewport();
  await page.getByLabel("Сообщение в WhatsApp").fill("Строка\n".repeat(6));
  const jumpBox = (await scrollDown.boundingBox())!;
  const composerBox = (await page.locator(".chat-composer").boundingBox())!;
  expect(jumpBox.y + jumpBox.height).toBeLessThan(composerBox.y);
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-scroll-down-mobile.png`,
    animations: "disabled",
    fullPage: true,
  });
  await scrollDown.click();
  await expect(scrollDown).toBeHidden();
  expect(
    await page
      .getByRole("log")
      .evaluate((el) => el.scrollHeight - el.scrollTop - el.clientHeight),
  ).toBeLessThan(2);
  await page.getByRole("button", { name: "Карточка рядом с чатом" }).click();
  await expect(page.getByLabel("Клиент в переписке")).toBeVisible();
  await page.getByRole("button", { name: "Скрыть карточку клиента" }).click();
  await page.getByRole("button", { name: "К списку диалогов" }).click();
  await expect(
    page.getByRole("button", { name: "Диалог: Мария Ким" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Диалог: Мария Ким" }).click();
  await expect(page.locator(".chat-new-messages")).toBeHidden();
  await expect(page.locator(".chat-reply-reason")).toContainText("24 часа");
  await expect(
    page.getByRole("button", { name: "Отправить сообщение", exact: true }),
  ).toBeDisabled();
});

test("Enter сохраняет курсор при отправке и сетевой ошибке", async ({
  page,
}) => {
  const seeded = scenario("seed");
  await login(page);
  await page.goto(
    `/?view=chats&business=${account.business_id}&chat=${seeded.chat_id}`,
  );
  await expect(page.getByRole("log")).toContainText("Сообщение 65");
  const input = page.getByLabel("Сообщение в WhatsApp");
  let release = () => {};
  let gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let fail = false;
  let sends = 0;
  await page.route("**/chats/*/messages/", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    sends++;
    await gate;
    if (fail) return route.abort();
    return route.continue();
  });
  await input.fill("Первое сообщение");
  try {
    await page.keyboard.press("Enter");
    await expect.poll(() => sends).toBe(1);
    await expect(input).toBeFocused();
    await expect(input).not.toBeEditable();
    await page.keyboard.type("Не должно попасть в отправляемый текст");
    await page.keyboard.press("Enter");
    await expect(input).toHaveValue("Первое сообщение");
    expect(sends).toBe(1);
  } finally {
    release();
  }
  await expect(input).toHaveValue("");
  await expect(input).toBeFocused();
  await expect(input).toBeEditable();
  // Use the keyboard without focusing the textarea again.
  await page.keyboard.type("Второе сообщение");
  await page.keyboard.press("Shift+Enter");
  await page.keyboard.type("с новой строкой");
  await expect(input).toHaveValue("Второе сообщение\nс новой строкой");
  expect(sends).toBe(1);
  fail = true;
  await page.keyboard.press("Enter");
  await expect(
    page.getByText("Не удалось связаться с сервером.", { exact: false }),
  ).toBeVisible();
  await expect(input).toHaveValue("Второе сообщение\nс новой строкой");
  await expect(input).toBeFocused();
  await expect(input).toBeEditable();
  fail = false;
  await page.keyboard.press("Enter");
  await expect(input).toHaveValue("");
  await expect(input).toBeFocused();

  // Finishing a request must not steal focus if the user moved elsewhere.
  gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.keyboard.type("Третье сообщение");
  const search = page.locator(".chat-search input");
  try {
    await page.keyboard.press("Enter");
    await expect.poll(() => sends).toBe(4);
    await search.click();
    await expect(search).toBeFocused();
  } finally {
    release();
  }
  await expect(input).toHaveValue("");
  await expect(search).toBeFocused();
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
  await page.getByLabel("Ответственный за диалог").press("ArrowDown");
  const assignees = page.getByRole("listbox", {
    name: "Назначить ответственного",
  });
  await expect(assignees).toBeFocused();
  await assignees.press("End");
  await assignees.press("Enter");
  await page.reload();
  await expect(page.getByLabel("Ответственный за диалог")).not.toContainText(
    "Не назначен",
  );
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
