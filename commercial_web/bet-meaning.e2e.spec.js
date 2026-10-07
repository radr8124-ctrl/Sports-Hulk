import { test, expect } from '@playwright/test';

const baseRow = {
  sport: 'NFL',
  shadow_decision: 'PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE',
  calibrated_win_probability_pct: 52,
  market_reference_probability_pct: 50,
  conservative_expected_value_pct: 1.2,
  historical_edge_confidence: 'NO_INDEPENDENT_EDGE',
  selection_rule_status: 'NO_INDEPENDENT_MODEL_EDGE',
  book_count: 8,
  data_quality_grade: 'A',
};

test('Best Bets explains spread total and moneyline in plain English before evidence', async ({ page }) => {
  await page.route('**/betting_v2_all_markets_current.json*', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        summary: { candidates: 4, shadow_plays: 0, passes: 4 },
        picks: [
          {
            ...baseRow,
            game_key: 'g1',
            market: 'SPREAD',
            selection: 'Eagles',
            selection_key: 'HOME',
            line: -3.5,
            american_odds: -110,
          },
          {
            ...baseRow,
            game_key: 'g2',
            market: 'SPREAD',
            selection: 'Cowboys',
            selection_key: 'AWAY',
            line: 3.5,
            american_odds: -105,
          },
          {
            ...baseRow,
            game_key: 'g3',
            market: 'TOTAL',
            selection: 'OVER',
            selection_key: 'OVER',
            line: 47.5,
            american_odds: -110,
          },
          {
            ...baseRow,
            game_key: 'g4',
            market: 'MONEYLINE',
            selection: 'Bills',
            selection_key: 'HOME',
            line: null,
            american_odds: 130,
          },
        ],
      }),
    });
  });

  await page.goto('http://127.0.0.1:8510/#best-bets', { waitUntil: 'domcontentloaded' });

  await expect(page.getByText('Eagles -3.5', { exact: true })).toBeVisible();
  await expect(page.getByText('Eagles must win by 4 or more.', { exact: true })).toBeVisible();

  await expect(page.getByText('Cowboys +3.5', { exact: true })).toBeVisible();
  await expect(page.getByText('Cowboys can win outright or lose by 3 or fewer.', { exact: true })).toBeVisible();

  await expect(page.getByText('Over 47.5', { exact: true })).toBeVisible();
  await expect(page.getByText('The teams must combine for 48+ points.', { exact: true })).toBeVisible();

  await expect(page.getByText('Bills', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('For this moneyline to win: Bills must win the game.', { exact: true })).toBeVisible();

  await expect(page.getByText(/a \$110 practice stake would profit \$100/i).first()).toBeVisible();
  await expect(page.getByText(/a \$100 practice stake would profit \$130/i)).toBeVisible();

  const eaglesCard = page.locator('article').filter({ hasText: 'Eagles -3.5' });
  await expect(eaglesCard.getByText('Zenith probability', { exact: true })).toBeHidden();

  await eaglesCard.getByText('View evidence', { exact: true }).click();
  await expect(eaglesCard.getByText('Zenith probability', { exact: true })).toBeVisible();
  await expect(eaglesCard.getByText('Conservative EV', { exact: true })).toBeVisible();
});

test('integer spread and total explain push behavior correctly', async ({ page }) => {
  await page.route('**/betting_v2_all_markets_current.json*', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        summary: { candidates: 3, shadow_plays: 0, passes: 3 },
        picks: [
          { ...baseRow, game_key: 'p1', market: 'SPREAD', selection: 'Chiefs', selection_key: 'HOME', line: -3, american_odds: -110 },
          { ...baseRow, game_key: 'p2', market: 'SPREAD', selection: 'Raiders', selection_key: 'AWAY', line: 3, american_odds: -110 },
          { ...baseRow, game_key: 'p3', market: 'TOTAL', selection: 'UNDER', selection_key: 'UNDER', line: 47, american_odds: -110 },
        ],
      }),
    });
  });

  await page.goto('http://127.0.0.1:8510/#best-bets', { waitUntil: 'domcontentloaded' });

  await expect(page.getByText('Chiefs must win by 4 or more.', { exact: true })).toBeVisible();
  await expect(page.getByText('A 3-point win would push; winning by 4+ covers -3.', { exact: true })).toBeVisible();

  await expect(page.getByText('Raiders can win outright or lose by 2 or fewer.', { exact: true })).toBeVisible();
  await expect(page.getByText('Losing by exactly 3 would push the +3 spread.', { exact: true })).toBeVisible();

  await expect(page.getByText('The teams must combine for 46 or fewer points.', { exact: true })).toBeVisible();
  await expect(page.getByText('Exactly 47 points would push; 46 or fewer wins the Under.', { exact: true })).toBeVisible();
});
