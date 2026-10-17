// Screenshot the v2 mockups at 1440x900 (2x) into ./png. Needs the local preview server on :8765.
// Run from frontend/: NODE_PATH=node_modules node ../design-reminders/v2/shoot.cjs
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const pages = [
  "1-list",
  "2-queue-card",
  "3-week-board",
  "4-settings-scenarios",
  "5-mobile",
];

(async () => {
  const out = path.join(__dirname, "png");
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome" });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });
  for (const name of pages) {
    await page.goto(`http://127.0.0.1:8765/v2/${name}.html`, { waitUntil: "networkidle" });
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(out, `${name}.png`) });
    console.log("shot", name);
  }
  await browser.close();
})();
