/**
 * Screenshot every page, so the interface can actually be looked at.
 *
 * The bundled Chromium will not start on this box: it needs libnspr4, libnss3
 * and libasound, and installing them needs root. They are extracted into
 * ~/.local/chromium-deps instead and reached through LD_LIBRARY_PATH, which
 * needs no privileges. setup:
 *
 *   npx playwright install chromium
 *   mkdir -p ~/.local/chromium-deps/debs && cd ~/.local/chromium-deps/debs
 *   apt-get download libnspr4 libnss3 libasound2t64
 *   cd .. && for d in debs/*.deb; do dpkg -x "$d" root/; done
 *
 * run (with the dev server up):
 *   cd /tmp/shotenv && npm i playwright-core
 *   LD_LIBRARY_PATH=$HOME/.local/chromium-deps/root/usr/lib/x86_64-linux-gnu \
 *     node screenshot.mjs
 *
 * Each spec is name::path[::scheme[::width]]. Reports page height, horizontal
 * overflow and console errors, which is what catches a broken layout.
 */
import { chromium } from 'playwright-core';

const CHROME = process.env.PW_CHROME
  || `${process.env.HOME}/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome`;
const BASE = process.env.BASE_URL || 'http://localhost:3000';

const DEFAULT = [
  'home::/', 'alerts::/alerts', 'signals::/signals', 'works::/projects',
  'map::/map', 'agencies::/analysis',
  'home-dark::/::dark', 'alerts-dark::/alerts::dark',
  'home-mobile::/::light::390', 'alerts-mobile::/alerts::light::390',
];

const specs = process.argv.slice(2).length ? process.argv.slice(2) : DEFAULT;
const browser = await chromium.launch({
  executablePath: CHROME,
  args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
});

let failures = 0;
for (const spec of specs) {
  const [name, path, scheme = 'light', width = '1440'] = spec.split('::');
  const ctx = await browser.newContext({
    viewport: { width: Number(width), height: 960 },
    colorScheme: scheme,
  });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 140)); });
  page.on('pageerror', e => errors.push('PAGEERROR ' + String(e).slice(0, 140)));

  await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: `/tmp/shots/${name}.png`, fullPage: true });

  const box = await page.evaluate(() => ({
    scrollW: document.documentElement.scrollWidth,
    clientW: document.documentElement.clientWidth,
    height: document.documentElement.scrollHeight,
  }));
  const overflow = box.scrollW > box.clientW + 1;
  if (overflow || errors.length) failures++;
  console.log(
    `${name.padEnd(18)} ${box.clientW}x${box.height}` +
    (overflow ? `  H-SCROLL ${box.scrollW}>${box.clientW}` : '') +
    (errors.length ? `  CONSOLE: ${errors.slice(0, 2).join(' | ')}` : '')
  );
  await ctx.close();
}
await browser.close();
process.exit(failures ? 1 : 0);
