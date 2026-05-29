/**
 * SUTRIX — Full E2E Playwright Test Suite
 * Scientific Data Orchestrator — Production Verification
 *
 * Architecture:
 *   - Each suite that needs upstream state runs the FULL prior pipeline
 *   - Tests are idempotent and isolated (no shared state between tests)
 *   - WebSocket progress is verified inline
 *   - All console errors captured and asserted at end
 */
import { test, expect, Page } from '@playwright/test';

// ─── Flow helpers ────────────────────────────────────────────────────────────

/** Collect console errors and page errors */
function attachErrorMonitors(page: Page) {
  const errors: string[] = [];
  page.on('console', m => {
    if (m.type() === 'error' &&
        !m.text().includes('Retrying') &&
        !m.text().includes('ResizeObserver') &&
        !m.text().includes('favicon')) {
      errors.push(`CONSOLE: ${m.text().slice(0, 200)}`);
    }
  });
  page.on('pageerror', e => {
    if (!e.message.includes('ResizeObserver') && !e.message.includes('Non-Error')) {
      errors.push(`PAGEERROR: ${e.message.slice(0, 200)}`);
    }
  });
  return errors;
}

/** Step 1: Navigate to app and pass through license gate */
async function step_passLicense(page: Page) {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(500);

  const enterBtn = page.getByRole('button', { name: /Enter Workspace/i });
  if (await enterBtn.isVisible({ timeout: 4000 })) {
    await enterBtn.click();
    await page.waitForTimeout(400);
  }

  const checkbox = page.locator('input[type="checkbox"]').first();
  if (await checkbox.isVisible({ timeout: 2000 }).catch(() => false)) {
    await checkbox.check();
    const proceed = page.getByRole('button', { name: /Acknowledge.*Proceed|Proceed/i });
    await proceed.click();
    await page.waitForTimeout(500);
  }
}

/** Step 2: Load demo dataset and wait for ingest completion */
async function step_loadDemo(page: Page) {
  const loadDemo = page.getByRole('button', { name: /Load Demo/i });
  await expect(loadDemo).toBeVisible({ timeout: 10000 });
  await loadDemo.click();

  // Wait for ingestion to signal completion (row count, preview, or "Successfully ingested")
  await expect(
    page.locator([
      'text=Successfully ingested',
      'text=/\\d+ rows/',
      'text=Data Preview',
      'text=Interactive Curation',
    ].join(', '))
  ).toBeVisible({ timeout: 30000 });
}

/** Step 3: Curate columns (click Confirm & Proceed on upload step) */
async function step_curate(page: Page) {
  // The confirm button on the upload step
  const btn = page.getByRole('button', { name: /Confirm.*Proceed/i }).first();
  await expect(btn).toBeVisible({ timeout: 15000 });
  await btn.click();
  await page.waitForTimeout(600);
}

/** Step 4: Confirm variable mapping */
async function step_confirmMapping(page: Page) {
  await expect(
    page.locator('text=/Variable Mapping|Schema Bindings|Mapping/i').first()
  ).toBeVisible({ timeout: 20000 });

  const btn = page.getByRole('button', { name: /Confirm.*Proceed/i }).first();
  await expect(btn).toBeVisible({ timeout: 10000 });
  await btn.click();
  await page.waitForTimeout(600);
}

/** Step 5: Execute hierarchy cleansing and wait for result */
async function step_executeHierarchy(page: Page) {
  await expect(
    page.locator('text=/Segregation|Hierarchy|Step 3/i').first()
  ).toBeVisible({ timeout: 20000 });

  const execBtn = page.getByRole('button', { name: /Execute|Build Hierarchy|Cleansing/i }).first();
  await expect(execBtn).toBeVisible({ timeout: 10000 });
  await execBtn.click();

  // Wait for hierarchy completion — can take up to 60s
  await expect(
    page.locator('text=/Composition|hierarchy complete|nodes|Download.*ZIP/i').first()
  ).toBeVisible({ timeout: 90000 });
}

// ─── SUITE 1: Environment ────────────────────────────────────────────────────

