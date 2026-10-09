import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { submitLogin } from "./login";

let account: { username: string; password: string; business_id: string };
const python = resolve("../backend/.venv/bin/python");
const fixture = resolve("../backend/tests/browser_fixture.py");
const base = () => `/api/v1/businesses/${account.business_id}`;
test.beforeEach(async ({ page }) => {
  account = JSON.parse(
    execFileSync(python, [fixture, "create"], { encoding: "utf8" }),
  );
  await page.goto("/");
  await submitLogin(page, account.username, account.password);
});
test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "wait" });
  if (account)
    execFileSync(python, [fixture, "delete"], {
      input: JSON.stringify(account),
    });
});
async function create(page: Page, resource: string, data: object) {
  const csrf = await (await page.request.get("/api/v1/auth/csrf/")).json();
  const response = await page.request.post(`${base()}/${resource}/`, {
    headers: { "X-CSRFToken": csrf.csrf_token },
    data,
  });
  expect(response.status()).toBe(201);
  return response.json();
}
const trigger = (page: Page) =>
  page.getByRole("button", { name: "Позиция прайса", exact: true });
const popup = (page: Page) =>
  page.getByRole("dialog", { name: "Выбор букета", exact: true });
async function openOrder(page: Page) {
  await page.getByRole("button", { name: "Новый заказ", exact: true }).click();
  await expect(trigger(page)).toBeVisible();
}

test("букеты с фото и ценой: поиск, выбор с клавиатуры и создание заказа", async ({
  page,
}, info) => {
  await create(page, "customers", {
    name: "Покупатель букета",
    phone: "+996555890031",
  });
  for (const [name, price] of [
    ["Нежность", "1800"],
    ["Композиция в коробке", "3200"],
  ])
    await create(page, "products", { name, price });
  const photo = execFileSync(python, [
    "-c",
    "import sys; from PIL import Image; Image.new('RGB', (50, 50), '#c789a9').save(sys.stdout.buffer, 'PNG')",
  ]);
  const csrf = await (await page.request.get("/api/v1/auth/csrf/")).json();
  const result = await page.request.post(`${base()}/products/`, {
    headers: { "X-CSRFToken": csrf.csrf_token },
    multipart: {
      name: "Яркий день",
      price: "2400",
      photo: { name: "flowers.png", mimeType: "image/png", buffer: photo },
    },
  });
  expect(result.status()).toBe(201);
  const product = await result.json();
  await openOrder(page);
  await page.getByRole("button", { name: /Покупатель букета/ }).click();
  await trigger(page).click();
  await expect(popup(page).getByRole("option")).toHaveCount(3);
  const option = popup(page).getByRole("option", { name: /Яркий день/ });
  await expect(option).toContainText(/2\s400 сом/);
  await expect
    .poll(() =>
      option.locator("img").evaluate((el: HTMLImageElement) => el.naturalWidth),
    )
    .toBeGreaterThan(0);
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-bouquet-picker.png`,
  });
  await popup(page).screenshot({
    path: `/tmp/tapme-${info.project.name}-bouquet-picker-detail.png`,
  });
  const search = page.getByRole("combobox", { name: "Найти букет" });
  await search.fill("ярКИЙ");
  await expect(popup(page).getByRole("option")).toHaveCount(1);
  await search.press("ArrowDown");
  await search.press("Enter");
  await expect(popup(page)).toHaveCount(0);
  await expect(trigger(page)).toContainText("Яркий день");
  await expect(page.locator("dialog")).toBeVisible();
  for (let i = 0; i < 2; i++)
    await page
      .getByRole("button", { name: "Добавить в заказ", exact: true })
      .click();
  await expect(
    page.getByLabel("Количество Яркий день", { exact: true }),
  ).toHaveValue("2");
  await page
    .getByRole("button", { name: "Создать заказ", exact: true })
    .click();
  await expect(page.locator("dialog")).toHaveCount(0);
  const orders = await (await page.request.get(`${base()}/orders/`)).json();
  expect(orders.results).toHaveLength(1);
  expect(orders.results[0].lines[0]).toMatchObject({
    product_id: product.id,
    quantity: 2,
  });
  expect(orders.results[0].total).toBe("4800.00");
});

test("телефон: длинное название, поиск без результатов, Escape и нажатие вне списка", async ({
  page,
}, info) => {
  const longName =
    "Нежность — большой авторский букет из пионовидных роз и эвкалипта в подарочной упаковке";
  await create(page, "products", { name: longName, price: "12500" });
  await page.setViewportSize({ width: 390, height: 844 });
  await openOrder(page);
  await trigger(page).click();
  await expect(popup(page).getByRole("option")).toHaveCount(1);
  const box = await popup(page).boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  expect(box!.y + box!.height).toBeLessThanOrEqual(844);
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-bouquet-picker-phone.png`,
  });
  const search = page.getByRole("combobox", { name: "Найти букет" });
  await search.fill("нет такого букета");
  await expect(
    popup(page).getByText("Букет не найден", { exact: true }),
  ).toBeVisible();
  await search.press("Enter");
  await expect(page.locator("dialog")).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.getByRole("button", { name: "Очистить поиск букетов" }).click();
  await expect(popup(page).getByRole("option")).toHaveCount(1);
  await search.press("Escape");
  await expect(popup(page)).toHaveCount(0);
  await expect(page.locator("dialog")).toBeVisible();
  await expect(trigger(page)).toBeFocused();
  await trigger(page).press("ArrowDown");
  await expect(popup(page)).toBeVisible();
  await page.setViewportSize({ width: 390, height: 420 });
  await expect
    .poll(async () => {
      const rect = await popup(page).boundingBox();
      return rect ? rect.y + rect.height : Infinity;
    })
    .toBeLessThanOrEqual(420);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("heading", { name: "Новый заказ", exact: true }).click();
  await expect(popup(page)).toHaveCount(0);
  await expect(page.locator("dialog")).toBeVisible();
});

