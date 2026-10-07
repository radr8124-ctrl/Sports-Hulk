import { mkdir, writeFile } from 'node:fs/promises'

const BASE = process.env.ASK_BASE || 'http://127.0.0.1:8537'
const OUT = process.env.ASK_SEMANTIC_OUT || '/home/ubuntu/sports-hulk/reports/ASK_SEMANTIC_ANSWER_GOLDEN_CURRENT.json'

function includesText(value, needle) {
  return String(value || '').toLowerCase().includes(String(needle || '').toLowerCase())
}

function mappedClaim(answer, claim) {
  return (Array.isArray(answer?.claim_sources) ? answer.claim_sources : [])
    .some(row => String(row?.claim || '').trim() === String(claim || '').trim())
}

const cases = [
  {
    id: 'current-fact-answer',
    question: 'What is the report on Orion Vale?',
    check(answer) {
      const checks = {
        intent: answer.intent === 'reporting',
        status: answer.status === 'CURRENT',
        take: answer.take === 'Orion Vale is listed as the starting slot receiver for Test City.',
        evidence: mappedClaim(answer, answer.take),
        source: (answer.sources || []).some(row => row.evidence_id === 'FACT:orion-vale-role'),
      }
      return checks
    },
  },
  {
    id: 'multi-source-consensus-answer',
    question: 'What is the latest injury update on Consensus Runner?',
    check(answer) {
      return {
        intent: answer.intent === 'reporting',
        status: answer.status === 'CURRENT',
        confidence: answer.confidence === 'MULTI-SOURCE AGREEMENT',
        agreement: answer.source_agreement?.source_count === 2,
        claim: answer.source_agreement?.claim === 'Consensus Runner returned to full practice.',
      }
    },
  },
  {
    id: 'stale-answer-withheld',
    question: 'What is Semantic Stale Runner injury status?',
    check(answer) {
      return {
        intent: answer.intent === 'reporting_stale',
        status: answer.status === 'STALE_SOURCE',
        confidence: answer.confidence === 'STALE / VERIFY',
        take: includesText(answer.take, 'fresh enough verified reporting'),
        restraint: (answer.risk || []).some(row => includesText(row, 'will not relabel stale evidence as current')),
      }
    },
  },
  {
    id: 'conflict-answer-withheld',
    question: 'What is Conflict Back injury status?',
    check(answer) {
      return {
        intent: answer.intent === 'reporting_conflict',
        status: answer.status === 'SOURCE_CONFLICT',
        confidence: answer.confidence === 'SOURCE CONFLICT / VERIFY',
        take: includesText(answer.take, 'sources disagree'),
        restraint: (answer.risk || []).some(row => includesText(row, 'will not silently choose one conflicting source')),
      }
    },
  },
  {
    id: 'unknown-answer-refuses-invention',
    question: 'What is Nebula Quarterback injury status?',
    check(answer) {
      return {
        status: answer.status === 'INSUFFICIENT_EVIDENCE',
        confidence: String(answer.confidence || '').toUpperCase() === 'INSUFFICIENT EVIDENCE',
        restraint: includesText(answer.take, "don't have enough verified information"),
        no_sources: (answer.sources || []).length === 0,
      }
    },
  },
]

const results = []
for (const item of cases) {
  const response = await fetch(`${BASE}/api/ask`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ question: item.question, context: { page: 'Ask' } }),
  })
  const answer = await response.json()
  const checks = item.check(answer)
  const passed = response.ok && Object.values(checks).every(Boolean)
  results.push({
    id: item.id,
    passed,
    intent: answer.intent || null,
    status: answer.status || null,
    confidence: answer.confidence || null,
    checks,
  })
}

const passed = results.filter(row => row.passed).length
const report = {
  status: passed === results.length ? 'PASS' : 'FAIL',
  generated_at: new Date().toISOString(),
  benchmark: 'DETERMINISTIC_SEMANTIC_ANSWER_GOLDEN_SET',
  cases: results.length,
  passed,
  semantic_answer_pass_pct: Number(((passed / results.length) * 100).toFixed(1)),
  results,
}

await mkdir(new URL('../reports/', import.meta.url), { recursive: true }).catch(() => {})
await writeFile(OUT, JSON.stringify(report, null, 2) + '\n', 'utf8')
console.log(JSON.stringify(report, null, 2))

if (report.status !== 'PASS') process.exitCode = 1
