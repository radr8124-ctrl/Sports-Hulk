import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('Ask evaluation summary exposes quality and latency metrics', async ({ request }) => {
  await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What are reporters saying about BYU Martin injury?',
      context: { page: 'Home' },
    },
  });

  await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What is Zorbax McFlurry injury status?',
      context: { page: 'Home' },
    },
  });

  const response = await request.get(`${BASE}/api/ask/evaluation-summary?limit=50`);
  expect(response.ok()).toBeTruthy();

  const body = await response.json();
  expect(body.status).toBe('READY');
  expect(body.tracked).toBeGreaterThanOrEqual(2);
  expect(body.grounded_current_pct).toBeGreaterThanOrEqual(0);
  expect(body.withheld_or_flagged_pct).toBeGreaterThanOrEqual(0);
  expect(body.insufficient_evidence).toBeGreaterThanOrEqual(1);
  expect(body.reporting_answers).toBeGreaterThanOrEqual(1);
  expect(body.avg_latency_ms).toBeGreaterThanOrEqual(0);
});
