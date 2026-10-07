import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

async function ask(request, question) {
  const response = await request.post(`${BASE}/api/ask`, {
    data: { question, context: { page: 'Home' } },
  });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(typeof body.intent).toBe('string');
  expect(typeof body.take).toBe('string');
  expect(typeof body.confidence).toBe('string');
  expect(typeof body.status).toBe('string');
  expect(Array.isArray(body.why)).toBeTruthy();
  expect(Array.isArray(body.risk)).toBeTruthy();
  expect(Array.isArray(body.sources)).toBeTruthy();
  expect(Array.isArray(body.cards)).toBeTruthy();
  return body;
}

test('Ask response states distinguish missing context, projections, history and current research', async ({ request }) => {
  const startSit = await ask(request, 'Who should I start this week?');
  expect(startSit.intent).toBe('start_sit');
  expect(startSit.confidence).toBe('NEEDS PLAYER CONTEXT');
  expect(startSit.status).toBe('INSUFFICIENT_EVIDENCE');

  const dfs = await ask(request, 'Best DraftKings DFS lineup');
  expect(dfs.intent).toBe('dfs');
  expect(dfs.confidence).toBe('PROJECTED');
  expect(dfs.status).toBe('PROJECTED');

  const history = await ask(request, 'What is the historical evidence for Amon-Ra St. Brown?');
  expect(history.intent).toBe('player_history');
  expect(history.status).toBe('HISTORICAL_CONTEXT');

  const schedule = await ask(request, 'Who do the Eagles play next?');
  expect(schedule.intent).toBe('schedule');
  expect(schedule.confidence).toBe('GOVERNED SCHEDULE');
  expect(schedule.status).toBe('CURRENT');
});
