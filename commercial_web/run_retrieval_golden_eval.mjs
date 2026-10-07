import { mkdir, writeFile } from 'node:fs/promises'

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8535'
const OUT = process.env.ASK_GOLDEN_OUT || '/home/ubuntu/sports-hulk/reports/ASK_RETRIEVAL_GOLDEN_CURRENT.json'

const cases = [
  {
    id: 'atlas-martin-exact',
    question: 'What is the latest injury update on Atlas Martin?',
    expectedEvidenceIds: ['NEWS:atlas-martin'],
    forbiddenEvidenceIds: ['NEWS:martin-solo'],
    requiredText: 'Atlas Martin',
    expectedIntent: 'reporting',
  },
  {
    id: 'martin-solo-exact',
    question: 'What is the latest injury update on Martin Solo?',
    expectedEvidenceIds: ['NEWS:martin-solo'],
    forbiddenEvidenceIds: ['NEWS:atlas-martin'],
    requiredText: 'Martin Solo',
    expectedIntent: 'reporting',
  },
  {
    id: 'consensus-runner-recall',
    question: 'What is the latest injury update on Consensus Runner?',
    expectedEvidenceIds: ['NEWS:consensus-official', 'NEWS:consensus-beat'],
    forbiddenEvidenceIds: [],
    requiredText: 'Consensus Runner',
    expectedIntent: 'reporting',
    expectedConfidence: 'MULTI-SOURCE AGREEMENT',
  },
  {
    id: 'orion-vale-fact',
    question: 'What is the report on Orion Vale?',
    expectedEvidenceIds: ['FACT:orion-vale-role'],
    forbiddenEvidenceIds: [],
    requiredText: 'Orion Vale',
    expectedIntent: 'reporting',
  },
  {
    id: 'unknown-subject-restraint',
    question: 'What is Nebula Quarterback injury status?',
    expectedEvidenceIds: [],
    forbiddenEvidenceIds: [
      'NEWS:atlas-martin',
      'NEWS:martin-solo',
      'NEWS:consensus-official',
      'NEWS:consensus-beat',
      'FACT:orion-vale-role',
    ],
    requiredText: '',
    expectedStatus: 'INSUFFICIENT_EVIDENCE',
  },
]

const results = []
let expectedTotal = 0
let truePositiveTotal = 0
let returnedPositiveTotal = 0

for (const item of cases) {
  const response = await fetch(`${BASE}/api/ask`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      question: item.question,
      context: { page: 'Ask' },
    }),
  })

  const body = await response.json()
  const returnedEvidenceIds = [...new Set(
    (Array.isArray(body.claim_sources) ? body.claim_sources : [])
      .map(row => String(row?.evidence_id || '').trim())
      .filter(Boolean)
  )]

  const expected = new Set(item.expectedEvidenceIds)
  const returned = new Set(returnedEvidenceIds)
  const truePositives = item.expectedEvidenceIds.filter(id => returned.has(id))
  const unexpected = returnedEvidenceIds.filter(id => !expected.has(id))
  const forbiddenHits = item.forbiddenEvidenceIds.filter(id => returned.has(id))
  const answerText = JSON.stringify({
    take: body.take,
    why: body.why,
    cards: body.cards,
    claim_sources: body.claim_sources,
  })

  const recallOk = item.expectedEvidenceIds.every(id => returned.has(id))
  const precisionOk = forbiddenHits.length === 0 && unexpected.length === 0
  const textOk = !item.requiredText || answerText.includes(item.requiredText)
  const intentOk = !item.expectedIntent || body.intent === item.expectedIntent
  const statusOk = !item.expectedStatus || body.status === item.expectedStatus
  const confidenceOk = !item.expectedConfidence || body.confidence === item.expectedConfidence
  const passed = response.ok && recallOk && precisionOk && textOk && intentOk && statusOk && confidenceOk

  if (item.expectedEvidenceIds.length) {
    expectedTotal += item.expectedEvidenceIds.length
    truePositiveTotal += truePositives.length
    returnedPositiveTotal += returnedEvidenceIds.length
  }

  results.push({
    id: item.id,
    passed,
    intent: body.intent || null,
    status: body.status || null,
    confidence: body.confidence || null,
    expected_evidence_ids: item.expectedEvidenceIds,
    returned_evidence_ids: returnedEvidenceIds,
    forbidden_hits: forbiddenHits,
    unexpected_evidence_ids: unexpected,
    relevance_pass: textOk && intentOk && statusOk && confidenceOk,
  })
}

const positivePrecision = returnedPositiveTotal
  ? Number(((truePositiveTotal / returnedPositiveTotal) * 100).toFixed(1))
  : null
const recall = expectedTotal
  ? Number(((truePositiveTotal / expectedTotal) * 100).toFixed(1))
  : null
const relevancePassed = results.filter(row => row.relevance_pass).length
const passed = results.filter(row => row.passed).length

const report = {
  status: passed === results.length ? 'PASS' : 'FAIL',
  generated_at: new Date().toISOString(),
  benchmark: 'DETERMINISTIC_SYNTHETIC_GOLDEN_SET',
  cases: results.length,
  passed,
  retrieval_recall_pct: recall,
  retrieval_precision_pct: positivePrecision,
  answer_relevance_pct: Number(((relevancePassed / results.length) * 100).toFixed(1)),
  expected_evidence_count: expectedTotal,
  recovered_expected_evidence_count: truePositiveTotal,
  returned_positive_evidence_count: returnedPositiveTotal,
  results,
}

await mkdir(new URL('../reports/', import.meta.url), { recursive: true }).catch(() => {})
await writeFile(OUT, JSON.stringify(report, null, 2) + '\n', 'utf8')
console.log(JSON.stringify(report, null, 2))

if (report.status !== 'PASS') process.exitCode = 1
