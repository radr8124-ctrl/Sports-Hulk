import { test, expect } from '@playwright/test';

function fakeJwt(subject) {
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  return `${encode({ alg: 'none', typ: 'JWT' })}.${encode({ sub: subject, exp: now + 3600, iat: now })}.test-signature`;
}

async function installSignedInSession(page) {
  const token = fakeJwt('freshness-user');
  await page.addInitScript(() => {
    window.localStorage.setItem('sports-zenith-auth-session', '1');
    window.localStorage.setItem('sports-zenith-active-fantasy-league', 'league-fresh');
  });

  await page.route('**/api/auth/public-config', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        emailVerificationRequired: true,
        verificationMethod: 'code',
        allowSignup: true,
        oauthProviders: [],
      }),
    });
  });

  await page.route('**/api/auth/refresh', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        accessToken: token,
        user: { id: 'freshness-user', email: 'freshness@example.test', name: 'Freshness User' },
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
  roster_settings: {
    starting_slots: { qb: 1, rb: 2, wr: 2, te: 1, flex: 1, dst: 1, k: 1, dl: 1, lb: 1, db: 1 },
    ir_slots: 1,
  },
};

function freshness(status, age, extra = {}) {
  return {
    lane: extra.lane || 'test',
    status,
    source_available: status !== 'MISSING',
    source_timestamp: '2026-10-06T23:00:00.000Z',
    age_minutes: age,
    max_age_minutes: 30,
    row_count: status === 'MISSING' ? 0 : 100,
    row_state: status === 'MISSING' ? 'EMPTY_REVIEW' : 'HAS_ROWS',
    manifest_checked_at: '2026-10-06T23:10:00.000Z',
    roster_updated_at: '2026-10-06T23:12:00.000Z',
    roster_newer_than_research: false,
    roster_ahead_minutes: 0,
    ...extra,
  };
}

test('Fantasy lanes display honest research freshness and roster-newer warnings', async ({ page }) => {
  await installSignedInSession(page);

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
        research_freshness: freshness('FRESH', 8, { lane: 'weekly', row_count: 474 }),
        league: {
          id: 'league-fresh',
          team_name: 'Freshness Team',
          scoring_connected: true,
          scoring_format: 'ppr',
          slot_context_connected: true,
        },
        coverage: { roster_size: 3, matched_count: 3, unmatched_count: 0, coverage_pct: 100, decision_coverage_pct: 100 },
        groups: [],
        players: [],
        unmatched: [],
        recognized_without_decision: [],
        lineup_research: {
          status: 'SLOT_AWARE_RESEARCH',
          starter_candidates: [],
          bench_candidates: [],
          open_slots: [],
          unscored_slots: [],
          tiebreakers: [],
        },
        note: 'Fresh weekly research',
      }),
    });
  });

  await page.route('**/api/fantasy/waivers*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'READY',
        research_freshness: freshness('AGING', 44, { lane: 'faab', row_count: 310 }),
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
        research_freshness: freshness('STALE', 75, { lane: 'ir_stash', row_count: 1083 }),
        league: { id: 'league-fresh', team_name: 'Freshness Team', ir_slots: 1 },
        ir_capacity: {
          saved_ir_slots: 1,
          likely_ir_designation_count: 0,
          possible_ir_eligibility_count: 0,
          likely_open_slots: 1,
          likely_overflow_count: 0,
        },
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
        research_freshness: freshness('MISSING', null, {
          lane: 'defense_streaming',
          source_available: false,
          source_timestamp: null,
          row_count: 0,
          row_state: 'EMPTY_REVIEW',
        }),
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
        research_freshness: freshness('UNKNOWN', null, {
          lane: 'idp_opportunity',
          source_timestamp: null,
          roster_newer_than_research: true,
          roster_ahead_minutes: 12.4,
          row_count: 788,
        }),
        league: {
          id: 'league-fresh',
          team_name: 'Freshness Team',
          idp_slots: { dl: 1, lb: 1, db: 1, idp_flex: 0 },
        },
        slot_aware: true,
        idp_slots: { DL: 1, LB: 1, DB: 1, IDP_FLEX: 0 },
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

  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'domcontentloaded' });

  await page.getByRole('button', { name: 'Start / Sit' }).click();
  await expect(page.getByText('Research current')).toBeVisible();
  await expect(page.getByText('8 min old')).toBeVisible();
  await expect(page.getByText('target ≤ 30 min')).toBeVisible();

  await page.getByRole('button', { name: 'Waivers & FAAB' }).click();
  await expect(page.getByText('Research aging')).toBeVisible();
  await expect(page.getByText('44 min old')).toBeVisible();

  await page.getByRole('button', { name: 'IR Stash' }).click();
  await expect(page.getByText('Research stale')).toBeVisible();
  await expect(page.getByText('1.3 hr old')).toBeVisible();

  await page.getByRole('button', { name: 'Defense', exact: true }).click();
  await expect(page.getByText('Research source missing')).toBeVisible();
  await expect(page.getByText('Source file unavailable')).toBeVisible();
  await expect(page.getByText(/Source state: EMPTY REVIEW/)).toBeVisible();

  await page.getByRole('button', { name: 'IDP', exact: true }).click();
  await expect(page.getByText('Freshness unknown')).toBeVisible();
  await expect(page.getByText(/saved roster is newer than this research snapshot/i)).toBeVisible();
  await expect(page.getByText(/about 12 min/)).toBeVisible();
});
