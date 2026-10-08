import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { submitLogin } from "./login";

let account: { username: string; password: string; business_id: string };
const python = resolve("../backend/.venv/bin/python"),
  fixture = resolve("../backend/tests/browser_fixture.py");
test.use({
  baseURL: process.env.TAPME_LAN_URL || "http://127.0.0.1:5173",
  viewport: { width: 390, height: 844 },
});
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

test("телефон: импорт CSV и создание шаблона без secure-context randomUUID", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.addInitScript(() =>
    Object.defineProperty(crypto, "randomUUID", {
      value: undefined,
      configurable: true,
    }),
  );
  await page.goto("/");
  await submitLogin(page, account.username, account.password);
  await page.getByRole("button", { name: "Клиенты", exact: true }).click();
  await page.getByRole("button", { name: "Импорт", exact: true }).click();
  await page.getByLabel("Файл клиентов").setInputFiles({
    name: "contacts.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "name,phone,notes\nТест телефона,0555111222,Проверка импорта\n",
    ),
  });
  await expect(page.getByRole("status")).toContainText("Готово к импорту: 1");
  await page
    .getByRole("button", { name: "Импортировать выбранные (1)" })
    .click();
  await expect(page.getByRole("status")).toContainText("Создано: 1");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Закрыть", exact: true })
    .last()
    .click();
  await expect(
    page.getByRole("button", { name: "Тест телефона", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await page.getByRole("tab", { name: "Шаблоны", exact: true }).click();
  await page.getByRole("button", { name: "Добавить шаблон" }).click();
  await page.getByLabel("Название шаблона", { exact: true }).fill("Телефон");
  await page
    .getByLabel("Текст шаблона", { exact: true })
    .fill("Здравствуйте, {имя}!");
  await page.getByRole("button", { name: "Сохранить шаблоны" }).first().click();
  await expect(page.getByRole("status")).toContainText("Шаблоны сохранены");
  const rules = await (
    await page.request.get(
      `/api/v1/businesses/${account.business_id}/reminder-rules/`,
    )
  ).json();
  expect(rules.custom_templates[0].id).toMatch(
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
  );
  expect(errors).toEqual([]);
});

test("вход помещается на телефоне без боковой прокрутки и мелких полей", async ({
  page,
}, info) => {
  for (const [width, height] of [
    [320, 568],
    [390, 844],
    [430, 932],
    [844, 390],
    [1440, 1000],
  ]) {
    await page.setViewportSize({ width, height });
    await page.goto("/");
    const button = page.getByRole("button", {
      name: "Войти в CRM",
      exact: true,
    });
    await expect(button).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    const username = page.getByLabel("Логин", { exact: true });
    expect(
      await username.evaluate((el) =>
        parseFloat(getComputedStyle(el).fontSize),
      ),
    ).toBeGreaterThanOrEqual(16);
    await expect(username).not.toBeFocused();
    if (width <= 430) {
      const bounds = await button.boundingBox();
      expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(height);
      const story = await page.locator(".login-story").boundingBox();
      expect(story!.height).toBeLessThan(110);
    }
    if (width === 390 || width === 320)
      await page.screenshot({
        path: `/tmp/tapme-login-after-${info.project.name}-${width}.png`,
        fullPage: true,
      });
  }
});

test("VCF: поиск и выбор контакта на телефоне, остальные не импортируются", async ({
  page,
}, info) => {
  await page.goto("/");
  await submitLogin(page, account.username, account.password);
  await page.getByRole("button", { name: "Клиенты", exact: true }).click();
  await page.getByRole("button", { name: "Импорт", exact: true }).click();
  const vcf = [
    "BEGIN:VCARD\nVERSION:3.0\nFN:Алия\nN:VCF;Алия;;;\nTEL;TYPE=CELL:\nTEL;TYPE=CELL:0555444666\nTEL;TYPE=HOME:+996312444666\nTEL;TYPE=WORK:0312444666\nEND:VCARD",
    "BEGIN:VCARD\nVERSION:4.0\nFN:Второй VCF\nTEL;VALUE=uri:tel:+996700444666\nEND:VCARD",
    "BEGIN:VCARD\nVERSION:3.0\nFN:Дубликат\nTEL:+996555444666\nEND:VCARD",
    "BEGIN:VCARD\nVERSION:3.0\nFN:Без номера\nEND:VCARD",
  ].join("\n");
  await page.getByLabel("Файл клиентов").setInputFiles({
    name: "phone.vcf",
    mimeType: "text/vcard",
    buffer: Buffer.from(vcf),
  });
  await expect(page.getByRole("status")).toContainText("Готово к импорту: 2");
  await expect(page.getByRole("checkbox", { name: /Дубликат/ })).toBeDisabled();
  await expect(
    page.getByRole("checkbox", { name: /Без номера/ }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Снять выбор", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Импортировать выбранные (0)" }),
  ).toBeDisabled();
  await page.getByLabel("Найти контакт в файле").fill("312444666");
  await page
    .getByRole("checkbox", {
      name: "Выбрать Алия VCF +996555444666",
      exact: true,
    })
    .check();
  await page.getByLabel("Найти контакт в файле").fill("");
  const modal = page.getByRole("dialog");
  expect(
    await modal.evaluate((el) => el.scrollWidth - el.clientWidth),
  ).toBeLessThanOrEqual(1);
  await page.screenshot({
    path: `/tmp/tapme-vcf-selection-${info.project.name}.png`,
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Импортировать выбранные (1)" })
    .click();
  await expect(page.getByRole("status")).toContainText("Создано: 1");
  const customers = await (
    await page.request.get(
      `/api/v1/businesses/${account.business_id}/customers/?search=VCF`,
    )
  ).json();
  expect(customers.count).toBe(1);
  expect(customers.results[0].name).toBe("Алия VCF");
  expect(customers.results[0].phone).toBe("+996555444666");
  expect(customers.results[0].additional_phones).toEqual(["+996312444666"]);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Закрыть", exact: true })
    .last()
    .click();
  await page.getByLabel("Поиск клиентов", { exact: true }).fill("312444666");
  await page.getByRole("button", { name: "Алия VCF", exact: true }).click();
  await page
    .getByRole("button", { name: "Изменить", exact: true })
    .first()
    .click();
  await expect(
    page.getByLabel("Дополнительный телефон 1", { exact: true }),
  ).toHaveValue("+996312444666");
  await page
    .getByRole("button", { name: "Сделать телефон 1 основным", exact: true })
    .click();
  await expect(page.getByLabel("Телефон клиента", { exact: true })).toHaveValue(
    "+996312444666",
  );
  await page
    .getByRole("button", { name: "Добавить телефон", exact: true })
    .click();
  await page
    .getByLabel("Дополнительный телефон 2", { exact: true })
    .fill("0777444666");
  await page
    .getByLabel("Категория клиента", { exact: true })
    .selectOption("both");
  await page.getByText("Другие метки", { exact: true }).click();
  await page
    .getByLabel("Дополнительные метки", { exact: true })
    .fill("Постоянный, Любит розы");
  await page
    .getByRole("button", { name: "Сохранить клиента", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Карточка сохранена");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Закрыть", exact: true })
    .last()
    .click();
  const profilePath = `/api/v1/businesses/${account.business_id}/customers/${customers.results[0].id}/`;
  const profile = await (await page.request.get(profilePath)).json();
  expect(profile.phone).toBe("+996312444666");
  expect(profile.additional_phones).toEqual(["+996555444666", "+996777444666"]);
  expect(profile.tags).toEqual([
    "VIP",
    "Корпоративный",
    "Постоянный",
    "Любит розы",
  ]);
  await page.getByRole("button", { name: "Клиенты", exact: true }).click();
  await page
    .getByRole("button", { name: "VIP и корпоративные", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "VIP и корпоративные", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: /^Алия VCF/ }).click();
  await expect(page.getByRole("heading", { name: /^Алия VCF/ })).toBeVisible();
  await page
    .getByRole("button", { name: "Новый заказ", exact: true })
    .last()
    .click();
  await expect(
    page.getByLabel("Телефон получателя", { exact: true }),
  ).toHaveValue("+996312444666");
  await page
    .getByLabel("Телефон клиента для получателя", { exact: true })
    .selectOption("+996777444666");
  await expect(
    page.getByLabel("Телефон получателя", { exact: true }),
  ).toHaveValue("+996777444666");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Закрыть", exact: true })
    .last()
    .click();
  await page
    .getByRole("button", { name: "Изменить", exact: true })
    .first()
    .click();
  await page
    .getByLabel("Категория клиента", { exact: true })
    .selectOption("regular");
  await page
    .getByRole("button", {
      name: "Удалить дополнительный телефон 2",
      exact: true,
    })
    .click();
  await page
    .getByRole("button", { name: "Сохранить клиента", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Карточка сохранена");
  const edited = await (await page.request.get(profilePath)).json();
  expect(edited.tags).toEqual(["Постоянный", "Любит розы"]);
  expect(edited.additional_phones).toEqual(["+996555444666"]);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Закрыть", exact: true })
    .last()
    .click();
  await page.getByRole("button", { name: "Клиенты", exact: true }).click();
  await page
    .getByRole("button", { name: "VIP и корпоративные", exact: true })
    .click();
  await expect(
    page.getByText("Никого не нашли. Проверьте телефон или добавьте клиента."),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Давно не заказывали", exact: true })
    .click();
  await expect(page.getByText(/Прошло 90 дней или больше/)).toBeVisible();
});

test("импорт: видимая загрузка, повтор после обрыва и замена ошибочного файла", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 568 });
  await page.goto("/");
  await submitLogin(page, account.username, account.password);
  await page.getByRole("button", { name: "Клиенты", exact: true }).click();
  await page.getByRole("button", { name: "Импорт", exact: true }).click();
  const before = await (
    await page.request.get(
      `/api/v1/businesses/${account.business_id}/customers/`,
    )
  ).json();
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(
    "**/customers/import/",
    async (route) => {
      await gate;
      await route.abort("failed");
    },
    { times: 1 },
  );
  const contactFile = {
    name: "iPhone.vcf",
    mimeType: "text/vcard",
    buffer: Buffer.from(
      "BEGIN:VCARD\nVERSION:3.0\nFN:Проверка без сохранения\nTEL:0555777999\nEND:VCARD",
    ),
  };
  await page.getByLabel("Файл клиентов").setInputFiles(contactFile);
  try {
    const loading = page.getByRole("status");
    await expect(loading).toHaveText("Проверяем файл контактов…");
    await expect(loading).toBeInViewport();
    await expect(
      page.getByRole("button", { name: /Импортировать выбранные/ }),
    ).toHaveCount(0);
    await expect(page.getByLabel("Файл клиентов")).toBeDisabled();
  } finally {
    release();
  }
  await expect(page.getByRole("alert")).toContainText(
    "Не удалось связаться с сервером",
  );
  await expect(page.getByRole("alert")).toBeInViewport();
  await page.getByRole("button", { name: "Повторить проверку" }).click();
  await expect(page.getByRole("status")).toContainText("Готово к импорту: 1");
  await page.getByText("Файл: iPhone.vcf · изменить", { exact: true }).click();
  await page.getByLabel("Файл клиентов").setInputFiles({
    ...contactFile,
    name: "broken.vcf",
    buffer: Buffer.from("invalid vcard"),
  });
  await expect(page.getByRole("alert")).toContainText("VCF");
  await expect(page.getByRole("checkbox")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: /Импортировать выбранные/ }),
  ).toHaveCount(0);
  await page.getByText("Файл: broken.vcf · изменить", { exact: true }).click();
  await page.getByLabel("Файл клиентов").setInputFiles(contactFile);
  await expect(page.getByRole("status")).toContainText("Готово к импорту: 1");
  await expect(page.getByRole("alert")).toHaveCount(0);
  const after = await (
    await page.request.get(
      `/api/v1/businesses/${account.business_id}/customers/`,
    )
  ).json();
  expect(after.count).toBe(before.count);
});
