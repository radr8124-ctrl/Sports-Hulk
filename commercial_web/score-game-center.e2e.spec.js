import { test, expect } from '@playwright/test';

const game = {
  event_id: '401999001',
  league: 'NBA',
  start_time: '2026-10-07T23:30:00Z',
  name: 'BOS @ NYK',
  home: 'New York Knicks',
  home_abbr: 'NYK',
  home_score: 112,
  home_logo: '',
  home_record: '2-1',
  away: 'Boston Celtics',
  away_abbr: 'BOS',
  away_score: 108,
  away_logo: '',
  away_record: '3-0',
  live: false,
  final: true,
  state: 'post',
  status: 'Final',
  period: 4,
  clock: '0.0',
  venue: 'Madison Square Garden',
  broadcasts: ['ESPN'],
  source: 'ESPN NBA',
  boxscore_available: true,
};

const scorePayload = {
  status: 'READY',
  generated_at: '2026-10-07T02:00:00Z',
  counts: { games: 1, live: 0, final: 1, upcoming: 0 },
  games: [game],
};

const boxPayload = {
  league: 'NBA',
  event_id: game.event_id,
  venue: 'Madison Square Garden',
  attendance: 19812,
  teams: [
    {
      team: 'Boston Celtics',
      abbreviation: 'BOS',
      stats: [
        { label: 'FG%', value: '47.1' },
        { label: 'Rebounds', value: '44' },
        { label: 'Assists', value: '25' },
      ],
    },
    {
      team: 'New York Knicks',
      abbreviation: 'NYK',
      stats: [
        { label: 'FG%', value: '49.8' },
        { label: 'Rebounds', value: '48' },
        { label: 'Assists', value: '27' },
      ],
    },
  ],
  leaders: [
    { team: 'NYK', category: 'Points', player: 'Jalen Brunson', value: '31' },
    { team: 'BOS', category: 'Points', player: 'Jayson Tatum', value: '29' },
  ],
};

async function installScoreMocks(page) {
  await page.route('**/nba_scores.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(scorePayload),
  }));

  await page.route('**/api/boxscore?*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(boxPayload),
  }));
}

async function openNbaGameCenter(page) {
  await page.goto('http://127.0.0.1:8510/#scores', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'NBA', exact: true }).click();

  await expect(page.getByRole('heading', { name: 'NBA scores' })).toBeVisible();
  await expect(page.getByText('Boston Celtics', { exact: true })).toBeVisible();
  await expect(page.getByText('New York Knicks', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: /Open Game Center/ }).click();
  await expect(page.getByText('Game Center', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Boston Celtics @ New York Knicks' })).toBeVisible();
}

test('Game Center presents overview, real box score, and honest next-connection tabs', async ({ page }) => {
  await installScoreMocks(page);
  await openNbaGameCenter(page);

  await expect(page.getByText('Madison Square Garden', { exact: true })).toBeVisible();
  await expect(page.locator('#score-game-center').getByText('ESPN', { exact: true })).toBeVisible();

  await page.getByRole('tab', { name: 'Box Score', exact: true }).click();
  await expect(page.getByText('Jalen Brunson', { exact: true })).toBeVisible();
  await expect(page.getByText('Jayson Tatum', { exact: true })).toBeVisible();
  await expect(page.getByText('Attendance 19,812', { exact: false })).toBeVisible();

  for (const [tab, title] of [
    ['Props', 'Player props will live with the game'],
    ['Zenith', 'Sports Zenith game intelligence'],
    ['News', 'Game news and impact'],
  ]) {
    await page.getByRole('tab', { name: tab, exact: true }).click();
    await expect(page.getByRole('heading', { name: title })).toBeVisible();
    await expect(page.getByText(/no placeholder odds, props or recommendations are being invented/i)).toBeVisible();
  }
});

test('Game Center remains contained and usable on phone width', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installScoreMocks(page);
  await openNbaGameCenter(page);

  const dimensions = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client + 1);

  for (const tab of ['Overview', 'Box Score', 'Odds', 'Props', 'Zenith', 'News']) {
    const button = page.getByRole('tab', { name: tab, exact: true });
    await expect(button).toBeVisible();
    const box = await button.boundingBox();
    expect(box?.height || 0).toBeGreaterThanOrEqual(44);
  }

  await page.getByRole('tab', { name: 'Box Score', exact: true }).click();
  await expect(page.getByText('Jalen Brunson', { exact: true })).toBeVisible();

  const afterBox = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(afterBox.scroll).toBeLessThanOrEqual(afterBox.client + 1);
});

