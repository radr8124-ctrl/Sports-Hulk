export function allMarketsProofRows(bundle = {}) {
  const current = bundle?.current || {}
  const validation = bundle?.validation?.lanes || {}
  const forward = bundle?.forward || {}

  const currentProof = current.by_proof_lane || {}
  const forwardProof = forward.by_proof_lane || {}
  const proofAware =
    Object.keys(currentProof).length > 0 ||
    Object.keys(forwardProof).length > 0

  const liveView = proofAware ? currentProof : (current.by_lane || {})
  const forwardView = proofAware ? forwardProof : (forward.by_lane || {})

  const validationView = {}
  for (const [key, row] of Object.entries(validation)) {
    if (!proofAware) {
      validationView[key] = row || {}
      continue
    }

    const explicitProofKey = String(row?.proof_lane_key || '').trim()
    const proofKey =
      explicitProofKey ||
      (key.includes('|') || liveView[key] || forwardView[key] ? key : '')

    if (proofKey) validationView[proofKey] = row || {}
  }

  const keys = new Set([
    ...Object.keys(liveView),
    ...Object.keys(validationView),
    ...Object.keys(forwardView),
  ])

  return [...keys]
    .sort((a, b) => a.localeCompare(b))
    .map(key => {
      const live = liveView[key] || {}
      const historical = validationView[key] || {}
      const forwardRow = forwardView[key] || {}
      const pipeIndex = key.indexOf('|')
      const keyLane = pipeIndex >= 0 ? key.slice(0, pipeIndex) : key
      const keyRegime = pipeIndex >= 0 ? key.slice(pipeIndex + 1) : ''

      return {
        key,
        laneKey: live.lane_key || historical.lane_key || keyLane,
        competitionRegime:
          live.competition_regime ||
          historical.competition_regime ||
          keyRegime ||
          null,
        live,
        validation: historical,
        forward: forwardRow,
      }
    })
}
