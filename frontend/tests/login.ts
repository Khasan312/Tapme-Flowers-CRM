import { expect, test, type Page } from "@playwright/test";

export async function submitLogin(
  page: Page,
  username: string,
  password: string,
) {
  await page.getByLabel("Логин", { exact: true }).fill(username);
  await page.getByLabel("Пароль", { exact: true }).fill(password);
  for (let attempt = 0; attempt < 3; attempt++) {
    const [response] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.url().endsWith("/api/v1/auth/login/") &&
          r.request().method() === "POST",
      ),
      page.getByRole("button", { name: "Войти в CRM" }).click(),
    ]);
    // Multiple browser projects share localhost's login limit. Honor it without disabling it.
    if (response.status() === 429 && attempt < 2) {
      const seconds = Number(response.headers()["retry-after"]);
      expect(seconds).toBeGreaterThan(0);
      expect(seconds).toBeLessThanOrEqual(60);
      test.setTimeout(test.info().timeout + seconds * 1000 + 1000);
      await page.waitForTimeout(seconds * 1000);
      continue;
    }
    expect(response.status()).toBe(200);
    return;
  }
}
