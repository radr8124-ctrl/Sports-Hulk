function firstBoolean(...values) {
  for (const value of values) {
    if (value === true || value === false) return value
  }
  return null
}

export function survivorBuybackState(entry = {}, poolState = {}) {
  const entryStatus = String(entry?.status || '').toUpperCase()
  if (entryStatus && entryStatus !== 'ELIMINATED') {
    return {
      status: 'NOT_APPLICABLE_ACTIVE_ENTRY',
      eligible: false,
      recorded: true,
      reason: 'Entry is still active.',
    }
  }

  const record =
    (entry?.buyback && typeof entry.buyback === 'object' ? entry.buyback : null)
    || (entry?.reentry && typeof entry.reentry === 'object' ? entry.reentry : null)
    || (entry?.buyback_state && typeof entry.buyback_state === 'object' ? entry.buyback_state : null)
    || (entry?.reentry_state && typeof entry.reentry_state === 'object' ? entry.reentry_state : null)

  const poolRules =
    (poolState?.buyback_rules && typeof poolState.buyback_rules === 'object' ? poolState.buyback_rules : {})
  const eligible = firstBoolean(
    record?.eligible,
    record?.allowed,
    record?.available,
    entry?.buyback_eligible,
    entry?.reentry_eligible,
  )

  const hasRecord = Boolean(record) || eligible !== null

  if (!hasRecord) {
    return {
      status: 'NO_VERIFIED_BUYBACK_STATE',
      eligible: null,
      recorded: false,
      reason: 'No explicit buyback or re-entry state is recorded for this entry.',
    }
  }

  if (eligible !== true) {
    return {
      status: 'BUYBACK_NOT_ELIGIBLE',
      eligible: false,
      recorded: true,
      reason: record?.reason || 'Recorded buyback/re-entry state does not mark this entry eligible.',
      deadline: record?.deadline || poolRules?.deadline || null,
      cost: record?.cost ?? poolRules?.cost ?? null,
      reentry_week: record?.reentry_week ?? null,
    }
  }

  return {
    status: 'BUYBACK_ELIGIBLE_RECORDED',
    eligible: true,
    recorded: true,
    reason: record?.reason || 'Explicit buyback/re-entry eligibility is recorded.',
    deadline: record?.deadline || poolRules?.deadline || null,
    cost: record?.cost ?? poolRules?.cost ?? null,
    reentry_week: record?.reentry_week ?? null,
    reset_used_teams: record?.reset_used_teams === true,
  }
}
