function nonEmptyString(value, max = 5000) {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= max
}

function safeHttpUrl(value) {
  if (value == null || value === '') return true
  try {
    const parsed = new URL(String(value))
    return ['http:', 'https:'].includes(parsed.protocol)
  } catch {
    return false
  }
}

function boundedArray(value, max) {
  return Array.isArray(value) && value.length <= max
}

export function validateAskOutput(answer = {}) {
  const errors = []

  if (!answer || typeof answer !== 'object' || Array.isArray(answer)) {
    return { valid: false, errors: ['answer_not_object'] }
  }

  if (!nonEmptyString(answer.intent, 120)) errors.push('invalid_intent')
  if (!nonEmptyString(answer.take, 5000)) errors.push('invalid_take')
  if (!nonEmptyString(answer.confidence, 160)) errors.push('invalid_confidence')
  if (!nonEmptyString(answer.status, 160)) errors.push('invalid_status')

  if (!boundedArray(answer.why, 20)) errors.push('invalid_why')
  if (!boundedArray(answer.risk, 20)) errors.push('invalid_risk')
  if (!boundedArray(answer.sources, 20)) errors.push('invalid_sources')
  if (!boundedArray(answer.cards, 20)) errors.push('invalid_cards')
  if (!boundedArray(answer.followups, 12)) errors.push('invalid_followups')

  for (const source of Array.isArray(answer.sources) ? answer.sources : []) {
    if (!source || typeof source !== 'object' || Array.isArray(source)) {
      errors.push('invalid_source_object')
      continue
    }
    if (!safeHttpUrl(source.url)) errors.push('unsafe_source_url')
  }

  if (answer.claim_sources != null) {
    if (!boundedArray(answer.claim_sources, 30)) {
      errors.push('invalid_claim_sources')
    } else {
      for (const row of answer.claim_sources) {
        if (!row || typeof row !== 'object' || Array.isArray(row)) {
          errors.push('invalid_claim_source_object')
          continue
        }
        if (!nonEmptyString(row.claim, 5000)) errors.push('invalid_claim_text')
        if (!nonEmptyString(row.source || row.label, 240)) errors.push('invalid_claim_source_label')
        if (!safeHttpUrl(row.url)) errors.push('unsafe_claim_source_url')
      }
    }
  }

  const status = String(answer.status || '').toUpperCase()
  const confidence = String(answer.confidence || '').toUpperCase()
  const intent = String(answer.intent || '').toLowerCase()

  if (status === 'STALE_SOURCE') {
    if (intent !== 'reporting_stale') errors.push('stale_intent_mismatch')
    if (!confidence.includes('STALE')) errors.push('stale_confidence_mismatch')
  }

  if (status === 'SOURCE_CONFLICT') {
    if (intent !== 'reporting_conflict') errors.push('conflict_intent_mismatch')
    if (!confidence.includes('SOURCE CONFLICT')) errors.push('conflict_confidence_mismatch')
  }

  if (status === 'CURRENT' && intent === 'reporting') {
    if (!Array.isArray(answer.sources) || answer.sources.length === 0) errors.push('current_reporting_without_source')
  }

  return {
    valid: errors.length === 0,
    errors: [...new Set(errors)],
  }
}

export function outputValidationFallback(errors = []) {
  const cleanErrors = [...new Set((Array.isArray(errors) ? errors : []).map(value => String(value || '')).filter(Boolean))]
  return {
    intent: 'output_guardrail',
    take: 'The sports analyst withheld an invalid answer before it reached the app.',
    confidence: 'WITHHELD',
    status: 'OUTPUT_VALIDATION_FAILED',
    why: ['The generated response failed the Sports Zenith output contract.'],
    risk: ['No malformed or internally inconsistent answer was shown as valid sports intelligence.'],
    sources: [],
    cards: [],
    updated_at: null,
    followups: ['Try the question again'],
    validation_errors: cleanErrors.slice(0, 8),
  }
}
