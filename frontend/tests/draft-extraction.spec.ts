import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { submitLogin } from "./login";

let account: { username: string; password: string; business_id: string };
let seeded: { chat_id: string };
const python = resolve("../backend/.venv/bin/python");
const fixture = resolve("../backend/tests/browser_fixture.py");
const chats = resolve("../backend/tests/chat_browser_fixture.py");
function fixturePython(code: string) {
  return execFileSync(
    python,
    [
      "-c",
      `import os,sys,json; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); import django; django.setup(); data=json.load(sys.stdin)\n${code}`,
    ],
    {
      cwd: resolve("../backend"),
      input: JSON.stringify({ ...account, ...seeded }),
      encoding: "utf8",
    },
  );
}
function inbound(text: string) {
  execFileSync(python, [chats, "inbound"], {
    input: JSON.stringify({ ...account, ...seeded, text }),
    encoding: "utf8",
  });
}
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
  fixturePython(
    "from tapme.messaging.models import ChannelAccount; ChannelAccount.objects.filter(business_id=data['business_id']).update(provider_mode='fake')",
  );
});
test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "wait" });
  execFileSync(python, [fixture, "delete"], { input: JSON.stringify(account) });
});
async function openEditor(page: Page, mobile = false) {
  await page.goto("/");
  await submitLogin(page, account.username, account.password);
  await api(page, "products/", "POST", {
    name: "Нежный букет",
    price: "3200.00",
  });
  await page.goto(
    `/?view=chats&business=${account.business_id}&chat=${seeded.chat_id}`,
  );
  if (mobile)
    await page
      .getByRole("group", { name: "Клиент и черновик", exact: true })
      .getByRole("button", { name: "Черновик заказа", exact: true })
      .click();
  await page
    .getByRole("button", { name: "Создать черновик", exact: true })
    .click();
  await expect(page.getByLabel("Автозаполнение черновика")).toContainText(
    "Демонстрационный режим без ИИ",
  );
}
for (const mobile of [false, true])
  test(`автозаполнение, проверка и защита ручных полей ${mobile ? "390" : "1440"}`, async ({
    page,
  }, info) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    await openEditor(page, mobile);
    await page
      .getByLabel("Адрес доставки", { exact: true })
      .fill("Ручной адрес");
    await page
      .getByRole("button", { name: "Сохранить черновик", exact: true })
      .click();
    await expect(page.getByRole("status")).toContainText("Черновик сохранён");
    inbound(
      "Нежный букет; завтра; доставка; 10:00–12:00; Адрес: Адрес из чата; Получатель: Айдана; Телефон получателя: +996700123456; Открытка: С праздником!",
    );
    await expect(
      page.getByLabel("Текст открытки", { exact: true }),
    ).toHaveValue("С праздником!", { timeout: 25000 });
    await expect(
      page.getByLabel("Адрес доставки", { exact: true }),
    ).toHaveValue("Ручной адрес");
    await expect(
      page.getByRole("button", {
        name: "Создать заказ · ждёт подтверждения",
        exact: true,
      }),
    ).toBeDisabled();
    await page
      .getByRole("button", { name: "Проверил заполнение", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Сохранить черновик", exact: true })
      .click();
    await expect(page.getByRole("status")).toContainText("Черновик сохранён");
    const data = await api(page, `chats/${seeded.chat_id}/order-draft/`);
    expect(data.draft.field_meta.card_text.locked).toBeTruthy();
    expect(data.draft.field_meta.card_text.needs_check).toBeFalsy();
    expect(data.draft.fields.items).toHaveLength(1);
    await page.getByLabel("Автозаполнение черновика").scrollIntoViewIfNeeded();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(mobile ? 390 : 1440);
    await page.screenshot({
      path: `/tmp/tapme-extraction-${info.project.name}-${mobile ? 390 : 1440}.png`,
      fullPage: true,
    });
  });

test("обновление из чата сохраняет несохранённый ввод при конфликте", async ({
  page,
}) => {
  await openEditor(page);
  // Wait for the initial automatic pass, then deliberately leave a local edit unsaved.
  await expect
    .poll(
      async () =>
        (await api(page, `chats/${seeded.chat_id}/order-draft/`)).draft
          .extraction.status,
      { timeout: 20000 },
    )
    .toBe("applied");
  await page
    .getByLabel("Адрес доставки", { exact: true })
    .fill("Мой несохранённый адрес");
  inbound("Открытка: Новое пожелание");
  await expect(
    page.getByRole("button", { name: "Загрузить актуальный черновик" }),
  ).toBeVisible({ timeout: 25000 });
  await expect(page.getByLabel("Адрес доставки", { exact: true })).toHaveValue(
    "Мой несохранённый адрес",
  );
  await expect(
    page.getByRole("button", { name: "Сохранить черновик", exact: true }),
  ).toBeDisabled();
  page.once("dialog", (dialog) => dialog.dismiss());
  await page
    .getByRole("button", { name: "Загрузить актуальный черновик" })
    .click();
  await expect(page.getByLabel("Адрес доставки", { exact: true })).toHaveValue(
    "Мой несохранённый адрес",
  );
});

test("ручной разбор после сетевой ошибки сохраняет правки", async ({
  page,
}) => {
  await openEditor(page);
  fixturePython(`from datetime import timedelta
from django.utils import timezone
from tapme.orders.models import OrderDraft
from tapme.messaging.models import Conversation, Message
chat = Conversation.objects.get(id=data['chat_id'])
OrderDraft.objects.filter(conversation=chat).update(extraction_actor=None, extraction_state={})
message = Message.objects.create(conversation=chat, direction='in', status='received', text='Открытка: Проверка ручного разбора')
Message.objects.filter(id=message.id).update(created_at=timezone.now()-timedelta(seconds=8))`);
  await page
    .getByLabel("Адрес доставки", { exact: true })
    .fill("Сохранить мой адрес");
  let fail = true;
  await page.route("**/order-draft/extract/", async (route) => {
    if (fail) {
      fail = false;
      await route.abort();
    } else await route.continue();
  });
  const button = page.getByRole("button", {
    name: "Обновить из чата",
    exact: true,
  });
  await button.click();
  await expect(button).toBeEnabled();
  await expect(page.getByLabel("Адрес доставки", { exact: true })).toHaveValue(
    "Сохранить мой адрес",
  );
  await button.click();
  await expect(page.getByLabel("Текст открытки", { exact: true })).toHaveValue(
    "Проверка ручного разбора",
    { timeout: 25000 },
  );
  await expect(page.getByLabel("Адрес доставки", { exact: true })).toHaveValue(
    "Сохранить мой адрес",
  );
});
