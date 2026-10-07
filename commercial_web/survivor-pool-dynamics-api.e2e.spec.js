import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('unsigned pool-dynamics question requires private pool context', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'How many entries are left in my Survivor pool?',
      context: { page: 'Survivor' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('survivor_pool_dynamics');
  expect(body.status).toBe('PERSONAL_CONTEXT_REQUIRED');
  expect(body.confidence).toBe('PERSONAL CONTEXT REQUIRED');
  expect(body.take).toContain('require linked private pool state');
  expect((body.risk || []).join(' ')).toContain('will not estimate');
});
