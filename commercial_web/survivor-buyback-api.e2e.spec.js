import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('unsigned buyback question requires personal pool context and never invents eligibility', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'Can I buy back into my Survivor pool?',
      context: { page: 'Survivor' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('survivor_buyback');
  expect(body.status).toBe('PERSONAL_CONTEXT_REQUIRED');
  expect(body.confidence).toBe('PERSONAL CONTEXT REQUIRED');
  expect(body.take).toContain('requires a linked Survivor entry');
  expect((body.risk || []).join(' ')).toContain('will not assume');
});
