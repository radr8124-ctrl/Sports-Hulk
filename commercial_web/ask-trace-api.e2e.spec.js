import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';
const TRACE_PATH = '/tmp/sports-hulk-ask-trace.jsonl';

test('Ask request emits privacy-safe correlated trace and aggregate summary', async ({ request }) => {
  const question = 'What is the report on Orion Vale?';
  const response = await request.post(`${BASE}/api/ask`, {
    data: { question, context: { page: 'Ask' } },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(typeof body.trace_id).toBe('string');
  expect(body.trace_id.length).toBeGreaterThan(10);

  const raw = await readFile(TRACE_PATH, 'utf8');
  expect(raw).not.toContain(question);
  const rows = raw.trim().split(/\r?\n/).map(line => JSON.parse(line));
  expect(rows).toHaveLength(1);

  const trace = rows[0];
  expect(trace.trace_id).toBe(body.trace_id);
  expect(trace.route_lane).toBe('GENERIC');
  expect(trace.intent).toBe('reporting');
  expect(trace.status).toBe('CURRENT');
  expect(trace.output_validation_valid).toBe(true);
  expect(trace.error).toBe(false);
  expect(trace.question_hash).toMatch(/^[a-f0-9]{64}$/);
  expect(Object.prototype.hasOwnProperty.call(trace, 'question')).toBe(false);

  const summaryResponse = await request.get(`${BASE}/api/ask/trace-summary?limit=50`);
  expect(summaryResponse.ok()).toBeTruthy();
  const summary = await summaryResponse.json();

  expect(summary.status).toBe('READY');
  expect(summary.tracked).toBe(1);
  expect(summary.route_counts.GENERIC).toBe(1);
  expect(summary.intent_counts.reporting).toBe(1);
  expect(summary.validation_failures).toBe(0);
  expect(summary.error_count).toBe(0);
  expect(summary.avg_latency_ms).toBeGreaterThanOrEqual(0);
  expect(summary.p95_latency_ms).toBeGreaterThanOrEqual(0);
});
