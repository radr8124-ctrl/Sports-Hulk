import { test, expect } from '@playwright/test';

const game = {
  event_id: '401908620',
  league: 'NBA',
  start_time: '2026-10-08T00:00:00Z',
  away: 'Milwaukee Bucks',
  away_abbr: 'MIL',
  away_score: null,
  away_record: '0-0',
  home: 'Oklahoma City Thunder',
  home_abbr: 'OKC',
  home_score: null,
  home_record: '0-0',
  live: false,
  final: false,
  status: '10/7 - 8:00 PM EDT',
  boxscore_available: true,
};

const scorePayload = {
  status: 'READY',
  counts: { games: 1, live: 0, final: 0, upcoming: 1 },
  games: [game],
};

const devigPayload = {
  status: 'READY',
  current: {
    NBA: {
      mlAway: {
        fair_probability: 0.245,
        paired_books: 7,
        median_selected_odds: 305,
        market: 'MONEYLINE',
        selection_key: 'AWAY',
        line: null,
        event_identity: 'DATE|2026-10-08|MIL|OKC',
      },
      mlHome: {
        fair_probability: 0.755,
        paired_books: 7,
        median_selected_odds: -375,
        market: 'MONEYLINE',
        selection_key: 'HOME',
        line: null,
        event_identity: 'DATE|2026-10-08|MIL|OKC',
      },
      spreadAway: {
        fair_probability: 0.51,
        paired_books: 6,
        median_selected_odds: -108,
        market: 'SPREAD',
        selection_key: 'AWAY',
        line: 3.5,
        event_identity: 'DATE|2026-10-08|MIL|OKC',
      },
      spreadHome: {
        fair_probability: 0.49,
        paired_books: 6,
        median_selected_odds: -112,
        market: 'SPREAD',
        selection_key: 'HOME',
        line: -3.5,
        event_identity: 'DATE|2026-10-08|MIL|OKC',
      },
      spreadAwayAlt: {
        fair_probability: 0.7,
        paired_books: 2,
        median_selected_odds: -220,
        market: 'SPREAD',
        selection_key: 'AWAY',
        line: 7.5,
        event_identity: 'DATE|2026-10-08|MIL|OKC',
      },
      spreadHomeAlt: {
        fair_probability: 0.3,
        paired_books: 2,
        median_selected_odds: 180,
        market: 'SPREAD',
        selection_key: 'HOME',
        line: -7.5,
        event_identity: 'DATE|2026-10-08|MIL|OKC',
      },
      totalOver: {
        fair_probability: 0.5,
        paired_books: 5,
        median_selected_odds: -110,
        market: 'TOTAL',
        selection_key: 'OVER',
        line: 219.5,
        event_identity: 'DATE|2026-10-08|MIL|OKC',
      },
      totalUnder: {
        fair_probability: 0.5,
        paired_books: 5,
        median_selected_odds: -110,
        market: 'TOTAL',
        selection_key: 'UNDER',
        line: 219.5,
        event_identity: 'DATE|2026-10-08|MIL|OKC',
      },
      wrongGame: {
        fair_probability: 0.5,
        paired_books: 20,
        median_selected_odds: -110,
        market: 'TOTAL',
        selection_key: 'OVER',
        line: 230.5,
        event_identity: 'DATE|2026-10-08|LAL|GS',
      },
    },
  },
};

const v2Payload = {
  summary: { candidates: 2, shadow_plays: 0, passes: 2 },
  picks: [
    {
      sport: 'NBA',
      game_key: '2026-10-08|MIL|OKC',
      event_start: '2026-10-08 00:00:00+00:00',
      market: 'MONEYLINE',
      selection: 'OKC',
      selection_key: 'HOME',
      line: null,
      american_odds: -400,
      calibrated_win_probability_pct: 75.5,
      market_reference_probability_pct: 75.5,
      conservative_expected_value_pct: -4.0,
      book_count: 7,
      selection_rule_status: 'NO_INDEPENDENT_MODEL_EDGE',
      shadow_decision: 'PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE',
    },
    {
      sport: 'NBA',
      game_key: '2026-10-08|MIL|OKC',
      event_start: '2026-10-08 00:00:00+00:00',
      market: 'TOTAL',
      selection: 'OVER',
      selection_key: 'OVER',
      line: 219.5,
      american_odds: -120,
      calibrated_win_probability_pct: 52,
      market_reference_probability_pct: 50,
      conservative_expected_value_pct: -1.0,
      book_count: 5,
      selection_rule_status: 'INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY',
      shadow_decision: 'PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE',
    },
  ],
};

async function installMocks(page) {
  await page.route('**/nba_scores.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(scorePayload),
  }));
  await page.route('**/betting_v2_all_market_devig.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(devigPayload),
  }));
  await page.route('**/betting_v2_all_markets_current.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(v2Payload),
  }));
}

async function openOdds(page) {
  await page.goto('http://127.0.0.1:8510/#scores', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'NBA', exact: true }).click();
  await page.getByRole('button', { name: 'Open Game Center', exact: true }).click();
  await page.getByRole('tab', { name: 'Odds', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Understand the line before the evidence' })).toBeVisible();
}

test('Game Center Odds shows exact paired markets with plain-English interpretation', async ({ page }) => {
  await installMocks(page);
  await openOdds(page);

  await expect(page.getByText('Oklahoma City Thunder', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('For this moneyline to win: Oklahoma City Thunder must win the game.', { exact: true })).toBeVisible();

  await expect(page.getByText('Oklahoma City Thunder -3.5', { exact: true })).toBeVisible();
  await expect(page.getByText('Oklahoma City Thunder must win by 4 or more.', { exact: true })).toBeVisible();

  await expect(page.getByText('Milwaukee Bucks +3.5', { exact: true })).toBeVisible();
  await expect(page.getByText('Milwaukee Bucks can win outright or lose by 3 or fewer.', { exact: true })).toBeVisible();

  await expect(page.getByText('Over 219.5', { exact: true })).toBeVisible();
  await expect(page.getByText('The teams must combine for 220+ points.', { exact: true })).toBeVisible();
  await expect(page.getByText('Under 219.5', { exact: true })).toBeVisible();

  await expect(page.getByText('Oklahoma City Thunder -7.5', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Over 230.5', { exact: true })).toHaveCount(0);

  const okcMoneyline = page.locator('article').filter({ hasText: 'For this moneyline to win: Oklahoma City Thunder must win the game.' });
  await expect(okcMoneyline.getByText('PASS', { exact: true })).toBeVisible();
  await okcMoneyline.getByText('View market evidence', { exact: true }).click();
  await expect(okcMoneyline.getByText('De-vig fair', { exact: true })).toBeVisible();
  await expect(okcMoneyline.getByText('7', { exact: true })).toBeVisible();
  await expect(okcMoneyline.getByText(/NO INDEPENDENT MODEL EDGE/i)).toBeVisible();

  const milMoneyline = page.locator('article').filter({ hasText: 'For this moneyline to win: Milwaukee Bucks must win the game.' });
  await expect(milMoneyline.getByText('MARKET ONLY', { exact: true })).toBeVisible();
});

test('Game Center Odds stays contained on phone and rejects unmatched games', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installMocks(page);
  await openOdds(page);

  const dims = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dims.scroll).toBeLessThanOrEqual(dims.client + 1);

  await expect(page.getByText(/not a complete sportsbook board/i)).toBeVisible();
  await expect(page.getByText(/not labeled “best odds”/i)).toBeVisible();
});
