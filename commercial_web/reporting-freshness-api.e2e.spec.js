import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('current injury questions withhold stale reporting', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What is Stale Runner injury status?',
      context: { page: 'Home' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('reporting_stale');
  expect(body.status).toBe('STALE_SOURCE');
  expect(body.confidence).toBe('STALE / VERIFY');
  expect(body.take).toBe('I do not have fresh enough verified reporting to answer that as current.');
  expect(body.risk || []).toContain('Sports Zenith will not relabel stale evidence as current.');
  expect(body.sources?.[0]?.updated_at).toBeTruthy();
});

test('fresh injury reporting still passes the freshness gate', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What is Fresh Runner injury status?',
      context: { page: 'Home' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('reporting');
  expect(body.status).toBe('CURRENT');
  expect(body.take).toBe('Fresh Runner injury update');
  expect(body.sources?.[0]?.url).toBe('https://example.com/fresh-runner');
});
