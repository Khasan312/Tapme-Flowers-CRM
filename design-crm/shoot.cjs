// Screenshot the CRM mockups at 1440x900 (2x) into ./png via file:// URLs.
// Run from frontend/: NODE_PATH=node_modules node ../design-crm/shoot.cjs
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const pages = ["1-chats", "2-clients", "3-client-card", "4-mobile"];

(async () => {
  const out = path.join(__dirname, "png");
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome" });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  for (const name of pages) {
    await page.goto("file://" + path.join(__dirname, `${name}.html`), { waitUntil: "networkidle" });
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(out, `${name}.png`) });
    console.log("shot", name);
  }
  await browser.close();
})();
