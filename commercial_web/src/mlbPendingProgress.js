// Exact-source MLB forward research progress for the compact Brain Record panel.
// This is NOT the official published-bets record, a sportsbook void report,
// or proof of a settled real-money wager.
const integer = value => Number.isSafeInteger(value) && value >= 0

export function mlbPendingProgress(brain) {
  const root = brain?.forward_results_accountability
  const props = root?.by_sport?.MLB?.PROPS
  if (!props) return null

  const keys = ['entries', 'settled', 'wins', 'losses', 'pending']
  if (!keys.every(key => integer(props[key]))) return null
  if (props.settled + props.pending !== props.entries) return null
  if (props.wins + props.losses + (props.pushes || 0) !== props.settled) return null

  const detail = root.mlb_official_pending_breakdown || props.official_pending_breakdown
  const sourceValid = (
    detail?.status === 'SOURCE_RECONCILED' &&
    detail.pending_total === props.pending &&
    detail.settled_total === props.settled &&
    ['awaiting_official_final', 'unverified_player_participation',
      'unverified_pregame_capture', 'other_source_holds',
      'verified_ready_next_batch'].every(key => integer(detail[key])) &&
    detail.awaiting_official_final + detail.unverified_player_participation +
      detail.unverified_pregame_capture + detail.other_source_holds +
      detail.verified_ready_next_batch === props.pending
  )
  return {
    tracked: props.entries,
    settled: props.settled,
    wins: props.wins,
    losses: props.losses,
    pending: props.pending,
    overdue: integer(props.pending_overdue_12h) ? props.pending_overdue_12h : null,
    sourceValid,
    sourceTime: sourceValid ? detail.official_receipt_generated_at : null,
    awaitingFinal: sourceValid ? detail.awaiting_official_final : null,
    participationHold: sourceValid ? detail.unverified_player_participation : null,
    pregameHold: sourceValid ? detail.unverified_pregame_capture : null,
    otherHold: sourceValid ? detail.other_source_holds : null,
    readyToGrade: sourceValid ? detail.verified_ready_next_batch : null,
    sourceStatus: detail?.status || 'OFFICIAL_RECEIPT_NOT_AVAILABLE',
  }
}
