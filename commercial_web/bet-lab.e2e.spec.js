import { test, expect } from '@playwright/test';

function emptyScores() {
  return { games: [], today_games: [], next_games: [], recent_games: [] };
}

async function installScoreFeeds(page, getNfl) {
  for (const sport of ['mlb', 'nba', 'nhl', 'cfb', 'cbb']) {
    await page.route(`**/${sport}_scores.json*`, route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(emptyScores()),
    }));
  }

  await page.route('**/nfl_scores.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ games: [getNfl()] }),
  }));
}

const upcomingGame = () => ({
  sport: 'NFL',
  event_id: 'practice-1',
  start_time: '2026-10-11T20:25:00Z',
  away: 'Philadelphia Eagles',
  away_abbr: 'PHI',
  away_score: null,
  home: 'Dallas Cowboys',
  home_abbr: 'DAL',
  home_score: null,
  live: false,
  final: false,
  status: 'Sun 4:25 PM',
  source: 'ESPN Core',
});

test('Bet Lab teaches and settles a practice spread from the connected final score', async ({ page }) => {
  let finalState = false;
  await installScoreFeeds(page, () => finalState ? {
    ...upcomingGame(),
    away_score: 20,
    home_score: 24,
    final: true,
    status: 'Final',
  } : upcomingGame());

  await page.goto('http://127.0.0.1:8510/#bet-lab', { waitUntil: 'domcontentloaded' });

  await expect(page.getByRole('heading', { name: /Understand it\. Test it\. Learn without risking real money/i })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Bet Lab', exact: true })).toBeVisible();

  await page.getByLabel('Bet Lab market').selectOption('SPREAD');
  await page.getByLabel('Bet Lab selection').selectOption('HOME');
  await page.getByLabel('Bet Lab line').fill('-3.5');
  await page.getByLabel('Bet Lab odds').fill('-110');

  await expect(page.getByText('Dallas Cowboys -3.5', { exact: true })).toBeVisible();
  await expect(page.getByText('Dallas Cowboys must win by 4 or more.', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'TEST THIS BET', exact: true }).click();
  await page.getByLabel('Bet Lab stake').fill('25');
  await page.getByRole('button', { name: 'ADD TO PRACTICE BANKROLL', exact: true }).click();

  await expect(page.getByText(/Practice bet added: Dallas Cowboys -3\.5 -110/i)).toBeVisible();
  await expect(page.getByText('$975.00', { exact: true })).toBeVisible();
  await expect(page.getByText('$25.00', { exact: true }).first()).toBeVisible();

  const history = page.getByRole('heading', { name: 'Bankroll history' }).locator('..').locator('..');
  await expect(page.getByText('PENDING', { exact: true })).toBeVisible();
  await expect(page.getByText('Dallas Cowboys -3.5', { exact: true }).last()).toBeVisible();

  finalState = true;
  await page.reload({ waitUntil: 'domcontentloaded' });

  await expect(page.getByText('WIN', { exact: true })).toBeVisible();
  await expect(page.getByText('$1,022.73', { exact: true })).toBeVisible();
  await expect(page.getByText('$22.73', { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/With -3\.5 applied, this spread covers/i)).toBeVisible();
});

test('Bet Lab grades an integer total landing exactly on the line as a push', async ({ page }) => {
  let finalState = false;
  await installScoreFeeds(page, () => finalState ? {
    ...upcomingGame(),
    away_score: 23,
    home_score: 24,
    final: true,
    status: 'Final',
  } : upcomingGame());

  await page.goto('http://127.0.0.1:8510/#bet-lab', { waitUntil: 'domcontentloaded' });

  await page.getByLabel('Bet Lab market').selectOption('TOTAL');
  await page.getByLabel('Bet Lab selection').selectOption('UNDER');
  await page.getByLabel('Bet Lab line').fill('47');
  await page.getByLabel('Bet Lab odds').fill('-110');

  await expect(page.getByText('The teams must combine for 46 or fewer points.', { exact: true })).toBeVisible();
  await expect(page.getByText('Exactly 47 points would push; 46 or fewer wins the Under.', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'TEST THIS BET', exact: true }).click();
  await page.getByLabel('Bet Lab stake').fill('50');
  await page.getByRole('button', { name: 'ADD TO PRACTICE BANKROLL', exact: true }).click();
  await expect(page.getByText('$950.00', { exact: true })).toBeVisible();

  finalState = true;
  await page.reload({ waitUntil: 'domcontentloaded' });

  await expect(page.getByText('PUSH', { exact: true })).toBeVisible();
  await expect(page.getByText('$1,000.00', { exact: true })).toBeVisible();
  await expect(page.getByText(/The teams combined for 47 points\. UNDER 47 pushes/i)).toBeVisible();
});

test('legacy practice route opens Bet Lab and phone layout stays contained', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installScoreFeeds(page, upcomingGame);

  await page.goto('http://127.0.0.1:8510/#practice', { waitUntil: 'domcontentloaded' });

  await expect(page.getByText('Bet Lab', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'LEARN THIS BET', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'TEST THIS BET', exact: true })).toBeVisible();

  const dims = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dims.scroll).toBeLessThanOrEqual(dims.client + 1);
});
