function num(value, fallback = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

export function survivorFutureValueOptions(candidates = [], usedTeams = [], limit = 5) {
  const used = new Set(Array.isArray(usedTeams) ? usedTeams : [])
  return [...(Array.isArray(candidates) ? candidates : [])]
    .filter(row => row?.team && !used.has(row.team))
    .sort((a, b) =>
      num(b.future_value_index) - num(a.future_value_index)
      || num(b.strategy_index) - num(a.strategy_index)
    )
    .slice(0, Math.max(1, Number(limit) || 5))
}

export function survivorSaveForLater(candidates = [], usedTeams = []) {
  const options = survivorFutureValueOptions(candidates, usedTeams, 5)
  const top = options[0] || null

  if (!top || num(top.future_value_index) <= 0) {
    return {
      status: 'NO_CLEAR_SAVE_VALUE',
      top: null,
      options,
    }
  }

  return {
    status: 'SAVE_VALUE_AVAILABLE',
    top,
    options,
  }
}
