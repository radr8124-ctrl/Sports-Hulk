import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('reporting surfaces governed source disagreement instead of choosing a source', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What is Alvin Kamara injury status?',
      context: { page: 'Home' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('reporting_conflict');
  expect(body.status).toBe('SOURCE_CONFLICT');
  expect(body.confidence).toBe('SOURCE CONFLICT / VERIFY');
  expect(body.take).toBe("Sources disagree on Alvin Kamara's current availability.");
  expect(body.why || []).toContain('Current structured status: QUESTIONABLE.');
  expect(body.risk || []).toContain('Sports Zenith will not silently choose one conflicting source as truth.');
  expect(body.cards?.[0]?.title).toBe('Alvin Kamara');
  expect(body.cards?.[0]?.source_count).toBeGreaterThanOrEqual(2);
});
