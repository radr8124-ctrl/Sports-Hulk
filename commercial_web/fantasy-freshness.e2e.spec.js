import { test, expect } from '@playwright/test';

function fakeJwt() {
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  return `${encode({ alg: 'none', typ: 'JWT' })}.${encode({ sub: 'fresh-user', exp: now + 3600, iat: now })}.sig`;
}

async function installSession(page) {
  const token = fakeJwt();
  await page.addInitScript(() => {
    window.localStorage.setItem('sports-zenith-auth-session', '1');
    window.localStorage.setItem('sports-zenith-active-fantasy-league', 'league-fresh');
  });

  await page.route('**/api/auth/public-config', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ emailVerificationRequired: true, verificationMethod: 'code', allowSignup: true, oauthProviders: [] }),
    });
  });

  await page.route('**/api/auth/refresh', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        accessToken: token,
        user: { id: 'fresh-user', email: 'fresh-user@example.test', name: 'Fresh User' },
      }),
    });
  });
}

const team = {
  league_id: 'league-fresh',
  roster_id: 'roster-fresh',
  platform: 'manual',
  league_name: 'Freshness League',
  team_name: 'Freshness Team',
  season: 2026,
  sync_status: 'manual',
  roster: ['Josh Allen', 'CeeDee Lamb', 'Dallas Cowboys D/ST'],
  scoring: { preset: 'ppr', reception_points: 1 },
  roster_settings: { starting_slots: { qb: 1, rb: 2, wr: 2, te: 1, flex: 1, dst: 1, k: 1 }, ir_slots: 1 },
};

function freshness(status, age, rows, extras = {}) {
  return {
    lane: extras.lane || 'weekly',
    status,
    source_available: status !== 'MISSING',
    source_timestamp: '2026-10-06T23:00:00.000Z',
    age_minutes: age,
    max_age_minutes: 30,
    row_count: rows,
    row_state: status === 'MISSING' ? 'UNKNOWN' : 'HAS_ROWS',
    roster_updated_at: '2026-10-06T23:05:00.000Z',
    roster_newer_than_research: Boolean(extras.rosterNewer),
    roster_ahead_minutes: extras.rosterNewer ? 5 : 0,
  };
}

async function mockBase(page) {
  await page.route('**/api/fantasy/my-teams', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'READY', team_count: 1, teams: [team] }),
    });
  });

  await page.route('**/api/fantasy/start-sit*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'READY',
        research_freshness: freshness('FRESH', 8.2, 474, { rosterNewer: true, lane: 'weekly' }),
        league: { id: 'league-fresh', team_name: 'Freshness Team', scoring_connected: true, scoring_format: 'ppr', slot_context_connected: true },
        coverage: { roster_size: 3, matched_count: 3, unmatched_count: 0, coverage_pct: 100, decision_coverage_pct: 100 },
        groups: [],
        players: [],
        unmatched: [],
        recognized_without_decision: [],
        lineup_research: { status: 'SLOT_AWARE_RESEARCH', starter_candidates: [], bench_candidates: [], open_slots: [], unscored_slots: [], tiebreakers: [] },
        note: 'Fresh Start/Sit snapshot',
      }),
    });
  });

  await page.route('**/api/fantasy/waivers*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'READY',
        research_freshness: freshness('AGING', 44.8, 310, { lane: 'faab' }),
        league: { id: 'league-fresh', team_name: 'Freshness Team' },
        position_needs: [],
        targets: [],
        availability_cautions: [],
        budget_context: { connected: false },
        budget_context_connected: false,
      }),
    });
  });

  await page.route('**/api/fantasy/ir-stash*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'READY',
        research_freshness: freshness('STALE', 78.4, 1083, { lane: 'ir_stash' }),
        league: { id: 'league-fresh', team_name: 'Freshness Team', ir_slots: 1 },
        ir_capacity: { saved_ir_slots: 1, likely_open_slots: 1, likely_overflow_count: 0 },
        roster_injured: [],
        outside_targets_to_check: [],
        outside_source_conflicts: [],
      }),
    });
  });

  await page.route('**/api/fantasy/defense-streaming*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'READY',
        research_freshness: freshness('MISSING', null, null, { lane: 'defense_streaming' }),
        league: { id: 'league-fresh', team_name: 'Freshness Team', dst_slots: 1 },
        saved_defenses: [],
        alternatives_to_check: [],
      }),
    });
  });

  await page.route('**/api/fantasy/idp*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'READY',
        research_freshness: { ...freshness('UNKNOWN', null, null, { lane: 'idp_opportunity' }), source_available: false },
        league: { id: 'league-fresh', team_name: 'Freshness Team', idp_slots: { dl: 0, lb: 0, db: 0, idp_flex: 0 } },
        slot_aware: false,
        idp_slots: { DL: 0, LB: 0, DB: 0, IDP_FLEX: 0 },
        matched_idp: [],
        starter_candidates: [],
        bench_candidates: [],
        unavailable_roster: [],
        open_slots: [],
        group_summary: [],
        outside_targets_to_check: [],
        unmatched_idp: [],
      }),
    });
  });
}

test('personalized Fantasy lanes show real freshness states consistently', async ({ page }) => {
  await installSession(page);
  await mockBase(page);

  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'domcontentloaded' });

  await page.getByRole('button', { name: 'Start / Sit' }).click();
  await expect(page.getByText('Fresh research')).toBeVisible();
  await expect(page.getByText('updated 8 min ago')).toBeVisible();
  await expect(page.getByText('474 research rows')).toBeVisible();
  await expect(page.getByText(/Roster newer than research/)).toBeVisible();
  await expect(page.getByText(/changed 5 min after this research snapshot/)).toBeVisible();

  await page.getByRole('button', { name: 'Waivers & FAAB' }).click();
  await expect(page.getByText('Research aging')).toBeVisible();
  await expect(page.getByText('updated 45 min ago')).toBeVisible();
  await expect(page.getByText('310 research rows')).toBeVisible();

  await page.getByRole('button', { name: 'IR Stash' }).click();
  await expect(page.getByText('Research stale')).toBeVisible();
  await expect(page.getByText('updated 1.3 hr ago')).toBeVisible();

  await page.getByRole('button', { name: 'Defense', exact: true }).click();
  await expect(page.getByText('Research source missing')).toBeVisible();
  await expect(page.getByText('age unknown')).toBeVisible();

  await page.getByRole('button', { name: 'IDP', exact: true }).click();
  await expect(page.getByText('Freshness unknown')).toBeVisible();
  await expect(page.getByText('age unknown')).toBeVisible();
});
