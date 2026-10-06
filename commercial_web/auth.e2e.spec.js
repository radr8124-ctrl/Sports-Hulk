import { test, expect } from '@playwright/test';

test('passwordless auth opens and reaches code step without a real email', async ({ page }) => {
  await page.route('**/api/auth/email/send-otp', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, message: 'Code sent' }),
    });
  });

  await page.goto('http://127.0.0.1:8510/', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Sign in to Sports Zenith' }).click();

  await expect(page.getByRole('heading', { name: 'Sign in to continue' })).toBeVisible();
  await expect(page.getByText('No password to remember')).toBeVisible();

  await page.getByLabel('Email address').fill('browser-test@example.com');
  await page.getByRole('button', { name: /Continue/ }).click();

  await expect(page.getByRole('heading', { name: 'Check your email' })).toBeVisible();
  await expect(page.getByLabel('Verification code')).toBeVisible();
  await expect(page.getByText(/secure 6-digit code/i)).toBeVisible();
});

test('passwordless auth uses the mobile sheet layout', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('http://127.0.0.1:8510/', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Sign in to Sports Zenith' }).click();

  const dialog = page.getByRole('dialog', { name: /Sign in to continue/i });
  await expect(dialog).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Sign in to continue' })).toBeVisible();
  await expect(page.getByLabel('Email address')).toBeVisible();
});
