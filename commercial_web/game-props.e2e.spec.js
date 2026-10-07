import { test, expect } from '@playwright/test';

const nhlGame = {
  event_id: '401999777',
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

const nflGame = {
  sport: 'NFL',
  event_id: '401999888',
  start_time: '2026-10-09T00:15:00Z',
  away: 'Tampa Bay Buccaneers',
  away_abbr: 'TB',
  away_score: null,
  home: 'Dallas Cowboys',
  home_abbr: 'DAL',
  home_score: null,
  live: false,
  final: false,
  status: 'Thu 8:15 PM',
  source: 'ESPN Core',
  boxscore: null,
};

const baseProp = {
  lane: 'PROP',
  data_quality_grade: 'B',
  data_quality_book_count: 5,
  devig_paired_books: 4,
  market_reference_probability_pct: 51,
  v2_probability_pct: 54,
  conservative_probability_pct: 49,
  conservative_edge_pct_points: -2,
  historical_edge_confidence: 'BUILDING_SAMPLE',
  selection_rule_status: 'FORWARD_TRACKING_ONLY',
  shadow_decision: 'PASS_INSUFFICIENT_HISTORY',
};

async function openLeagueGameCenter(page, league) {
  await page.goto('http://127.0.0.1:8510/#scores', { waitUntil: 'domcontentloaded' });
  if (league !== 'NFL') await page.getByRole('button', { name: league, exact: true }).click();
  await page.getByRole('button', { name: 'Open Game Center', exact: true }).first().click();
  await page.getByRole('tab', { name: 'Props', exact: true }).click();
}

test('NHL props use exact game_key and reject another matchup', async ({ page }) => {
  await page.route('**/nhl_scores.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      status: 'READY',
      counts: { games: 1, live: 0, final: 0, upcoming: 1 },
      games: [nhlGame],
    }),
  }));

  await page.route('**/prop_v2_current.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      picks: [
        {
          ...baseProp,
          sport: 'NHL',
          event_id: 'prop-nhl-good',
          game_key: '2026-10-07|PIT|WSH',
          event_start: '2026-10-07 23:30:00+00:00',
          player: 'Alex Ovechkin',
          player_key: 'alexovechkin',
          market_subtype: 'PLAYER_TOTAL_GOALS',
          side: 'OVER',
          line: 0.5,
          american_odds: -115,
          shadow_decision: 'SHADOW_MONITOR',
          selection_rule_status: 'FORWARD_MONITOR_ONLY',
        },
        {
          ...baseProp,
          sport: 'NHL',
          event_id: 'prop-nhl-good-2',
          game_key: '2026-10-07|PIT|WSH',
          event_start: '2026-10-07 23:30:00+00:00',
          player: 'Sidney Crosby',
          player_key: 'sidneycrosby',
          market_subtype: 'PLAYER_TOTAL_ASSISTS',
          side: 'UNDER',
          line: 0.5,
          american_odds: -105,
        },
        {
          ...baseProp,
          sport: 'NHL',
          event_id: 'prop-nhl-wrong',
          game_key: '2026-10-07|COL|WPG',
          event_start: '2026-10-07 23:30:00+00:00',
          player: 'Wrong Game Player',
          player_key: 'wronggameplayer',
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

  await openLeagueGameCenter(page, 'NHL');

  await expect(page.getByRole('heading', { name: 'Player line first. Meaning second. Evidence underneath.' })).toBeVisible();
  await expect(page.getByText('Alex Ovechkin', { exact: true })).toBeVisible();
  await expect(page.getByText('Alex Ovechkin needs 1+ total goals.', { exact: true })).toBeVisible();
  await expect(page.getByText('MONITOR', { exact: true })).toBeVisible();

  await expect(page.getByText('Sidney Crosby', { exact: true })).toBeVisible();
  await expect(page.getByText('Sidney Crosby needs 0 or fewer total assists.', { exact: true })).toBeVisible();
  await expect(page.getByText('Wrong Game Player', { exact: true })).toHaveCount(0);

  const dims = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dims.scroll).toBeLessThanOrEqual(dims.client + 1);
});

