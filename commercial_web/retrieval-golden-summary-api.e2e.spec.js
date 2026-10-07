import { test, expect } from '@playwright/test';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';

test('evaluation summary exposes deterministic retrieval benchmark metrics', async ({ request }) => {
  const response = await request.get(`${BASE}/api/ask/evaluation-summary?limit=50`);
  expect(response.ok()).toBeTruthy();

  const body = await response.json();

  expect(body.status).toBe('READY');
  expect(body.retrieval_golden_status).toBe('PASS');
  expect(body.retrieval_golden_cases).toBe(5);
  expect(body.retrieval_golden_passed).toBe(5);
  expect(body.retrieval_recall_pct).toBe(100);
  expect(body.retrieval_precision_pct).toBe(100);
  expect(body.answer_relevance_pct).toBe(100);
  expect(body.retrieval_golden_generated_at).toBeTruthy();
  expect(body.semantic_golden_status).toBe('PASS');
  expect(body.semantic_golden_cases).toBe(5);
  expect(body.semantic_golden_passed).toBe(5);
  expect(body.semantic_answer_pass_pct).toBe(100);
  expect(body.semantic_golden_generated_at).toBeTruthy();
});
