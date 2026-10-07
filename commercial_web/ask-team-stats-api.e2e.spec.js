import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('current NFL team style uses current structured stats', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: { question: 'How do the Ravens play on offense?', context: { page: 'Home' } },
  });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('team_stats');
  expect(body.status).toBe('CURRENT');
  expect(body.confidence).toBe('CURRENT STRUCTURED TEAM STATS');
  expect(body.take).toContain('Baltimore Ravens');
  expect(body.why || []).toContain('Pass rate: 46.9%.');
  expect(body.why || []).toContain('Rush rate: 53.1%.');
});

test('prior-baseline team stats are not presented as current', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: { question: 'What is the Timberwolves team style and pace?', context: { page: 'Home' } },
  });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('team_stats');
  expect(body.status).toBe('BACKGROUND_BASELINE');
  expect(body.confidence).toBe('PRIOR BASELINE');
  expect(body.take).toContain('Minnesota Timberwolves');
  expect(body.risk || []).toContain('This is a prior-season baseline, not a claim about current-season performance.');
});

test('unknown team style query does not borrow another team', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: { question: 'What is Mystery Unicorns team style?', context: { page: 'Home' } },
  });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('team_stats');
  expect(body.status).toBe('INSUFFICIENT_EVIDENCE');
  expect(body.confidence).toBe('NEEDS TEAM');
  expect(body.cards || []).toHaveLength(0);
});
