import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('source clicks attach to the exact Ask answer and update quality metrics', async ({ request }) => {
  const askResponse = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What are reporters saying about BYU Martin injury?',
      context: { page: 'Home' },
    },
  });
  expect(askResponse.ok()).toBeTruthy();
  const answer = await askResponse.json();
  expect(answer.sources?.[0]?.url).toBeTruthy();
  expect(answer.generated_at).toBeTruthy();

  const clickResponse = await request.post(`${BASE}/api/ask/source-click`, {
    data: {
      url: answer.sources[0].url,
      source_label: answer.sources[0].source,
      answer_generated_at: answer.generated_at,
      intent: answer.intent,
      status: answer.status,
      page: answer.context?.page,
    },
  });
  expect(clickResponse.ok()).toBeTruthy();

  const summaryResponse = await request.get(`${BASE}/api/ask/evaluation-summary?limit=50`);
  expect(summaryResponse.ok()).toBeTruthy();
  const summary = await summaryResponse.json();

  expect(summary.source_clicks).toBeGreaterThanOrEqual(1);
  expect(summary.unique_answers_with_source_click).toBeGreaterThanOrEqual(1);
  expect(summary.source_click_rate_pct).toBeGreaterThan(0);
});

test('source click endpoint rejects unsafe URLs', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask/source-click`, {
    data: {
      url: 'javascript:alert(1)',
      source_label: 'Unsafe',
      answer_generated_at: new Date().toISOString(),
    },
  });

  expect(response.status()).toBe(400);
});
