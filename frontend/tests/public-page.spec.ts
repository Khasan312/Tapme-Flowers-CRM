import { test, expect } from "@playwright/test";

const sample = {
  number: 24,
  status: "new",
  fulfillment: "courier",
  delivery_date: "2026-10-10",
  window_start: "14:00:00",
  window_end: "16:00:00",
  shop_name: "Цветочная мастерская",
  shop_phone: "+996555000000",
  can_review: false,
};
const path = "**/api/v1/public/orders/design-preview/";

test("страница клиента: все статусы, самовывоз, доставка, телефон и уменьшение движения", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  let current = { ...sample };
  await page.route(path, (route) => route.fulfill({ json: current }));
  await page.setViewportSize({ width: 390, height: 844 });
  for (const fulfillment of ["pickup", "courier"]) {
    for (const status of [
      "new",
      "work",
      "ready",
      ...(fulfillment === "courier" ? ["route"] : []),
      "done",
      "cancelled",
    ]) {
      current = {
        ...sample,
        fulfillment,
        status,
        can_review: status === "done",
      };
      await page.goto("/track/design-preview");
      await expect(page.getByText("Заказ №24", { exact: true })).toBeVisible();
      await expect(
        page.getByRole("heading", { name: "Самовывоз", exact: true }),
      ).toHaveCount(fulfillment === "pickup" ? 1 : 0);
      const steps = page.locator(".tracking-steps li");
      await expect(steps).toHaveCount(
        status === "cancelled" ? 0 : fulfillment === "pickup" ? 3 : 4,
      );
      await expect(
        page.getByRole("button", { name: "Отправить отзыв", exact: true }),
      ).toHaveCount(status === "done" ? 1 : 0);
      if (status === "cancelled") {
        await expect(
          page.getByRole("heading", { name: "Заказ отменён", exact: true }),
        ).toBeVisible();
      } else if (status === "done") {
        await expect(page.locator(".tracking-steps .is-complete")).toHaveCount(
          fulfillment === "pickup" ? 3 : 4,
        );
        await expect(
          page.locator(".tracking-steps [aria-current=step]"),
        ).toHaveCount(0);
        for (const dot of await page.locator(".tracking-step-dot").all()) {
          const outer = await dot.boundingBox(),
            inner = await dot.locator("svg").boundingBox();
          expect(
            Math.abs(outer!.x + outer!.width / 2 - inner!.x - inner!.width / 2),
          ).toBeLessThan(1);
          expect(
            Math.abs(
              outer!.y + outer!.height / 2 - inner!.y - inner!.height / 2,
            ),
          ).toBeLessThan(1);
        }
      } else {
        await expect(
          page.locator(".tracking-steps [aria-current=step]"),
        ).toHaveCount(1);
      }
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(390);
      if (fulfillment === "courier" && status === "route") {
        await page.screenshot({
          path: `/tmp/tapme-${info.project.name}-tracking-phone.png`,
          fullPage: true,
          animations: "disabled",
        });
      }
    }
  }
  current = { ...sample, status: "done", can_review: true };
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto("/track/design-preview");
  await expect(page.getByText("Вручён", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Позвонить магазину" }),
  ).toHaveAttribute("href", "tel:+996555000000");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect
    .poll(() =>
      page
        .locator(".tracking-bouquet")
        .evaluate((el) => getComputedStyle(el).animationName),
    )
    .toBe("none");
  await page.screenshot({
    path: `/tmp/tapme-${info.project.name}-tracking-desktop.png`,
    fullPage: true,
    animations: "disabled",
  });
  await page.setViewportSize({ width: 320, height: 720 });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(320);
  expect(errors).toEqual([]);
});

