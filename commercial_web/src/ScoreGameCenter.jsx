import React, { useEffect, useState } from 'react'
import {
  Activity, AlertTriangle, BarChart3, Brain, ChevronRight, Newspaper,
  Radio, Sparkles, Target, Trophy,
} from 'lucide-react'

const GameOddsPanel = React.lazy(() => import('./GameOddsPanel'))
const GamePropsPanel = React.lazy(() => import('./GamePropsPanel'))
const GameZenithPanel = React.lazy(() => import('./GameZenithPanel'))
const GameNewsPanel = React.lazy(() => import('./GameNewsPanel'))

const TABS = [
  ['Overview', Trophy],
  ['Box Score', BarChart3],
  ['Odds', Target],
  ['Props', Radio],
  ['Zenith', Brain],
  ['News', Newspaper],
]

const formatStart = value => {
  if (!value) return 'Time TBD'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString([], {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function StatusPill({ game }) {
  const label = game?.live ? 'LIVE' : game?.final ? 'FINAL' : 'UPCOMING'
  const tone = game?.live
    ? 'bg-rose-50 text-rose-700 border-rose-100'
    : game?.final
      ? 'bg-slate-100 text-slate-700 border-slate-200'
      : 'bg-blue-50 text-blue-700 border-blue-100'

  return <span className={`rounded-full border px-3 py-1 text-[10px] font-black ${tone}`}>{label}</span>
}

function TeamRow({ name, abbr, score, record, logo, pregame }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      {logo
        ? <img src={logo} alt="" className="h-10 w-10 shrink-0 object-contain" />
        : <div className="h-10 w-10 shrink-0 rounded-full bg-slate-100" />}
      <div className="min-w-0 flex-1">
        <div className="truncate text-base font-black text-slate-950">{name || abbr || 'Team'}</div>
        <div className="mt-0.5 text-[11px] font-semibold text-slate-400">{record || abbr || 'Record unavailable'}</div>
      </div>
      <div className="shrink-0 text-2xl font-black text-slate-950">{pregame ? '—' : (score ?? '—')}</div>
    </div>
  )
}

function GameOverview({ game, league }) {
  const pregame = !game?.live && !game?.final
  const gameClock = game?.live
    ? [game.period ? `Period ${game.period}` : null, game.clock || null].filter(Boolean).join(' · ')
    : null

  return (
    <div className="grid gap-4 lg:grid-cols-[1.15fr_.85fr]">
      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex items-center justify-between gap-3">
          <div className="text-[10px] font-black uppercase tracking-[0.14em] text-blue-700">{league} game</div>
          <StatusPill game={game} />
        </div>

        <div className="mt-5 space-y-4">
          <TeamRow
            name={game.away}
            abbr={game.away_abbr}
            score={game.away_score}
            record={game.away_record}
            logo={game.away_logo}
            pregame={pregame}
          />
          <div className="border-t border-slate-100" />
          <TeamRow
            name={game.home}
            abbr={game.home_abbr}
            score={game.home_score}
            record={game.home_record}
            logo={game.home_logo}
            pregame={pregame}
          />
        </div>

        <div className="mt-5 rounded-2xl bg-slate-50 p-4 text-sm font-semibold text-slate-600">
          {gameClock || game.status || formatStart(game.start_time)}
        </div>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-slate-950 p-5 text-white shadow-soft">
        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.14em] text-emerald-300">
          <Sparkles size={14} /> Game snapshot
        </div>
        <div className="mt-4 space-y-3 text-sm">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Status</div>
            <div className="mt-1 font-black">{game.status || (pregame ? formatStart(game.start_time) : 'Current')}</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Venue</div>
            <div className="mt-1 font-black">{game.venue || 'Venue unavailable'}</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-[10px] font-black uppercase tracking-wide text-slate-400">Watch</div>
            <div className="mt-1 font-black">{game.broadcasts?.length ? game.broadcasts.join(' · ') : 'Broadcast unavailable'}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

function BoxScoreContent({ league, eventId, available }) {
  const [state, setState] = useState({ loading: Boolean(available), error: '', data: null })

  useEffect(() => {
    let cancelled = false

    if (!available || !eventId) {
      setState({ loading: false, error: '', data: null })
      return () => { cancelled = true }
    }

    const load = async () => {
      setState({ loading: true, error: '', data: null })
      try {
        const response = await fetch(`/api/boxscore?league=${encodeURIComponent(league)}&event=${encodeURIComponent(eventId)}`, { cache: 'no-store' })
        const payload = await response.json()
        if (!response.ok) throw new Error(payload.error || 'Box score unavailable')
        if (!cancelled) setState({ loading: false, error: '', data: payload })
      } catch (error) {
        if (!cancelled) setState({ loading: false, error: error?.message || 'Box score unavailable', data: null })
      }
    }

    load()
    return () => { cancelled = true }
  }, [league, eventId, available])

  if (!available) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-200 bg-white p-6 text-sm font-semibold text-slate-500">
        Detailed box-score data is not available for this game yet.
      </div>
    )
  }

  if (state.loading) {
    return (
      <div role="status" className="flex items-center gap-3 rounded-3xl border border-slate-200 bg-white p-6 text-sm font-black text-slate-600">
        <Activity size={17} className="animate-pulse text-blue-600" /> Loading box score…
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

  const data = state.data
  if (!data) return null

  const teams = data.teams || []
  const statLabels = Array.from(new Set(teams.flatMap(team => (team.stats || []).map(stat => stat.label)))).slice(0, 8)
  const byTeam = team => Object.fromEntries((team.stats || []).map(stat => [stat.label, stat.value]))

  return (
    <div className="space-y-5">
      {!!statLabels.length && (
        <div className="overflow-x-auto rounded-3xl border border-slate-200 bg-white shadow-soft">
          <table className="w-full min-w-[620px] text-xs">
            <thead className="bg-slate-50 text-slate-400">
              <tr>
                <th className="px-4 py-3 text-left font-black">Team</th>
                {statLabels.map(label => <th key={label} className="px-4 py-3 text-right font-black">{label}</th>)}
              </tr>
            </thead>
            <tbody>
              {teams.map(team => {
                const stats = byTeam(team)
                return (
                  <tr key={team.abbreviation || team.team} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-black text-slate-800">{team.abbreviation || team.team}</td>
                    {statLabels.map(label => <td key={label} className="px-4 py-3 text-right font-semibold text-slate-600">{stats[label] ?? '—'}</td>)}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {!!data.leaders?.length && (
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="text-[10px] font-black uppercase tracking-[0.14em] text-slate-400">Game leaders</div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {data.leaders.slice(0, 12).map((leader, index) => (
              <div key={`${leader.team}-${leader.category}-${index}`} className="flex min-w-0 items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-black text-slate-900">{leader.player || '—'}</div>
                  <div className="mt-0.5 text-[10px] font-semibold text-slate-400">{leader.team} · {leader.category}</div>
                </div>
                <div className="shrink-0 text-sm font-black text-blue-700">{leader.value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {(data.venue || data.attendance) && (
        <div className="text-[11px] font-semibold text-slate-400">
          {data.venue || 'Venue unavailable'}{data.attendance ? ` · Attendance ${Number(data.attendance).toLocaleString()}` : ''}
        </div>
      )}
    </div>
  )
}

export default function ScoreGameCenter({ game, league, onClose, boxScoreOverride = null }) {
  const [tab, setTab] = useState('Overview')

  useEffect(() => {
    setTab('Overview')
  }, [game?.event_id, league])

  useEffect(() => {
    if (!game?.event_id || !league) return undefined
    const context = {
      surface: 'GAME_CENTER',
      league,
      event_id: String(game.event_id),
      away: game.away || game.away_abbr || '',
      away_abbr: game.away_abbr || '',
      home: game.home || game.home_abbr || '',
      home_abbr: game.home_abbr || '',
      status: game.status || '',
      start_time: game.start_time || null,
    }
    window.dispatchEvent(new CustomEvent('sports-zenith-game-context', { detail: context }))
    return () => {
      window.dispatchEvent(new CustomEvent('sports-zenith-game-context', {
        detail: { surface: 'GAME_CENTER', event_id: String(game.event_id), cleared: true },
      }))
    }
  }, [game?.event_id, game?.away, game?.away_abbr, game?.home, game?.home_abbr, game?.status, game?.start_time, league])

  if (!game) return null

  return (
    <section className="scroll-mt-28 rounded-[30px] border border-slate-200 bg-slate-50 p-4 shadow-soft md:p-6" id="score-game-center">
      <div className="flex flex-col justify-between gap-4 border-b border-slate-200 pb-5 md:flex-row md:items-start">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-blue-50 px-3 py-1 text-[10px] font-black uppercase tracking-[0.12em] text-blue-700">Game Center</span>
            <StatusPill game={game} />
          </div>
          <h2 className="mt-3 truncate text-2xl font-black tracking-tight text-slate-950 md:text-3xl">
            {game.away || game.away_abbr} @ {game.home || game.home_abbr}
          </h2>
          <div className="mt-2 text-sm font-semibold text-slate-500">{game.status || formatStart(game.start_time)}</div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="min-h-11 shrink-0 rounded-xl border border-slate-200 bg-white px-4 text-xs font-black text-slate-600"
        >
          Close Game Center
        </button>
      </div>

      <div className="mt-4 flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Game Center sections">
        {TABS.map(([label, Icon]) => (
          <button
            key={label}
            type="button"
            role="tab"
            aria-selected={tab === label}
            onClick={() => setTab(label)}
            className={`inline-flex min-h-11 shrink-0 items-center gap-2 whitespace-nowrap rounded-xl px-4 text-sm font-black transition ${tab === label ? 'bg-slate-950 text-white' : 'border border-slate-200 bg-white text-slate-500'}`}
          >
            <Icon size={15} /> {label}
          </button>
        ))}
      </div>

      <div className="mt-5" role="tabpanel">
        {tab === 'Overview' && <GameOverview game={game} league={league} />}
        {tab === 'Box Score' && (
          boxScoreOverride || <BoxScoreContent league={league} eventId={game.event_id} available={game.boxscore_available} />
        )}
        {tab === 'Odds' && (
          <React.Suspense fallback={
            <div role="status" className="flex items-center gap-3 rounded-3xl border border-slate-200 bg-white p-6 text-sm font-black text-slate-600">
              <Activity size={17} className="animate-pulse text-blue-600" /> Loading game odds…
            </div>
          }>
            <GameOddsPanel game={game} league={league} />
          </React.Suspense>
        )}
        {tab === 'Props' && (
          <React.Suspense fallback={
            <div role="status" className="flex items-center gap-3 rounded-3xl border border-slate-200 bg-white p-6 text-sm font-black text-slate-600">
              <Activity size={17} className="animate-pulse text-blue-600" /> Loading game props…
            </div>
          }>
            <GamePropsPanel game={game} league={league} />
          </React.Suspense>
        )}
        {tab === 'Zenith' && (
          <React.Suspense fallback={
            <div role="status" className="flex items-center gap-3 rounded-3xl border border-slate-200 bg-white p-6 text-sm font-black text-slate-600">
              <Activity size={17} className="animate-pulse text-blue-600" /> Loading Zenith game intelligence…
            </div>
          }>
            <GameZenithPanel
              game={game}
              league={league}
              onOpenOdds={() => setTab('Odds')}
              onOpenProps={() => setTab('Props')}
            />
          </React.Suspense>
        )}
        {tab === 'News' && (
          <React.Suspense fallback={
            <div role="status" className="flex items-center gap-3 rounded-3xl border border-slate-200 bg-white p-6 text-sm font-black text-slate-600">
              <Activity size={17} className="animate-pulse text-blue-600" /> Loading game news…
            </div>
          }>
            <GameNewsPanel game={game} league={league} />
          </React.Suspense>
        )}
      </div>
    </section>
  )
}
