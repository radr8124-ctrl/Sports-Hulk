import { test, expect } from '@playwright/test';

test('Ask carries the active fantasy league into its request context', async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('sports-zenith-active-fantasy-league', 'league-test-2');
  });

  let captured = null;
  await page.route('**/api/ask', async (route) => {
    captured = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        intent: 'personal_start_sit',
        take: 'Test personalized answer',
        confidence: 'PERSONAL ROSTER RESEARCH',
        status: 'PERSONALIZED_RESEARCH',
        why: [],
        risk: [],
        cards: [],
        sources: [],
      }),
    });
  });

  await page.goto('http://127.0.0.1:8510/#ask', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Start / Sit' }).click();

  await expect(page.getByText('Test personalized answer')).toBeVisible();
  expect(captured?.context?.fantasy_league_id).toBe('league-test-2');
  expect(captured?.question).toBe('Who should I start this week?');
});
