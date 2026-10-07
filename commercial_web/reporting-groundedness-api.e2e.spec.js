import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('unknown named subject returns insufficient evidence instead of unrelated reporting', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What is Zorbax McFlurry injury status?',
      context: { page: 'Home' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.status).toBe('INSUFFICIENT_EVIDENCE');
  expect(body.confidence).toBe('INSUFFICIENT EVIDENCE');
  expect(body.take).toBe("I don't have enough verified information yet to answer that confidently.");
  expect(body.sources || []).toHaveLength(0);
  expect(JSON.stringify(body)).not.toContain('Lamar Jackson');
  expect(JSON.stringify(body)).not.toContain('Brad Marchand');
});

test('real named subject still returns grounded reporting', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What are reporters saying about BYU Martin injury?',
      context: { page: 'Home' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('reporting');
  expect(body.status).toBe('CURRENT');
  expect(body.take).toContain('BYU star RB Martin');
  expect(body.sources?.[0]?.url).toContain('/50122325/');
});
