import { expect, test } from "@playwright/test";

test("opens marketing for anonymous visitors and preserves the CRM entry", async ({
  page,
}) => {
  let authRequests = 0;
  await page.route("**/api/v1/auth/me/", async (route) => {
    authRequests++;
    await route.fulfill({ status: 403, json: { detail: "Требуется вход" } });
  });

  await page.goto("/?utm_source=preview");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "до вручения букета",
  );
  expect(authRequests).toBe(0);

  const navigation = page.getByRole("navigation", {
    name: "Основная навигация",
  });
  const product = navigation.getByRole("button", { name: "Продукт" });
  await product.click();
  await expect(
    navigation.getByRole("link", { name: "Возможности" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(product).toHaveAttribute("aria-expanded", "false");
  await expect(product).toBeFocused();

  await page.getByRole("link", { name: "Войти", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("button", { name: "Войти в CRM" })).toBeVisible();
  expect(authRequests).toBeGreaterThan(0);
  await page.goto("/?view=customers");
  await expect(page.getByRole("button", { name: "Войти в CRM" })).toBeVisible();

  await page.goto("/platform/");
  await expect(
    page.getByRole("button", { name: "Войти в панель TapMe" }),
  ).toBeVisible();
});

test("mobile visitors can use the menu, demo, FAQ and legal pages", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Основная навигация" });
  await page.getByRole("button", { name: "Открыть меню" }).click();
  await expect(nav.getByRole("link", { name: "Главная" })).toBeFocused();
  await nav.getByRole("link", { name: "Попробовать демо" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Попробуйте Tapme Flowers",
  );

  await page.getByRole("button", { name: /Данияр/ }).click();
  await page.getByRole("button", { name: "Собрать заказ" }).click();
  await expect(
    page.getByRole("heading", { name: "Черновик заказа" }),
  ).toBeVisible();
  await expect(
    page.getByText("Букет из белых роз", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Смотреть пример доставки" }).click();
  await expect(
    page.getByRole("heading", { name: "Букет уже в пути" }),
  ).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(
    390,
  );

  const footer = page.getByRole("contentinfo");
  await footer.getByRole("link", { name: "Частые вопросы" }).click();
  await page
    .getByText("Можно ли посмотреть CRM без аккаунта?", { exact: true })
    .click();
  await expect(
    page.getByText(/В примере используются вымышленные данные/),
  ).toBeVisible();

  for (const name of [
    "Политика конфиденциальности",
    "Публичная оферта",
    "Пользовательское соглашение",
  ]) {
    await footer.getByRole("link", { name }).click();
    await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
      "content",
      "noindex",
    );
  }
});