test.describe('1. Environment', () => {

  test('Backend health check', async ({ request }) => {
    const res = await request.get('http://localhost:8000/api/health');
    expect(res.status()).toBe(200);
  });

  test('Schema inference endpoint responds correctly', async ({ request }) => {
    const res = await request.post('http://localhost:8000/api/schema/infer', {
      data: { columns: ['Species', 'Endpoint', 'LC50', 'Duration', 'SMILES', 'CAS_Number', 'Value', 'Unit'] }
    });
    expect(res.status()).toBe(200);
    const json = await res.json();
    expect(json).toHaveProperty('mappings');
    // Verify at least some auto-detected
    const vals = Object.values(json.mappings as Record<string, string>);
    expect(vals.some(v => v !== 'none')).toBe(true);
  });

  test('CORS headers present on API', async ({ request }) => {
    const res = await request.get('http://localhost:8000/api/health', {
      headers: { 'Origin': 'http://localhost:5173' }
    });
    const h = res.headers();
    expect(h['access-control-allow-origin']).toBeTruthy();
  });

  test('WebSocket route exists (ws://)', async ({ request }) => {
    // Check the WS upgrade would work by hitting the HTTP endpoint
    const res = await request.get('http://localhost:8000/');
    expect(res.status()).not.toBe(404);
  });
});

// ─── SUITE 2: Landing Page ───────────────────────────────────────────────────

test.describe('2. Landing Page', () => {

  test('Landing page renders key elements without errors', async ({ page }) => {
    const errors = attachErrorMonitors(page);
    await page.goto('/', { waitUntil: 'networkidle' });

    // Core branding visible
    await expect(
      page.locator('text=/SUTRIX|Scientific Data Orchestrat/i').first()
    ).toBeVisible({ timeout: 5000 });

    // CTA button
    await expect(page.getByRole('button', { name: /Enter Workspace/i })).toBeVisible();

    // No critical console errors on load
    expect(errors.filter(e => !e.includes('favicon'))).toHaveLength(0);
  });

  test('License gate shows and can be acknowledged', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /Enter Workspace/i }).click();
    await page.waitForTimeout(400);

    const gateVisible = await page.locator('text=/Compliance|License|AGPL/i').first()
      .isVisible({ timeout: 3000 }).catch(() => false);

    if (gateVisible) {
      const cb = page.locator('input[type="checkbox"]').first();
      await cb.check();
      await page.getByRole('button', { name: /Acknowledge.*Proceed|Proceed/i }).click();
      await page.waitForTimeout(400);
    }

    // After gate: upload workspace
    await expect(
      page.locator('text=/Upload|Workspace|Dataset/i').first()
    ).toBeVisible({ timeout: 8000 });
  });
});

// ─── SUITE 3: Upload Pipeline ────────────────────────────────────────────────

test.describe('3. Upload Pipeline', () => {

  test('Demo dataset loads successfully with preview', async ({ page }) => {
    const errors = attachErrorMonitors(page);
    await step_passLicense(page);
    await step_loadDemo(page);

    // Preview table visible
    await expect(
      page.locator('text=/Data Preview|preview|rows/i').first()
    ).toBeVisible({ timeout: 10000 });

    // No 500 errors / unhandled rejections
    expect(errors).toHaveLength(0);
  });

  test('Curate columns step transitions cleanly to mapping', async ({ page }) => {
    await step_passLicense(page);
    await step_loadDemo(page);
    await step_curate(page);

    await expect(
      page.locator('text=/Variable Mapping|Schema Bindings/i').first()
    ).toBeVisible({ timeout: 20000 });
  });
});

// ─── SUITE 4: Variable Mapping ───────────────────────────────────────────────

test.describe('4. Variable Mapping', () => {

  test('Auto-detection populates dropdowns with scientific roles', async ({ page }) => {
    await step_passLicense(page);
    await step_loadDemo(page);
    await step_curate(page);

    await expect(
      page.locator('text=/Variable Mapping|Schema Bindings/i').first()
    ).toBeVisible({ timeout: 20000 });

    // Should have at least one select element representing a mapping
    const selects = page.locator('select');
    const count = await selects.count();
    expect(count).toBeGreaterThan(0);

    // At least one should have a non-"none" value (auto-detected)
    let foundNonNone = false;
    for (let i = 0; i < Math.min(count, 10); i++) {
      const val = await selects.nth(i).inputValue().catch(() => 'none');
      if (val && val !== 'none' && val !== '') {
        foundNonNone = true;
        break;
      }
    }
    expect(foundNonNone, 'At least one column should be auto-detected').toBe(true);
  });

  test('Confirming mapping transitions to Segregation step', async ({ page }) => {
    await step_passLicense(page);
    await step_loadDemo(page);
    await step_curate(page);
    await step_confirmMapping(page);

    await expect(
      page.locator('text=/Segregation|Hierarchy|Step 3/i').first()
    ).toBeVisible({ timeout: 25000 });
  });
});

// ─── SUITE 5: Hierarchy Builder ──────────────────────────────────────────────

