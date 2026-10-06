import { test, expect } from '@playwright/test';

function fakeJwt(subject) {
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  return `${encode({ alg: 'none', typ: 'JWT' })}.${encode({ sub: subject, exp: now + 3600, iat: now })}.test-signature`;
}

async function installSignedInSession(page, userId = 'user-a') {
  const token = fakeJwt(userId);
  await page.addInitScript(() => {
    window.localStorage.setItem('sports-zenith-auth-session', '1');
    window.localStorage.setItem('sports-zenith-active-fantasy-league', 'league-a');
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
        user: { id: userId, email: userId + '@example.test', name: userId },
      }),
    });
  });

  return token;
}

const teams = [
  {
    league_id: 'league-a',
    roster_id: 'roster-a',
    platform: 'manual',
    league_name: 'Alpha League',
    team_name: 'Alpha Team',
    season: 2026,
    sync_status: 'manual',
    roster: ['Josh Allen', 'CeeDee Lamb', 'Dallas Cowboys D/ST'],
    starters: [],
    bench: [],
    scoring: { preset: 'ppr', reception_points: 1 },
    roster_settings: { starting_slots: { qb: 1, rb: 2, wr: 2, te: 1, flex: 1, dst: 1, k: 1 }, ir_slots: 1 },
    last_analysis: { roster_research_index: 78.2, roster_research_band: 'STRONG_RESEARCH', matched_count: 3, roster_size: 3, coverage_pct: 100 },
  },
  {
    league_id: 'league-b',
    roster_id: 'roster-b',
    platform: 'manual',
    league_name: 'Beta League',
    team_name: 'Beta Team',
    season: 2026,
    sync_status: 'manual',
    roster: ['Jalen Hurts', 'Amon-Ra St. Brown', 'Minnesota Vikings D/ST'],
    starters: [],
    bench: [],
    scoring: { preset: 'half_ppr', reception_points: 0.5 },
    roster_settings: { starting_slots: { qb: 1, rb: 2, wr: 2, te: 1, flex: 1, dst: 1, k: 1, dl: 1, lb: 1, db: 1 }, ir_slots: 2 },
    last_analysis: { roster_research_index: 72.1, roster_research_band: 'STRONG_RESEARCH', matched_count: 3, roster_size: 3, coverage_pct: 100 },
  },
];

