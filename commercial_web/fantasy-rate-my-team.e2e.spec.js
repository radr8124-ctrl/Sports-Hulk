import { test, expect } from '@playwright/test';

test('Fantasy opens on My Teams / Rate My Team for signed-out users', async ({ page }) => {
  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'networkidle' });
  await expect(page.getByRole('heading', { name: 'Fantasy command center' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'My Teams / Rate My Team' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Rate my team' })).toBeVisible();
  await expect(page.getByText('Sign in to save a private team')).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Roster' })).toBeVisible();
});

test('Fantasy research tabs still switch away from My Teams', async ({ page }) => {
  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Start / Sit' }).click();
  await expect(page.getByRole('heading', { name: 'Decision research' })).toBeVisible();
  await expect(page.getByText('Generic intelligence is live')).toBeVisible();
});
