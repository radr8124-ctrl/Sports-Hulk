import React, { useEffect, useMemo, useState } from 'react'
import { Activity, AlertTriangle, ChevronRight, ShieldCheck } from 'lucide-react'
import BetMeaning, { betDisplayLabel, formatAmericanOdds } from './BetMeaning'

const compactToken = value => String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '')

const numeric = value => {
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

const isoDate = value => {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString().slice(0, 10)
}

const closeTime = (leftValue, rightValue, toleranceMinutes = 10) => {
  const left = new Date(leftValue).getTime()
  const right = new Date(rightValue).getTime()
  if (!Number.isFinite(left) || !Number.isFinite(right)) return false
  return Math.abs(left - right) <= toleranceMinutes * 60 * 1000
}

const sideTokens = (game, side) => {
  const prefix = side === 'AWAY' ? 'away' : 'home'
  return new Set([
    compactToken(game?.[prefix]),
    compactToken(game?.[`${prefix}_abbr`]),
  ].filter(Boolean))
}

const matchesSide = (token, game, side) => {
  const normalized = compactToken(token)
  return Boolean(normalized && sideTokens(game, side).has(normalized))
}

function parseEventIdentity(value) {
  const parts = String(value || '').split('|')
  if (parts[0] === 'GAME' && parts[1]?.includes('@')) {
    const [away, home] = parts[1].split('@')
    return { date: '', start: '', away, home }
  }
  if (parts[0] === 'DATE' && parts.length >= 4) {
    return { date: parts[1], start: '', away: parts[2], home: parts[3] }
  }
  if (parts[0] === 'START' && parts.length >= 4) {
    return { date: String(parts[1]).slice(0, 10), start: parts[1], away: parts[2], home: parts[3] }
  }
  return null
}

function identityMatchesGame(identity, game) {
  const parsed = parseEventIdentity(identity)
  if (!parsed || !game) return false
  if (!matchesSide(parsed.away, game, 'AWAY') || !matchesSide(parsed.home, game, 'HOME')) return false

  if (parsed.date) {
    const gameDate = isoDate(game.start_time || game.gameDate)
    if (!gameDate || gameDate !== parsed.date) return false
  }

  if (parsed.start && game.start_time && !closeTime(parsed.start, game.start_time, 10)) return false
  return true
}

function gameKeyMatchesGame(gameKey, game) {
  const parts = String(gameKey || '').split('|')
  if (parts.length < 3 || !/^\d{4}-\d{2}-\d{2}$/.test(parts[0])) return false
  return isoDate(game?.start_time || game?.gameDate) === parts[0]
    && matchesSide(parts[1], game, 'AWAY')
    && matchesSide(parts[2], game, 'HOME')
}

function v2MatchesGame(row, game, league) {
  if (String(row?.sport || '').toUpperCase() !== String(league || '').toUpperCase()) return false
  if (gameKeyMatchesGame(row?.game_key, game)) return true

  const side = String(row?.selection_key || '').toUpperCase()
  if (!['HOME', 'AWAY'].includes(side)) return false
  if (!row?.event_start || !(game?.start_time || game?.gameDate)) return false
  if (!closeTime(row.event_start, game.start_time || game.gameDate, 10)) return false
  return matchesSide(row.selection, game, side)
}

const lineKey = value => {
  const number = numeric(value)
  return number == null ? '' : number.toFixed(4)
}

const marketKey = row => [
  String(row?.market || '').toUpperCase(),
  String(row?.selection_key || '').toUpperCase(),
  lineKey(row?.line),
].join('|')

function dedupeV2Rows(rows) {
  const best = new Map()
  for (const row of rows) {
    const key = marketKey(row)
    const current = best.get(key)
    if (!current || (numeric(row.book_count) || 0) > (numeric(current.book_count) || 0)) {
      best.set(key, row)
    }
  }
  return [...best.values()]
}

function selectMoneyline(rows) {
  const marketRows = rows.filter(row => String(row.market).toUpperCase() === 'MONEYLINE')
  const pick = side => marketRows
    .filter(row => String(row.selection_key).toUpperCase() === side)
    .sort((a, b) => (numeric(b.paired_books) || 0) - (numeric(a.paired_books) || 0))[0]
  return [pick('AWAY'), pick('HOME')].filter(Boolean)
}

function selectSpread(rows) {
  const spreadRows = rows.filter(row => String(row.market).toUpperCase() === 'SPREAD' && numeric(row.line) != null)
  const candidates = []
  for (const away of spreadRows.filter(row => String(row.selection_key).toUpperCase() === 'AWAY')) {
    for (const home of spreadRows.filter(row => String(row.selection_key).toUpperCase() === 'HOME')) {
      if (Math.abs((numeric(away.line) || 0) + (numeric(home.line) || 0)) > 0.0001) continue
      const minBooks = Math.min(numeric(away.paired_books) || 0, numeric(home.paired_books) || 0)
      const totalBooks = (numeric(away.paired_books) || 0) + (numeric(home.paired_books) || 0)
      candidates.push({ rows: [away, home], score: minBooks * 1000 + totalBooks })
    }
  }
  candidates.sort((a, b) => b.score - a.score)
  return candidates[0]?.rows || []
}

function selectTotal(rows) {
  const totalRows = rows.filter(row => String(row.market).toUpperCase() === 'TOTAL' && numeric(row.line) != null)
  const candidates = []
  for (const over of totalRows.filter(row => String(row.selection_key).toUpperCase() === 'OVER')) {
    for (const under of totalRows.filter(row => String(row.selection_key).toUpperCase() === 'UNDER')) {
      if (Math.abs((numeric(over.line) || 0) - (numeric(under.line) || 0)) > 0.0001) continue
      const minBooks = Math.min(numeric(over.paired_books) || 0, numeric(under.paired_books) || 0)
      const totalBooks = (numeric(over.paired_books) || 0) + (numeric(under.paired_books) || 0)
      candidates.push({ rows: [over, under], score: minBooks * 1000 + totalBooks })
    }
  }
  candidates.sort((a, b) => b.score - a.score)
  return candidates[0]?.rows || []
}

function statusFromV2(row) {
  if (!row) return { label: 'MARKET ONLY', tone: 'bg-blue-50 text-blue-700 border-blue-100' }
  const decision = String(row.shadow_decision || '').toUpperCase()
  if (decision === 'SHADOW_PLAY') return { label: 'PLAY', tone: 'bg-emerald-50 text-emerald-700 border-emerald-100' }
  if (decision === 'SHADOW_MONITOR') return { label: 'MONITOR', tone: 'bg-amber-50 text-amber-700 border-amber-100' }
  return { label: 'PASS', tone: 'bg-slate-100 text-slate-700 border-slate-200' }
}

function displaySelection(entry, game) {
  const side = String(entry.selection_key || '').toUpperCase()
  if (side === 'HOME') return game.home || game.home_abbr || 'Home'
  if (side === 'AWAY') return game.away || game.away_abbr || 'Away'
  if (side === 'OVER') return 'OVER'
  if (side === 'UNDER') return 'UNDER'
  return side || 'Market'
}

function toDisplayRow(entry, game) {
  return {
    market: entry.market,
    selection_key: entry.selection_key,
    selection: displaySelection(entry, game),
    line: entry.line,
    american_odds: entry.median_selected_odds,
  }
}

function MarketCard({ row, v2 }) {
  const status = statusFromV2(v2)
  const fair = numeric(row.fair_probability)
  const pairedBooks = numeric(row.paired_books)

  return (
    <article className="min-w-0 rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-black uppercase tracking-[0.14em] text-blue-700">
            {String(row.market || '').replaceAll('_', ' ')}
          </div>
          <div className="mt-2 truncate text-xl font-black tracking-tight text-slate-950">{betDisplayLabel(row)}</div>
          <div className="mt-1 text-sm font-black text-slate-600">{formatAmericanOdds(row.american_odds) || 'Price unavailable'}</div>
        </div>
        <span className={`shrink-0 rounded-full border px-3 py-1 text-[10px] font-black ${status.tone}`}>
          {status.label}
        </span>
      </div>

      <div className="mt-4">
        <BetMeaning row={row} compact />
      </div>

      <details className="group mt-4 rounded-2xl border border-slate-200 bg-white">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-xs font-black text-slate-700">
          <span>View market evidence</span>
          <ChevronRight size={16} className="shrink-0 text-slate-400 transition-transform group-open:rotate-90" />
        </summary>
        <div className="border-t border-slate-100 px-4 pb-4 pt-4 text-xs leading-5 text-slate-600">
          <div className="grid grid-cols-2 gap-2 text-center">
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="font-black text-slate-950">{fair == null ? '—' : `${(fair * 100).toFixed(1)}%`}</div>
              <div className="mt-1 text-slate-400">De-vig fair</div>
            </div>
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="font-black text-slate-950">{pairedBooks ?? '—'}</div>
              <div className="mt-1 text-slate-400">Paired books</div>
            </div>
          </div>
          <div className="mt-3 text-[11px] font-semibold text-slate-500">
            Consensus price is the median selected price across paired books in the current snapshot. It is not advertised as the best sportsbook price.
          </div>
          {v2 ? (
            <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
              <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Sports Zenith V2</div>
              <div className="mt-1 font-black text-slate-800">
                {status.label} · {String(v2.selection_rule_status || v2.shadow_decision || '').replaceAll('_', ' ')}
              </div>
            </div>
          ) : (
            <div className="mt-3 text-[11px] font-semibold text-slate-400">
              No V2 recommendation is attached to this exact market row. Market information is shown without turning it into a pick.
            </div>
          )}
        </div>
      </details>
    </article>
  )
}

function V2FallbackCard({ row }) {
  const status = statusFromV2(row)

  return (
    <article className="min-w-0 rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-black uppercase tracking-[0.14em] text-blue-700">
            {String(row.market || '').replaceAll('_', ' ')}
          </div>
          <div className="mt-2 truncate text-xl font-black tracking-tight text-slate-950">{betDisplayLabel(row)}</div>
          <div className="mt-1 text-sm font-black text-slate-600">{formatAmericanOdds(row.american_odds) || 'Price unavailable'}</div>
        </div>
        <span className={`shrink-0 rounded-full border px-3 py-1 text-[10px] font-black ${status.tone}`}>
          {status.label}
        </span>
      </div>

      <div className="mt-4">
        <BetMeaning row={row} compact />
      </div>

      <details className="group mt-4 rounded-2xl border border-slate-200 bg-white">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-xs font-black text-slate-700">
          <span>View Zenith evidence</span>
          <ChevronRight size={16} className="shrink-0 text-slate-400 transition-transform group-open:rotate-90" />
        </summary>
        <div className="border-t border-slate-100 px-4 pb-4 pt-4">
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="font-black text-slate-950">{row.calibrated_win_probability_pct ?? '—'}%</div>
              <div className="mt-1 text-slate-400">Zenith probability</div>
            </div>
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="font-black text-slate-950">{row.market_reference_probability_pct ?? '—'}%</div>
              <div className="mt-1 text-slate-400">Market fair</div>
            </div>
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="font-black text-slate-950">{row.conservative_expected_value_pct == null ? '—' : `${row.conservative_expected_value_pct}%`}</div>
              <div className="mt-1 text-slate-400">Conservative EV</div>
            </div>
          </div>
          <div className="mt-3 text-[11px] font-semibold leading-5 text-slate-500">
            {row.book_count ?? '—'} books · {String(row.selection_rule_status || row.shadow_decision || '').replaceAll('_', ' ')}
          </div>
        </div>
      </details>
    </article>
  )
}

export default function GameOddsPanel({ game, league }) {
  const [state, setState] = useState({ loading: true, devig: {}, v2: { picks: [] }, error: '' })

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setState(current => ({ ...current, loading: true, error: '' }))
      try {
        const [devigResponse, v2Response] = await Promise.all([
          fetch(`/betting_v2_all_market_devig.json?ts=${Date.now()}`, { cache: 'no-store' }),
          fetch(`/betting_v2_all_markets_current.json?ts=${Date.now()}`, { cache: 'no-store' }),
        ])
        if (!devigResponse.ok || !v2Response.ok) throw new Error('Current game market research is unavailable')
        const [devig, v2] = await Promise.all([devigResponse.json(), v2Response.json()])
        if (!cancelled) setState({ loading: false, devig, v2, error: '' })
      } catch (error) {
        if (!cancelled) {
          setState({
            loading: false,
            devig: {},
            v2: { picks: [] },
            error: error?.message || 'Current game market research is unavailable',
          })
        }
      }
    }
    load()
    return () => { cancelled = true }
  }, [game?.event_id, game?.gamePk, league])

  const matched = useMemo(() => {
    const leagueKey = String(league || '').toUpperCase()
    const current = state.devig?.current?.[leagueKey] || {}
    const devigRows = Object.values(current).filter(row => identityMatchesGame(row.event_identity, game))
    const v2Rows = dedupeV2Rows(
      (state.v2?.picks || []).filter(row => v2MatchesGame(row, game, leagueKey)),
    )

    const selectedDevig = [
      ...selectMoneyline(devigRows),
      ...selectSpread(devigRows),
      ...selectTotal(devigRows),
    ]

    const v2ByMarket = new Map(v2Rows.map(row => [marketKey(row), row]))
    const marketRows = selectedDevig.map(entry => {
      const display = toDisplayRow(entry, game)
      return {
        display,
        fair_probability: entry.fair_probability,
        paired_books: entry.paired_books,
        v2: v2ByMarket.get(marketKey(display)) || null,
      }
    })

    const represented = new Set(marketRows.map(item => marketKey(item.display)))
    const fallback = v2Rows.filter(row => !represented.has(marketKey(row)))

    return { marketRows, fallback }
  }, [state.devig, state.v2, game, league])

  if (state.loading) {
    return (
      <div role="status" className="flex items-center gap-3 rounded-3xl border border-slate-200 bg-white p-6 text-sm font-black text-slate-600">
        <Activity size={17} className="animate-pulse text-blue-600" /> Loading current game markets…
      </div>
    )
  }

  if (state.error) {
    return (
      <div className="flex gap-3 rounded-3xl border border-amber-200 bg-amber-50 p-5 text-sm font-semibold text-amber-900">
        <AlertTriangle size={18} className="mt-0.5 shrink-0" /> {state.error}
      </div>
    )
  }

  const hasRows = matched.marketRows.length > 0 || matched.fallback.length > 0

  if (!hasRows) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-200 bg-white p-6">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
          <ShieldCheck size={20} />
        </div>
        <h3 className="mt-4 text-xl font-black text-slate-950">No exact market snapshot is attached to this game</h3>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Sports Zenith could not prove an exact current matchup join for Moneyline, Spread or Total, so the Odds tab is staying empty instead of borrowing a line from another game.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="rounded-3xl border border-blue-100 bg-blue-50/70 p-5">
        <div className="text-[10px] font-black uppercase tracking-[0.14em] text-blue-700">Connected game markets</div>
        <h3 className="mt-2 text-xl font-black text-slate-950">Understand the line before the evidence</h3>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          Paired-book market consensus is shown first when an exact matchup is available. Sports Zenith V2 status is overlaid only when the exact market row is also being evaluated. Missing markets stay missing.
        </p>
      </div>

      {!!matched.marketRows.length && (
        <div>
          <div className="mb-3 text-[10px] font-black uppercase tracking-[0.14em] text-slate-400">Paired-book market snapshot</div>
          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
            {matched.marketRows.map(({ display, fair_probability, paired_books, v2 }) => (
              <MarketCard
                key={marketKey(display)}
                row={{ ...display, fair_probability, paired_books }}
                v2={v2}
              />
            ))}
          </div>
        </div>
      )}

      {!!matched.fallback.length && (
        <div>
          <div className="mb-3 text-[10px] font-black uppercase tracking-[0.14em] text-slate-400">Additional Zenith-tracked market rows</div>
          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
            {matched.fallback.map(row => <V2FallbackCard key={marketKey(row)} row={row} />)}
          </div>
        </div>
      )}

      <div className="text-[11px] font-semibold leading-5 text-slate-400">
        This is a Sports Zenith-connected market snapshot, not a complete sportsbook board. Consensus price is not labeled “best odds” unless a future live provider explicitly proves that.
      </div>
    </div>
  )
}
