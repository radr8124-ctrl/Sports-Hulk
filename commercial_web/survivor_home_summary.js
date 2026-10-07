function humanize(value) {
  return String(value || '').replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, letter => letter.toUpperCase())
}

export function survivorHomeSummary({ signedIn = false, privateState = {}, genericState = {} } = {}) {
  const hasEntry = Boolean(signedIn && privateState?.entry_linked)
  if (!hasEntry) {
    return signedIn
      ? {
          status: 'NO POOL',
          title: 'No Survivor pool linked',
          detail: 'Your account is ready; personal pool state appears only after a secure link.',
          tone: 'blue',
        }
      : {
          status: 'SIGN IN',
          title: `Week ${genericState?.pool_current_week ?? '—'} generic research`,
          detail: 'Sign in for private used teams, saved picks and pool-specific guidance.',
          tone: 'blue',
        }
  }

  const linkedCount = Number(privateState?.linked_entry_count || 1)
  const allocations = Array.isArray(privateState?.diversified_allocations)
    ? privateState.diversified_allocations
    : []
  const actionable = allocations.filter(row => row?.team)

  if (linkedCount > 1) {
    if (actionable.length) {
      return {
        status: 'DIVERSIFIED',
        title: `${linkedCount} entries · diversified plan ready`,
        detail: actionable
          .slice(0, 3)
          .map(row => `${row.entry_name} → ${row.team}`)
          .join(' · '),
        tone: 'emerald',
      }
    }

    return {
      status: 'WAITING',
      title: `Week ${privateState?.pool_current_week ?? genericState?.pool_current_week ?? '—'} multi-entry plan locked`,
      detail: allocations.length
        ? allocations.slice(0, 2).map(row => `${row.entry_name}: ${humanize(row.status || 'WAITING')}`).join(' · ')
        : humanize(privateState?.rule_status || 'Personal pool rule is still waiting'),
      tone: 'amber',
    }
  }

  const survivorPick = Array.isArray(privateState?.shadow_recommendation)
    ? privateState.shadow_recommendation[0]
    : null
  const ready = Boolean(privateState?.rule_confirmed)

  return {
    status: ready ? 'READY' : 'WAITING',
    title: survivorPick?.team
      || `Week ${privateState?.pool_current_week ?? genericState?.pool_current_week ?? '—'} personal decision locked`,
    detail: ready
      ? `${privateState?.active_entry || 'Active entry'} · ${survivorPick?.market_prob_pct ?? '—'}% market survival`
      : humanize(privateState?.rule_status || 'Personal pool rule is still waiting'),
    tone: ready ? 'emerald' : 'amber',
  }
}
