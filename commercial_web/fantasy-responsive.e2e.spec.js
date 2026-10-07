import { test, expect } from '@playwright/test';

function fakeJwt(subject) {
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  return `${encode({ alg: 'none', typ: 'JWT' })}.${encode({ sub: subject, exp: now + 3600, iat: now })}.test-signature`;
}

async function installSession(page) {
  const token = fakeJwt('responsive-user');
  await page.addInitScript(() => {
    window.localStorage.setItem('sports-zenith-auth-session', '1');
    window.localStorage.setItem('sports-zenith-active-fantasy-league', 'league-responsive');
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
        user: { id: 'responsive-user', email: 'responsive@example.test', name: 'Responsive User' },
      }),
    });
  });
}

const longTeamName = 'The Extremely Long Sunday Morning Championship Fantasy Team Name That Must Never Break The Layout';
const longLeagueName = 'Queens Very Long Friends And Family Keeper Superflex IDP Championship League Name';

const team = {
  league_id: 'league-responsive',
  roster_id: 'roster-responsive',
  platform: 'manual',
  league_name: longLeagueName,
  team_name: longTeamName,
  season: 2026,
  sync_status: 'manual',
  roster_updated_at: '2026-10-06T23:00:00Z',
  roster: ['Very Long Quarterback Player Name', 'Very Long Wide Receiver Player Name', 'TST D/ST', 'Very Long Linebacker Player Name'],
  scoring: { preset: 'ppr', reception_points: 1, faab_budget: 100, faab_remaining: 64 },
  roster_settings: {
    starting_slots: { qb: 1, rb: 2, wr: 2, te: 1, flex: 1, dst: 1, k: 1, lb: 1 },
    bench_slots: 6,
    ir_slots: 1,
  },
  last_analysis: {
    generated_at: '2026-10-06T23:02:00Z',
    roster_size: 4,
    matched_count: 4,
    coverage_pct: 100,
    roster_research_index: 76,
    roster_research_band: 'STRONG_RESEARCH',
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

async function mockFantasy(page) {
  await page.route('**/api/fantasy/my-teams', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'READY', team_count: 1, teams: [team] }),
    });
  });

  await page.route('**/fantasy_decisions.json*', async (route) => {
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
              player: 'Generic Very Long Wide Receiver Name For Responsive Testing',
              team: 'TST',
              position: 'WR',
              opponent: 'OPP',
              role_signal: 'ROLE_UP',
              snap_pct: 87,
              weekly_research_score: 76,
              weekly_tier: 'START_LEAN',
              ros_research_score: 70,
              research_reasons: 'Responsive test signal',
            }],
          },
          faab: {
            source_rows: 1,
            rows: [{
              sport: 'NFL',
              player: 'Generic Very Long Waiver Candidate Name For Responsive Testing',
              team: 'TST',
              position: 'WR',
              waiver_research_score: 75,
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
              player: 'Generic Very Long Injured Reserve Player Name',
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
              player: 'Generic Very Long Individual Defensive Player Name',
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

  await page.route('**/fantasy_v2_current.json*', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ lanes: {} }) });
  });
  await page.route('**/brain_performance.json*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ fantasy_v2: { forward: {} }, dfs: { replay_modes: [] } }),
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
          id: 'league-responsive',
          team_name: longTeamName,
          league_name: longLeagueName,
          scoring_connected: false,
          scoring_format: null,
          slot_context_connected: false,
        },
        coverage: { roster_size: 1, matched_count: 1, unmatched_count: 0, coverage_pct: 100, decision_coverage_pct: 100 },
        groups: [{
          position: 'WR',
          count: 1,
          players: [{
            player: 'Very Long Personalized Wide Receiver Player Name For Responsive Layout Testing',
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
        note: 'Responsive Start/Sit fixture',
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
        league: { id: 'league-responsive', team_name: longTeamName },
        position_needs: [{ position: 'WR', roster_need_score: 70, roster_need_tier: 'NEED', roster_count: 1 }],
        targets: [{
          player: 'Very Long Personalized Waiver Candidate Player Name For Responsive Testing',
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
        research_freshness: { ...fresh, lane: 'ir_stash' },
        league: { id: 'league-responsive', team_name: longTeamName, ir_slots: 0 },
        ir_capacity: { saved_ir_slots: 0, likely_open_slots: 0, likely_overflow_count: 0 },
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
        research_freshness: { ...fresh, lane: 'defense_streaming' },
        league: { id: 'league-responsive', team_name: longTeamName, dst_slots: 1 },
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
        league: { id: 'league-responsive', team_name: longTeamName, idp_slots: { dl: 0, lb: 0, db: 0, idp_flex: 0 } },
        slot_aware: false,
        idp_slots: { DL: 0, LB: 0, DB: 0, IDP_FLEX: 0 },
        matched_idp: [{
          player: 'Very Long Personalized Linebacker Player Name For Responsive Testing',
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

async function dimensions(page) {
  return page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
}

async function expectNoPageOverflow(page, label = 'page') {
  const size = await dimensions(page);
  if (size.scrollWidth > size.clientWidth + 1) {
    const offenders = await page.evaluate(() => {
      const viewportWidth = document.documentElement.clientWidth;
      const clippedByAncestor = (element) => {
        let parent = element.parentElement;
        while (parent && parent !== document.body) {
          const overflowX = getComputedStyle(parent).overflowX;
          if (['auto', 'scroll', 'hidden', 'clip'].includes(overflowX)) return true;
          parent = parent.parentElement;
        }
        return false;
      };
      return [...document.querySelectorAll('body *')]
        .map((element) => {
          const rect = element.getBoundingClientRect();
          const style = getComputedStyle(element);
          return {
            element,
            tag: element.tagName,
            className: String(element.className || '').slice(0, 180),
            text: String(element.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 120),
            left: Math.round(rect.left),
            right: Math.round(rect.right),
            width: Math.round(rect.width),
            overflowX: style.overflowX,
          };
        })
        .filter((row) => (row.right > viewportWidth + 1 || row.left < -1) && !clippedByAncestor(row.element))
        .sort((a, b) => b.right - a.right)
        .slice(0, 8)
        .map(({ element, ...row }) => row);
    });
    throw new Error(`${label} overflow: viewport ${size.clientWidth}px, page ${size.scrollWidth}px; offenders=${JSON.stringify(offenders)}`);
  }
  expect(size.scrollWidth).toBeLessThanOrEqual(size.clientWidth + 1);
}

async function expectMinButtonHeight(page, names, minimum = 44) {
  for (const name of names) {
    const button = page.getByRole('button', { name, exact: true }).first();
    await expect(button).toBeVisible();
    const box = await button.boundingBox();
    expect(box?.height || 0).toBeGreaterThanOrEqual(minimum);
  }
}

test('Fantasy stays contained and touch-friendly at phone tablet and desktop widths', async ({ browser }) => {
  const viewports = [
    { name: 'phone', width: 390, height: 844 },
    { name: 'tablet', width: 768, height: 1024 },
    { name: 'desktop', width: 1440, height: 900 },
  ];

  for (const viewport of viewports) {
    const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
    const page = await context.newPage();

    try {
      await installSession(page);
      await mockFantasy(page);
      await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'domcontentloaded' });
      await expect(page.getByText('Fantasy Team Control')).toBeVisible();

      await expectNoPageOverflow(page);
      await expectMinButtonHeight(page, [
        'Season-Long',
        'DFS Lineup Lab',
        'My Teams / Rate My Team',
        'Start / Sit',
        'Waivers & FAAB',
        'IR Stash',
        'Defense',
        'IDP',
      ]);

      if (viewport.width < 1024) {
        await expect(page.getByRole('navigation', { name: 'Mobile primary navigation', exact: true })).toBeVisible();
        await expect(page.getByRole('navigation', { name: 'Primary navigation', exact: true })).toBeHidden();
        const header = page.locator('header');
        const askBox = await header.getByRole('button', { name: 'Ask' }).boundingBox();
        const moreBox = await header.getByRole('button', { name: 'More' }).boundingBox();
        expect(askBox?.height || 0).toBeGreaterThanOrEqual(44);
        expect(moreBox?.height || 0).toBeGreaterThanOrEqual(44);
      } else {
        await expect(page.getByRole('navigation', { name: 'Primary navigation', exact: true })).toBeVisible();
        await expect(page.getByRole('navigation', { name: 'Mobile primary navigation', exact: true })).toBeHidden();
      }

      const lanes = [
        ['Start / Sit', 'My Start / Sit'],
        ['Waivers & FAAB', 'My Waiver Targets'],
        ['IR Stash', 'My IR / Stash'],
        ['Defense', 'My Defense Streaming'],
        ['IDP', 'My IDP'],
      ];

      for (const [tab, marker] of lanes) {
        await page.getByRole('button', { name: tab, exact: true }).click();
        await expect(page.getByText(marker, { exact: true })).toBeVisible();
        await expectNoPageOverflow(page, `${viewport.name}:${tab}`);
      }
    } finally {
      await context.close();
    }
  }
});


test('Fantasy keyboard navigation and direct league-settings action work on phone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installSession(page);
  await mockFantasy(page);
  await page.goto('http://127.0.0.1:8510/#fantasy', { waitUntil: 'domcontentloaded' });
  await expect(page.getByText('Fantasy Team Control')).toBeVisible();

  const startSit = page.getByRole('button', { name: 'Start / Sit', exact: true });
  await startSit.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('My Start / Sit', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Roster & league settings', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Rate my team' })).toBeVisible();

  const settings = page.locator('#fantasy-league-settings');
  await expect(settings).toBeVisible();
  await expect(settings.getByText('Close', { exact: true })).toBeVisible();
  await expect(settings).toBeFocused();

  await expect.poll(async () => {
    const box = await settings.boundingBox();
    return box?.y ?? 9999;
  }, { timeout: 3000 }).toBeLessThan(844);

  await expectMinButtonHeight(page, ['PPR', 'Half-PPR', 'Standard']);
  for (const label of ['QB starter slots', 'Bench slots', 'IR slots', 'FAAB total budget', 'FAAB remaining']) {
    const control = page.getByLabel(label);
    await expect(control).toBeVisible();
    const box = await control.boundingBox();
    expect(box?.height || 0).toBeGreaterThanOrEqual(44);
  }
  await expectNoPageOverflow(page, 'phone:open league settings');

  await page.getByRole('button', { name: 'Start / Sit', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Open league settings', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Open league settings', exact: true }).click();
  await expect(settings).toBeVisible();
  await expect(settings.getByText('Close', { exact: true })).toBeVisible();
  await expect(settings).toBeFocused();
  await expectNoPageOverflow(page, 'phone:direct settings from Start/Sit');

  await page.getByRole('button', { name: 'IR Stash', exact: true }).click();
  await expect(page.getByText('My IR / Stash', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Edit league settings', exact: true }).click();
  await expect(settings).toBeVisible();
  await expect(settings.getByText('Close', { exact: true })).toBeVisible();
  await expect(settings).toBeFocused();

  await page.getByRole('button', { name: 'IDP', exact: true }).click();
  await expect(page.getByText('My IDP', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Open league settings', exact: true }).click();
  await expect(settings).toBeVisible();
  await expect(settings.getByText('Close', { exact: true })).toBeVisible();
  await expect(settings).toBeFocused();
  await expectNoPageOverflow(page, 'phone:direct settings from IDP');
});