test("оценка звёздами отправляет выбранное число и сохраняет отзыв при ошибке", async ({
  page,
}) => {
  let fail = true,
    reviewed = false;
  const submissions: unknown[] = [];
  await page.route(path, (route) => {
    if (route.request().method() === "POST") {
      submissions.push(route.request().postDataJSON());
      if (fail) return route.fulfill({ status: 503, json: { detail: "test" } });
      reviewed = true;
      return route.fulfill({ status: 201, json: { id: "test-review" } });
    }
    return route.fulfill({
      json: { ...sample, status: "done", can_review: !reviewed },
    });
  });
  await page.goto("/track/design-preview");
  await page.getByRole("radio", { name: "3 из 5", exact: true }).check();
  await page
    .getByRole("radio", { name: "3 из 5", exact: true })
    .press("ArrowLeft");
  await expect(
    page.getByRole("radio", { name: "2 из 5", exact: true }),
  ).toBeChecked();
  await page.getByLabel("Ваш отзыв", { exact: true }).fill("Тестовый отзыв");
  await page
    .getByRole("button", { name: "Отправить отзыв", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Сервер не смог выполнить запрос",
  );
  await expect(page.getByLabel("Ваш отзыв", { exact: true })).toHaveValue(
    "Тестовый отзыв",
  );
  expect(submissions).toEqual([{ rating: 2, message: "Тестовый отзыв" }]);
  fail = false;
  await page
    .getByRole("button", { name: "Отправить отзыв", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Магазин получил вашу оценку",
  );
  await expect(
    page.getByRole("button", { name: "Отправить отзыв", exact: true }),
  ).toHaveCount(0);
});

test("недоступная ссылка и временный сбой обновления оставляют понятный выход", async ({
  page,
}) => {
  let status = 404;
  await page.route(path, (route) =>
    route.fulfill({
      status,
      json: status === 200 ? sample : { detail: "Ссылка недоступна" },
    }),
  );
  await page.goto("/track/design-preview");
  await expect(
    page.getByRole("heading", {
      name: "Не удалось открыть заказ",
      exact: true,
    }),
  ).toBeVisible();
  status = 200;
  await page
    .getByRole("button", { name: "Попробовать снова", exact: true })
    .click();
  await expect(page.getByText("Заказ №24", { exact: true })).toBeVisible();
  status = 503;
  await page
    .getByRole("button", { name: "Обновить статус", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Сервер не смог выполнить запрос",
  );
  await expect(page.getByText("Заказ №24", { exact: true })).toBeVisible();
  status = 404;
  await page
    .getByRole("button", { name: "Обновить статус", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Не удалось открыть заказ",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText("Заказ №24", { exact: true })).toHaveCount(0);
});

test("статус меняется автоматически, скрытая и офлайн-страница не делают запросов", async ({
  page,
}) => {
  await page.clock.install({ time: 0 });
  await page.clock.pauseAt(1000);
  let current = { ...sample },
    requests = 0;
  await page.route(path, (route) => {
    requests++;
    return route.fulfill({ json: current });
  });
  await page.goto("/track/design-preview", { waitUntil: "networkidle" });
  await expect(
    page.getByRole("heading", { name: "Ваш заказ принят" }),
  ).toBeVisible();
  const initialRequests = requests;
  current = { ...sample, status: "work" };
  await page.clock.fastForward(15000);
  await expect(
    page.getByRole("heading", { name: "Собираем ваш букет" }),
  ).toBeVisible();
  expect(requests).toBe(initialRequests + 1);

  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "hidden",
    });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  current = { ...sample, status: "ready" };
  await page.clock.fastForward(60000);
  expect(requests).toBe(initialRequests + 1);
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect(
    page.getByRole("heading", { name: "Ваш букет готов" }),
  ).toBeVisible();
  expect(requests).toBe(initialRequests + 2);

  await page.evaluate(() => {
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: false,
    });
    window.dispatchEvent(new Event("offline"));
  });
  current = { ...sample, status: "route" };
  await page.clock.fastForward(60000);
  expect(requests).toBe(initialRequests + 2);
  await page.evaluate(() => {
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: true,
    });
    window.dispatchEvent(new Event("online"));
  });
  await expect(
    page.getByRole("heading", { name: "Цветы уже в пути" }),
  ).toBeVisible();
  expect(requests).toBe(initialRequests + 3);
});

