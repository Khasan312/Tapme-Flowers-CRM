// Rebuild screenshots with Playwright's Chromium; no preview server is required.
// From the repository root: NODE_PATH=./frontend/node_modules node design-crm/shoot.cjs
// Set MOCKUP_OUTPUT_DIR to keep review images outside the tracked png/ directory.
const { chromium } = require("playwright");
const path = require("node:path");
const fs = require("node:fs");
const { pathToFileURL } = require("node:url");

const pages = ["1-chats", "2-clients", "3-client-card", "4-mobile", "5-chats-monday"];

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
      await page.screenshot({ path: path.join(out, name + ".png"), fullPage: true });
      console.log("shot", name);
    }
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
