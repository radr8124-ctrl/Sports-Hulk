import { test, expect } from '@playwright/test';

test('Ask drawer and full route', async ({ page }) => {
  await page.goto('http://127.0.0.1:8510/', { waitUntil: 'networkidle' });

  const launcher = page.getByRole('button', { name: 'Open the Ref sports assistant' });
  await expect(launcher).toBeVisible();
  await launcher.click();

  const dialog = page.getByRole('dialog', { name: 'Ask the Ref on this page' });
  await expect(dialog.getByText('Open full analyst')).toBeVisible();
  await dialog.getByRole('button', { name: 'Waiver Adds' }).click();
  await expect(dialog.getByText(/ANALYST TAKE/).last()).toBeVisible({ timeout: 10000 });

  await dialog.getByText('Open full analyst').click();
  await expect(page).toHaveURL(/#ask/);
  await expect(page.getByRole('heading', { name: /Ask the Brain/i })).toBeVisible();
});