test("медленный запрос не перекрывается следующими проверками", async ({
  page,
}) => {
  await page.clock.install({ time: 0 });
  await page.clock.pauseAt(1000);
  let requests = 0,
    hold = false;
  let release!: () => void;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route(path, async (route) => {
    requests++;
    if (hold) await pending;
    await route.fulfill({
      json: { ...sample, status: hold ? "work" : "new" },
    });
  });
  try {
    await page.goto("/track/design-preview", { waitUntil: "networkidle" });
    await expect(
      page.getByRole("heading", { name: "Ваш заказ принят" }),
    ).toBeVisible();
    const initialRequests = requests;
    hold = true;
    await page.clock.fastForward(15000);
    await expect.poll(() => requests).toBe(initialRequests + 1);
    await expect(
      page.getByRole("button", { name: "Обновляем статус…" }),
    ).toBeDisabled();
    await page.clock.fastForward(60000);
    expect(requests).toBe(initialRequests + 1);
    await expect(
      page.getByRole("heading", { name: "Ваш заказ принят" }),
    ).toBeVisible();
    release();
    await expect(
      page.getByRole("heading", { name: "Собираем ваш букет" }),
    ).toBeVisible();
  } finally {
    release();
    await page.unrouteAll({ behavior: "wait" });
  }
});

test("сбой сохраняет последний статус и повторяет проверку реже", async ({
  page,
}) => {
  await page.clock.install({ time: 0 });
  await page.clock.pauseAt(1000);
  let requests = 0,
    fail = false,
    current = { ...sample };
  await page.route(path, (route) => {
    requests++;
    return fail
      ? route.fulfill({ status: 503, json: {} })
      : route.fulfill({
          json: current,
        });
  });
  await page.goto("/track/design-preview", { waitUntil: "networkidle" });
  await expect(
    page.getByRole("heading", { name: "Ваш заказ принят" }),
  ).toBeVisible();
  const initialRequests = requests;
  fail = true;
  await page.clock.fastForward(15000);
  await expect(page.getByRole("alert")).toContainText("Сервер не смог");
  await expect(
    page.getByRole("heading", { name: "Ваш заказ принят" }),
  ).toBeVisible();
  await page.clock.fastForward(29999);
  expect(requests).toBe(initialRequests + 1);
  fail = false;
  current = { ...sample, status: "ready" };
  await page.clock.fastForward(1);
  await expect(
    page.getByRole("heading", { name: "Ваш букет готов" }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(requests).toBe(initialRequests + 2);
});

for (const status of ["done", "cancelled"]) {
  test(`после ${status} автоматические проверки прекращаются`, async ({
    page,
  }) => {
    await page.clock.install({ time: 0 });
    await page.clock.pauseAt(1000);
    let requests = 0,
      finished = false;
    await page.route(path, (route) => {
      requests++;
      return route.fulfill({
        json: {
          ...sample,
          status: finished ? status : "new",
          can_review: finished && status === "done",
        },
      });
    });
    await page.goto("/track/design-preview", { waitUntil: "networkidle" });
    await expect(
      page.getByRole("heading", { name: "Ваш заказ принят" }),
    ).toBeVisible();
    const initialRequests = requests;
    finished = true;
    await page.clock.fastForward(15000);
    await expect(
      page.getByRole("heading", {
        name: status === "done" ? "Букет у получателя" : "Заказ отменён",
      }),
    ).toBeVisible();
    if (status === "done")
      await page.getByLabel("Ваш отзыв", { exact: true }).fill("Мой черновик");
    await page.clock.fastForward(60000);
    expect(requests).toBe(initialRequests + 1);
    if (status === "done")
      await expect(page.getByLabel("Ваш отзыв", { exact: true })).toHaveValue(
        "Мой черновик",
      );
    await page
      .getByRole("button", { name: "Обновить статус", exact: true })
      .click();
    await expect.poll(() => requests).toBe(initialRequests + 2);
  });
}

test("отозванная ссылка скрывает заказ и останавливает автоматические запросы", async ({
  page,
}) => {
  await page.clock.install({ time: 0 });
  await page.clock.pauseAt(1000);
  let requests = 0,
    revoked = false;
  await page.route(path, (route) => {
    requests++;
    return revoked
      ? route.fulfill({ status: 404, json: { detail: "Ссылка отозвана" } })
      : route.fulfill({ json: sample });
  });
  await page.goto("/track/design-preview", { waitUntil: "networkidle" });
  await expect(page.getByText("Заказ №24", { exact: true })).toBeVisible();
  const initialRequests = requests;
  revoked = true;
  await page.clock.fastForward(15000);
  await expect(
    page.getByRole("heading", { name: "Не удалось открыть заказ" }),
  ).toBeVisible();
  await expect(page.getByText("Заказ №24", { exact: true })).toHaveCount(0);
  await page.clock.fastForward(60000);
  expect(requests).toBe(initialRequests + 1);
});
