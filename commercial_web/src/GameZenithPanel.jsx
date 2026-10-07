import React, { useEffect, useMemo, useState } from 'react'
import { Activity, AlertTriangle, Brain, ShieldCheck } from 'lucide-react'
import { betDisplayLabel } from './BetMeaning'

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

const teamTokens = (game, side) => {
  const prefix = side === 'AWAY' ? 'away' : 'home'
  return new Set([
    compactToken(game?.[prefix]),
    compactToken(game?.[`${prefix}_abbr`]),
  ].filter(Boolean))
}

const teamMatches = (value, game, side) => {
  const token = compactToken(value)
  return Boolean(token && teamTokens(game, side).has(token))
}

function gameKeyMatches(gameKey, game) {
  const parts = String(gameKey || '').split('|')
  if (parts.length < 3 || !/^\d{4}-\d{2}-\d{2}$/.test(parts[0])) return false
  return isoDate(game?.start_time || game?.gameDate) === parts[0]
    && teamMatches(parts[1], game, 'AWAY')
    && teamMatches(parts[2], game, 'HOME')
}

function gameMarketMatches(row, game, league) {
  if (String(row?.sport || '').toUpperCase() !== String(league || '').toUpperCase()) return false
  if (gameKeyMatches(row?.game_key, game)) return true

  const side = String(row?.selection_key || '').toUpperCase()
  if (!['HOME', 'AWAY'].includes(side)) return false
  if (!row?.event_start || !(game?.start_time || game?.gameDate)) return false
  if (!closeTime(row.event_start, game.start_time || game.gameDate, 10)) return false

  return teamMatches(row.selection, game, side)
}

const sameMarket = (left, right) => compactToken(left) === compactToken(right)

function nflBridgeMatches(row, bridge, game) {
  if (!bridge || !game) return false
  if (!teamMatches(bridge.away_team, game, 'AWAY')) return false
  if (!teamMatches(bridge.home_team, game, 'HOME')) return false
  if (!closeTime(row.event_start, bridge.start_dfs, 10)) return false
  if (compactToken(row.player) !== compactToken(bridge.player_dfs)) return false
  if (!sameMarket(row.market_subtype, bridge.market)) return false
  if (String(row.side || '').toUpperCase() !== String(bridge.side || '').toUpperCase()) return false

  const left = numeric(row.line)
  const right = numeric(bridge.sportsbook_line ?? bridge.dfs_line)
  return left != null && right != null && Math.abs(left - right) < 0.0001
}

function exactPropRows(rows, game, league, nflBridges) {
  const sport = String(league || '').toUpperCase()
  const sportsbook = rows.filter(row =>
    String(row.sport || '').toUpperCase() === sport
    && String(row.lane || '').toUpperCase() === 'PROP'
  )

  if (sport === 'NBA' || sport === 'NHL') {
    return sportsbook.filter(row => gameKeyMatches(row.game_key, game))
  }

  if (sport === 'NFL') {
    const eventIds = new Set()
    for (const row of sportsbook) {
      if ((nflBridges || []).some(bridge => nflBridgeMatches(row, bridge, game))) {
        eventIds.add(String(row.event_id || ''))
      }
    }
    return sportsbook.filter(row => eventIds.has(String(row.event_id || '')))
  }

  return []
}

const decisionLabel = row => {
  const decision = String(row?.shadow_decision || '').toUpperCase()
  if (decision === 'SHADOW_PLAY') return 'PLAY'
  if (decision === 'SHADOW_MONITOR') return 'MONITOR'
  return 'PASS'
}

const decisionTone = label => {
  if (label === 'PLAY') return 'border-emerald-200 bg-emerald-50 text-emerald-700'
  if (label === 'MONITOR') return 'border-amber-200 bg-amber-50 text-amber-700'
  return 'border-slate-200 bg-slate-100 text-slate-700'
}

const reasonText = value => {
  const code = String(value || '').toUpperCase()
  if (!code) return 'The exact proof gate did not clear.'
  if (code.includes('NO_INDEPENDENT_MODEL_EDGE') || code.includes('NO_PROVEN_INDEPENDENT')) {
    return 'The market is not being beaten by an independently proven model edge.'
  }
  if (code.includes('INSUFFICIENT_HISTORY') || code.includes('FORWARD_TRACKING_ONLY')) {
    return 'This lane is still building enough forward evidence to earn a stronger recommendation.'
  }
  if (code.includes('CONTRADICTORY_GAME_SIDES')) {
    return 'The available market evidence contains a side conflict, so Sports Zenith will not force a pick.'
  }
  if (code.includes('PRICE') || code.includes('EV')) {
    return 'The current price or expected-value gate is not strong enough.'
  }
  if (code.includes('QUALITY')) {
    return 'The current source quality gate is not strong enough.'
  }
  return String(value).replaceAll('_', ' ').toLowerCase().replace(/^./, letter => letter.toUpperCase()) + '.'
}

