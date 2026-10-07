export function faabBudgetLines(budget = {}) {
  if (!budget?.connected) return []
  return [
    `Saved FAAB remaining ${budget.remaining_budget ?? '—'} of ${budget.total_budget ?? '—'} (${budget.remaining_pct_of_total ?? '—'}% left).`,
    `Saved-budget translation ${budget.research_low_units ?? '—'}–${budget.research_high_units ?? '—'} units · ${String(budget.budget_pressure || 'UNKNOWN').replaceAll('_', ' ')}.`,
  ]
}
