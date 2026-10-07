import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('Ask routes team schedule and fatigue questions to governed schedule data', async ({ request }) => {
  const nextResponse = await request.post(`${BASE}/api/ask`, {
    data: { question: 'Who do the Eagles play next?', context: { page: 'Home' } },
  });
  expect(nextResponse.ok()).toBeTruthy();
  const next = await nextResponse.json();
  expect(next.intent).toBe('schedule');
  expect(next.status).toBe('CURRENT');
  expect(next.take).toContain('Philadelphia Eagles');
  expect(next.take).toContain('Jacksonville Jaguars');
  expect(next.cards?.[0]?.opponent).toBe('JAX');

  const fatigueResponse = await request.post(`${BASE}/api/ask`, {
    data: { question: 'Are the Timberwolves on a back to back?', context: { page: 'Home' } },
  });
  expect(fatigueResponse.ok()).toBeTruthy();
  const fatigue = await fatigueResponse.json();
  expect(fatigue.intent).toBe('schedule');
  expect(fatigue.cards?.[0]?.back_to_back).toBe(true);
  expect(fatigue.why || []).toContain('This is a back-to-back spot.');
});

test('Ask ranks future schedule difficulty without calling it probability', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: { question: 'Who has the hardest NBA schedule?', context: { page: 'Home' } },
  });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.intent).toBe('schedule_difficulty');
  expect(body.status).toBe('CURRENT');
  expect(body.cards?.length).toBeGreaterThanOrEqual(3);
  expect(body.risk || []).toContain('Schedule strength is a research index, not a win-probability forecast.');
});

test('unknown team schedule query does not borrow another team', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: { question: 'What is the schedule for Mystery Unicorns?', context: { page: 'Home' } },
  });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.intent).toBe('schedule');
  expect(body.status).toBe('INSUFFICIENT_EVIDENCE');
  expect(body.confidence).toBe('NEEDS TEAM');
  expect(body.cards || []).toHaveLength(0);
});
