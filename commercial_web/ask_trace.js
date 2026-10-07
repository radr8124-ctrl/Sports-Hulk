import { appendFile, readFile } from 'node:fs/promises'
import { createHash, randomUUID } from 'node:crypto'

function hash(value) {
  return createHash('sha256').update(String(value || ''), 'utf8').digest('hex')
}

function count(value) {
  return Array.isArray(value) ? value.length : 0
}

export function newAskTraceId() {
  return randomUUID()
}

export function buildAskTraceRecord({
  traceId,
  question,
  context = {},
  routeLane = 'GENERIC',
  sessionResolved = false,
  answer = null,
  outputValidation = null,
  latencyMs = null,
  error = null,
} = {}) {
  const cleanQuestion = String(question || '').trim().replace(/\s+/g, ' ')

  return {
    recorded_at: new Date().toISOString(),
    trace_id: String(traceId || ''),
    question_hash: cleanQuestion ? hash(cleanQuestion.toLowerCase()) : null,
    page: String(context?.page || '').slice(0, 80) || null,
    has_game_context: Boolean(context?.game_context?.event_id),
    session_reference_resolved: Boolean(sessionResolved),
    route_lane: String(routeLane || 'GENERIC').slice(0, 80),
    intent: answer?.intent || null,
    status: error ? 'ERROR' : answer?.status || null,
    confidence: error ? 'ERROR' : answer?.confidence || null,
    source_count: count(answer?.sources),
    claim_source_count: count(answer?.claim_sources),
    card_count: count(answer?.cards),
    output_validation_valid: outputValidation?.valid === true,
    output_validation_error_count: count(outputValidation?.errors),
    output_validation_errors: Array.isArray(outputValidation?.errors)
      ? outputValidation.errors.map(value => String(value || '')).filter(Boolean).slice(0, 8)
      : [],
    latency_ms: Number.isFinite(Number(latencyMs)) ? Math.max(0, Math.round(Number(latencyMs))) : null,
    error: Boolean(error),
    error_name: error?.name ? String(error.name).slice(0, 120) : null,
  }
}

export async function appendAskTrace(tracePath, record) {
  await appendFile(tracePath, JSON.stringify(record) + '\n', { encoding: 'utf8', mode: 0o600 })
}

export async function askTraceSummary(tracePath, limit = 500) {
  let raw = ''
  try {
    raw = await readFile(tracePath, 'utf8')
  } catch {
    return { status: 'NO_DATA', tracked: 0 }
  }

  const rows = raw
    .split(/\r?\n/)
    .filter(Boolean)
    .slice(-Math.max(1, Math.min(Number(limit) || 500, 5000)))
    .flatMap(line => {
      try { return [JSON.parse(line)] } catch { return [] }
    })

  if (!rows.length) return { status: 'NO_DATA', tracked: 0 }

  const routeCounts = {}
  const intentCounts = {}
  for (const row of rows) {
    const lane = String(row.route_lane || 'UNKNOWN')
    routeCounts[lane] = (routeCounts[lane] || 0) + 1
    const intent = String(row.intent || 'UNKNOWN')
    intentCounts[intent] = (intentCounts[intent] || 0) + 1
  }

  const latencies = rows.map(row => Number(row.latency_ms)).filter(Number.isFinite)
  const sortedLatencies = [...latencies].sort((a, b) => a - b)
  const percentile = (p) => {
    if (!sortedLatencies.length) return null
    const index = Math.min(sortedLatencies.length - 1, Math.max(0, Math.ceil(p * sortedLatencies.length) - 1))
    return sortedLatencies[index]
  }

  const validationFailures = rows.filter(row => row.output_validation_valid === false).length
  const errors = rows.filter(row => row.error === true).length
  const sessionResolved = rows.filter(row => row.session_reference_resolved === true).length

  return {
    status: 'READY',
    tracked: rows.length,
    route_counts: routeCounts,
    intent_counts: intentCounts,
    validation_failures: validationFailures,
    error_count: errors,
    session_reference_resolved_count: sessionResolved,
    avg_latency_ms: latencies.length ? Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length) : null,
    p95_latency_ms: percentile(0.95),
    generated_at: new Date().toISOString(),
  }
}