test('signed-in active team switches every personalized Fantasy lane and Ask context', async ({ page }) => {
  const token = await installSignedInSession(page);
  const requests = [];

  await page.route('**/api/fantasy/my-teams', async (route) => {
    requests.push({ path: '/api/fantasy/my-teams', auth: route.request().headers()['authorization'] || null });
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'READY', team_count: teams.length, teams }),
    });
  });

  const personalRoutes = {
    '/api/fantasy/start-sit': (leagueId) => ({
      status: 'READY',
      league: { id: leagueId, team_name: leagueId === 'league-b' ? 'Beta Team' : 'Alpha Team', scoring_connected: true, slot_context_connected: true },
      coverage: { roster_size: 3, matched_count: 3, coverage_pct: 100 },
      groups: [],
      players: [],
      lineup_research: { status: 'SLOT_AWARE_RESEARCH', starter_candidates: [], bench_candidates: [], open_slots: [], unscored_slots: [], tiebreakers: [] },
      note: 'Mock personalized Start/Sit',
    }),
    '/api/fantasy/waivers': (leagueId) => ({
      status: 'READY',
      league: { id: leagueId, team_name: leagueId === 'league-b' ? 'Beta Team' : 'Alpha Team' },
      position_needs: [],
      targets: [],
      availability_cautions: [],
      budget_context: { connected: false },
      budget_context_connected: false,
    }),
    '/api/fantasy/ir-stash': (leagueId) => ({
      status: 'READY',
      league: { id: leagueId, team_name: leagueId === 'league-b' ? 'Beta Team' : 'Alpha Team' },
      ir_capacity: { saved_ir_slots: leagueId === 'league-b' ? 2 : 1, likely_open_slots: 1 },
      roster_injured: [],
      outside_targets_to_check: [],
      outside_source_conflicts: [],
    }),
    '/api/fantasy/defense-streaming': (leagueId) => ({
      status: 'READY',
      league: { id: leagueId, team_name: leagueId === 'league-b' ? 'Beta Team' : 'Alpha Team', dst_slots: 1 },
      saved_defenses: [],
      alternatives_to_check: [],
    }),
    '/api/fantasy/idp': (leagueId) => ({
      status: 'READY',
      league: { id: leagueId, team_name: leagueId === 'league-b' ? 'Beta Team' : 'Alpha Team', idp_slots: { dl: 1, lb: 1, db: 1, idp_flex: 0 } },
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
  };

  for (const [path, payload] of Object.entries(personalRoutes)) {
    await page.route('**' + path + '*', async (route) => {
      const requestUrl = new URL(route.request().url());
      const leagueId = requestUrl.searchParams.get('league_id');
      requests.push({
        path,
        leagueId,
        auth: route.request().headers()['authorization'] || null,
      });
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(payload(leagueId)),
      });
    });
  }

  let askBody = null;
  let askAuth = null;
  await page.route('**/api/ask', async (route) => {
    askBody = route.request().postDataJSON();
    askAuth = route.request().headers()['authorization'] || null;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        intent: 'personal_start_sit',
        take: 'Beta Team personalized Ask response',
        confidence: 'PERSONAL ROSTER RESEARCH',
        status: 'PERSONALIZED_RESEARCH',
        why: [],
        risk: [],
        cards: [],
        sources: [{ source: 'PRIVATE_SAVED_FANTASY_TEAM' }],
      }),
    });
  });

  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'networkidle' });

  await expect(page.getByText('Alpha Team').first()).toBeVisible();
  await page.getByRole('button', { name: 'Start / Sit' }).click();
  await expect(page.getByText('Active fantasy team')).toBeVisible();
  await expect(page.getByText('Alpha Team').first()).toBeVisible();

  await expect.poll(() => requests.some((row) => row.path === '/api/fantasy/start-sit' && row.leagueId === 'league-a')).toBe(true);

  const betaButton = page.getByRole('button', { name: /Beta Team/ });
  await betaButton.click();

  await expect.poll(() => requests.some((row) => row.path === '/api/fantasy/start-sit' && row.leagueId === 'league-b')).toBe(true);
  await expect(page.getByText('Beta Team').first()).toBeVisible();

  const lanes = [
    ['Waivers & FAAB', '/api/fantasy/waivers'],
    ['IR Stash', '/api/fantasy/ir-stash'],
    ['Defense', '/api/fantasy/defense-streaming'],
    ['IDP', '/api/fantasy/idp'],
  ];

  for (const [label, path] of lanes) {
    await page.getByRole('button', { name: label, exact: true }).click();
    await expect.poll(() => requests.some((row) => row.path === path && row.leagueId === 'league-b')).toBe(true);
  }

  for (const path of Object.keys(personalRoutes)) {
    const hit = requests.find((row) => row.path === path && row.leagueId === 'league-b');
    expect(hit?.auth).toBe('Bearer ' + token);
  }

  await page.evaluate(() => { window.location.hash = '#ask'; });
  await expect(page.getByText('Sports Intelligence Analyst')).toBeVisible();
  await page.getByRole('button', { name: 'Start / Sit' }).click();

  await expect(page.getByText('Beta Team personalized Ask response')).toBeVisible();
  expect(askBody?.context?.fantasy_league_id).toBe('league-b');
  expect(askAuth).toBe('Bearer ' + token);
});

test('two simulated users keep independent active team context', async ({ browser }) => {
  const contextA = await browser.newContext();
  const contextB = await browser.newContext();
  const pageA = await contextA.newPage();
  const pageB = await contextB.newPage();

  try {
    await installSignedInSession(pageA, 'user-a');
    await installSignedInSession(pageB, 'user-b');

    await pageA.addInitScript(() => {
      window.localStorage.setItem('sports-zenith-active-fantasy-league', 'league-a');
    });
    await pageB.addInitScript(() => {
      window.localStorage.setItem('sports-zenith-active-fantasy-league', 'league-b');
    });

    const seenA = [];
    const seenB = [];

    for (const [page, userTeams, seen] of [
      [pageA, [teams[0]], seenA],
      [pageB, [teams[1]], seenB],
    ]) {
      await page.route('**/api/fantasy/my-teams', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'READY', team_count: userTeams.length, teams: userTeams }),
        });
      });

      await page.route('**/api/fantasy/start-sit*', async (route) => {
        const leagueId = new URL(route.request().url()).searchParams.get('league_id');
        seen.push(leagueId);
        const team = userTeams[0];
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'READY',
            league: { id: leagueId, team_name: team.team_name, scoring_connected: true, slot_context_connected: true },
            coverage: { roster_size: 3, matched_count: 3, coverage_pct: 100 },
            groups: [],
            players: [],
            lineup_research: { status: 'SLOT_AWARE_RESEARCH', starter_candidates: [], bench_candidates: [], open_slots: [], unscored_slots: [], tiebreakers: [] },
            note: 'isolated test',
          }),
        });
      });
    }

    await Promise.all([
      pageA.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'networkidle' }),
      pageB.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'networkidle' }),
    ]);

    await Promise.all([
      pageA.getByRole('button', { name: 'Start / Sit' }).click(),
      pageB.getByRole('button', { name: 'Start / Sit' }).click(),
    ]);

    await expect.poll(() => seenA.includes('league-a')).toBe(true);
    await expect.poll(() => seenB.includes('league-b')).toBe(true);
    expect(seenA).not.toContain('league-b');
    expect(seenB).not.toContain('league-a');
  } finally {
    await contextA.close();
    await contextB.close();
  }
});
