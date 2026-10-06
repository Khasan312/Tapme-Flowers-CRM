import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { submitLogin } from "./login";

let account: {
  username: string;
  password: string;
  business_id: string;
  removed_staff: string[];
};
const python = resolve("../backend/.venv/bin/python"),
  fixture = resolve("../backend/tests/browser_fixture.py");

test.beforeEach(() => {
  account = {
    ...JSON.parse(
      execFileSync(python, [fixture, "create"], { encoding: "utf8" }),
    ),
    removed_staff: [],
  };
});
test.afterEach(() => {
  if (account)
    execFileSync(python, [fixture, "delete"], {
      input: JSON.stringify(account),
    });
});

async function login(page: Page) {
  await page.goto("/");
  await submitLogin(page, account.username, account.password);
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
}

test("владелец удаляет сотрудника с подтверждением", async ({ page }, info) => {
  await login(page);
  const username = account.username + "_courier";
  account.removed_staff.push(username);
  await page.getByRole("button", { name: "Пригласить", exact: true }).click();
  await page
    .getByLabel("Имя сотрудника", { exact: true })
    .fill("Курьер для проверки");
  await page.getByLabel("Логин сотрудника", { exact: true }).fill(username);
  await page
    .getByLabel("Начальный пароль", { exact: true })
    .fill(account.password);
  await expect(page.getByLabel("Телефон сотрудника")).toHaveValue("+996");
  await page.getByLabel("Телефон сотрудника").fill("0555 123 456");
  await page
    .getByLabel("Роль сотрудника", { exact: true })
    .selectOption("courier");
  await page
    .getByRole("button", { name: "Создать сотрудника", exact: true })
    .click();
  const row = page.getByRole("row").filter({ hasText: "Курьер для проверки" });
  await expect(row).toContainText("+996555123456");
  await row.getByRole("button", { name: "Курьер для проверки" }).click();
  await page
    .getByRole("button", { name: "Удалить сотрудника", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Удалить сотрудника?" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Отмена", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Сохранить сотрудника" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Удалить сотрудника", exact: true })
    .click();
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-staff-removal.png`,
  });
  await page.getByRole("button", { name: "Да, удалить сотрудника" }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Сотрудник удалён из магазина",
  );
  await expect(row).toHaveCount(0);
  await page.reload();
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await expect(
    page.getByRole("cell", { name: account.username, exact: true }),
  ).toBeVisible();
  await expect(row).toHaveCount(0);
});

test("свои шаблоны сохраняются, редактируются и удаляются", async ({
  page,
}, info) => {
  await login(page);
  await page.getByRole("tab", { name: "Шаблоны", exact: true }).click();
  await page.getByRole("button", { name: "Добавить шаблон" }).click();
  await page
    .getByLabel("Название шаблона", { exact: true })
    .fill("Спасибо за заказ");
  await page.getByLabel("Текст шаблона", { exact: true }).fill("{unknown}");
  await page.getByRole("button", { name: "Сохранить шаблоны" }).first().click();
  await expect(page.getByRole("alert")).toContainText("Проверьте подстановки");
  await page
    .getByLabel("Текст шаблона", { exact: true })
    .fill("{имя}, спасибо за заказ! Ваш {магазин}.");
  await page.getByRole("button", { name: "Сохранить шаблоны" }).first().click();
  await expect(page.getByRole("status")).toHaveText("Шаблоны сохранены");
  await page.reload();
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await page.getByRole("tab", { name: "Шаблоны", exact: true }).click();
  await expect(
    page.getByLabel("Название шаблона", { exact: true }),
  ).toHaveValue("Спасибо за заказ");
  await expect(page.getByLabel("Текст шаблона", { exact: true })).toHaveValue(
    "{имя}, спасибо за заказ! Ваш {магазин}.",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-custom-templates-mobile.png`,
  });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page
    .getByLabel("Текст шаблона", { exact: true })
    .fill("{имя}, ждём вас снова!");
  await page.getByRole("button", { name: "Сохранить шаблоны" }).first().click();
  await expect(page.getByRole("status")).toHaveText("Шаблоны сохранены");
  const url = `/api/v1/businesses/${account.business_id}/reminder-rules/`;
  expect(
    (await (await page.request.get(url)).json()).custom_templates[0].text,
  ).toBe("{имя}, ждём вас снова!");
  await page.getByRole("button", { name: "Убрать шаблон" }).click();
  await page.getByRole("button", { name: "Сохранить шаблоны" }).first().click();
  await expect(page.getByRole("status")).toHaveText("Шаблоны сохранены");
  expect((await (await page.request.get(url)).json()).custom_templates).toEqual(
    [],
  );
});

test("местные телефоны принимаются в магазине и при создании заказа", async ({
  page,
}, info) => {
  await login(page);
  await page.getByRole("tab", { name: "Магазин", exact: true }).click();
  await expect(page.getByLabel("Телефон", { exact: true })).toHaveValue("+996");
  await expect(
    page.getByLabel("WhatsApp магазина", { exact: true }),
  ).toHaveValue("+996");
  await page.getByLabel("Телефон", { exact: true }).fill("555 123 456");
  await page
    .getByLabel("WhatsApp магазина", { exact: true })
    .fill("0700123456");
  await page.getByRole("button", { name: "Сохранить", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Сохранено");
  await expect(page.getByLabel("Телефон", { exact: true })).toHaveValue(
    "+996555123456",
  );
  await expect(
    page.getByLabel("WhatsApp магазина", { exact: true }),
  ).toHaveValue("+996700123456");
  await page.getByRole("tab", { name: "Прайс", exact: true }).click();
  await page
    .getByRole("button", { name: "Добавить позицию", exact: true })
    .click();
  await page.getByLabel("Название", { exact: true }).fill("Букет теста");
  await page.getByLabel("Цена, сом").fill("1000");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Добавить позицию", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: "Заказы", exact: true }).click();
  await page.getByRole("button", { name: "Новый заказ", exact: true }).click();
  await page
    .getByText("Новый клиент — создать прямо в заказе", { exact: true })
    .click();
  await expect(page.getByLabel("Телефон нового клиента")).toHaveValue("+996");
  await expect(page.getByLabel("Телефон получателя")).toHaveValue("+996");
  await page.getByLabel("Имя нового клиента").fill("Покупатель теста");
  await page.getByLabel("Телефон нового клиента").fill("0555333444");
  await page.getByRole("button", { name: "Создать и выбрать клиента" }).click();
  await expect(page.getByText(/Выбран: Покупатель теста/)).toContainText(
    "+996555333444",
  );
  await page
    .getByRole("button", { name: "Добавить в заказ", exact: true })
    .click();
  await page.getByLabel("Телефон получателя").fill("700 333 444");
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-phone-inputs.png`,
  });
  await page
    .getByRole("button", { name: "Создать заказ", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Открыть заказ №1", exact: true }),
  ).toBeVisible();
  const orders = await (
    await page.request.get(`/api/v1/businesses/${account.business_id}/orders/`)
  ).json();
  expect(orders.results[0].recipient_phone).toBe("+996700333444");
  expect(orders.results[0].customer_phone).toBe("+996555333444");
});
