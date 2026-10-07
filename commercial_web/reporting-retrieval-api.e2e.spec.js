import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('multi-word reporting query prefers full entity coverage and rejects substring leaks', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What are reporters saying about BYU Martin injury?',
      context: { page: 'Home' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('reporting');
  expect(body.take).toContain('BYU star RB Martin');
  expect(body.why || []).toEqual([
    "BYU will be without running back LJ Martin and linebacker Isaiah Glasker for Friday's game against Iowa State.",
  ]);
  expect(body.sources || []).toHaveLength(1);
  expect(body.sources[0].source).toBe('ESPN');
  expect(body.sources[0].url).toContain('/50122325/');
  expect(JSON.stringify(body)).not.toContain('Shaedon Sharpe');
  expect(JSON.stringify(body)).not.toContain('Nick Martinez');
  expect(JSON.stringify(body)).not.toContain('fantasy/basketball');
});
