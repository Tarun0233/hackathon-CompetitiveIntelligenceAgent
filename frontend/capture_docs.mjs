/**
 * Capture README screenshots straight to docs/.
 *
 * Run:  node capture_docs.mjs
 * Requires the backend (:8000) and Vite dev server (:5173) to be running.
 *
 * Kept in the repo because the screenshots are reproducible - anyone can
 * regenerate them after changing the UI, so docs never go stale.
 */
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const OUT = "../docs";
const URL = "http://localhost:5173/";

await mkdir(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1600, height: 950 },
});

const shot = async (name) => {
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/${name}.png` });
  console.log(`  saved ${name}.png`);
};

const ask = async (text) => {
  await page.fill(".composer__input", text);
  await page.click(".composer__send");
  await page.waitForSelector(".plan-card", { timeout: 90_000 });
};

await page.goto(URL, { waitUntil: "networkidle" });
await page.waitForTimeout(1500);

// ---- 1. Cold: no memory, generic advice -------------------------------
console.log("Cold...");
await page.locator(".stage").first().click();
await page.waitForTimeout(400);
await page.click(".sidebar .btn--primary");
await page.waitForSelector(".plan-card", { timeout: 90_000 });
await page.evaluate(() => window.scrollTo(0, 0));
await shot("cold");

// ---- 2. Full: same event, memory-backed answer ------------------------
console.log("Full...");
await page.locator(".stage").nth(2).click();
await page.waitForTimeout(400);
await page.click(".sidebar .btn--primary");
await page.waitForSelector(".plan-card", { timeout: 90_000 });
await page.evaluate(() => window.scrollTo(0, 0));
await shot("full");

// ---- 3. Live: learning cycle + before/after ---------------------------
console.log("Live learning cycle...");
await page.locator(".stage--live").click();
await page.waitForTimeout(600);
await ask(
  "Sitara Bazaar just launched free same-day home delivery above Rs 499. Should we match it?"
);
await page.fill(
  ".outcome__input",
  "Pilot in 3 zones; delivery costs 40% over budget, basket size up 6%."
);
await page.click(".decision .btn--primary");
await page.waitForSelector(".result", { timeout: 180_000 });
await page.waitForTimeout(2000);
await shot("learning-result");

await browser.close();
console.log("Done.");
