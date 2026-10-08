// Research Lab view-model: summarize only real, already published research files.
// Never convert replay, historical diagnostics, or shadow research into OFFICIAL picks.
export function researchSummary({ performance, selectivity, forward, fantasy, ask, health } = {}) {
  const official = performance?.official || null
  const forwardSummary = forward?.summary || null
  const experiments = Array.isArray(selectivity?.threshold_tests) ? selectivity.threshold_tests : null
  const candidates = Array.isArray(selectivity?.actionable) ? selectivity.actionable : null
  const lanes = ['weekly', 'faab', 'ir_stash', 'defense_streaming', 'idp'].map(key => {
    const record = fantasy?.[key] || null
    return {
      key,
      label: ({ weekly: 'Start / Sit', faab: 'Waivers / FAAB', ir_stash: 'IR stash',
        defense_streaming: 'Defense', idp: 'IDP' })[key],
      tracked: safeCount(record?.tracked),
      settled: safeCount(record?.settled),
      proofStatus: record?.proof_status || 'UNKNOWN',
    }
  })
  return {
    official: {
      published: safeCount(official?.published),
      settled: safeCount(official?.settled),
      wins: safeCount(official?.wins),
      losses: safeCount(official?.losses),
      units: safeNumber(official?.units),
      status: official?.status || 'UNKNOWN',
      generatedAt: performance?.generated_at || null,
    },
    forward: {
      tracked: safeCount(forwardSummary?.tracked),
      settled: safeCount(forwardSummary?.settled),
      overdue48h: safeCount(forwardSummary?.pending_overdue_48h),
      status: forward?.status || 'UNKNOWN',
      generatedAt: forward?.generated_at || null,
    },
    calibration: {
      method: selectivity?.method || null,
      thresholdTests: experiments?.length ?? null,
      researchCandidates: candidates?.length ?? null,
      automaticallyChanged: selectivity?.automatic_model_changes === true,
      candidates: candidates ? candidates.slice(0,6).map(c => ({
        sport: String(c.sport || '—'), lane: String(c.lane || '—'),
        market: String(c.market || ''), sample: safeCount(c.sample),
      })) : [],
      generatedAt: selectivity?.generated_at || null,
    },
    fantasy: {
      lanes,
      generatedAt: fantasy?.generated_at || null,
    },
    ask: {
      evaluated: safeCount(ask?.tracked),
      grounded: safeCount(ask?.grounded_current),
      withheld: safeCount(ask?.insufficient_evidence),
      claimSamples: safeCount(ask?.reporting_claim_count),
      supportedClaims: safeCount(ask?.supported_reporting_claim_count),
      retrievalCases: safeCount(ask?.retrieval_golden_cases),
      retrievalPasses: safeCount(ask?.retrieval_golden_passed),
      status: ask?.status || 'UNKNOWN',
    },
    sources: Object.entries(health?.sources || {}).map(([key,exists]) => ({
      key,
      present: exists === true,
    })),
    sourceCheckedAt: health?.generated_at || null,
    sourceHealth: health?.status || 'UNKNOWN',
  }
}

function safeCount(value) {
  if (value === undefined || value === null || value === '') return null
  const number = Number(value)
  return Number.isInteger(number) && number >= 0 ? number : null
}

function safeNumber(value) {
  if (value === undefined || value === null || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}