test('NFL prop event UUID is admitted only after a trusted matchup bridge proves the event', async ({ page }) => {
  await page.route('**/nfl_scores.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ games: [nflGame] }),
  }));

  await page.route('**/nfl_decisions.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      props: [{
        player_dfs: 'Javonte Williams',
        away_team: 'Tampa Bay Buccaneers',
        home_team: 'Dallas Cowboys',
        start_dfs: '2026-10-09 00:15:00+00:00',
        market: 'PLAYER_TOTAL_RECEPTIONS',
        side: 'OVER',
        dfs_line: 2.5,
        sportsbook_line: 2.5,
      }],
    }),
  }));

  await page.route('**/prop_v2_current.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      picks: [
        {
          ...baseProp,
          sport: 'NFL',
          event_id: 'trusted-event',
          game_key: '',
          event_start: '2026-10-09 00:15:00+00:00',
          player: 'Javonte Williams',
          player_key: 'javontewilliams',
          market_subtype: 'PLAYER_TOTAL_RECEPTIONS',
          side: 'OVER',
          line: 2.5,
          american_odds: -130,
        },
        {
          ...baseProp,
          sport: 'NFL',
          event_id: 'trusted-event',
          game_key: '',
          event_start: '2026-10-09 00:15:00+00:00',
          player: 'CeeDee Lamb',
          player_key: 'ceedeelamb',
          market_subtype: 'PLAYER_TOTAL_REC_YARDS',
          side: 'OVER',
          line: 79.5,
          american_odds: -110,
        },
        {
          ...baseProp,
          sport: 'NFL',
          event_id: 'untrusted-same-time',
          game_key: '',
          event_start: '2026-10-09 00:15:00+00:00',
          player: 'Same Time Wrong Event',
          player_key: 'sametimewrongevent',
          market_subtype: 'PLAYER_TOTAL_REC_YARDS',
          side: 'OVER',
          line: 55.5,
          american_odds: -110,
        },
      ],
    }),
  }));

  await openLeagueGameCenter(page, 'NFL');

  await expect(page.getByText('Javonte Williams', { exact: true })).toBeVisible();
  await expect(page.getByText('CeeDee Lamb', { exact: true })).toBeVisible();
  await expect(page.getByText('Same Time Wrong Event', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Javonte Williams needs 3+ total receptions.', { exact: true })).toBeVisible();
  await expect(page.getByText('CeeDee Lamb needs 80+ total rec yards.', { exact: true })).toBeVisible();
});

test('MLB does not join props by matching start time alone', async ({ page }) => {
  const mlbGame = {
    gamePk: 900777,
    gameDate: '2026-10-08T00:00:00Z',
    away: 'Tampa Bay Rays',
    home: 'New York Yankees',
    away_score: null,
    home_score: null,
    status: 'Scheduled',
    live: false,
    final: false,
    source: 'MLB StatsAPI',
  };

  await page.route('**/mlb_scores.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ today_games: [mlbGame], next_games: [], recent_games: [] }),
  }));

  await page.route('**/prop_v2_current.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      picks: [{
        ...baseProp,
        sport: 'MLB',
        event_id: 'mlb-provider-uuid',
        game_key: '',
        event_start: '2026-10-08 00:00:00+00:00',
        player: 'Yandy Diaz',
        player_key: 'yandydiaz',
        market_subtype: 'PLAYER_TOTAL_RUNS',
        side: 'OVER',
        line: 0.5,
        american_odds: 135,
      }],
    }),
  }));

  await page.route('**/nfl_decisions.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ props: [] }),
  }));

  await page.goto('http://127.0.0.1:8510/#scores', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'MLB', exact: true }).click();
  await page.getByRole('button', { name: 'Open Game Center', exact: true }).first().click();
  await page.getByRole('tab', { name: 'Props', exact: true }).click();

  await expect(page.getByRole('heading', { name: 'No exact sportsbook props are attached to this game' })).toBeVisible();
  await expect(page.getByText('Yandy Diaz', { exact: true })).toHaveCount(0);
  await expect(page.getByText(/matching start time by itself is not enough/i)).toBeVisible();
  await expect(page.getByText(/PrizePicks remains a separate product/i)).toBeVisible();
});
