import React, { useEffect, useMemo, useState } from 'react'
import { Activity, AlertTriangle, ChevronRight, ShieldCheck } from 'lucide-react'
import BetMeaning, { betDisplayLabel, formatAmericanOdds } from './BetMeaning'

const compactToken = value => String(value || '')
  .toLowerCase()
  .replace(/[^a-z0-9]/g, '')

const numeric = value => {
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

const closeTime = (leftValue, rightValue, toleranceMinutes = 10) => {
  const left = new Date(leftValue).getTime()
  const right = new Date(rightValue).getTime()
  if (!Number.isFinite(left) || !Number.isFinite(right)) return false
  return Math.abs(left - right) <= toleranceMinutes * 60 * 1000
}

const isoDate = value => {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString().slice(0, 10)
}

const sideTokens = (game, side) => {
  const prefix = side === 'AWAY' ? 'away' : 'home'
  return new Set([
    compactToken(game?.[prefix]),
    compactToken(game?.[`${prefix}_abbr`]),
  ].filter(Boolean))
}

const matchesTeam = (value, game, side) => {
  const token = compactToken(value)
  return Boolean(token && sideTokens(game, side).has(token))
}

function gameKeyMatches(row, game) {
  const parts = String(row?.game_key || '').split('|')
  if (parts.length < 3 || !/^\d{4}-\d{2}-\d{2}$/.test(parts[0])) return false
  return isoDate(game?.start_time || game?.gameDate) === parts[0]
    && matchesTeam(parts[1], game, 'AWAY')
    && matchesTeam(parts[2], game, 'HOME')
}

const sameMarket = (left, right) => compactToken(left) === compactToken(right)

function nflBridgeMatches(row, bridge, game) {
  if (!bridge || !game) return false
  if (!matchesTeam(bridge.away_team, game, 'AWAY')) return false
  if (!matchesTeam(bridge.home_team, game, 'HOME')) return false
  if (!closeTime(row.event_start, bridge.start_dfs, 10)) return false
  if (compactToken(row.player) !== compactToken(bridge.player_dfs)) return false
  if (!sameMarket(row.market_subtype, bridge.market)) return false
  if (String(row.side || '').toUpperCase() !== String(bridge.side || '').toUpperCase()) return false

  const rowLine = numeric(row.line)
  const bridgeLine = numeric(bridge.sportsbook_line ?? bridge.dfs_line)
  return rowLine != null && bridgeLine != null && Math.abs(rowLine - bridgeLine) < 0.0001
}

function matchPropRows(rows, game, league, nflBridges) {
  const sport = String(league || '').toUpperCase()
  const sportsbookRows = rows.filter(row =>
    String(row.sport || '').toUpperCase() === sport
    && String(row.lane || '').toUpperCase() === 'PROP'
  )

  if (sport === 'NBA' || sport === 'NHL') {
    return sportsbookRows.filter(row => gameKeyMatches(row, game))
  }

  if (sport === 'NFL') {
    const matchedEventIds = new Set()
    for (const row of sportsbookRows) {
      if ((nflBridges || []).some(bridge => nflBridgeMatches(row, bridge, game))) {
        matchedEventIds.add(String(row.event_id || ''))
      }
    }
    return sportsbookRows.filter(row => matchedEventIds.has(String(row.event_id || '')))
  }

  return []
}

const propKey = row => [
  compactToken(row.player_key || row.player),
  String(row.market_subtype || '').toUpperCase(),
  String(row.side || '').toUpperCase(),
  numeric(row.line) == null ? '' : numeric(row.line).toFixed(4),
].join('|')

function dedupeProps(rows) {
  const best = new Map()
  for (const row of rows) {
    const key = propKey(row)
    const current = best.get(key)
    const rowQuality = numeric(row.data_quality_book_count) || numeric(row.devig_paired_books) || 0
    const currentQuality = numeric(current?.data_quality_book_count) || numeric(current?.devig_paired_books) || 0
    if (!current || rowQuality > currentQuality) best.set(key, row)
  }
  return [...best.values()]
}

const decisionRank = row => {
  const decision = String(row?.shadow_decision || '').toUpperCase()
  if (decision === 'SHADOW_PLAY') return 3
  if (decision === 'SHADOW_MONITOR') return 2
  return 1
}

const statusFor = row => {
  const decision = String(row?.shadow_decision || '').toUpperCase()
  if (decision === 'SHADOW_PLAY') return { label: 'PLAY', tone: 'bg-emerald-50 text-emerald-700 border-emerald-100' }
  if (decision === 'SHADOW_MONITOR') return { label: 'MONITOR', tone: 'bg-amber-50 text-amber-700 border-amber-100' }
  return { label: 'PASS', tone: 'bg-slate-100 text-slate-700 border-slate-200' }
}

const humanizeMetric = value => String(value || 'Player prop')
  .replace(/^PLAYER_TOTAL_/i, '')
  .replaceAll('_+_', ' + ')
  .replaceAll('_', ' ')
  .toLowerCase()
  .replace(/\brec\b/g, 'receiving')
  .replace(/\brush\b/g, 'rushing')
  .replace(/\bpass\b/g, 'passing')
  .replace(/\bthrees\b/g, 'three-pointers')
  .replace(/\b\w/g, letter => letter.toUpperCase())


function PropCard({ row }) {
  const status = statusFor(row)
  const displayRow = { ...row, market: 'PROP' }

  return (
    <article className="min-w-0 rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-black uppercase tracking-[0.14em] text-blue-700">
            {humanizeMetric(row.market_subtype)}
          </div>
          <div className="mt-2 truncate text-xl font-black tracking-tight text-slate-950">{row.player}</div>
          <div className="mt-1 text-lg font-black text-slate-800">
            {String(row.side || '').toUpperCase()} {row.line}
          </div>
          {formatAmericanOdds(row.american_odds) && (
            <div className="mt-1 text-sm font-black text-slate-500">{formatAmericanOdds(row.american_odds)}</div>
          )}
        </div>
        <span className={`shrink-0 rounded-full border px-3 py-1 text-[10px] font-black ${status.tone}`}>
          {status.label}
        </span>
      </div>

      <div className="mt-4">
        <BetMeaning row={displayRow} compact />
      </div>

      <details className="group mt-4 rounded-2xl border border-slate-200 bg-white">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-xs font-black text-slate-700">
          <span>View evidence</span>
          <ChevronRight size={16} className="shrink-0 text-slate-400 transition-transform group-open:rotate-90" />
        </summary>
        <div className="border-t border-slate-100 px-4 pb-4 pt-4">
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="font-black text-slate-950">{row.v2_probability_pct ?? '—'}%</div>
              <div className="mt-1 text-slate-400">Zenith</div>
            </div>
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="font-black text-slate-950">{row.market_reference_probability_pct ?? '—'}%</div>
              <div className="mt-1 text-slate-400">Market</div>
            </div>
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="font-black text-slate-950">{row.conservative_probability_pct ?? '—'}%</div>
              <div className="mt-1 text-slate-400">Conservative</div>
            </div>
          </div>

          <div className="mt-3 text-[11px] font-semibold leading-5 text-slate-500">
            Quality {row.data_quality_grade || '—'} · {row.data_quality_book_count ?? row.devig_paired_books ?? '—'} books · {String(row.historical_edge_confidence || '').replaceAll('_', ' ')}
          </div>
          <div className="mt-2 text-[11px] leading-5 text-slate-400">
            {String(row.selection_rule_status || row.shadow_decision || '').replaceAll('_', ' ')}
          </div>
        </div>
      </details>
    </article>
  )
}

export default function GamePropsPanel({ game, league }) {
  const [state, setState] = useState({
    loading: true,
    props: { picks: [] },
    nfl: { props: [] },
    error: '',
  })

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      setState(current => ({ ...current, loading: true, error: '' }))
      try {
        const [propResponse, nflResponse] = await Promise.all([
          fetch(`/prop_v2_current.json?ts=${Date.now()}`, { cache: 'no-store' }),
          fetch(`/nfl_decisions.json?ts=${Date.now()}`, { cache: 'no-store' }),
        ])

        if (!propResponse.ok) throw new Error('Current prop research is unavailable')
        const propPayload = await propResponse.json()
        const nflPayload = nflResponse.ok ? await nflResponse.json() : { props: [] }

        if (!cancelled) {
          setState({
            loading: false,
            props: propPayload,
            nfl: nflPayload,
            error: '',
          })
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            loading: false,
            props: { picks: [] },
            nfl: { props: [] },
            error: error?.message || 'Current prop research is unavailable',
          })
        }
      }
    }

    load()
    return () => { cancelled = true }
  }, [game?.event_id, game?.gamePk, league])

  const rows = useMemo(() => {
    return dedupeProps(
      matchPropRows(state.props?.picks || [], game, league, state.nfl?.props || []),
    )
      .sort((a, b) =>
        decisionRank(b) - decisionRank(a)
        || (numeric(b.conservative_edge_pct_points) ?? -999) - (numeric(a.conservative_edge_pct_points) ?? -999)
        || (numeric(b.v2_probability_pct) ?? -999) - (numeric(a.v2_probability_pct) ?? -999)
      )
      .slice(0, 18)
  }, [state.props, state.nfl, game, league])

  if (state.loading) {
    return (
      <div role="status" className="flex items-center gap-3 rounded-3xl border border-slate-200 bg-white p-6 text-sm font-black text-slate-600">
        <Activity size={17} className="animate-pulse text-blue-600" /> Loading exact-game props…
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

  if (!rows.length) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-200 bg-white p-6">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
          <ShieldCheck size={20} />
        </div>
        <h3 className="mt-4 text-xl font-black text-slate-950">No exact sportsbook props are attached to this game</h3>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Sports Zenith only shows a player prop here when the current prop row can be tied to this exact matchup. A matching start time by itself is not enough.
        </p>
        <p className="mt-2 max-w-2xl text-xs font-semibold leading-5 text-slate-400">
          PrizePicks remains a separate product because pick-em entry economics are not the same as sportsbook prop pricing.
        </p>
      </div>
    )
  }

  const plays = rows.filter(row => String(row.shadow_decision).toUpperCase() === 'SHADOW_PLAY').length
  const monitors = rows.filter(row => String(row.shadow_decision).toUpperCase() === 'SHADOW_MONITOR').length

  return (
    <div className="space-y-5">
      <div className="rounded-3xl border border-blue-100 bg-blue-50/70 p-5">
        <div className="text-[10px] font-black uppercase tracking-[0.14em] text-blue-700">Exact-game player props</div>
        <h3 className="mt-2 text-xl font-black text-slate-950">Player line first. Meaning second. Evidence underneath.</h3>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          {rows.length} sportsbook prop row{rows.length === 1 ? '' : 's'} matched to this exact game · {plays} PLAY · {monitors} MONITOR. PASS is a valid answer.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {rows.map(row => <PropCard key={propKey(row)} row={row} />)}
      </div>
    </div>
  )
}
