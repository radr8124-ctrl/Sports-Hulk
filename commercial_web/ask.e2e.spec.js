import { test, expect } from '@playwright/test';

test('Ask drawer and full route', async ({ page }) => {
  await page.goto('http://127.0.0.1:8510/', { waitUntil: 'networkidle' });

  const launcher = page.getByRole('button', { name: 'Ask' }).last();
  await expect(launcher).toBeVisible();
  await launcher.click();

  await expect(page.getByText('Open full analyst')).toBeVisible();
  await page.getByRole('button', { name: 'Waiver Adds' }).last().click();
  await expect(page.getByText('ANALYST TAKE').last()).toBeVisible({ timeout: 10000 });

  await page.getByText('Open full analyst').click();
  await expect(page).toHaveURL(/#ask/);
  await expect(page.getByRole('heading', { name: /Ask the Brain/i })).toBeVisible();
});
