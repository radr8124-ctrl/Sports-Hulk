import { test, expect } from '@playwright/test';

const nbaGame = {
  event_id: '401999001',
  league: 'NBA',
  start_time: '2026-10-07T23:30:00Z',
  away: 'Boston Celtics',
  away_abbr: 'BOS',
  away_score: null,
  away_record: '2-0',
  home: 'New York Knicks',
  home_abbr: 'NYK',
  home_score: null,
  home_record: '1-1',
  live: false,
  final: false,
  status: '10/7 - 7:30 PM EDT',
  boxscore_available: true,
};

async function installNbaMocks(page) {
  await page.route('**/nba_scores.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      counts: { games: 1, live: 0, final: 0, upcoming: 1 },
      games: [nbaGame],
    }),
  }));

  await page.route('**/ask_retrieval.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      news_events: [
        {
          event_node_id: 'FACT:direct',
          sport: 'NBA',
          event_source_type: 'FACT',
          event_type: 'LINEUP_ROLE',
          title: 'Knicks starting lineup confirmed',
          detail: 'New York has confirmed its starting five for tonight.',
          source: 'Official NBA feed',
          source_tier: 'OFFICIAL_FACT',
          verified_status: 'OFFICIAL_LISTING',
          published_or_effective_at: '2026-10-07T22:30:00Z',
          game_event_id: 401999001,
        },
        {
          event_node_id: 'NEWS:matchup',
          sport: 'NBA',
          event_source_type: 'NEWS',
          event_type: 'RECAP',
          title: 'Boston Celtics vs. New York Knicks: what to watch',
          detail: 'Boston Celtics and New York Knicks meet tonight in New York.',
          source: 'ESPN',
          source_tier: 'EXTERNAL_NEWS',
          verified_status: 'ATTRIBUTED_NEWS_REPORT',
          published_or_effective_at: '2026-10-07T21:45:00Z',
          source_url: 'https://example.test/matchup',
          game_event_id: null,
        },
        {
          event_node_id: 'NEWS:injury',
          sport: 'NBA',
          event_source_type: 'NEWS',
          event_type: 'INJURY',
          title: 'Jayson Tatum listed questionable',
          detail: 'Boston is monitoring Jayson Tatum before tip.',
          source: 'ESPN',
          source_tier: 'EXTERNAL_NEWS',
          verified_status: 'ATTRIBUTED_NEWS_REPORT',
          published_or_effective_at: '2026-10-07T21:00:00Z',
          source_url: 'https://example.test/injury',
          game_event_id: null,
        },
        {
          event_node_id: 'NEWS:unrelated',
          sport: 'NBA',
          event_source_type: 'NEWS',
          event_type: 'INJURY',
          title: 'Lakers injury update',
          detail: 'Los Angeles Lakers injury context.',
          source: 'ESPN',
          source_tier: 'EXTERNAL_NEWS',
          verified_status: 'ATTRIBUTED_NEWS_REPORT',
          published_or_effective_at: '2026-10-07T22:50:00Z',
          game_event_id: null,
        },
        {
          event_node_id: 'FACT:wrong-game',
          sport: 'NBA',
          event_source_type: 'FACT',
          event_type: 'LINEUP_ROLE',
          title: 'Knicks lineup for another game',
          detail: 'A structured New York Knicks fact tied to a different game.',
          source: 'Official NBA feed',
          source_tier: 'OFFICIAL_FACT',
          verified_status: 'OFFICIAL_LISTING',
          published_or_effective_at: '2026-10-07T20:00:00Z',
          game_event_id: 401999999,
        },
      ],
      entity_links: [
        {
          event_node_id: 'NEWS:injury',
          sport: 'NBA',
          entity_type: 'PLAYER',
          entity_name: 'Jayson Tatum',
          entity_team: 'BOS',
          link_basis: 'EXACT_CATEGORY_PLAYER',
        },
        {
          event_node_id: 'NEWS:unrelated',
          sport: 'NBA',
          entity_type: 'TEAM',
          entity_name: 'Los Angeles Lakers',
          entity_team: 'LAL',
          link_basis: 'EXACT_CATEGORY_TEAM',
        },
        {
          event_node_id: 'FACT:wrong-game',
          sport: 'NBA',
          entity_type: 'TEAM',
          entity_name: 'New York Knicks',
          entity_team: 'NYK',
          link_basis: 'EXACT_CATEGORY_TEAM',
        },
      ],
    }),
  }));
}

