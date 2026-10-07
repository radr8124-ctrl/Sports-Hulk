function evidenceTime(row = {}, kind = 'event') {
  return kind === 'fact'
    ? row.effective_at || row.ingested_at || null
    : row.published_or_effective_at || row.generated_at || null
}

function evidenceId(row = {}, kind = 'event') {
  return kind === 'fact'
    ? row.fact_id || row.source_record_id || null
    : row.event_node_id || row.source_record_id || null
}

export function reportingEvidenceSource(row = {}, kind = 'event') {
  const label = String(row.source || 'Sports reporting')
  return {
    label,
    source: label,
    url: row.source_url || null,
    updated_at: evidenceTime(row, kind),
    tier: row.source_tier || null,
    evidence_type: kind.toUpperCase(),
    evidence_id: evidenceId(row, kind),
  }
}

export function reportingEvidenceSources(events = [], facts = [], limit = 8) {
  const rows = [
    ...(Array.isArray(events) ? events : []).map(row => ({ row, kind: 'event' })),
    ...(Array.isArray(facts) ? facts : []).map(row => ({ row, kind: 'fact' })),
  ]

  const sources = []
  const seen = new Set()

  for (const item of rows) {
    if (!item.row) continue
    const source = reportingEvidenceSource(item.row, item.kind)
    const key = [
      source.source,
      source.url || '',
      source.evidence_id || '',
    ].join('|')
    if (seen.has(key)) continue
    seen.add(key)
    sources.push(source)
    if (sources.length >= limit) break
  }

  return sources
}

export function reportingClaimSources(events = [], facts = []) {
  const claims = []

  for (const fact of (Array.isArray(facts) ? facts : []).slice(0, 2)) {
    if (!fact?.fact_text) continue
    claims.push({
      claim: fact.fact_text,
      ...reportingEvidenceSource(fact, 'fact'),
    })
  }

  for (const event of (Array.isArray(events) ? events : []).slice(0, 3)) {
    const eventSource = reportingEvidenceSource(event, 'event')
    if (event?.title) {
      claims.push({
        claim: event.title,
        ...eventSource,
      })
    }
    if (event?.detail && event.detail !== event.title) {
      claims.push({
        claim: event.detail,
        ...eventSource,
      })
    }
  }

  return claims
}
