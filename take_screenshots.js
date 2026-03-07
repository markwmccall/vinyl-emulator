const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE_URL = 'http://localhost:5555';
const OUT_DIR = path.join(__dirname, 'static', 'screenshots');

fs.mkdirSync(OUT_DIR, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1280, height: 900 });

  // Search with results loaded
  try {
    await page.goto(BASE_URL + '/', { waitUntil: 'networkidle', timeout: 10000 });
    await page.fill('#search-input', 'Radiohead');
    // Wait for search results to appear (either grid items or error)
    await page.waitForFunction(() => {
      const results = document.getElementById('results');
      return results && results.children.length > 0;
    }, { timeout: 8000 });
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(OUT_DIR, 'search_results.png') });
    console.log('✓ Search results -> search_results.png');
  } catch (err) {
    console.error(`✗ Search results: ${err.message}`);
  }

  await browser.close();
})();