async function openNbaNews(page) {
  await page.goto('http://127.0.0.1:8510/#scores', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'NBA', exact: true }).click();
  await page.getByRole('button', { name: 'Open Game Center', exact: true }).click();
  await page.getByRole('tab', { name: 'News', exact: true }).click();
}

test('Game Center News ranks direct-game matchup and team-impact context while excluding unrelated items', async ({ page }) => {
  await installNbaMocks(page);
  await openNbaNews(page);

  await expect(page.getByRole('heading', { name: 'Only context tied to this matchup' })).toBeVisible();
  await expect(page.getByText(/3 relevant items · 1 direct game · 1 matchup · 1 team impact/i)).toBeVisible();

  const direct = page.locator('article').filter({ hasText: 'Knicks starting lineup confirmed' });
  await expect(direct.getByText('DIRECT GAME', { exact: true })).toBeVisible();
  await expect(direct.getByText('OFFICIAL', { exact: true })).toBeVisible();

  const matchup = page.locator('article').filter({ hasText: 'Boston Celtics vs. New York Knicks: what to watch' });
  await expect(matchup.getByText('MATCHUP', { exact: true })).toBeVisible();
  await expect(matchup.getByText('ATTRIBUTED', { exact: true })).toBeVisible();
  await expect(matchup.getByRole('link', { name: /Read source/ })).toHaveAttribute('href', 'https://example.test/matchup');

  const injury = page.locator('article').filter({ hasText: 'Jayson Tatum listed questionable' });
  await expect(injury.getByText('TEAM IMPACT', { exact: true })).toBeVisible();
  await expect(injury.getByText('INJURY', { exact: true })).toBeVisible();

  await expect(page.getByText('Lakers injury update', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Knicks lineup for another game', { exact: true })).toHaveCount(0);
});

test('direct game ID facts work for MLB without leaking another game fact', async ({ page }) => {
  const mlbGame = {
    gamePk: 849837,
    gameDate: '2026-10-09T00:00:00Z',
    away: 'Boston Red Sox',
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

  await page.route('**/ask_retrieval.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      news_events: [
        {
          event_node_id: 'FACT:rodon',
          sport: 'MLB',
          event_source_type: 'FACT',
          event_type: 'PROBABLE_PITCHER',
          title: 'Carlos Rodón',
          detail: 'Carlos Rodón is listed as the probable pitcher for New York Yankees.',
          source: 'MLB StatsAPI',
          source_tier: 'OFFICIAL_FACT',
          verified_status: 'OFFICIAL_LISTING',
          published_or_effective_at: '2026-10-09T00:00:00Z',
          game_event_id: 849837.0,
        },
        {
          event_node_id: 'FACT:other-yankees-game',
          sport: 'MLB',
          event_source_type: 'FACT',
          event_type: 'PROBABLE_PITCHER',
          title: 'Other Yankees starter',
          detail: 'New York Yankees probable pitcher for a different game.',
          source: 'MLB StatsAPI',
          source_tier: 'OFFICIAL_FACT',
          verified_status: 'OFFICIAL_LISTING',
          published_or_effective_at: '2026-10-10T00:00:00Z',
          game_event_id: 849999.0,
        },
      ],
      entity_links: [
        {
          event_node_id: 'FACT:other-yankees-game',
          sport: 'MLB',
          entity_type: 'TEAM',
          entity_name: 'New York Yankees',
          entity_team: 'New York Yankees',
          link_basis: 'EXACT_CATEGORY_TEAM',
        },
      ],
    }),
  }));

  await page.goto('http://127.0.0.1:8510/#scores', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'MLB', exact: true }).click();
  await page.getByRole('button', { name: 'Open Game Center', exact: true }).click();
  await page.getByRole('tab', { name: 'News', exact: true }).click();

  await expect(page.getByText('Carlos Rodón', { exact: true })).toBeVisible();
  await expect(page.getByText('Other Yankees starter', { exact: true })).toHaveCount(0);
  await expect(page.getByText('DIRECT GAME', { exact: true })).toBeVisible();
});

test('Game Center News stays contained on phone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installNbaMocks(page);
  await openNbaNews(page);

  const dims = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dims.scroll).toBeLessThanOrEqual(dims.client + 1);
});
