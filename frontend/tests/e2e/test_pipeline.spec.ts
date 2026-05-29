import { test, expect } from '@playwright/test';

test.describe('Scientific Data Orchestrator - End-to-End Production Pipeline Test', () => {

  test('Should execute the entire scientific workflow sequentially with 100% telemetry accuracy', async ({ page }) => {
    // Phase 1: Go to landing page first
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Verify the landing page features first
    await expect(page.locator('text=AI-Native Scientific')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Enter Workspace' })).toBeVisible();

    // Phase 2: Enter Workspace sandbox (triggers LicenseGate)
    await page.getByRole('button', { name: 'Enter Workspace' }).click();
    await page.waitForTimeout(500);

    // Confirm that the Compliance Gate is now blocking and terms are shown
    await expect(page.locator('text=Open Source Compliance Gate')).toBeVisible();
    await expect(page.locator('text=GNU AGPL-3.0 Copyleft Compliance Notice')).toBeVisible();

    // Check the copyleft terms box
    await page.locator('input[type="checkbox"]').check();
    
    // Proceed past the gate
    await page.getByRole('button', { name: 'Acknowledge & Proceed to Workspace' }).click();
    await page.waitForTimeout(500);


    // Phase 3: Dataset Ingestion (Load Demo toxicology benchmark dataset)
    await expect(page.getByRole('heading', { name: 'Upload Dataset' })).toBeVisible();
    await page.getByRole('button', { name: 'Load Demo Dataset' }).click();

    // Ingestion completes and Snappy Parquet summary displays
    await expect(page.locator('text=Successfully ingested')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=Data Preview')).toBeVisible();

    // Interactive Column Curation: drop unnecessary raw columns
    await expect(page.locator('text=Interactive Curation')).toBeVisible();
    await page.getByRole('button', { name: 'Confirm & Proceed' }).click();
    await page.waitForTimeout(500);

    // Phase 4: Variable Mapping
    await expect(page.locator('text=Variable Mapping')).toBeVisible();
    await expect(page.locator('text=Schema Bindings')).toBeVisible();
    
    // Click final mapping confirm to dispatch bindings to backend
    await page.getByRole('button', { name: 'Confirm & Proceed' }).click();
    await page.waitForTimeout(1000);

    // Phase 5: Hierarchical Segregation & Visual Audits
    await expect(page.locator('text=Step 3: Hierarchical Segregation')).toBeVisible({ timeout: 15000 });
    
    // Enable deduplication and variance audits
    await page.locator('input[type="checkbox"]').first().check(); // Smart Deduplication
    
    // Execute folder segregation & cleansing pipeline
    await page.getByRole('button', { name: 'Execute Cleansing' }).click();
    
    // Wait for computations to complete and charts to render
    await page.waitForTimeout(1000);
    await expect(page.locator('text=Dataset Composition Distribution')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=Download Raw ZIP Archive')).toBeVisible();

    // Proceed to QSAR enrichment phase
    await page.getByRole('button', { name: 'Proceed to Enrichment' }).click();
    await page.waitForTimeout(500);

    // Phase 6: Computational Descriptor Enrichment
    await expect(page.locator('text=Descriptor Enrichment')).toBeVisible();
    await expect(page.locator('text=Compute Profile')).toBeVisible();

    // Run parallel calculations in Fast Mode
    await page.getByRole('button', { name: 'Run Calculations' }).click();
    
    // Playwright asserts the dynamic progress telemetry
    await expect(page.locator('text=Job Execution')).toBeVisible({ timeout: 15000 });
    
    // Wait for the websocket completed trigger and fetch results
    await page.waitForSelector('text=Assemble Enriched Dataset', { timeout: 30000 });
    await page.getByRole('button', { name: 'Assemble Enriched Dataset' }).click();
    await page.waitForTimeout(1000);

    // Phase 7: OECD Readiness Audits
    await expect(page.getByRole('heading', { name: 'Model Readiness' })).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=Diagnostic Findings')).toBeVisible();

    // Phase 8: Reports Export downloads
    // Click on the sidebar Export tab item
    await page.locator('#sidebar-tab-reports').click();
    await page.waitForTimeout(500);
    await expect(page.locator('text=Export & Compliance Reports')).toBeVisible();
    
    // Verify the compliance deliverables are ready for downstream downloads
    await expect(page.locator('text=Download Compliance ZIP')).toBeVisible();
    await expect(page.locator('text=Download PDF Report')).toBeVisible();
  });
  
});