test("поиск включает позиции за пределами первой страницы API", async ({
  page,
}) => {
  // Populate through the real API; pagination must not hide the final product from search.
  for (let i = 0; i < 101; i++)
    await create(page, "products", {
      name: `Букет ${String(i).padStart(3, "0")}`,
      price: "1000",
    });
  const final = await create(page, "products", {
    name: "Янтарное утро",
    price: "2300",
  });
  await openOrder(page);
  await trigger(page).click();
  await expect(
    popup(page).getByText("Позиций в прайсе: 102", { exact: true }),
  ).toBeVisible();
  await expect(popup(page).getByRole("option")).toHaveCount(20);
  await popup(page)
    .getByRole("button", { name: /Показать ещё/ })
    .click();
  await expect(popup(page).getByRole("option")).toHaveCount(40);
  await page.getByRole("combobox", { name: "Найти букет" }).fill("янтарное");
  await popup(page)
    .getByRole("option", { name: new RegExp(final.name) })
    .click();
  await expect(trigger(page)).toContainText(final.name);
  await page
    .getByRole("button", { name: "Добавить в заказ", exact: true })
    .click();
  await expect(
    page.getByLabel(`Количество ${final.name}`, { exact: true }),
  ).toHaveValue("1");
});

test("пустой прайс и ошибка загрузки объясняются, повтор работает без потери формы", async ({
  page,
}) => {
  await openOrder(page);
  await trigger(page).click();
  await expect(
    popup(page).getByText("В прайсе пока нет букетов", { exact: true }),
  ).toBeVisible();
  await page.getByRole("combobox", { name: "Найти букет" }).press("Escape");
  await expect(
    page.getByRole("button", { name: "Добавить в заказ", exact: true }),
  ).toBeDisabled();
  await page
    .locator("dialog")
    .getByRole("button", { name: "Закрыть", exact: true })
    .first()
    .click();
  await create(page, "products", { name: "После повтора", price: "1400" });
  let fail = true;
  await page.route("**/products/?*", (route) => {
    if (!fail) return route.continue();
    return route.fulfill({ status: 503, json: { detail: "test" } });
  });
  await openOrder(page);
  await page
    .getByLabel("Получатель", { exact: true })
    .fill("Черновик получателя");
  await trigger(page).click();
  await expect(popup(page).getByRole("alert")).toContainText(
    "Сервер не смог выполнить запрос",
  );
  fail = false;
  await popup(page)
    .getByRole("button", { name: "Попробовать снова", exact: true })
    .click();
  await expect(
    popup(page).getByRole("option", { name: /После повтора/ }),
  ).toBeVisible();
  await page.getByRole("combobox", { name: "Найти букет" }).press("Escape");
  await expect(page.getByLabel("Получатель", { exact: true })).toHaveValue(
    "Черновик получателя",
  );
});