test('NFL and MLB use the same Game Center while preserving native box scores', async ({ page }) => {
  const nflGame = {
    sport: 'NFL',
    event_id: '401999100',
    start_time: '2026-10-07T20:00:00Z',
    away: 'Philadelphia Eagles',
    away_abbr: 'PHI',
    away_score: '27',
    home: 'Dallas Cowboys',
    home_abbr: 'DAL',
    home_score: '20',
    state: 'post',
    status: 'Final',
    live: false,
    final: true,
    source: 'ESPN Core',
    boxscore: {
      team_stats: {
        PHI: { firstDowns: '22', thirdDownEff: '7-13', totalYards: '402', netPassingYards: '258', rushingYards: '144', turnovers: '1', possessionTime: '31:04', sacksYardsLost: '2-13' },
        DAL: { firstDowns: '18', thirdDownEff: '5-12', totalYards: '344', netPassingYards: '232', rushingYards: '112', turnovers: '2', possessionTime: '28:56', sacksYardsLost: '3-21' },
      },
      players: {
        PHI: {
          passing: [{ name: 'Jalen Hurts', stats: { 'C/ATT': '21/30', YDS: '271', TD: '2', INT: '0', QBR: '78.1', RTG: '118.3' } }],
          rushing: [],
          receiving: [],
        },
        DAL: { passing: [], rushing: [], receiving: [] },
      },
      scoring_plays: [],
      leaders: [{ team: 'PHI', category: 'Passing', player: 'Jalen Hurts', value: '271 YDS' }],
    },
  };

  const mlbGame = {
    gamePk: 900001,
    gameDate: '2026-10-07T23:00:00Z',
    away: 'New York Yankees',
    home: 'Boston Red Sox',
    away_score: 6,
    home_score: 4,
    status: 'Final',
    live: false,
    final: true,
    source: 'MLB StatsAPI',
    boxscore: {
      away: {
        batting: [{ name: 'Aaron Judge', ab: 4, r: 2, h: 2, rbi: 3, bb: 1, so: 1, hr: 1 }],
        pitching: [],
      },
      home: {
        batting: [{ name: 'Rafael Devers', ab: 4, r: 1, h: 2, rbi: 2, bb: 0, so: 1, hr: 1 }],
        pitching: [],
      },
    },
  };

  await page.route('**/nfl_scores.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ generated_at: '2026-10-07T02:00:00Z', games: [nflGame] }),
  }));

  await page.route('**/mlb_scores.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ today_games: [mlbGame], next_games: [], recent_games: [] }),
  }));

  await page.goto('http://127.0.0.1:8510/#scores', { waitUntil: 'domcontentloaded' });

  await page.getByRole('button', { name: 'Open Game Center', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Philadelphia Eagles @ Dallas Cowboys' })).toBeVisible();
  await page.getByRole('tab', { name: 'Box Score', exact: true }).click();
  await expect(page.getByText('Jalen Hurts', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('271 YDS', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'MLB', exact: true }).click();
  await expect(page.getByText('New York Yankees', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Open Game Center', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'New York Yankees @ Boston Red Sox' })).toBeVisible();
  await page.getByRole('tab', { name: 'Box Score', exact: true }).click();
  await expect(page.getByText('Aaron Judge', { exact: true })).toBeVisible();
  await expect(page.getByText('Rafael Devers', { exact: true })).toBeVisible();

  const dimensions = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client + 1);
});
