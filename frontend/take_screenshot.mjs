import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  try {
    await page.goto('http://localhost:5174/', { waitUntil: 'networkidle' });
    await page.screenshot({ path: 'screenshot1.png' });
    console.log('Saved screenshot1.png');
  } catch (err) {
    console.error(err);
  } finally {
    await browser.close();
  }
})();
