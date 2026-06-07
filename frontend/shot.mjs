import { chromium } from '@playwright/test';
import { mkdirSync } from 'fs';
mkdirSync('/tmp/vmms-screenshots', { recursive: true });

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
const page = await ctx.newPage();
const jsErrors = [];
page.on('pageerror', e => jsErrors.push(e.message));

async function visit(url, label) {
  await page.goto(url, { waitUntil: 'networkidle', timeout: 20000 });
  await page.screenshot({ path: `/tmp/vmms-screenshots/${label}.png` });
  const h1 = await page.locator('h1').first().textContent().catch(() => 'no h1');
  const nav = await page.locator('.navbar').isVisible().catch(() => false);
  const primary = await page.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim()
  ).catch(() => 'n/a');
  console.log(`[${label.toUpperCase()}] h1="${h1.trim()}" | navbar=${nav} | --color-primary="${primary}"`);
}

await visit('http://localhost:8080/', 'home');
await visit('http://localhost:8080/register', 'register');
await visit('http://localhost:8080/login', 'login');

console.log('JS errors:', jsErrors.length ? jsErrors.join(' | ') : 'none');
await browser.close();
