import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('save-for-later routes to future-value research instead of current-week Survivor pick', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What team should I save for later?',
      context: { page: 'Survivor' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('survivor_future_value');
  expect(body.status).toBe('RESEARCH_ONLY');
  expect(body.confidence).toBe('FUTURE VALUE RESEARCH');
  expect(body.cards?.length).toBeGreaterThan(0);

  const values = body.cards.map(card => Number(card.future_value_index || 0));
  expect(values).toEqual([...values].sort((a, b) => b - a));
  expect(body.take).toContain(body.cards[0].title);
  expect(body.why || []).toContain('A high future-value team can be worth saving even when another team is the better current-week recommendation.');
});