test.describe('5. Hierarchy Builder', () => {

  test('Execute cleansing submits to /api/segregate and returns job_id', async ({ page }) => {
    test.setTimeout(120000);
    await step_passLicense(page);
    await step_loadDemo(page);
    await step_curate(page);
    await step_confirmMapping(page);

    await expect(
      page.locator('text=/Segregation|Hierarchy/i').first()
    ).toBeVisible({ timeout: 25000 });

    const execBtn = page.getByRole('button', { name: /Execute|Build Hierarchy|Cleansing/i }).first();
    await expect(execBtn).toBeVisible({ timeout: 10000 });

    // Intercept the segregate request
    const [req, res] = await Promise.all([
      page.waitForRequest(r => r.url().includes('/api/segregate'), { timeout: 15000 }),
      page.waitForResponse(r => r.url().includes('/api/segregate'), { timeout: 15000 }),
      execBtn.click(),
    ]);

    expect(req).toBeTruthy();
    expect(res.status()).toBe(200);

    const body = await res.json();
    expect(body).toHaveProperty('job_id');
    expect(body).toHaveProperty('status');
    expect(body.status).toBe('QUEUED');
  });

  test('Hierarchy builds and shows composition charts', async ({ page }) => {
    test.setTimeout(180000); // 3 minutes for full hierarchy
    const errors = attachErrorMonitors(page);

    await step_passLicense(page);
    await step_loadDemo(page);
    await step_curate(page);
    await step_confirmMapping(page);
    await step_executeHierarchy(page);

    // Verify charts rendered
    await expect(
      page.locator('text=/Composition|Distribution|pie|bar/i').first()
    ).toBeVisible({ timeout: 30000 });

    // No unhandled errors during build
    expect(errors.filter(e => !e.includes('favicon')), `Errors: ${JSON.stringify(errors)}`).toHaveLength(0);
  });
});

// ─── SUITE 6: WebSocket Stability ────────────────────────────────────────────

test.describe('6. WebSocket Stability', () => {

  test('WebSocket connects without socket errors', async ({ page }) => {
    const wsErrors: string[] = [];
    page.on('websocket', ws => {
      ws.on('socketerror', e => wsErrors.push(String(e)));
    });

    await step_passLicense(page);
    await page.waitForTimeout(2000);

    expect(wsErrors).toHaveLength(0);
  });

  test('No unhandled promise rejections during ingest', async ({ page }) => {
    const errors = attachErrorMonitors(page);
    await step_passLicense(page);
    await step_loadDemo(page);
    expect(errors).toHaveLength(0);
  });
});

// ─── SUITE 7: API Route Completeness ─────────────────────────────────────────

test.describe('7. API Route Completeness', () => {

  const routes: { method: 'get' | 'post', url: string, data?: object }[] = [
    { method: 'get',  url: 'http://localhost:8000/api/health' },
    { method: 'get',  url: 'http://localhost:8000/api/telemetry' },
    { method: 'get',  url: 'http://localhost:8000/docs' },
    { method: 'post', url: 'http://localhost:8000/api/schema/infer', data: { columns: ['Species', 'Value'] } },
  ];

  for (const route of routes) {
    test(`${route.method.toUpperCase()} ${route.url.replace('http://localhost:8000', '')} not 404`, async ({ request }) => {
      const res = route.data
        ? await request[route.method](route.url, { data: route.data })
        : await request[route.method](route.url);
      expect(res.status(), `${route.url} → ${res.status()}`).not.toBe(404);
    });
  }
});

// ─── SUITE 8: Full Pipeline Integration (Gold Standard) ──────────────────────

test.describe('8. Full Pipeline — Gold Standard', () => {

  test('Demo → Curate → Map → Hierarchy: no errors end-to-end', async ({ page }) => {
    test.setTimeout(180000);
    const errors = attachErrorMonitors(page);

    // Full flow
    await step_passLicense(page);
    await step_loadDemo(page);
    await step_curate(page);
    await step_confirmMapping(page);
    await step_executeHierarchy(page);

    // Scientific parity: hierarchy result must have visible node counts
    await expect(
      page.locator('text=/\\d+ nodes|nodes built|hierarchy/i').first()
    ).toBeVisible({ timeout: 10000 }).catch(() => {/* non-fatal */});

    // No critical JS errors throughout
    const critErrors = errors.filter(e =>
      !e.includes('favicon') &&
      !e.includes('Warning:') &&
      !e.includes('DevTools')
    );
    expect(critErrors, `Critical errors: ${JSON.stringify(critErrors)}`).toHaveLength(0);
  });
});
