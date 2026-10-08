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

test("фото прайса: создание, карандаш справа, замена, архив и удаление фото", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const png = execFileSync(python, [
    "-c",
    "import sys; from PIL import Image; Image.new('RGB', (300, 200), 'pink').save(sys.stdout.buffer, 'PNG')",
  ]);
  const blue = execFileSync(python, [
    "-c",
    "import sys; from PIL import Image; Image.new('RGB', (300, 200), 'blue').save(sys.stdout.buffer, 'PNG')",
  ]);
  await page.goto("/");
  await submitLogin(page, account.username, account.password);
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await page.getByRole("tab", { name: "Прайс", exact: true }).click();
  await page
    .getByRole("button", { name: "Добавить позицию", exact: true })
    .click();
  await page.getByLabel("Название", { exact: true }).fill("Нежность");
  await page.getByLabel("Цена, сом", { exact: true }).fill("2500");
  await page.getByLabel("Фото букета").setInputFiles({
    name: "reference.png",
    mimeType: "image/png",
    buffer: png,
  });
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Добавить позицию", exact: true })
    .click();
  let row = page.getByRole("row").filter({
    has: page.getByRole("button", { name: "Нежность", exact: true }),
  });
  const image = row.getByRole("img", { name: "Нежность", exact: true });
  await expect(image).toBeVisible();
  await expect
    .poll(() => image.evaluate((el: HTMLImageElement) => el.naturalWidth))
    .toBeGreaterThan(0);
  const imageBounds = await image.boundingBox();
  const nameBounds = await row
    .getByRole("button", { name: "Нежность", exact: true })
    .boundingBox();
  expect(imageBounds!.x + imageBounds!.width).toBeLessThanOrEqual(
    nameBounds!.x,
  );
  const hideBounds = await row
    .getByRole("button", { name: "Скрыть Нежность", exact: true })
    .boundingBox();
  const editBounds = await row
    .getByRole("button", { name: "Изменить Нежность", exact: true })
    .boundingBox();
  expect(editBounds!.x).toBeGreaterThan(hideBounds!.x);
  await row
    .getByRole("button", { name: "Посмотреть фото Нежность", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Фото: Нежность", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Закрыть", exact: true })
    .click();
  await row
    .getByRole("button", { name: "Изменить Нежность", exact: true })
    .click();
  await page.getByLabel("Название", { exact: true }).fill("Яркий день");
  await page.getByLabel("Фото букета").setInputFiles({
    name: "invalid.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.from("bad"),
  });
  await page
    .getByRole("button", { name: "Сохранить позицию", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Файл не является допустимой фотографией",
  );
  await page
    .getByLabel("Фото букета")
    .setInputFiles({ name: "blue.png", mimeType: "image/png", buffer: blue });
  await page
    .getByRole("button", { name: "Сохранить позицию", exact: true })
    .click();
  row = page.getByRole("row").filter({
    has: page.getByRole("button", { name: "Яркий день", exact: true }),
  });
  await expect(
    row.getByRole("img", { name: "Яркий день", exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: `/tmp/tapme-catalog-photos-${info.project.name}.png`,
    fullPage: true,
  });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await row
    .getByRole("button", { name: "Скрыть Яркий день", exact: true })
    .click();
  await expect(row).toHaveCount(0);
  await page.getByRole("button", { name: "Архив", exact: true }).click();
  await row
    .getByRole("button", { name: "Вернуть Яркий день", exact: true })
    .click();
  await row
    .getByRole("button", { name: "Изменить Яркий день", exact: true })
    .click();
  await page.getByRole("button", { name: "Убрать фото", exact: true }).click();
  await page
    .getByRole("button", { name: "Сохранить позицию", exact: true })
    .click();
  await expect(row.locator("img")).toHaveCount(0);
  await page.reload();
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await page.getByRole("tab", { name: "Прайс", exact: true }).click();
  await expect(row).toBeVisible();
  await expect(row.locator("img")).toHaveCount(0);
  expect(errors).toEqual([]);
});
