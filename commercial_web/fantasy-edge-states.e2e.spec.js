import { test, expect } from '@playwright/test';

function fakeJwt(subject) {
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  return `${encode({ alg: 'none', typ: 'JWT' })}.${encode({ sub: subject, exp: now + 3600, iat: now })}.test-signature`;
}

async function installSignedInSession(page, activeLeagueId = 'league-a') {
  const token = fakeJwt('edge-user');
  await page.addInitScript(({ activeLeagueId }) => {
    window.localStorage.setItem('sports-zenith-auth-session', '1');
    window.localStorage.setItem('sports-zenith-active-fantasy-league', activeLeagueId);
  }, { activeLeagueId });

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
        user: { id: 'edge-user', email: 'edge-user@example.test', name: 'Edge User' },
      }),
    });
  });

  return token;
}

const teamA = {
  league_id: 'league-a',
  roster_id: 'roster-a',
  platform: 'manual',
  league_name: 'Alpha League',
  team_name: 'Alpha Team',
  season: 2026,
  sync_status: 'manual',
  roster: ['Josh Allen', 'Mystery Player', 'Unknown Backup'],
  scoring: { preset: 'ppr', reception_points: 1 },
  roster_settings: { starting_slots: { qb: 1, rb: 2, wr: 2, te: 1, flex: 1, dst: 1, k: 1 }, ir_slots: 1 },
};

const teamB = {
  league_id: 'league-b',
  roster_id: 'roster-b',
  platform: 'manual',
  league_name: 'Beta League',
  team_name: 'Beta Team',
  season: 2026,
  sync_status: 'manual',
  roster: ['Jalen Hurts', 'Amon-Ra St. Brown', 'Minnesota Vikings D/ST'],
  scoring: { preset: 'half_ppr', reception_points: 0.5 },
  roster_settings: { starting_slots: { qb: 1, rb: 2, wr: 2, te: 1, flex: 1, dst: 1, k: 1 }, ir_slots: 1 },
};

async function mockMyTeams(page, teams = [teamA]) {
  await page.route('**/api/fantasy/my-teams', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'READY', team_count: teams.length, teams }),
    });
  });
}

test('Start Sit shows retry, partial coverage, unmatched names, and missing setup action', async ({ page }) => {
  await installSignedInSession(page);
  await mockMyTeams(page);

  let calls = 0;
  await page.route('**/api/fantasy/start-sit*', async (route) => {
    calls += 1;
    if (calls === 1) {
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ERROR', message: 'Temporary Start/Sit test failure' }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'READY',
        league: {
          id: 'league-a',
          team_name: 'Alpha Team',
          scoring_connected: false,
          scoring_format: null,
          slot_context_connected: false,
        },
        coverage: {
          roster_size: 3,
          matched_count: 1,
          unmatched_count: 2,
          coverage_pct: 33.3,
          decision_coverage_pct: 33.3,
        },
        groups: [],
        players: [],
        unmatched: [{ input: 'Mystery Player' }, { input: 'Unknown Backup' }],
        recognized_without_decision: [],
        lineup_research: {
          status: 'SLOT_CONTEXT_WAITING',
          starter_candidates: [],
          bench_candidates: [],
          open_slots: [],
          unscored_slots: [],
          tiebreakers: [],
        },
        note: 'Partial coverage test',
      }),
    });
  });

  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'Start / Sit' }).click();

  await expect(page.getByText('Your roster-aware Start/Sit research could not load.')).toBeVisible();
  await page.getByRole('button', { name: 'Try again' }).click();

  await expect(page.getByText(/Partial roster coverage/)).toBeVisible();
  await expect(page.getByText(/Mystery Player/)).toBeVisible();
  await expect(page.getByText(/Unknown Backup/)).toBeVisible();
  await expect(page.getByText(/No QB\/RB\/WR\/TE\/DST player/)).toBeVisible();
  await expect(page.getByText(/League setup is incomplete/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Open league settings' })).toBeVisible();
  expect(calls).toBe(2);
});

