import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('fact-only reporting answer cites the exact fact source and maps the claim', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What is the report on Orion Vale?',
      context: { page: 'Ask' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('reporting');
  expect(body.take).toBe('Orion Vale is listed as the starting slot receiver for Test City.');

  const exactSource = (body.sources || []).find(source => source.evidence_id === 'fact-orion-vale-001');
  expect(exactSource).toBeTruthy();
  expect(exactSource.source).toBe('Test City Official');
  expect(exactSource.url).toBe('https://example.com/orion-vale-official');
  expect(exactSource.evidence_type).toBe('FACT');

  const claim = (body.claim_sources || []).find(item => item.claim === body.take);
  expect(claim).toBeTruthy();
  expect(claim.evidence_id).toBe('fact-orion-vale-001');
  expect(claim.source).toBe('Test City Official');
  expect(claim.url).toBe('https://example.com/orion-vale-official');

  expect((body.sources || []).some(source => source.source === 'Structured news/event graph')).toBe(false);
});
