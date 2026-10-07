function clean(value) {
  return String(value || '').trim().replace(/\s+/g, ' ')
}

export function askClaimCoverage(answer = {}) {
  const intent = String(answer?.intent || '').toUpperCase()
  if (intent !== 'REPORTING') {
    return {
      eligible: false,
      claim_count: 0,
      supported_claim_count: 0,
      unsupported_claim_count: 0,
      claim_evidence_coverage_pct: null,
    }
  }

  const claims = []
  const seenClaims = new Set()
  for (const value of [answer?.take, ...(Array.isArray(answer?.why) ? answer.why : [])]) {
    const claim = clean(value)
    if (!claim || seenClaims.has(claim)) continue
    seenClaims.add(claim)
    claims.push(claim)
  }

  const mapped = new Set(
    (Array.isArray(answer?.claim_sources) ? answer.claim_sources : [])
      .map(row => clean(row?.claim))
      .filter(Boolean)
  )

  const supported = claims.filter(claim => mapped.has(claim)).length
  const unsupported = Math.max(0, claims.length - supported)

  return {
    eligible: true,
    claim_count: claims.length,
    supported_claim_count: supported,
    unsupported_claim_count: unsupported,
    claim_evidence_coverage_pct: claims.length
      ? Math.round((supported / claims.length) * 1000) / 10
      : null,
  }
}
