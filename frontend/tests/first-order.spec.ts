import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

let account: { username: string; password: string; business_id: string };
const python = resolve("../backend/.venv/bin/python");
const fixture = resolve("../backend/tests/browser_fixture.py");

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

test("вход, клиент, прайс, заказ и сохранение после повторного входа", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  async function login() {
    await page.getByLabel("Логин", { exact: true }).fill(account.username);
    await page.getByLabel("Пароль", { exact: true }).fill(account.password);
    await page.getByRole("button", { name: "Войти в CRM" }).click();
    await expect(
      page.getByRole("heading", { name: "Заказы", exact: true }),
    ).toBeVisible();
  }
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "С возвращением" }),
  ).toBeVisible();
  await page.screenshot({ path: "/tmp/tapme-login.png", fullPage: true });
  await login();
  await page.getByRole("button", { name: "Клиенты", exact: true }).click();
  await page.getByRole("button", { name: "Новый клиент" }).click();
  await page.getByLabel("Имя клиента").fill("Тестовый покупатель");
  await page.getByLabel("Телефон", { exact: true }).fill("+996555123456");
  await page
    .getByLabel("Заметка", { exact: true })
    .fill("Предпочитает белые цветы");
  await page.getByRole("button", { name: "Сохранить клиента" }).click();
  await expect(
    page.getByRole("cell", { name: "Тестовый покупатель", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await page.getByRole("tab", { name: "Прайс", exact: true }).click();
  await page
    .getByRole("button", { name: "Добавить позицию", exact: true })
    .click();
  await page.getByLabel("Название", { exact: true }).fill("Букет дня");
  await page.getByLabel("Цена, сом").fill("2500.50");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Добавить позицию" })
    .click();
  await expect(
    page.getByRole("cell", { name: "Букет дня", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Заказы", exact: true }).click();
  await page.getByRole("button", { name: "Новый заказ", exact: true }).click();
  await page.getByRole("button", { name: /Тестовый покупатель/ }).click();
  await page.getByRole("button", { name: "Добавить в заказ" }).click();
  await page
    .getByRole("spinbutton", { name: "Количество Букет дня" })
    .fill("2");
  await page
    .getByLabel("Получатель", { exact: true })
    .fill("Тестовый получатель");
  await page.getByLabel("Получение", { exact: true }).selectOption("courier");
  await page.getByLabel("Адрес доставки").fill("Бишкек, тестовый адрес");
  await page.getByLabel("Заметка к заказу").fill("Позвонить перед доставкой");
  await page
    .getByRole("button", { name: "Создать заказ", exact: true })
    .click();
  await page.getByRole("button", { name: "Список", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "№1", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("cell", { name: /5\s001 сом/ })).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "Список", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "№1", exact: true }),
  ).toBeVisible();
  // Clicking the active navigation entry must retain/refetch the current list.
  await page.getByRole("button", { name: "Заказы", exact: true }).click();
  await page.getByRole("button", { name: "Список", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "№1", exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: "/tmp/tapme-orders.png", fullPage: true });
  await page.getByRole("button", { name: "№1", exact: true }).click();
  await expect(
    page.getByText("Позвонить перед доставкой", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Закрыть", exact: true })
    .last()
    .click();
  await page.getByRole("button", { name: "Меню пользователя" }).click();
  await page.getByRole("menuitem", { name: "Выйти", exact: true }).click();
  await login();
  await page.getByRole("button", { name: "Список", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "№1", exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Меню пользователя" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Новый заказ", exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: "/tmp/tapme-mobile.png", fullPage: true });
  expect(errors).toEqual([]);
});
