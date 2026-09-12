/**
 * Render each board in boards.html to a PNG, and record its true pixel size.
 *
 * The deck places every image at its own aspect ratio rather than a guessed
 * one, so the boards are authored with a fixed width and whatever height their
 * content needs, and the sizes written here are what the builder reads back.
 *
 * Run through scripts/build_sih_deck.py, which fills the template's figures
 * from the database first.
 */
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// fileURLToPath, not `new URL(...).pathname`: this repository's path contains a
// space, and the raw pathname keeps it percent-encoded, so the renderer quietly
// wrote every PNG into a parallel "SIH%20HACKATHON" tree while the deck kept
// picking up whichever stale images were already here.
const DIR = path.dirname(fileURLToPath(import.meta.url));
const CHROME =
  process.env.DECK_CHROME ||
  `${process.env.HOME}/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome`;

const BOARDS = ["arch", "pipeline", "stack", "feas", "impact", "refs"];

const browser = await chromium.launch({
  executablePath: CHROME,
  args: ["--no-sandbox"],
});
// 2x so the images stay sharp when a slide is shown full screen or printed.
const page = await browser.newPage({
  viewport: { width: 2500, height: 1400 },
  deviceScaleFactor: 2,
});
await page.goto("file://" + path.join(DIR, "boards.html"));
// The boards use the product's own woff2 files; measuring before they load
// gives every board the fallback's metrics and the wrong height.
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(600);

fs.mkdirSync(path.join(DIR, "png"), { recursive: true });
const sizes = {};
for (const id of BOARDS) {
  const el = await page.$("#" + id);
  if (!el) throw new Error(`board #${id} is not in boards.html`);
  const box = await el.boundingBox();
  await el.screenshot({ path: path.join(DIR, "png", `${id}.png`) });
  sizes[id] = [Math.round(box.width), Math.round(box.height)];
  console.log(`  ${id.padEnd(9)} ${sizes[id][0]}x${sizes[id][1]}`);
}
fs.writeFileSync(path.join(DIR, "png", "sizes.json"), JSON.stringify(sizes, null, 1));
await browser.close();
