import { test, expect } from '@playwright/test';

test('commercial Survivor editor filters used teams', async ({ page }) => {
  await page.goto('http://127.0.0.1:8510/', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Survivor', exact: true }).click();

  const selects = page.locator('select');
  await expect(selects.first()).toBeVisible();

  const options = await selects.first().locator('option').allTextContents();
  const team = options.find(x => x && !x.includes('Choose used team'));
  expect(team).toBeTruthy();

  await selects.first().selectOption({ label: team });
  await page.getByRole('button', { name: 'Add', exact: true }).click();

  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('sports-hulk-survivor-preview') || '{}'));
  expect(stored.usedTeams).toContain(team);

  const strategyTitles = await page.locator('div.text-lg.font-black.text-slate-950').allTextContents();
  expect(strategyTitles.filter(x => x === team)).toHaveLength(0);

  const pickSelect = selects.nth(1);
  const pickOptions = await pickSelect.locator('option').allTextContents();
  expect(pickOptions).not.toContain(team);
});
