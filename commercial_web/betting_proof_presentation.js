// Read-only translation of the existing model decisions into useful, plain
// language. Do not change candidate qualification or invent research proof.
const MIN_HISTORY_ROWS = 50
const MIN_INDEPENDENT_GAMES = 25

function nonnegativeInteger(value) {
  if (value === null || value === undefined || value === '') return null
  const n = Number(value)
  return Number.isInteger(n) && n >= 0 ? n : null
}

export function explainBetProof(row = {}, byProofLane = {}) {
  const isPlay = row.shadow_decision === 'SHADOW_PLAY'
  const proof = byProofLane[row.proof_lane_key] || byProofLane[row.lane_key] || {}
  const observed = nonnegativeInteger(proof.history_n ?? row.lane_history_n ?? row.sport_history_n)
  const independent = nonnegativeInteger(proof.independent_blocks)
  const code = String(row.selection_rule_status || '')

  if (isPlay) {
    return {
      kind: 'SHADOW_PLAY', label: 'Shadow play', isPlay: true,
      estimateLabel: 'Zenith probability',
      description: 'Qualified for forward paper testing. This is not a wager submitted to a sportsbook.',
      historyCount: observed, independentGameCount: independent,
    }
  }

  if (code === 'INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY' || code.includes('INSUFFICIENT_HISTORY')) {
    const parts = [
      observed === null
        ? `At least ${MIN_HISTORY_ROWS} settled, pregame-priced outcomes are required`
        : `${observed} of ${MIN_HISTORY_ROWS} pregame outcomes recorded`,
      independent === null
        ? `at least ${MIN_INDEPENDENT_GAMES} separate games are also required`
        : `${independent} of ${MIN_INDEPENDENT_GAMES} separate games`,
    ]
    return {
      kind: 'HISTORY_BUILDING', label: 'Building history', isPlay: false,
      estimateLabel: 'Market-based estimate',
      description: `Not a recommended bet: ${parts.join(' across ')}. The model has not yet shown a tested edge over market prices.`,
      historyCount: observed, independentGameCount: independent,
    }
  }

  if (code === 'NO_INDEPENDENT_MODEL_EDGE') {
    return {
      kind: 'NO_PROVEN_EDGE', label: 'No proven edge', isPlay: false,
      estimateLabel: 'Market-based estimate',
      description: 'The available history was tested, but Zenith did not beat the market baseline. No profitable advantage is established for this selection.',
      historyCount: observed, independentGameCount: independent,
    }
  }

  if (code === 'CALIBRATION_ONLY_NO_INDEPENDENT_EDGE') {
    return {
      kind: 'MARKET_CALIBRATION_ONLY', label: 'Market calibration only', isPlay: false,
      estimateLabel: 'Market-based estimate',
      description: 'The market probability calibration has research value, but no separate betting edge has been proven.',
      historyCount: observed, independentGameCount: independent,
    }
  }

  if (code === 'FORWARD_VALIDATION_REQUIRED' || code.includes('UNCERTAIN')) {
    return {
      kind: 'FORWARD_PROOF_PENDING', label: 'Forward proof pending', isPlay: false,
      estimateLabel: 'Research estimate',
      description: 'Some historical signal exists, but future pregame predictions must be tested before this is a verified play.',
      historyCount: observed, independentGameCount: independent,
    }
  }

  return {
    kind: 'RESEARCH_ONLY', label: 'Research only', isPlay: false,
    estimateLabel: 'Market-based estimate',
    description: 'The required independent betting proof has not cleared. Research status does not make this a recommended wager.',
    historyCount: observed, independentGameCount: independent,
  }
}

export function organizeBetResearch(rows = [], sport = 'ALL', market = 'ALL') {
  const filtered = (Array.isArray(rows) ? rows : []).filter(row =>
    (sport === 'ALL' || row.sport === sport)
    && (market === 'ALL' || row.market === market)
  )
  const plays = filtered.filter(row => row.shadow_decision === 'SHADOW_PLAY')
  const research = filtered.filter(row => row.shadow_decision !== 'SHADOW_PLAY')
  return { plays, research, count: filtered.length }
}
