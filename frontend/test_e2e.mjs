import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.error(`Browser Error: ${msg.text()}`);
    }
  });
  
  try {
    console.log('Navigating to http://localhost:5173/');
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
    
    try {
      const enterBtn = await page.waitForSelector('button:has-text("Enter Workspace")', { timeout: 3000 });
      await enterBtn.click();
      await page.waitForTimeout(1000);
    } catch(e) {}
    
    try {
      const checkbox = await page.waitForSelector('input[type="checkbox"]', { timeout: 3000 });
      if (checkbox) {
        await checkbox.check();
        const licenseBtn = await page.waitForSelector('button:has-text("Acknowledge & Proceed to Workspace")', { timeout: 3000 });
        await licenseBtn.click();
        await page.waitForTimeout(1000);
      }
    } catch(e) {}
    
    console.log('Clicking Load Demo Dataset...');
    const demoBtn = await page.waitForSelector('button:has-text("Load Demo Dataset")', { timeout: 5000 });
    await demoBtn.click();
    
    console.log('Clicking Confirm & Proceed (Upload Workspace)...');
    const confirmBtn = await page.waitForSelector('button:has-text("Confirm & Proceed")', { timeout: 5000 });
    await confirmBtn.click();
    
    console.log('Waiting for mapping page to load...');
    await page.waitForSelector('text=Variable Mapping', { timeout: 10000 });
    
    console.log('Clicking Confirm & Proceed (Mapping)...');
    const mappingConfirmBtn = await page.waitForSelector('button:has-text("Confirm & Proceed")', { timeout: 5000 });
    await mappingConfirmBtn.click();
    
    console.log('Waiting for Hierarchy Builder to load...');
    await page.waitForSelector('text=Hierarchy Graph Builder', { timeout: 10000 });
    
    console.log('Taking screenshot of initial state...');
    await page.screenshot({ path: 'screenshot6_initial.png', fullPage: true });

    console.log('Clicking on some available dimensions...');
    // Find all buttons inside Available Dimensions and click the first two
    const availableBtns = await page.$$('div.glass >> text=Available Dimensions >> .. >> button');
    if (availableBtns.length > 0) {
      await availableBtns[0].click();
      await page.waitForTimeout(500);
      if (availableBtns.length > 1) {
        await availableBtns[1].click();
        await page.waitForTimeout(500);
      }
    }

    console.log('Taking screenshot of built state...');
    await page.screenshot({ path: 'screenshot7_built.png', fullPage: true });
    
    console.log('Clicking Execute...');
    const executeBtn = await page.waitForSelector('button:has-text("Execute Graph Generation")', { timeout: 5000 });
    await executeBtn.click();
    
    console.log('Waiting for Analysis Workspace...');
    // We expect the 'Analysis Workspace' title to appear once done.
    await page.waitForSelector('text=Analysis Workspace', { timeout: 30000 });
    
    // Give it a moment to render charts
    await page.waitForTimeout(3000);
    
    console.log('Taking screenshot of Analysis Workspace...');
    await page.screenshot({ path: 'screenshot8_analysis.png', fullPage: true });
    
    // Check for next steps: Data Deduplication, Chemical Enrichment, Readiness Engine
    const tabs = [
      { name: 'Deduplication', btn: 'button:has-text("Deduplication")' }, // Replace with actual side nav selector if different
      { name: 'Enrichment', btn: 'button:has-text("Enrichment")' }, // Check the actual sidebar icon for navigation
    ];
    
    // Instead of side nav, let's just use the store in the browser to switch tabs, or click the bottom navigation arrows if they exist.
    // Let's click through the left sidebar navigation icons. They might not have text.
    // So let's evaluate javascript to change the active tab in Zustand!
    console.log('Navigating to Deduplication...');
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('test-nav', { detail: 'dedup' })); // Need a way to navigate.
    });
    
    // Since I don't know the exact selectors for the sidebar, I'll look at Sidebar.tsx to find them.
    console.error('Test script encountered an error:', err);
  } finally {
    await browser.close();
  }
})();