const propKey = row => [
  compactToken(row.player_key || row.player),
  String(row.market_subtype || '').toUpperCase(),
  String(row.side || '').toUpperCase(),
  numeric(row.line) == null ? '' : numeric(row.line).toFixed(4),
].join('|')

function dedupe(rows, keyFn) {
  const map = new Map()
  for (const row of rows) {
    const key = keyFn(row)
    const current = map.get(key)
    const quality = numeric(row.book_count ?? row.data_quality_book_count ?? row.devig_paired_books) || 0
    const currentQuality = numeric(current?.book_count ?? current?.data_quality_book_count ?? current?.devig_paired_books) || 0
    if (!current || quality > currentQuality) map.set(key, row)
  }
  return [...map.values()]
}

const gameRowKey = row => [
  String(row.market || '').toUpperCase(),
  String(row.selection_key || '').toUpperCase(),
  numeric(row.line) == null ? '' : numeric(row.line).toFixed(4),
].join('|')


function DecisionCard({ row, kind }) {
  const label = decisionLabel(row)
  const title = kind === 'PROP'
    ? `${row.player} · ${String(row.side || '').toUpperCase()} ${row.line} · ${String(row.market_subtype || '').replace(/^PLAYER_TOTAL_/i, '').replaceAll('_', ' ')}`
    : betDisplayLabel(row)

  return (
    <article className="min-w-0 max-w-full overflow-hidden rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-black uppercase tracking-[0.12em] text-blue-700">{kind === 'PROP' ? 'Player prop' : String(row.market || '').replaceAll('_', ' ')}</div>
          <div className="mt-1 truncate text-sm font-black text-slate-950">{title}</div>
        </div>
        <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-black ${decisionTone(label)}`}>{label}</span>
      </div>

      <div className="mt-3 text-xs font-semibold leading-5 text-slate-600">
        {reasonText(row.selection_rule_status || row.shadow_decision)}
      </div>
    </article>
  )
}

export default function GameZenithPanel({ game, league, onOpenOdds, onOpenProps }) {
  const [state, setState] = useState({
    loading: true,
    gameMarkets: { picks: [] },
    props: { picks: [] },
    nfl: { props: [] },
    error: '',
  })

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      setState(current => ({ ...current, loading: true, error: '' }))
      try {
        const [gameResponse, propResponse, nflResponse] = await Promise.all([
          fetch(`/betting_v2_all_markets_current.json?ts=${Date.now()}`, { cache: 'no-store' }),
          fetch(`/prop_v2_current.json?ts=${Date.now()}`, { cache: 'no-store' }),
          fetch(`/nfl_decisions.json?ts=${Date.now()}`, { cache: 'no-store' }),
        ])

        if (!gameResponse.ok || !propResponse.ok) throw new Error('Sports Zenith game intelligence is unavailable')
        const [gameMarkets, props] = await Promise.all([gameResponse.json(), propResponse.json()])
        const nfl = nflResponse.ok ? await nflResponse.json() : { props: [] }

        if (!cancelled) {
          setState({
            loading: false,
            gameMarkets,
            props,
            nfl,
            error: '',
          })
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            loading: false,
            gameMarkets: { picks: [] },
            props: { picks: [] },
            nfl: { props: [] },
            error: error?.message || 'Sports Zenith game intelligence is unavailable',
          })
        }
      }
    }

    load()
    return () => { cancelled = true }
  }, [game?.event_id, game?.gamePk, league])

  const matched = useMemo(() => {
    const gameRows = dedupe(
      (state.gameMarkets?.picks || []).filter(row => gameMarketMatches(row, game, league)),
      gameRowKey,
    )

    const propRows = dedupe(
      exactPropRows(state.props?.picks || [], game, league, state.nfl?.props || []),
      propKey,
    )

    const all = [...gameRows, ...propRows]
    const plays = all.filter(row => decisionLabel(row) === 'PLAY')
    const monitors = all.filter(row => decisionLabel(row) === 'MONITOR')
    const passes = all.filter(row => decisionLabel(row) === 'PASS')

    const sortRows = rows => [...rows].sort((a, b) =>
      (numeric(b.conservative_expected_value_pct) ?? numeric(b.conservative_edge_pct_points) ?? -999)
      - (numeric(a.conservative_expected_value_pct) ?? numeric(a.conservative_edge_pct_points) ?? -999)
    )

    return {
      gameRows: sortRows(gameRows),
      propRows: sortRows(propRows),
      plays: sortRows(plays),
      monitors: sortRows(monitors),
      passes: sortRows(passes),
    }
  }, [state.gameMarkets, state.props, state.nfl, game, league])

  if (state.loading) {
    return (
      <div role="status" className="flex items-center gap-3 rounded-3xl border border-slate-200 bg-white p-6 text-sm font-black text-slate-600">
        <Activity size={17} className="animate-pulse text-blue-600" /> Loading Sports Zenith game intelligence…
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

  const totalTracked = matched.gameRows.length + matched.propRows.length
  const headline = matched.plays.length
    ? `${matched.plays.length} PLAY${matched.plays.length === 1 ? '' : 'S'} cleared for this matchup.`
    : matched.monitors.length
      ? `Nothing is a PLAY yet. ${matched.monitors.length} item${matched.monitors.length === 1 ? '' : 's'} ${matched.monitors.length === 1 ? 'remains' : 'remain'} on MONITOR.`
      : totalTracked
        ? 'No proven PLAY for this matchup.'
        : 'No exact Zenith decision rows are attached to this matchup.'

  const posture = matched.plays.length ? 'PLAY' : matched.monitors.length ? 'MONITOR' : 'PASS'

  const uniqueReasons = [...new Set(
    matched.passes
      .map(row => reasonText(row.selection_rule_status || row.shadow_decision))
      .filter(Boolean),
  )].slice(0, 4)

  return (
    <div className="min-w-0 max-w-full space-y-5 overflow-hidden">
      <section className="min-w-0 max-w-full overflow-hidden rounded-[30px] border border-slate-800 bg-slate-950 p-6 text-white shadow-soft">
        <div className="flex flex-col justify-between gap-5 md:flex-row md:items-start">
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.16em] text-emerald-300">
              <Brain size={15} /> Sports Zenith take
            </div>
            <h3 className="mt-3 text-2xl font-black tracking-tight md:text-3xl">{headline}</h3>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              {totalTracked
                ? 'This is the current governed decision state for exact game markets and sportsbook props tied to this matchup. PASS is an answer, not missing analysis.'
                : 'Sports Zenith will not borrow research from another game just to fill this screen.'}
            </p>
          </div>
          <span className={`self-start rounded-full border px-3 py-1.5 text-[10px] font-black ${posture === 'PLAY' ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300' : posture === 'MONITOR' ? 'border-amber-400/30 bg-amber-400/10 text-amber-200' : 'border-slate-600 bg-white/5 text-slate-300'}`}>
            {posture}
          </span>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Game markets</div>
            <div className="mt-2 text-2xl font-black">{matched.gameRows.length}</div>
            <div className="mt-1 text-xs text-slate-400">exact V2 rows</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Player props</div>
            <div className="mt-2 text-2xl font-black">{matched.propRows.length}</div>
            <div className="mt-1 text-xs text-slate-400">exact sportsbook props</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Current posture</div>
            <div className="mt-2 text-2xl font-black">{posture}</div>
            <div className="mt-1 text-xs text-slate-400">{matched.plays.length} play · {matched.monitors.length} monitor · {matched.passes.length} pass</div>
          </div>
        </div>
      </section>

      {!!uniqueReasons.length && !matched.plays.length && (
        <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5">
          <div className="text-[10px] font-black uppercase tracking-[0.14em] text-amber-700">Why Zenith is not forcing a PLAY</div>
          <div className="mt-3 space-y-2">
            {uniqueReasons.map(reason => (
              <div key={reason} className="flex gap-2 text-sm font-semibold leading-6 text-amber-950">
                <ShieldCheck size={16} className="mt-1 shrink-0 text-amber-700" />
                <span>{reason}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="min-w-0 max-w-full">
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[10px] font-black uppercase tracking-[0.14em] text-slate-400">What Zenith is seeing</div>
            <div className="mt-1 text-lg font-black text-slate-950">Exact decisions attached to this matchup</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={onOpenOdds} className="min-h-11 rounded-xl border border-slate-200 bg-white px-4 text-xs font-black text-slate-700">
              Open Odds
            </button>
            <button type="button" onClick={onOpenProps} className="min-h-11 rounded-xl bg-slate-950 px-4 text-xs font-black text-white">
              Open Props
            </button>
          </div>
        </div>

        {totalTracked ? (
          <div className="mt-4 grid min-w-0 max-w-full gap-3 lg:grid-cols-2">
            {matched.gameRows.slice(0, 3).map(row => (
              <DecisionCard key={gameRowKey(row)} row={row} kind="GAME" />
            ))}
            {matched.propRows.slice(0, 3).map(row => (
              <DecisionCard key={propKey(row)} row={row} kind="PROP" />
            ))}
          </div>
        ) : (
          <div className="mt-4 rounded-3xl border border-dashed border-slate-200 bg-white p-6 text-sm font-semibold text-slate-500">
            There is no exact governed V2 game or sportsbook-prop decision attached to this matchup right now.
          </div>
        )}
      </section>
    </div>
  )
}
