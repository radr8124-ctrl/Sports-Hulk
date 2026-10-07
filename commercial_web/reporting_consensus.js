function normalizeClaim(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s'-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function trustedTier(value) {
  const tier = String(value || '').toUpperCase()
  if (!tier) return false
  if (/COMMUNITY|SOCIAL|USER|FORUM|REDDIT/.test(tier)) return false
  return /OFFICIAL|EXTERNAL_NEWS|TRUSTED|BEAT|NEWS/.test(tier)
}

function sourceIdentity(row = {}) {
  try {
    const url = new URL(String(row.source_url || ''))
    if (['http:', 'https:'].includes(url.protocol) && url.hostname) {
      return url.hostname.toLowerCase().replace(/^www\./, '')
    }
  } catch {}

  return String(row.source || '').trim().toLowerCase()
}

function evidenceRows(events = [], facts = []) {
  return [
    ...(Array.isArray(events) ? events : []).map(row => ({
      claim: row?.detail || row?.title || '',
      source: row?.source || '',
      source_tier: row?.source_tier || '',
      source_url: row?.source_url || null,
      evidence_id: row?.event_node_id || row?.source_record_id || null,
      evidence_type: 'EVENT',
    })),
    ...(Array.isArray(facts) ? facts : []).map(row => ({
      claim: row?.fact_text || '',
      source: row?.source || '',
      source_tier: row?.source_tier || '',
      source_url: row?.source_url || null,
      evidence_id: row?.fact_id || row?.source_record_id || null,
      evidence_type: 'FACT',
    })),
  ]
}

export function reportingConsensus(events = [], facts = []) {
  const groups = new Map()

  for (const row of evidenceRows(events, facts)) {
    const normalized = normalizeClaim(row.claim)
    const identity = sourceIdentity(row)
    if (!normalized || !identity || !trustedTier(row.source_tier)) continue

    const group = groups.get(normalized) || {
      claim: String(row.claim || '').trim(),
      source_ids: new Set(),
      sources: [],
      evidence_ids: [],
    }

    if (!group.source_ids.has(identity)) {
      group.source_ids.add(identity)
      group.sources.push({
        source: row.source,
        source_tier: row.source_tier,
        source_url: row.source_url,
        source_identity: identity,
        evidence_type: row.evidence_type,
      })
    }

    if (row.evidence_id && !group.evidence_ids.includes(row.evidence_id)) {
      group.evidence_ids.push(row.evidence_id)
    }

    groups.set(normalized, group)
  }

  const ranked = [...groups.values()]
    .filter(group => group.source_ids.size >= 2)
    .sort((a, b) => b.source_ids.size - a.source_ids.size || b.evidence_ids.length - a.evidence_ids.length)

  if (!ranked.length) {
    return {
      status: 'NO_MULTI_SOURCE_AGREEMENT',
      source_count: 0,
      claim: null,
      sources: [],
      evidence_ids: [],
    }
  }

  const top = ranked[0]
  return {
    status: 'MULTI_SOURCE_AGREEMENT',
    source_count: top.source_ids.size,
    claim: top.claim,
    sources: top.sources,
    evidence_ids: top.evidence_ids,
  }
}
