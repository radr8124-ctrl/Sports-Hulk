import { test, expect } from '@playwright/test';

test('Fantasy opens on My Teams / Rate My Team for signed-out users', async ({ page }) => {
  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'networkidle' });
  await expect(page.getByRole('heading', { name: 'Fantasy command center' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'My Teams / Rate My Team' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Rate my team' })).toBeVisible();
  await expect(page.getByText('Sign in to save a private team')).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Roster' })).toBeVisible();
});

test('Start Sit shows personal boundary above league-wide research', async ({ page }) => {
  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Start / Sit' }).click();
  await expect(page.getByRole('heading', { name: 'Sign in for roster-aware research' })).toBeVisible();
  await expect(page.getByText('League-wide intelligence')).toBeVisible();
  await expect(page.getByText('GENERIC RESEARCH')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Decision research' })).toBeVisible();
});

test('Waivers shows personal boundary above generic FAAB research', async ({ page }) => {
  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Waivers & FAAB' }).click();
  await expect(page.getByRole('heading', { name: 'Sign in for roster-aware waiver research' })).toBeVisible();
  await expect(page.getByText('League-wide intelligence')).toBeVisible();
  await expect(page.getByText('GENERIC RESEARCH')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Decision research' })).toBeVisible();
});

test('IR Stash shows personal boundary above generic stash research', async ({ page }) => {
  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'IR Stash' }).click();
  await expect(page.getByRole('heading', { name: 'Sign in for roster-aware IR research' })).toBeVisible();
  await expect(page.getByText('League-wide intelligence')).toBeVisible();
  await expect(page.getByText('GENERIC RESEARCH')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Decision research' })).toBeVisible();
});
