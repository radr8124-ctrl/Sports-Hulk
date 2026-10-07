import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('player historical evidence returns governed context with sample size', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What is the historical evidence for Amon-Ra St. Brown?',
      context: { page: 'Home' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('player_history');
  expect(body.status).toBe('HISTORICAL_CONTEXT');
  expect(body.take).toContain("Amon-Ra St. Brown");
  expect(body.cards?.[0]?.title).toBe('Amon-Ra St. Brown');
  expect(body.cards?.[0]?.evidence_n).toBeGreaterThan(0);
  expect(body.risk || []).toContain('This is historical evidence context, not a career stat line or a prediction.');
});

test('career stat request does not invent a career stat line', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What are Amon-Ra St. Brown career stats?',
      context: { page: 'Home' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('player_history');
  expect(body.status).toBe('PARTIAL_CONTEXT');
  expect(body.take).toContain('not a verified career stat line');
  expect(body.risk || []).toContain('A verified career stat line is not connected in this Ask lane yet; these are historical evidence features only.');
});

test('unknown player history does not borrow another player', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What is the historical evidence for Mystery Unicorn?',
      context: { page: 'Home' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('player_history');
  expect(body.status).toBe('INSUFFICIENT_EVIDENCE');
  expect(body.confidence).toBe('NEEDS PLAYER');
  expect(body.cards || []).toHaveLength(0);
});
