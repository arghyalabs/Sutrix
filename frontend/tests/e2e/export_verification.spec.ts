import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Export Page Deliverables E2E Verification', () => {

  test('Execute full pipeline and verify all export deliverables', async ({ page }) => {
    test.setTimeout(210000); // 3.5 minutes total

    // Create a local downloads folder in the workspace
    const downloadsDir = path.join(__dirname, '..', 'fixtures', 'downloads');
    if (!fs.existsSync(downloadsDir)) {
      fs.mkdirSync(downloadsDir, { recursive: true });
    }

    console.log('--- Step 1: Navigating to Landing Page ---');
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    console.log('--- Step 2: Entering Workspace & Passing License Gate ---');
    await page.getByRole('button', { name: /Enter Workspace/i }).click();
    await page.waitForTimeout(500);

    await expect(page.locator('text=Open Source Compliance Gate')).toBeVisible();
    await page.locator('input[type="checkbox"]').check();
    await page.getByRole('button', { name: /Acknowledge.*Proceed|Proceed/i }).click();
    await page.waitForTimeout(500);

    console.log('--- Step 3: Loading Demo toxicology dataset ---');
    await page.getByRole('button', { name: /Load Demo/i }).click();
    await expect(page.locator('text=Successfully ingested').or(page.locator('text=Data Preview')).first()).toBeVisible({ timeout: 35000 });

    console.log('--- Step 4: Dropping columns and curating ---');
    await page.getByRole('button', { name: /Confirm.*Proceed/i }).click();
    await page.waitForTimeout(600);

    console.log('--- Step 5: Setting column mappings ---');
    await page.getByRole('button', { name: /Confirm.*Proceed/i }).click();
    await page.waitForTimeout(1000);

    console.log('--- Step 6: Setting Hierarchy & Segregating ---');
    await expect(page.locator('text=Hierarchy Graph Builder')).toBeVisible({ timeout: 20000 });

    // Select the first hierarchy column in the left panel to enable executing
    const columnBtn = page.locator('button').filter({ hasText: /Species|Endpoint|Duration|Chemical|Value/i }).first();
    const fallbackBtn = page.locator('button').nth(1); // fallback
    if (await columnBtn.isVisible().catch(() => false)) {
      await columnBtn.click();
    } else {
      await fallbackBtn.click();
    }
    await page.waitForTimeout(500);

    // Execute folder segregation & cleansing pipeline
    await page.getByRole('button', { name: 'Execute Graph Generation' }).click();
    
    // Wait for hierarchy completion - should show Continue to Analysis button
    const contAnalysisBtn = page.getByRole('button', { name: 'Continue to Analysis' });
    await expect(contAnalysisBtn).toBeVisible({ timeout: 60000 });
    await contAnalysisBtn.click();
    await page.waitForTimeout(800);

    console.log('--- Step 7: Proceeding from Analysis to Enrichment ---');
    const contEnrichmentBtn = page.getByRole('button', { name: 'Continue to Descriptor Enrichment' });
    await expect(contEnrichmentBtn).toBeVisible({ timeout: 10000 });
    await contEnrichmentBtn.click();
    await page.waitForTimeout(800);

    console.log('--- Step 8: Running Descriptor Calculations ---');
    // Click Fast Mode button
    await page.getByRole('button', { name: 'Fast Mode' }).click();
    await page.waitForTimeout(500);

    // Click the Run button (contains the number of descriptors selected, e.g. "Run (9 descriptors)")
    const runBtn = page.getByRole('button', { name: /Run \(/i });
    await expect(runBtn).toBeVisible();
    await runBtn.click();

    // Wait for the Next Step button to appear (indicating calculations completed)
    const nextStepBtn = page.getByRole('button', { name: 'Next Step' }).first();
    await expect(nextStepBtn).toBeVisible({ timeout: 60000 });
    await nextStepBtn.click();
    await page.waitForTimeout(1000);

    console.log('--- Step 9: Running AI Readiness Analysis ---');
    const runAnalysisBtn = page.getByRole('button', { name: 'Run AI Analysis' });
    await expect(runAnalysisBtn).toBeVisible({ timeout: 15000 });
    await runAnalysisBtn.click();

    // Wait for results
    await expect(page.locator('text=AI Readiness Workspace')).toBeVisible({ timeout: 45000 });
    await page.waitForTimeout(1000);

    console.log('--- Step 10: Navigating to Reports & Export Page ---');
    await page.locator('#sidebar-tab-reports').click();
    await page.waitForTimeout(1500);
    await expect(page.locator('text=Export & Reports')).toBeVisible();

    console.log('--- Step 11: Triggering and capturing downloads ---');

    // 1. Download Final Enriched Dataset (QSAR Ready)
    console.log('1. Fetching Final Enriched Dataset...');
    const parquetPromise = page.waitForEvent('download');
    await page.getByRole('link', { name: 'Download Enriched Dataset' }).click();
    const parquetDownload = await parquetPromise;
    const parquetPath = path.join(downloadsDir, 'enriched_dataset.parquet');
    await parquetDownload.saveAs(parquetPath);
    console.log(`Saved parquet file to ${parquetPath}, size: ${fs.statSync(parquetPath).size} bytes`);

    // 2. Download Raw Hierarchy Export ZIP
    console.log('2. Fetching Raw Hierarchy Export ZIP...');
    const hierarchyPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download Full Hierarchy ZIP' }).click();
    const hierarchyDownload = await hierarchyPromise;
    const hierarchyPath = path.join(downloadsDir, 'hierarchy_dataset.zip');
    await hierarchyDownload.saveAs(hierarchyPath);
    console.log(`Saved hierarchy ZIP to ${hierarchyPath}, size: ${fs.statSync(hierarchyPath).size} bytes`);

    // 3. Download Scientific Audit Report PDF
    console.log('3. Fetching Scientific Audit Report PDF...');
    const auditPromise = page.waitForEvent('download');
    await page.getByRole('link', { name: 'Download PDF Report' }).click();
    const auditDownload = await auditPromise;
    const auditPath = path.join(downloadsDir, 'audit_report.pdf');
    await auditDownload.saveAs(auditPath);
    console.log(`Saved audit report to ${auditPath}, size: ${fs.statSync(auditPath).size} bytes`);

    // 4. Download Full Compliance Package ZIP
    console.log('4. Fetching Full Compliance Package ZIP...');
    const compliancePromise = page.waitForEvent('download');
    await page.getByRole('link', { name: 'Download ZIP' }).click();
    const complianceDownload = await compliancePromise;
    const compliancePath = path.join(downloadsDir, 'compliance_package.zip');
    await complianceDownload.saveAs(compliancePath);
    console.log(`Saved compliance package to ${compliancePath}, size: ${fs.statSync(compliancePath).size} bytes`);

    console.log('--- Step 12: Testing Compound Preview Search ---');
    const searchInput = page.locator("input[placeholder*='Atenolol']");
    await expect(searchInput).toBeVisible();
    await searchInput.fill('CCO');
    await page.getByRole('button', { name: 'Search' }).click();

    // Verify search results are displayed
    await expect(page.locator('text=Matched Compound')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=SMILES Structure')).toBeVisible();
    await expect(page.locator('text=Top Calculated Descriptors')).toBeVisible();

    console.log('--- Step 13: E2E Download and Search successfully completed! ---');

    // Assert that the files exist and are not empty
    expect(fs.existsSync(parquetPath)).toBe(true);
    expect(fs.statSync(parquetPath).size).toBeGreaterThan(0);

    expect(fs.existsSync(hierarchyPath)).toBe(true);
    expect(fs.statSync(hierarchyPath).size).toBeGreaterThan(0);

    expect(fs.existsSync(auditPath)).toBe(true);
    expect(fs.statSync(auditPath).size).toBeGreaterThan(0);

    expect(fs.existsSync(compliancePath)).toBe(true);
    expect(fs.statSync(compliancePath).size).toBeGreaterThan(0);
  });
  
});
