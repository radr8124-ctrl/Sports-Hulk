import { test, expect } from '@playwright/test';

function fakeJwt(subject) {
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  return `${encode({ alg: 'none', typ: 'JWT' })}.${encode({ sub: subject, exp: now + 3600, iat: now })}.test-signature`;
}

async function installSignedInSession(page) {
  const token = fakeJwt('consistency-user');
  await page.addInitScript(() => {
    window.localStorage.setItem('sports-zenith-auth-session', '1');
    window.localStorage.setItem('sports-zenith-active-fantasy-league', 'league-consistency');
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
        user: { id: 'consistency-user', email: 'consistency@example.test', name: 'Consistency User' },
      }),
    });
  });
}

const team = {
  league_id: 'league-consistency',
  roster_id: 'roster-consistency',
  platform: 'manual',
  league_name: 'Consistency League',
  team_name: 'Consistency Team',
  season: 2026,
  sync_status: 'manual',
  roster: ['Test QB', 'Test WR', 'Test D/ST', 'Test LB'],
  scoring: { preset: 'ppr', reception_points: 1, faab_budget: 100, faab_remaining: 70 },
  roster_settings: {
    starting_slots: { qb: 1, rb: 2, wr: 2, te: 1, flex: 1, dst: 1, k: 1, lb: 1 },
    ir_slots: 1,
  },
};

const fresh = {
  lane: 'test',
  status: 'FRESH',
  source_available: true,
  source_timestamp: '2026-10-06T23:00:00.000Z',
  age_minutes: 5,
  max_age_minutes: 30,
  row_count: 10,
  row_state: 'HAS_ROWS',
  roster_newer_than_research: false,
  roster_ahead_minutes: 0,
};

