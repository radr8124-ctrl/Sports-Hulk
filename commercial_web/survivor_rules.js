// The verified season-wide pick count is separate from the weekly entry list.
import { readFileSync } from 'node:fs'
const path = new URL('../nfl_live/survivor_pool/2026_KNOCKOUT_RULES.json', import.meta.url)
let policy = null
try { policy = JSON.parse(readFileSync(path, 'utf8')) } catch { policy = null }

export function resolveWeekPickRule(week, state = {}) {
  const entry = state && typeof state === 'object' ? state : {}
  const w = Number(week)
  const known = policy && Number.isInteger(w) && w >= 1 && w <= Number(policy.regular_season_weeks)
    ? (policy.double_pick_weeks.includes(w) ? 2 : Number(policy.default_required_picks)) : null
  const raw = entry.required_picks
  const declared = raw === null || raw === undefined || raw === '' ? null : Number(raw)
  const declaredCount = Number.isInteger(declared) && declared > 0 ? declared : null
  const sheetStatus = String(entry.rule_status || '')
  const hasSheet = entry.official_pool_sheet_confirmed === true || sheetStatus.startsWith('CONFIRMED_FROM_IMPORTED_POOL_')
  if (known !== null) {
    if (declaredCount !== null && declaredCount !== known) return {
      required_picks: null, rule_confirmed: false, rule_status: 'RULE_SOURCE_CONFLICT_REVIEW_REQUIRED',
      rule_source: policy.source, official_pool_sheet_confirmed: hasSheet,
    }
    return {
      required_picks: known,
      rule_confirmed: true,
      rule_status: hasSheet && sheetStatus.startsWith('CONFIRMED_') ? sheetStatus : 'CONFIRMED_FROM_2026_ORIGINAL_RULES',
      rule_source: policy.source,
      official_pool_sheet_confirmed: hasSheet,
    }
  }
  return {
    required_picks: declaredCount, rule_confirmed: Boolean(declaredCount && hasSheet),
    rule_status: sheetStatus || 'AWAITING_VERIFIED_RULES', rule_source: null,
    official_pool_sheet_confirmed: hasSheet,
  }
}
