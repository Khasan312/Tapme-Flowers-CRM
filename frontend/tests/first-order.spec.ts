import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { submitLogin } from "./login";

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
    await submitLogin(page, account.username, account.password);
    await expect(
      page.getByRole("heading", { name: "Заказы", exact: true }),
    ).toBeVisible();
  }
  await page.goto("/login");
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
    .getByLabel("Категория клиента", { exact: true })
    .selectOption("vip");
  await page
    .getByLabel("Заметка", { exact: true })
    .fill("Предпочитает белые цветы");
  await page.getByRole("button", { name: "Сохранить клиента" }).click();
  await expect(
    page.getByRole("button", { name: /Тестовый покупатель/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: "VIP", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /Тестовый покупатель/ }),
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
    page
      .getByRole("dialog")
      .getByText("Позвонить перед доставкой", { exact: true }),
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

test("смена клиента обновляет получателя и телефон, ручной получатель сохраняется", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/login");
  await submitLogin(page, account.username, account.password);
  const base = `/api/v1/businesses/${account.business_id}`;
  const csrf = await (await page.request.get("/api/v1/auth/csrf/")).json();
  const headers = { "X-CSRFToken": csrf.csrf_token };
  const create = async (path: string, data: unknown) => {
    const response = await page.request.post(`${base}/${path}/`, {
      headers,
      data,
    });
    expect(response.status()).toBe(201);
    return response.json();
  };
  const first = await create("customers", {
    name: "Ахмат проверки",
    phone: "+996555800001",
  });
  const second = await create("customers", {
    name: "Алия проверки",
    phone: "+77018000002",
  });
  const product = await create("products", {
    name: "Букет для получателя",
    price: "1500",
  });
  const {
    id: _id,
    code: _code,
    created_at: _created,
    ...profile
  } = await (await page.request.get(`${base}/customers/${first.id}/`)).json();
  const updated = await page.request.put(`${base}/customers/${first.id}/`, {
    headers,
    data: {
      ...profile,
      recipients: [
        {
          name: "Мама Ахмата",
          relation: "Мама",
          phone: "+996700800003",
          address: "",
          notes: "",
        },
      ],
    },
  });
  expect(updated.status()).toBe(200);
  const savedRecipient = (await updated.json()).recipients[0];
  await page.getByRole("button", { name: "Новый заказ", exact: true }).click();
  const name = page.getByLabel("Получатель", { exact: true });
  const phone = page.getByLabel("Телефон получателя", { exact: true });
  for (const customer of [first, second, first]) {
    await page.getByRole("button", { name: new RegExp(customer.name) }).click();
    await expect(name).toHaveValue(customer.name);
    await expect(phone).toHaveValue(customer.phone);
  }
  const saved = page.getByLabel("Получатель из карточки", { exact: true });
  await saved.selectOption(savedRecipient.id);
  await expect(name).toHaveValue(savedRecipient.name);
  await expect(phone).toHaveValue(savedRecipient.phone);
  // Re-selecting the same client also restores both fields and clears the saved recipient selection.
  await page.getByRole("button", { name: new RegExp(first.name) }).click();
  await expect(name).toHaveValue(first.name);
  await expect(phone).toHaveValue(first.phone);
  await expect(saved).toHaveValue("");
  await page.getByRole("button", { name: new RegExp(second.name) }).click();
  await expect(name).toHaveValue(second.name);
  await expect(phone).toHaveValue(second.phone);
  await page
    .getByRole("button", { name: "Позиция прайса", exact: true })
    .click();
  await page.getByRole("option", { name: new RegExp(product.name) }).click();
  await page
    .getByRole("button", { name: "Добавить в заказ", exact: true })
    .click();
  await name.fill("Другой получатель");
  await phone.fill("+996700800004");
  // Searching alone and loading a client profile must not overwrite manual recipient data.
  await page
    .getByLabel("Поиск по имени или телефону", { exact: true })
    .fill(first.name);
  await expect(
    page.getByRole("button", { name: new RegExp(first.name) }),
  ).toBeVisible();
  await expect(name).toHaveValue("Другой получатель");
  await expect(phone).toHaveValue("+996700800004");
  const [response] = await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().endsWith(`${base}/orders/`) && r.request().method() === "POST",
    ),
    page.getByRole("button", { name: "Создать заказ", exact: true }).click(),
  ]);
  expect(response.status()).toBe(201);
  const order = await response.json();
  expect(order.customer_id).toBe(second.id);
  expect(order.recipient_name).toBe("Другой получатель");
  expect(order.recipient_phone).toBe("+996700800004");
  await page
    .getByRole("button", {
      name: `Открыть заказ №${order.number}`,
      exact: true,
    })
    .click();
  await page
    .getByRole("button", { name: "Редактировать заказ", exact: true })
    .click();
  await expect(name).toHaveValue("Другой получатель");
  await expect(phone).toHaveValue("+996700800004");
});
