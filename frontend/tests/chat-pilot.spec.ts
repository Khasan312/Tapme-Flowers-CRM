import { test, expect } from "@playwright/test";
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
  execFileSync(python, [fixture, "delete"], { input: JSON.stringify(account) });
});
for (const mobile of [false, true])
  test(`пилот WhatsApp: подключение, автоответ, QR и быстрые ответы ${mobile ? "390" : "1440"}`, async ({
    page,
  }, info) => {
    test.setTimeout(120000);
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/login");
    await submitLogin(page, account.username, account.password);
    await page.goto(
      `/?view=settings&tab=channels&business=${account.business_id}`,
    );
    // Navigation uses the existing settings route convention.
    await page.getByRole("tab", { name: "Каналы", exact: true }).click();
    await expect(
      page.getByText("Тестовый режим", { exact: true }),
    ).toBeVisible();
    await page.getByLabel(/^Phone Number ID/).fill(String(Date.now()));
    await page.getByLabel(/^WhatsApp Business Account ID/).fill("123456789");
    await page
      .getByLabel("Access token", { exact: true })
      .fill("fake-test-token");
    await page.getByLabel(/^App Secret/).fill("fake-test-secret");
    await page
      .getByRole("button", { name: "Проверить и подключить", exact: true })
      .click();
    await expect(
      page.getByText("Завершите подключение", { exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Подписать на сообщения", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Проверить тестовый вебхук", exact: true })
      .click();
    await expect(page.getByLabel("Access token", { exact: true })).toHaveValue(
      "",
    );
    await page.locator(".chat-upload input[type=file]").setInputFiles({
      name: "qr.png",
      mimeType: "image/png",
      buffer: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=",
        "base64",
      ),
    });
    await page.getByLabel("Подпись для сотрудников").fill("Тестовый QR");
    await page.getByRole("button", { name: "Сохранить QR и подпись" }).click();
    await expect(page.getByAltText("QR для оплаты магазина")).toBeVisible();
    await page
      .getByLabel("Имя клиента", { exact: true })
      .fill("Новый клиент из WhatsApp");
    const observer = await page.context().newPage();
    const firstSummary = observer.waitForResponse((r) =>
      r.url().includes("/chats/summary/"),
    );
    await observer.goto(`/?view=orders&business=${account.business_id}`);
    await expect(observer.locator(".app-shell")).toBeVisible();
    await firstSummary;
    await page.bringToFront();
    await page
      .getByLabel("Входящее сообщение")
      .fill("Нужен букет по новому макету");
    await page
      .getByRole("button", { name: "Создать входящее", exact: true })
      .click();
    await expect(observer.locator(".chat-toast")).toContainText(
      "Новый клиент из WhatsApp",
      { timeout: 25000 },
    );
    await expect(observer).toHaveTitle(/^\(1\)/);
    await observer.close();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: `/tmp/tapme-${info.project.name}-pilot-channels-${mobile ? 390 : 1440}.png`,
      fullPage: true,
    });
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(mobile ? 390 : 1440);
    await page.getByRole("button", { name: "Чаты", exact: true }).click();
    await page
      .getByRole("button", {
        name: "Диалог: Новый клиент из WhatsApp",
        exact: true,
      })
      .click({ timeout: 20000 });
    await expect(page.getByRole("log")).toContainText(
      "Нужен букет по новому макету",
    );
    await expect(page.getByRole("log")).toContainText("Автоответ", {
      timeout: 20000,
    });
    if (mobile)
      await page
        .getByRole("button", { name: "Карточка рядом с чатом" })
        .click();
    await page.getByLabel("Имя клиента из чата").fill("Айдана Тестовая");
    await page
      .getByRole("button", { name: "Сохранить имя", exact: true })
      .click();
    await expect(page.locator(".chat-dialog-heading")).toContainText(
      "Айдана Тестовая",
    );
    if (mobile)
      await page
        .getByRole("button", { name: "Скрыть карточку клиента" })
        .click();
    await page
      .getByRole("button", { name: "Быстрые ответы", exact: true })
      .click();
    await page.getByRole("button", { name: "Новый быстрый ответ" }).click();
    await page.getByLabel("Название ответа").fill("Наличие");
    await page
      .getByLabel("Текст ответа")
      .fill("{имя}, пионы есть в наличии 🌸");
    await page
      .getByRole("button", { name: "Сохранить ответ", exact: true })
      .click();
    await page
      .locator(".chat-quick-insert")
      .filter({ hasText: "Наличие" })
      .click();
    await expect(page.getByLabel("Сообщение в WhatsApp")).toHaveValue(
      "Айдана Тестовая, пионы есть в наличии 🌸",
    );
    await page.getByLabel("Сообщение в WhatsApp").press("Shift+Enter");
    await expect(page.getByLabel("Сообщение в WhatsApp")).toHaveValue(
      "Айдана Тестовая, пионы есть в наличии 🌸\n",
    );
    await page.getByLabel("Сообщение в WhatsApp").press("Enter");
    const bubble = page
      .locator(".chat-bubble")
      .filter({ hasText: "пионы есть в наличии" });
    await expect(bubble).toBeVisible();
    await expect(bubble.getByLabel("Прочитано")).toBeVisible({
      timeout: 35000,
    });
    await page
      .getByRole("button", { name: "Отправить QR", exact: true })
      .click();
    await page.getByLabel("Сумма к оплате, сом").fill("4800");
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Отправить QR", exact: true })
      .click();
    await expect(page.getByRole("log")).toContainText("4800");
    await expect(
      page.getByRole("log").getByAltText("Фото из переписки"),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Отправить сообщение", exact: true }),
    ).toBeInViewport();
    await page.screenshot({
      path: `/tmp/tapme-${info.project.name}-pilot-chat-${mobile ? 390 : 1440}.png`,
      fullPage: true,
    });
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(mobile ? 390 : 1440);
    if (mobile) {
      await page.getByRole("button", { name: "К списку диалогов" }).click();
      await expect(
        page.getByRole("button", {
          name: "Диалог: Айдана Тестовая",
          exact: true,
        }),
      ).toBeVisible();
    }
  });
