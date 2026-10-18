import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { submitLogin } from "./login";

const python = resolve("../backend/.venv/bin/python");
const fixture = resolve("../backend/tests/browser_fixture.py");
let account: { username: string; password: string; business_id: string };

test.beforeEach(() => {
  account = JSON.parse(
    execFileSync(python, [fixture, "create"], { encoding: "utf8" }),
  );
});
test.afterEach(() => {
  if (account)
    execFileSync(python, [fixture, "delete"], {
      input: JSON.stringify(account),
    });
});

for (const mobile of [false, true]) {
  test(`production bundle keeps CRM path after login, navigation and reload (${mobile ? "phone" : "desktop"})`, async ({
    page,
  }) => {
    if (mobile) await page.setViewportSize({ width: 390, height: 844 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const response = await page.goto("/crm-flowers/?view=customers");
    expect(response?.status()).toBe(200);
    await submitLogin(page, account.username, account.password);
    await expect(page.locator(".app-shell")).toBeVisible();
    await expect(page.locator(".nav [aria-current=page]")).toHaveText(
      /Клиенты/,
    );
    await expect(page).toHaveURL(/\/crm-flowers\/\?.*view=customers/);
    await page
      .getByRole("button", { name: "Напоминания", exact: true })
      .click();
    await expect(page).toHaveURL(/\/crm-flowers\/\?.*view=reminders/);
    await page.reload();
    await expect(page.locator(".nav [aria-current=page]")).toHaveText(
      /Напоминания/,
    );
    await expect(page).toHaveURL(/\/crm-flowers\/\?.*view=reminders/);
    await page.goBack();
    await expect(page.locator(".nav [aria-current=page]")).toHaveText(
      /Клиенты/,
    );
    expect(errors).toEqual([]);
  });
}
