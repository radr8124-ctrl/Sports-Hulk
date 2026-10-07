import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8510';
const FAILED_PATH = '/tmp/sports-hulk-output-validation-failed.jsonl';

test('unsafe Ask output is withheld at final API boundary and queued for review', async ({ request }) => {
  const response = await request.post(`${BASE}/api/ask`, {
    data: {
      question: 'What is the injury update on Unsafe Source Runner?',
      context: { page: 'Ask' },
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();

  expect(body.intent).toBe('output_guardrail');
  expect(body.status).toBe('OUTPUT_VALIDATION_FAILED');
  expect(body.confidence).toBe('WITHHELD');
  expect(body.sources).toEqual([]);
  expect(body.validation_errors).toContain('unsafe_source_url');
  expect(JSON.stringify(body)).not.toContain('javascript:alert');

  const raw = await readFile(FAILED_PATH, 'utf8');
  const rows = raw.trim().split(/\r?\n/).map(line => JSON.parse(line));
  expect(rows.some(row => row.status === 'OUTPUT_VALIDATION_FAILED')).toBeTruthy();
});
