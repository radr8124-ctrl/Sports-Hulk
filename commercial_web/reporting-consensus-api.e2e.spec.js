import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('independent trusted sources agreeing on the same claim raise reporting confidence', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What is the latest injury update on Consensus Runner?',
      context: { page: 'Ask' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('reporting');
  expect(body.status).toBe('CURRENT');
  expect(body.confidence).toBe('MULTI-SOURCE AGREEMENT');
  expect(body.source_agreement?.status).toBe('MULTI_SOURCE_AGREEMENT');
  expect(body.source_agreement?.source_count).toBe(2);
  expect(body.source_agreement?.claim).toBe('Consensus Runner returned to full practice.');

  const sourceNames = new Set((body.sources || []).map(source => source.source));
  expect(sourceNames.has('Test Team Official')).toBe(true);
  expect(sourceNames.has('Test Trusted Beat')).toBe(true);

  const claimMappings = (body.claim_sources || []).filter(row => row.claim === 'Consensus Runner returned to full practice.');
  expect(new Set(claimMappings.map(row => row.source)).size).toBe(2);
});
