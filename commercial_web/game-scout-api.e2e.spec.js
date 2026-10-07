import { test, expect } from '@playwright/test';

const BASE = 'http://127.0.0.1:8510/api/ask';

const fakeGameContext = {
  page: 'Scores',
  game_context: {
    surface: 'GAME_CENTER',
    league: 'NBA',
    event_id: '999999999',
    away: 'Exact Away Team',
    away_abbr: 'EAT',
    home: 'Exact Home Team',
    home_abbr: 'EHT',
    status: 'Upcoming',
    start_time: '2030-01-01T00:00:00Z',
  },
};

test('Game Scout never borrows markets from another matchup', async ({ request }) => {
  const response = await request.post(BASE, {
    data: {
      question: 'What is the best bet in this game?',
      context: fakeGameContext,
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('game_zenith');
  expect(body.status).toBe('RESEARCH_ONLY');
  expect(body.take).toContain('Exact Away Team @ Exact Home Team');
  expect(body.cards || []).toHaveLength(0);
  expect(body.risk || []).toContain('Game Scout will not borrow a bet, prop, or player line from another matchup.');
});

test('Game Scout does not substitute props from another matchup', async ({ request }) => {
  const response = await request.post(BASE, {
    data: {
      question: 'What props do you have for this game?',
      context: fakeGameContext,
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('game_props');
  expect(body.status).toBe('NO_EXACT_PROPS');
  expect(body.cards || []).toHaveLength(0);
  expect(body.risk || []).toContain('Game Scout will not substitute props from another matchup.');
});

test('Unrelated Survivor questions escape Game Scout context', async ({ request }) => {
  const response = await request.post(BASE, {
    data: {
      question: 'What Survivor team should I use?',
      context: fakeGameContext,
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('survivor');
  expect(body.intent).not.toBe('game_zenith');
});
