import { test, expect } from '@playwright/test';

const game = {
  event_id: '401999321',
  league: 'NHL',
  start_time: '2026-10-07T23:30:00Z',
  away: 'Pittsburgh Penguins',
  away_abbr: 'PIT',
  away_score: null,
  away_record: '0-0-0',
  home: 'Washington Capitals',
  home_abbr: 'WSH',
  home_score: null,
  home_record: '0-0-0',
  live: false,
  final: false,
  status: '10/7 - 7:30 PM EDT',
  boxscore_available: true,
};

const baseGameRow = {
  sport: 'NHL',
  game_key: '2026-10-07|PIT|WSH',
  event_start: '2026-10-07 23:30:00+00:00',
  calibrated_win_probability_pct: 55,
  market_reference_probability_pct: 53,
  conservative_expected_value_pct: -1,
  book_count: 8,
  data_quality_grade: 'B',
  historical_edge_confidence: 'NO_INDEPENDENT_EDGE',
  selection_rule_status: 'NO_INDEPENDENT_MODEL_EDGE',
  shadow_decision: 'PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE',
};

const baseProp = {
  lane: 'PROP',
  sport: 'NHL',
  game_key: '2026-10-07|PIT|WSH',
  event_start: '2026-10-07 23:30:00+00:00',
  data_quality_grade: 'B',
  data_quality_book_count: 5,
  devig_paired_books: 4,
  market_reference_probability_pct: 51,
  v2_probability_pct: 54,
  conservative_probability_pct: 49,
  conservative_edge_pct_points: -2,
  historical_edge_confidence: 'INSUFFICIENT_HISTORY',
  selection_rule_status: 'INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY',
  shadow_decision: 'PASS_INSUFFICIENT_HISTORY',
};

async function installMocks(page, { play = false } = {}) {
  await page.route('**/nhl_scores.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      status: 'READY',
      counts: { games: 1, live: 0, final: 0, upcoming: 1 },
      games: [game],
    }),
  }));

  await page.route('**/betting_v2_all_markets_current.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      picks: [
        {
          ...baseGameRow,
          market: 'MONEYLINE',
          selection: 'WSH',
          selection_key: 'HOME',
          line: null,
          american_odds: -160,
          shadow_decision: play ? 'SHADOW_PLAY' : 'PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE',
          selection_rule_status: play ? 'FORWARD_PLAY_GATE_CLEARED' : 'NO_INDEPENDENT_MODEL_EDGE',
        },
        {
          ...baseGameRow,
          market: 'TOTAL',
          selection: 'OVER',
          selection_key: 'OVER',
          line: 5.5,
          american_odds: -110,
          selection_rule_status: 'INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY',
          shadow_decision: 'PASS_INSUFFICIENT_HISTORY',
        },
        {
          ...baseGameRow,
          game_key: '2026-10-07|COL|WPG',
          market: 'MONEYLINE',
          selection: 'COL',
          selection_key: 'AWAY',
          line: null,
          american_odds: -175,
        },
      ],
    }),
  }));

  await page.route('**/prop_v2_current.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      picks: [
        {
          ...baseProp,
          event_id: 'good-prop',
          player: 'Dylan Strome',
          player_key: 'dylanstrome',
          market_subtype: 'PLAYER_TOTAL_GOALS',
          side: 'UNDER',
          line: 0.5,
          american_odds: -420,
          shadow_decision: 'SHADOW_MONITOR',
          selection_rule_status: 'FORWARD_MONITOR_ONLY',
        },
        {
          ...baseProp,
          event_id: 'good-prop-2',
          player: 'Sidney Crosby',
          player_key: 'sidneycrosby',
          market_subtype: 'PLAYER_TOTAL_ASSISTS',
          side: 'OVER',
          line: 0.5,
          american_odds: -105,
        },
        {
          ...baseProp,
          game_key: '2026-10-07|COL|WPG',
          event_id: 'wrong-prop',
          player: 'Wrong Matchup Player',
          player_key: 'wrongmatchupplayer',
          market_subtype: 'PLAYER_TOTAL_GOALS',
          side: 'OVER',
          line: 0.5,
          american_odds: -110,
        },
      ],
    }),
  }));

  await page.route('**/nfl_decisions.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ props: [] }),
  }));

  await page.route('**/betting_v2_all_market_devig.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ current: { NHL: {} } }),
  }));
}

async function openZenith(page) {
  await page.goto('http://127.0.0.1:8510/#scores', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'NHL', exact: true }).click();
  await page.getByRole('button', { name: 'Open Game Center', exact: true }).click();
  await page.getByRole('tab', { name: 'Zenith', exact: true }).click();
}

test('Zenith tab summarizes exact matchup decisions without forcing a PLAY', async ({ page }) => {
  await installMocks(page);
  await openZenith(page);

  await expect(page.getByRole('heading', { name: 'Nothing is a PLAY yet. 1 item remains on MONITOR.' })).toBeVisible();
  await expect(page.getByText('2', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('PASS is an answer, not missing analysis.', { exact: false })).toBeVisible();

  const noPlaySummary = page.getByText('Why Zenith is not forcing a PLAY', { exact: true }).locator('..');
  await expect(noPlaySummary.getByText('Why Zenith is not forcing a PLAY', { exact: true })).toBeVisible();
  await expect(noPlaySummary.getByText('The market is not being beaten by an independently proven model edge.', { exact: true })).toBeVisible();
  await expect(noPlaySummary.getByText('This lane is still building enough forward evidence to earn a stronger recommendation.', { exact: true })).toBeVisible();

  await expect(page.getByText('WSH', { exact: true })).toBeVisible();
  await expect(page.getByText(/Dylan Strome/)).toBeVisible();
  await expect(page.getByText('Wrong Matchup Player', { exact: true })).toHaveCount(0);

  await page.getByRole('button', { name: 'Open Odds', exact: true }).click();
  await expect(page.getByRole('tab', { name: 'Odds', exact: true })).toHaveAttribute('aria-selected', 'true');

  await page.getByRole('tab', { name: 'Zenith', exact: true }).click();
  await page.getByRole('button', { name: 'Open Props', exact: true }).click();
  await expect(page.getByRole('tab', { name: 'Props', exact: true })).toHaveAttribute('aria-selected', 'true');
});

test('Zenith tab promotes PLAY only when an exact governed row clears', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installMocks(page, { play: true });
  await openZenith(page);

  await expect(page.getByRole('heading', { name: '1 PLAY cleared for this matchup.' })).toBeVisible();
  await expect(page.getByText('PLAY', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('Why Zenith is not forcing a PLAY', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Wrong Matchup Player', { exact: true })).toHaveCount(0);

  const dims = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dims.scroll).toBeLessThanOrEqual(dims.client + 1);
});