test('Waiver zero-target and IR no-room states stay explicit', async ({ page }) => {
  await installSignedInSession(page);
  await mockMyTeams(page);

  await page.route('**/api/fantasy/waivers*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'READY',
        league: { id: 'league-a', team_name: 'Alpha Team' },
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
        league: { id: 'league-a', team_name: 'Alpha Team', ir_slots: 1 },
        ir_capacity: {
          saved_ir_slots: 1,
          likely_ir_designation_count: 1,
          possible_ir_eligibility_count: 0,
          likely_open_slots: 0,
          likely_overflow_count: 0,
        },
        roster_injured: [],
        outside_targets_to_check: [],
        outside_source_conflicts: [],
      }),
    });
  });

  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'Waivers & FAAB' }).click();

  await expect(page.getByText(/No personalized waiver target cleared/)).toBeVisible();
  await expect(page.getByText(/No scored QB\/RB\/WR\/TE roster-need rows/)).toBeVisible();

  await page.getByRole('button', { name: 'IR Stash' }).click();
  await expect(page.getByText(/No likely open IR capacity/)).toBeVisible();
});

test('Defense and IDP never leave empty research grids unexplained', async ({ page }) => {
  await installSignedInSession(page);
  await mockMyTeams(page);

  await page.route('**/api/fantasy/defense-streaming*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'READY',
        league: { id: 'league-a', team_name: 'Alpha Team', dst_slots: 1 },
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
        league: { id: 'league-a', team_name: 'Alpha Team', idp_slots: { dl: 0, lb: 0, db: 0, idp_flex: 0 } },
        slot_aware: false,
        idp_slots: { DL: 0, LB: 0, DB: 0, IDP_FLEX: 0 },
        matched_idp: [],
        starter_candidates: [],
        bench_candidates: [],
        unavailable_roster: [],
        open_slots: [],
        group_summary: [],
        outside_targets_to_check: [],
        unmatched_idp: [{ input: 'Fake Defender', reason: 'IDP_PLAYER_NOT_FOUND' }],
      }),
    });
  });

  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'Defense', exact: true }).click();

  await expect(page.getByText(/No D\/ST was recognized/)).toBeVisible();
  await expect(page.getByText(/No outside D\/ST alternative/)).toBeVisible();

  await page.getByRole('button', { name: 'IDP', exact: true }).click();
  await expect(page.getByText(/No IDP player on this saved roster matched/)).toBeVisible();
  await expect(page.getByText(/No outside IDP research target cleared/)).toBeVisible();
  await expect(page.getByText(/Fake Defender/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Open league settings' })).toBeVisible();
});

test('late Team A Start Sit response cannot overwrite Team B after switching during load', async ({ page }) => {
  await installSignedInSession(page, 'league-a');
  await mockMyTeams(page, [teamA, teamB]);

  const calls = [];
  await page.route('**/api/fantasy/start-sit*', async (route) => {
    const leagueId = new URL(route.request().url()).searchParams.get('league_id');
    calls.push(leagueId);

    if (leagueId === 'league-a') {
      await new Promise((resolve) => setTimeout(resolve, 650));
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'READY',
        league: {
          id: leagueId,
          team_name: leagueId === 'league-b' ? 'Beta Team' : 'Alpha Team',
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
        note: `StartSit response for ${leagueId}`,
      }),
    });
  });

  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'Start / Sit' }).click();
  await expect.poll(() => calls.includes('league-a')).toBe(true);

  await page.getByRole('button', { name: 'Switch active fantasy team to Beta Team' }).click();
  await expect.poll(() => calls.includes('league-b')).toBe(true);
  await expect(page.getByText('StartSit response for league-b')).toBeVisible();

  await page.waitForTimeout(800);
  await expect(page.getByText('StartSit response for league-b')).toBeVisible();
  await expect(page.getByText('StartSit response for league-a')).toHaveCount(0);
});
