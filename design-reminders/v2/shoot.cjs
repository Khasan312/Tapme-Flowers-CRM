// Rebuild screenshots with Playwright's Chromium; no preview server is required.
// From the repository root: NODE_PATH=./frontend/node_modules node design-reminders/v2/shoot.cjs
// Set MOCKUP_OUTPUT_DIR to keep review images outside the tracked png/ directory.
const { chromium } = require("playwright");
const path = require("node:path");
const fs = require("node:fs");
const { pathToFileURL } = require("node:url");

const pages = ["1-list", "2-queue-card", "3-week-board", "4-settings-scenarios", "5-mobile"];

(async () => {
  const out = path.resolve(process.env.MOCKUP_OUTPUT_DIR || path.join(__dirname, "png"));
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: 2,
    });
    const pageErrors = [];
    page.on("pageerror", (error) => pageErrors.push(error));
    for (const name of pages) {
      await page.goto(pathToFileURL(path.join(__dirname, name + ".html")).href, {
        waitUntil: "networkidle",
      });
      await page.evaluate(() => document.fonts.ready);
      if (pageErrors.length) throw pageErrors[0];
      await page.screenshot({ path: path.join(out, name + ".png") });
      console.log("shot", name);
    }
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
