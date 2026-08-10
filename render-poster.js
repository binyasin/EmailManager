const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 800, height: 1200 });
  await page.goto('file:///C:/Users/DELL%20LATITUDE%205520/.openclaw/workspace/poster.html', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'C:/Users/DELL LATITUDE 5520/.openclaw/workspace/poster.png', fullPage: true });
  console.log('DONE: poster.png');
  await browser.close();
})();