test('generic and personalized Fantasy use one metric and status vocabulary', async ({ page }) => {
  await installSignedInSession(page);

  await page.route('**/api/fantasy/my-teams', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'READY', team_count: 1, teams: [team] }),
    });
  });

  let genericDecisionHits = 0
  await page.route('**/fantasy_decisions.json*', async (route) => {
    genericDecisionHits += 1
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'READY',
        personalization: {},
        lanes: {
          weekly: {
            source_rows: 1,
            rows: [{
              sport: 'NFL',
              player: 'Generic Sit Player',
              team: 'TST',
              position: 'WR',
              opponent: 'OPP',
              role_signal: 'ROLE_FLAT',
              snap_pct: 61,
              weekly_research_score: 41,
              weekly_tier: 'SIT_CAUTION',
              ros_research_score: 50,
              research_reasons: 'Consistency fixture',
            }],
          },
          faab: {
            source_rows: 1,
            rows: [{
              sport: 'NFL',
              player: 'Generic Waiver Player',
              team: 'TST',
              position: 'WR',
              waiver_research_score: 76,
              waiver_priority: 'STRONG_ADD',
              suggested_faab_low_pct: 8,
              suggested_faab_high_pct: 14,
              adds_24h: 1200,
            }],
          },
          ir_stash: {
            source_rows: 1,
            rows: [{
              sport: 'NFL',
              player: 'Generic Stash Player',
              team: 'TST',
              status: 'IR',
              injury_type: 'Knee',
              return_window: '2_4_WEEKS',
              stash_research_score: 72,
              stash_tier: 'REVIEW_STASH',
              source_count: 2,
            }],
          },
          defense_streaming: {
            source_rows: 1,
            rows: [{
              sport: 'NFL',
              team: 'TST',
              dst_player: 'TST D/ST',
              next_opponent: 'OPP',
              next_side: 'HOME',
              rest_days: 7,
              future_schedule_signal: 'BALANCED',
              weekly_stream_score: 66,
              weekly_stream_tier: 'STREAM',
              multiweek_hold_score: 61,
              multiweek_hold_tier: 'SHORT_HOLD',
            }],
          },
          idp: {
            source_rows: 1,
            rows: [{
              sport: 'NFL',
              player: 'Generic IDP Player',
              team: 'TST',
              position: 'LB',
              idp_group: 'LB',
              snap_pct: 1,
              snap_pct_change: 0.25,
              role_signal: 'ROLE_UP',
              next_opponent: 'OPP',
              idp_usage_score: 81,
              idp_usage_tier: 'IDP_STRONG_USAGE',
            }],
          },
        },
      }),
    });
  });

  await page.route('**/api/fantasy/start-sit*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'READY',
        research_freshness: { ...fresh, lane: 'weekly' },
        league: {
          id: 'league-consistency',
          team_name: 'Consistency Team',
          scoring_connected: true,
          scoring_format: 'ppr',
          slot_context_connected: false,
        },
        coverage: { roster_size: 1, matched_count: 1, unmatched_count: 0, coverage_pct: 100, decision_coverage_pct: 100 },
        groups: [{
          position: 'WR',
          count: 1,
          players: [{
            player: 'Private WR',
            team: 'TST',
            position: 'WR',
            opponent: 'OPP',
            weekly_research_score: 77,
            ros_research_score: 69,
            weekly_tier: 'START_LEAN',
            role_signal: 'ROLE_UP',
            roster_position_rank: 1,
            roster_position_count: 1,
          }],
        }],
        players: [],
        unmatched: [],
        recognized_without_decision: [],
        lineup_research: {
          status: 'SLOT_CONTEXT_WAITING',
          starter_candidates: [],
          bench_candidates: [],
          open_slots: [],
          unscored_slots: [],
          tiebreakers: [],
        },
        note: 'Consistency fixture',
      }),
    });
  });

  await page.route('**/api/fantasy/waivers*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'READY',
        research_freshness: { ...fresh, lane: 'faab' },
        league: { id: 'league-consistency', team_name: 'Consistency Team' },
        position_needs: [{ position: 'WR', roster_need_score: 70, roster_need_tier: 'NEED', roster_count: 1 }],
        targets: [{
          player: 'Private Waiver Player',
          team: 'TST',
          position: 'WR',
          player_status: 'AVAILABLE',
          availability_status: 'AVAILABLE',
          roster_fit_research_score: 80,
          waiver_research_score: 78,
          roster_need_score: 70,
          waiver_priority: 'STRONG_ADD',
          research_faab_low_pct: 9,
          research_faab_high_pct: 15,
          budget_planning: { connected: false },
        }],
        availability_cautions: [{ player: 'Questionable Player', player_status: 'QUESTIONABLE', availability_status: 'QUESTIONABLE' }],
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
        research_freshness: { ...fresh, lane: 'ir_stash' },
        league: { id: 'league-consistency', team_name: 'Consistency Team', ir_slots: 1 },
        ir_capacity: { saved_ir_slots: 1, likely_open_slots: 1, likely_overflow_count: 0 },
        roster_injured: [{
          player: 'Private Stash Player',
          team: 'TST',
          position: 'WR',
          status: 'IR',
          stash_research_score: 74,
          source_count: 2,
          roster_action_research: 'IR_STASH_RESEARCH',
          ir_capacity_class: 'LIKELY_IR_DESIGNATION',
          return_window: '2_4_WEEKS',
        }],
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
        research_freshness: { ...fresh, lane: 'defense_streaming' },
        league: { id: 'league-consistency', team_name: 'Consistency Team', dst_slots: 1 },
        saved_defenses: [{
          player: 'TST D/ST',
          team: 'TST',
          next_opponent: 'OPP',
          future_schedule_signal: 'BALANCED',
          rest_days: 7,
          research_action: 'HOLD_RESEARCH',
          weekly_stream_score: 66,
          weekly_rank: 10,
          weekly_stream_tier: 'STREAM',
          multiweek_hold_score: 61,
          multiweek_rank: 12,
          multiweek_hold_tier: 'SHORT_HOLD',
        }],
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
        research_freshness: { ...fresh, lane: 'idp_opportunity' },
        league: { id: 'league-consistency', team_name: 'Consistency Team', idp_slots: { dl: 0, lb: 1, db: 0, idp_flex: 0 } },
        slot_aware: true,
        idp_slots: { DL: 0, LB: 1, DB: 0, IDP_FLEX: 0 },
        matched_idp: [{
          player: 'Private LB',
          team: 'TST',
          position: 'LB',
          idp_group: 'LB',
          next_opponent: 'OPP',
          snap_pct: 100,
          snap_pct_change: 25,
          idp_usage_score: 81,
          idp_usage_tier: 'IDP_STRONG_USAGE',
          role_signal: 'ROLE_UP',
          usage_action_research: 'STRONG_USAGE_RESEARCH',
        }],
        starter_candidates: [{
          player: 'Private LB',
          team: 'TST',
          position: 'LB',
          idp_group: 'LB',
          next_opponent: 'OPP',
          snap_pct: 100,
          snap_pct_change: 25,
          idp_usage_score: 81,
          idp_usage_tier: 'IDP_STRONG_USAGE',
          role_signal: 'ROLE_UP',
          usage_action_research: 'STRONG_USAGE_RESEARCH',
          assigned_slot: 'LB',
          slot_index: 1,
        }],
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
  await expect.poll(() => genericDecisionHits).toBeGreaterThan(0);
  await expect(page.getByText('Generic Sit Player')).toBeVisible();
  await expect(page.getByText('Weekly research').first()).toBeVisible();
  const sitTier = page.getByText('SIT CAUTION', { exact: true }).first();
  await expect(sitTier).toBeVisible();
  await expect(sitTier).toHaveClass(/bg-rose-50/);

  await page.getByRole('button', { name: 'Waivers & FAAB' }).click();
  await expect(page.getByText('Waiver research').first()).toBeVisible();
  await expect(page.getByText('Player status · Available')).toBeVisible();
  await expect(page.getByText('League availability is not connected.')).toBeVisible();
  await expect(page.getByText('Player-status cautions')).toBeVisible();

  await page.getByRole('button', { name: 'IR Stash' }).click();
  await expect(page.getByText('Stash research').first()).toBeVisible();

  await page.getByRole('button', { name: 'Defense', exact: true }).click();
  await expect(page.getByText('Weekly stream').first()).toBeVisible();
  await expect(page.getByText('Multi-week hold').first()).toBeVisible();

  await page.getByRole('button', { name: 'IDP', exact: true }).click();
  await expect(page.getByText('Usage research').first()).toBeVisible();
  await expect(page.getByText('100%').first()).toBeVisible();
  await expect(page.getByText('+25 pts').first()).toBeVisible();
});

