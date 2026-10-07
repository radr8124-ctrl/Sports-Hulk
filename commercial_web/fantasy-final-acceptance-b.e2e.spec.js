import { test, expect } from '@playwright/test';

test.describe.configure({ timeout: 45000 });

test('DFS Lineup Lab builds allowed mode and keeps Contrarian locked without verified ownership', async ({ page }) => {
  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'domcontentloaded' });

  await page.getByRole('button', { name: 'DFS Lineup Lab', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Let the brain build the lineup.' })).toBeVisible();

  await expect(page.getByRole('button', { name: /Best Overall/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /Cash Safe/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /Tournament Upside/ })).toBeVisible();

  const contrarian = page.getByRole('button', { name: /Contrarian/ });
  await expect(contrarian).toBeVisible();
  await expect(contrarian).toBeDisabled();
  await expect(contrarian).toContainText('Unavailable · verified slate ownership required.');

  await expect(page.getByText('Ownership required', { exact: true })).toBeVisible();

  const build = page.getByRole('button', { name: 'BUILD BEST LINEUP', exact: true });
  await expect(build).toBeEnabled();
  await build.click();

  await expect(page.getByText('Optimized result', { exact: true })).toBeVisible({ timeout: 20000 });
  await expect(page.getByText('LEGAL BUILD · DRAFTKINGS', { exact: true })).toBeVisible();
  await expect(page.getByText('Best Overall lineup', { exact: true })).toBeVisible();
});

test('DFS API enforces verified-only Contrarian ownership policy', async ({ request }) => {
  for (const platform of ['DRAFTKINGS', 'FANDUEL']) {
    const response = await request.post('http://127.0.0.1:8510/api/dfs/optimize', {
      data: {
        platform,
        mode: 'CONTRARIAN',
        locked_keys: [],
        excluded_keys: [],
        alternatives: 1,
      },
    });

    expect(response.ok()).toBeTruthy();
    const body = await response.json();

    expect(body.status).toBe('MODE_UNAVAILABLE');
    expect(body.ownership_available).toBe(false);
    expect(body.verified_ownership_available).toBe(false);
    expect(body.ownership_policy).toBe('VERIFIED_ONLY_FOR_CONTRARIAN');
    expect(body.lineups || []).toHaveLength(0);
    expect(String(body.reason || '')).toContain('verified current slate ownership');
    expect(String(body.reason || '')).not.toContain('HULK');
  }
});

test('Brain Record keeps Fantasy and DFS proof labels conservative', async ({ page }) => {
  await page.goto('http://127.0.0.1:8510/#brain-record', { waitUntil: 'domcontentloaded' });

  const diagnostics = page.locator('details').filter({ hasText: 'Advanced validation' }).first();
  await expect(diagnostics).toBeVisible();
  await diagnostics.locator('summary').click();

  await expect(page.getByText('Generic research and league-specific advice are not the same thing', { exact: true })).toBeVisible();
  await expect(page.getByText('FORWARD PROOF · NO AUTO PROMOTION', { exact: true })).toBeVisible();
  await expect(page.getByText(/Review-candidate status requires at least six independent weeks/)).toBeVisible();

  await expect(page.getByText('DFS accountability', { exact: true })).toBeVisible();
  await expect(page.getByText('PRE-LOCK REPLAY', { exact: true })).toBeVisible();
  await expect(page.getByText(/None of these are real contest percentiles or cash rates/)).toBeVisible();
  await expect(page.getByText('Live-forward frozen lineups', { exact: true })).toBeVisible();
  await expect(page.getByText('Real DFS cash rate', { exact: true })).toBeVisible();
  await expect(page.getByText('WAITING', { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/Replay evidence stays separate from future live-forward results/)).toBeVisible();
});
