// Screenshot the onboarding mockups at 1440x900 (2x) into ./png via file:// URLs.
// Run from frontend/: NODE_PATH=node_modules node ../design-onboarding/shoot.cjs
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const pages = ["1-setup", "2-channels", "3-points", "4-first-login"];

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
