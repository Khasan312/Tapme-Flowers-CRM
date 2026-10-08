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

test("команда, редактирование, флорист, доставка, оплата, клиент и напоминания", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  async function login(username: string) {
    await page.goto("/");
    await submitLogin(page, username, account.password);
  }
  const florist = account.username + "_florist",
    courier = account.username + "_courier";
  await login(account.username);
  await page.getByRole("button", { name: "Настройки", exact: true }).click();

  for (const [username, name, role] of [
    [florist, "Флорист теста", "florist"],
    [courier, "Курьер теста", "courier"],
  ]) {
    await page.getByRole("button", { name: "Пригласить", exact: true }).click();
    await page.getByLabel("Имя сотрудника", { exact: true }).fill(name);
    await page.getByLabel("Логин сотрудника", { exact: true }).fill(username);
    await page
      .getByLabel("Начальный пароль", { exact: true })
      .fill(account.password);
    await page
      .getByLabel("Роль сотрудника", { exact: true })
      .selectOption(role);
    await page
      .getByRole("button", { name: "Создать сотрудника", exact: true })
      .click();
    await expect(page.getByText(name, { exact: true })).toBeVisible();
  }
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await page.getByRole("tab", { name: "Прайс", exact: true }).click();
  await page
    .getByRole("button", { name: "Добавить позицию", exact: true })
    .click();
  await page.getByLabel("Название", { exact: true }).fill("Розы для теста");
  await page.getByLabel("Цена, сом").fill("1000");
  const referencePhoto = execFileSync(python, [
    "-c",
    "import sys; from PIL import Image; Image.new('RGB', (20, 20), 'pink').save(sys.stdout.buffer, 'PNG')",
  ]);
  await page.getByLabel("Фото букета").setInputFiles({
    name: "reference.png",
    mimeType: "image/png",
    buffer: referencePhoto,
  });
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Добавить позицию", exact: true })
    .click();
  await page.getByRole("button", { name: "Заказы", exact: true }).click();
  await page.getByRole("button", { name: "Новый заказ", exact: true }).click();
  await page
    .getByText("Новый клиент — создать прямо в заказе", { exact: true })
    .click();
  await page.getByLabel("Имя нового клиента").fill("Покупатель цикла");
  await page.getByLabel("Телефон нового клиента").fill("+996700333444");
  await page.getByRole("button", { name: "Создать и выбрать клиента" }).click();
  await expect(page.getByText(/Выбран: Покупатель цикла/)).toBeVisible();
  await page
    .getByRole("button", { name: "Добавить в заказ", exact: true })
    .click();
  await page.getByLabel("Получение", { exact: true }).selectOption("courier");
  await page.getByLabel("Адрес доставки").fill("Тестовый адрес");
  await page
    .getByRole("button", { name: "Создать заказ", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Открыть заказ №1", exact: true })
    .click();
  await page.getByRole("button", { name: "Редактировать заказ" }).click();
  await page.getByLabel("Получатель", { exact: true }).fill("Получатель цикла");
  await page
    .getByRole("button", { name: "Сохранить изменения", exact: true })
    .click();
  await page
    .getByLabel("Флорист", { exact: true })
    .selectOption({ label: "Флорист теста" });
  await page
    .getByLabel("Курьер", { exact: true })
    .selectOption({ label: "Курьер теста" });
  await page.getByRole("button", { name: "Назначить сотрудников" }).click();
  await page.getByLabel("Сумма, сом", { exact: true }).fill("1000");
  await page
    .getByRole("button", { name: "Записать оплату или возврат" })
    .click();
  await expect(page.getByText(/Внесено:/)).toContainText(/1\s000/);
  const photo = execFileSync(python, [
    "-c",
    "import sys; from PIL import Image; Image.new('RGB', (20, 20), 'green').save(sys.stdout.buffer, 'PNG')",
  ]);
  await page.getByLabel("Файл фотографии", { exact: true }).setInputFiles({
    name: "bouquet.png",
    mimeType: "image/png",
    buffer: photo,
  });
  await page
    .getByRole("button", { name: "Загрузить фото", exact: true })
    .click();
  await expect(
    page.getByRole("img", { name: "Фото букета", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Создать ссылку", exact: true })
    .click();
  const link = await page
    .getByLabel("Ссылка клиенту", { exact: true })
    .inputValue();
  await page.screenshot({
    path: "/tmp/tapme-order-workflow.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Закрыть", exact: true })
    .last()
    .click();
  await page.getByRole("button", { name: "Меню пользователя" }).click();
  await page.getByRole("menuitem", { name: "Выйти", exact: true }).click();
  await login(florist);
  const reference = page.getByRole("img", {
    name: "Розы для теста",
    exact: true,
  });
  await expect(reference).toBeVisible();
  await expect
    .poll(() => reference.evaluate((el: HTMLImageElement) => el.naturalWidth))
    .toBeGreaterThan(0);
  await page
    .getByRole("button", { name: "Взять в работу", exact: true })
    .click();
  await page.getByRole("button", { name: "Букет готов", exact: true }).click();
  await expect(page.getByText("Собран", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Меню пользователя" }).click();
  await page.getByRole("menuitem", { name: "Выйти", exact: true }).click();
  await login(courier);
  await page
    .getByRole("button", { name: "Передать курьеру", exact: true })
    .click();
  await page.getByRole("button", { name: "Заказ вручён", exact: true }).click();
  await expect(page.getByText("Вручён", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Меню пользователя" }).click();
  await page.getByRole("menuitem", { name: "Выйти", exact: true }).click();
  await page.goto(link);
  await expect(page.getByText("Вручён", { exact: true })).toBeVisible();
  await page.getByLabel("Ваш отзыв").fill("Красивый букет");
  await page.getByRole("button", { name: "Отправить отзыв" }).click();
  await expect(page.getByRole("status")).toContainText("Спасибо за отзыв");
  await login(account.username);
  await page.getByRole("button", { name: "Клиенты", exact: true }).click();
  await page
    .getByRole("button", { name: "Покупатель цикла", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Изменить", exact: true })
    .first()
    .click();
  await page.getByLabel("Заметка клиента", { exact: true }).fill("Любит розы");
  await page.getByLabel("Клиент согласился получать сообщения").check();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Добавить дату" })
    .click();
  await page.getByLabel("У кого", { exact: true }).fill("Мама");
  await page
    .getByRole("button", { name: "Сохранить клиента", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Карточка сохранена");
  await page.getByRole("button", { name: "Закрыть", exact: true }).click();
  await page.getByRole("button", { name: "Напоминания", exact: true }).click();
  await page.getByRole("button", { name: "Правила", exact: true }).click();
  await expect(page.getByLabel("Напоминания включены")).toBeChecked();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Доставка", exact: true }).click();
  await expect(
    page.getByText("Получатель цикла", { exact: true }).first(),
  ).toBeVisible();
  await page.screenshot({
    path: "/tmp/tapme-deliveries-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  expect(errors).toEqual([]);
});
