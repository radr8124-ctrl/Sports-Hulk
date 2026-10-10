import { test, expect } from '@playwright/test';

// Synthetic browser rows intentionally remain future dated for durable UI tests.
const testFuture=new Date(Date.now()+365*24*60*60*1000).toISOString()

const propRow = {
  lane: 'PROP',
  sport: 'NFL',
  event_id: 'prop-1',
  event_start: testFuture,
  player: 'Javonte Williams',
  player_key: 'javontewilliams',
  market_subtype: 'PLAYER_TOTAL_RUSH_YARDS',
  side: 'OVER',
  line: 72.5,
  american_odds: -114,
  v2_probability_pct: 53.27,
  market_reference_probability_pct: 53.27,
  conservative_probability_pct: 43.27,
  conservative_edge_pct_points: -10,
  data_quality_grade: 'C',
  data_quality_book_count: 5,
  historical_edge_confidence: 'INSUFFICIENT_HISTORY',
  selection_rule_status: 'INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY',
  shadow_decision: 'PASS_INSUFFICIENT_HISTORY',
};

const prizeRow = {
  lane: 'PRIZEPICKS',
  sport: 'NFL',
  event_id: 'pp-1',
  event_start: testFuture,
  player: 'Bucky Irving',
  player_key: 'buckyirving',
  market_subtype: 'PLAYER_TOTAL_RECEPTIONS',
  side: 'OVER',
  line: 2.5,
  american_odds: null,
  v2_probability_pct: 54.2,
  market_reference_probability_pct: 52.4,
  conservative_probability_pct: 49.7,
  conservative_edge_pct_points: -2.7,
  data_quality_grade: 'B',
  data_quality_book_count: 4,
  historical_edge_confidence: 'NO_INDEPENDENT_EDGE',
  selection_rule_status: 'MONITOR_FORWARD_SAMPLE',
  shadow_decision: 'SHADOW_MONITOR',
};

async function mockProps(page) {
  await page.route('**/prop_v2_current.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      summary: { candidates: 2, shadow_plays: 0, shadow_monitors: 1, passes: 1 },
      picks: [propRow, prizeRow],
    }),
  }));
}

test('sportsbook prop leads with player requirement and hides model evidence until requested', async ({ page }) => {
  await mockProps(page);
  await page.goto('http://127.0.0.1:8510/#props', { waitUntil: 'domcontentloaded' });

  const card = page.getByRole('region',{name:'Player props current line research'}).locator('[data-premium-player-card="props"]').filter({hasText:'Javonte Williams'});
  await expect(card).toBeVisible();
  await expect(card).toContainText('Over 72.5');
  await expect(card).toContainText('Javonte Williams needs 73+ total rush yards.');
  await expect(card).toContainText('Bookmaker reference -114');
  await expect(card).toContainText('Not approved as a bet');
  await expect(card.locator('details')).not.toHaveAttribute('open','');
  await card.getByText('View evidence',{exact:true}).click();
  await expect(card.locator('details')).toHaveAttribute('open','');
  await expect(card).toContainText('53.27%');
  await expect(card.getByText('Quality C',{exact:true})).toBeVisible();
});

test('PrizePicks keeps leg research separate from entry economics and does not invent a price', async ({ page }) => {
  await mockProps(page);
  await page.goto('http://127.0.0.1:8510/#prizepicks', { waitUntil: 'domcontentloaded' });

  const card = page.getByRole('region',{name:'PrizePicks current line research'}).locator('[data-premium-player-card="prizepicks"]').filter({hasText:'Bucky Irving'});
  await expect(card).toBeVisible();
  await expect(card).toContainText('MORE 2.5');
  await expect(card).toContainText('Bucky Irving needs 3+ total receptions.');
  await expect(card).toContainText('MONITOR');
  await expect(card).toContainText('Entry payout and correlation must be checked separately.');
  await expect(page.getByText('Payout proof required',{exact:true})).toBeVisible();
  await expect(card.locator('details')).not.toHaveAttribute('open','');
  await card.getByText('View evidence',{exact:true}).click();
  await expect(card).toContainText('PrizePicks leg probability is not being presented as entry EV');
});

test('PrizePicks active tab stays visible and layout stays contained on phone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockProps(page);
  await page.goto('http://127.0.0.1:8510/#prizepicks', { waitUntil: 'domcontentloaded' });

  const activeTab = page.getByRole('button', { name: 'PrizePicks', exact: true }).first();
  await expect.poll(async () => {
    const box = await activeTab.boundingBox();
    return Boolean(box && box.x >= 0 && box.x + box.width <= 390);
  }).toBeTruthy();

  const dims = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dims.scroll).toBeLessThanOrEqual(dims.client + 1);
});