test('generic Ask separates player status from league availability', async ({ request }) => {
  const waiver = await request.post('http://127.0.0.1:8510/api/ask', {
    data: { question: 'Top waiver adds', context: { page: 'Fantasy' } },
  });
  expect(waiver.ok()).toBeTruthy();
  const waiverBody = await waiver.json();
  expect(waiverBody.intent).toBe('waivers');
  expect(String(waiverBody.take || '')).toContain('research candidate to check');
  expect(waiverBody.risk || []).toContain('League free-agent availability is not verified in generic Ask.');
  expect((waiverBody.risk || []).some((item) => String(item).startsWith('Availability:'))).toBeFalsy();

  const defense = await request.post('http://127.0.0.1:8510/api/ask', {
    data: { question: 'Best defense to stream?', context: { page: 'Fantasy' } },
  });
  expect(defense.ok()).toBeTruthy();
  const defenseBody = await defense.json();
  expect(defenseBody.intent).toBe('defense_stream');
  expect(String(defenseBody.take || '')).toContain('streaming research option to check');
  expect((defenseBody.risk || []).some((item) => String(item).includes('league availability is not verified'))).toBeTruthy();

  const overview = await request.post('http://127.0.0.1:8510/api/ask', {
    data: {
      question: 'What can Fantasy do here?',
      context: { page: 'Fantasy', fantasy_league_id: 'stale-browser-id' },
    },
  });
  expect(overview.ok()).toBeTruthy();
  const overviewBody = await overview.json();
  expect(overviewBody.intent).toBe('fantasy_context');
  expect(overviewBody.confidence).toBe('FANTASY RESEARCH');
  expect(overviewBody.status).toBe('RESEARCH_ONLY');
  expect(String(overviewBody.take || '')).toContain('Signed-in users with an active saved team');
});
