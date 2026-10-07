import { writeFile, unlink } from 'node:fs/promises'

const evalPath = '/tmp/sports-hulk-golden-summary-eval.jsonl'
const clickPath = '/tmp/sports-hulk-golden-summary-click.jsonl'

await unlink(evalPath).catch(() => {})
await unlink(clickPath).catch(() => {})
await writeFile(evalPath, JSON.stringify({
  recorded_at: '2026-10-07T12:00:00Z',
  answer_generated_at: 'golden-summary-test',
  intent: 'reporting',
  status: 'CURRENT',
  confidence: 'ENTITY-LINKED REPORTING',
  source_count: 1,
  citation_url_count: 1,
  claim_count: 1,
  supported_claim_count: 1,
  unsupported_claim_count: 0,
  claim_evidence_coverage_pct: 100,
  latency_ms: 25,
  error: false
}) + '\n')

process.env.ASK_EVAL_LEDGER_PATH = evalPath
process.env.ASK_SOURCE_CLICK_LEDGER_PATH = clickPath
process.env.ASK_RETRIEVAL_GOLDEN_PATH = '/home/ubuntu/sports-hulk/reports/ASK_RETRIEVAL_GOLDEN_CURRENT.json'
process.env.PORT = '8536'

await import('../server.js')
