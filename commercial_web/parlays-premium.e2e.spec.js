import { test, expect } from '@playwright/test';

const baseRow = {
  model_version: 'PARLAY_TEST',
  sport: 'NFL',
  combo_signature: 'test-combo',
  leg_count: 3,
  resolved_legs: 3,
  all_source_legs_forward_proven: false,
  correlation_status: 'CROSS_GAME_RESEARCH_INDEPENDENCE',
  joint_probability_method: 'INDEPENDENCE_PRODUCT_RESEARCH_ONLY',
  joint_v2_probability_pct: 31.4,
  joint_reference_probability_pct: 30.9,
  joint_conservative_probability_pct: 22.8,
  joint_edge_pct_points: 0.5,
  captured_parlay_american_odds: null,
  payout_status: 'NO_CAPTURED_PARLAY_PRICE',
  shadow_decision: 'PASS_UNPROVEN_SOURCE_LEG',
  shared_leg_exposure_block: false,
  shared_event_exposure_block: false,
  legs: [
    {
      kind: 'GAME',
      event: 'PHI@NYG',
      market: 'MONEYLINE',
      selection: 'Philadelphia Eagles',
      line: null,
      resolution_mode: 'EXACT_SELECTION',
      source_conservative_probability_pct: 62,
      source_shadow_decision: 'PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE',
      source_proof_ready: false,
    },
    {
      kind: 'GAME',
      event: 'BUF@MIA',
      market: 'SPREAD',
      selection: 'Buffalo Bills',
      line: -3.5,
      source_exact_line: -3.5,
      source_exact_selection: 'Buffalo Bills',
      resolution_mode: 'EXACT_SELECTION',
      source_conservative_probability_pct: 58,
      source_shadow_decision: 'PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE',
      source_proof_ready: false,
    },
    {
      kind: 'PROP',
      event: 'prop-1',
      player: 'Jalen Hurts',
      player_key: 'jalenhurts',
      market: 'PLAYER_TOTAL_PASS_YARDS',
      selection: 'OVER',
      line: 244.5,
      source_exact_line: 244.5,
      source_exact_selection: 'OVER',
      resolution_mode: 'EXACT_EVENT',
      source_conservative_probability_pct: 54,
      source_shadow_decision: 'PASS_INSUFFICIENT_HISTORY',
      source_proof_ready: false,
    },
  ],
};

function payload(row = baseRow) {
  return {
    summary: {
      candidates: 1,
      resolved_all_legs: 1,
      all_source_legs_forward_proven: row.all_source_legs_forward_proven ? 1 : 0,
      research_joint_probability_available: 1,
      captured_parlay_price: row.captured_parlay_american_odds == null ? 0 : 1,
      shadow_monitors: 0,
      passes: row.shadow_decision === 'SHADOW_PLAY' ? 0 : 1,
    },
    picks: [row],
  };
}

test('Parlay card explains every leg, weakest leg, correlation and payout risk', async ({ page }) => {
  await page.route('**/parlay_v2_current.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(payload()),
  }));

  await page.goto('http://127.0.0.1:8510/#parlays', { waitUntil: 'domcontentloaded' });

  await expect(page.getByText('NFL · 3-LEG PARLAY', { exact: true })).toBeVisible();
  await expect(page.getByText('Price not captured', { exact: true })).toBeVisible();
  await expect(page.getByText('ALL LEGS MUST WIN', { exact: true })).toBeVisible();

  await expect(page.getByText('For this moneyline to win: Philadelphia Eagles must win the game.', { exact: true })).toBeVisible();
  await expect(page.getByText('Buffalo Bills must win by 4 or more.', { exact: true })).toBeVisible();
  await expect(page.getByText('Jalen Hurts needs 245+ total pass yards.', { exact: true })).toBeVisible();

  await expect(page.getByText('WEAKEST LEG', { exact: true })).toBeVisible();
  await expect(page.getByText(/Leg 3 · Jalen Hurts · Over 244\.5 Player Total Pass Yards/i)).toBeVisible();

  await expect(page.getByText('Cross-game research', { exact: true })).toBeVisible();
  await expect(page.getByText(/independence assumption here.*not the same as measured correlation/i)).toBeVisible();

  await expect(page.getByText(/Any one losing leg loses the entire parlay/i)).toBeVisible();
  await expect(page.getByText(/3 of 3 legs still lack forward source proof/i)).toBeVisible();
  await expect(page.getByText(/combined payout has not been captured/i)).toBeVisible();

  await expect(page.getByText('Research joint', { exact: true })).toBeHidden();
  await page.getByText('View parlay evidence', { exact: true }).click();
  await expect(page.getByText('Research joint', { exact: true })).toBeVisible();
  await expect(page.getByText('31.4%', { exact: true })).toBeVisible();
});

test('Parlay card shows a captured payout without inventing a missing-price warning', async ({ page }) => {
  const proven = {
    ...baseRow,
    combo_signature: 'captured-combo',
    captured_parlay_american_odds: 620,
    payout_status: 'CAPTURED_PRICE',
    all_source_legs_forward_proven: true,
    shadow_decision: 'SHADOW_MONITOR',
    legs: baseRow.legs.map(leg => ({
      ...leg,
      source_proof_ready: true,
      source_shadow_decision: 'SHADOW_PLAY',
    })),
  };

  await page.route('**/parlay_v2_current.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(payload(proven)),
  }));

  await page.goto('http://127.0.0.1:8510/#parlays', { waitUntil: 'domcontentloaded' });

  await expect(page.getByText('+620', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('MONITOR', { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/combined payout has not been captured/i)).toHaveCount(0);
});

test('premium parlay layout stays contained on phone width', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/parlay_v2_current.json*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(payload()),
  }));

  await page.goto('http://127.0.0.1:8510/#parlays', { waitUntil: 'domcontentloaded' });
  const rule = page.getByText('ALL LEGS MUST WIN', { exact: true }).first();
  await expect(rule).toBeVisible();

  const activeTab = page.getByRole('button', { name: 'Parlays', exact: true }).first();
  await expect.poll(async () => {
    const box = await activeTab.boundingBox();
    return Boolean(box && box.x >= 0 && box.x + box.width <= 390);
  }).toBeTruthy();

  const ruleBox = await rule.boundingBox();
  expect(ruleBox?.y ?? 9999).toBeLessThan(844);

  const dims = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dims.scroll).toBeLessThanOrEqual(dims.client + 1);
});
