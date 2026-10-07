import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('reporting claim evidence coverage is recorded in evaluation summary', async ({ request }) => {
  const answerResponse = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What is the report on Orion Vale?',
      context: { page: 'Ask' },
    },
  });

  expect(answerResponse.ok()).toBeTruthy();
  const answer = await answerResponse.json();
  expect(answer.intent).toBe('reporting');
  expect(answer.claim_sources?.length).toBeGreaterThan(0);

  const summaryResponse = await request.get(`${BASE}/api/ask/evaluation-summary?limit=50`);
  expect(summaryResponse.ok()).toBeTruthy();
  const summary = await summaryResponse.json();

  expect(summary.status).toBe('READY');
  expect(summary.claim_measured_reporting_answers).toBe(1);
  expect(summary.reporting_claim_count).toBe(1);
  expect(summary.supported_reporting_claim_count).toBe(1);
  expect(summary.unsupported_reporting_claim_count).toBe(0);
  expect(summary.claim_evidence_coverage_pct).toBe(100);
});
