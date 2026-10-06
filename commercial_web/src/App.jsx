import React, { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertTriangle, BarChart3, Brain, CheckCircle2, ChevronRight, CloudSun,
  Gauge, LayoutDashboard, Radio, ShieldCheck, Sparkles, Target,
  Trophy, Users, Zap,
} from 'lucide-react'
import { insforgeConfigured } from './insforge'
import { AccountButton, useAuth } from './AuthShell'
import { bettingNavItems, navItems, nflSections, scoreLeagues, statusCards } from './dashboardConfig'
import { PUBLIC_BRAND, PUBLIC_BRAND_WORD_1, PUBLIC_BRAND_WORD_2, PUBLIC_TAGLINE } from './brandConfig'

const AskSportsHulkPage = lazy(() => import('./AskSportsHulk').then(module => ({ default: module.AskSportsHulkPage })))
const AssistantDrawer = lazy(() => import('./AskSportsHulk').then(module => ({ default: module.AssistantDrawer })))
const DfsLineupLab = lazy(() => import('./DfsLineupLab'))
const PerformancePanel = lazy(() => import('./PerformancePanel'))
const PracticeBetting = lazy(() => import('./PracticeBetting'))
const PersonalIdpPanel = lazy(() => import('./PersonalIdpPanel'))
const PersonalDefenseStreamingPanel = lazy(() => import('./PersonalDefenseStreamingPanel'))
const PersonalIrStashPanel = lazy(() => import('./PersonalIrStashPanel'))
const PersonalWaiverPanel = lazy(() => import('./PersonalWaiverPanel'))
const PersonalStartSitPanel = lazy(() => import('./PersonalStartSitPanel'))
const FantasyTeamControl = lazy(() => import('./FantasyTeamControl'))

function LoadingSurface({ label = 'Loading' }) {
  return (
    <div role="status" aria-live="polite" className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
      <div className="flex items-center gap-3 text-sm font-black text-slate-600">
        <Activity size={17} className="animate-pulse text-blue-600" />
        {label}…
      </div>
    </div>
  )
}

const toneClass = {
  blue: 'bg-blue-50 text-blue-700 border-blue-100',
  amber: 'bg-amber-50 text-amber-700 border-amber-100',
  emerald: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  violet: 'bg-violet-50 text-violet-700 border-violet-100',
}

function Brand() {
  return (
    <div>
      <div className="text-xl font-black tracking-tight text-slate-950">
        {PUBLIC_BRAND_WORD_1} <span className="text-blue-700">{PUBLIC_BRAND_WORD_2}</span>
      </div>
      <div className="mt-1 text-[10px] font-bold uppercase tracking-[0.24em] text-slate-400 md:text-xs">
        {PUBLIC_TAGLINE}
      </div>
    </div>
  )
}

function StatusStrip() {
  const health = useJsonEndpoint('/api/health', { sources: {} })
  const performance = useJsonEndpoint('/performance_snapshot.json', { official: {} })
  const brain = useJsonEndpoint('/brain_performance.json', { experiment_registry: {} })
  const sources = health.sources || {}

  const scoreKeys = ['nfl_scores', 'mlb_scores', 'nba_scores', 'nhl_scores', 'cfb_scores', 'cbb_scores']
  const marketKeys = ['best_bets_v2', 'props_v2', 'parlays_v2']
  const scoreReady = scoreKeys.filter((key) => sources[key]).length
  const marketReady = marketKeys.filter((key) => sources[key]).length
  const official = performance.official || {}
  const experiments = brain.experiment_registry || {}

  const cards = [
    {
      label: 'Live scores',
      value: scoreReady === scoreKeys.length ? 'CONNECTED' : scoreReady ? 'DEGRADED' : 'WAITING',
      detail: `${scoreReady}/${scoreKeys.length} leagues`,
      tone: scoreReady === scoreKeys.length ? 'emerald' : scoreReady ? 'amber' : 'blue',
    },
    {
      label: 'Market models',
      value: marketReady === marketKeys.length ? 'CONNECTED' : marketReady ? 'DEGRADED' : 'WAITING',
      detail: `${marketReady}/${marketKeys.length} V2 lanes`,
      tone: marketReady === marketKeys.length ? 'emerald' : marketReady ? 'amber' : 'blue',
    },
    {
      label: 'Accountability',
      value: official.status || 'WAITING',
      detail: `${official.published ?? 0} published · ${official.pending ?? 0} pending`,
      tone: official.status ? 'emerald' : 'blue',
    },
    {
      label: 'Learning loop',
      value: experiments.unresolved_experiments === 0 && experiments.registered_experiments ? 'ACTIVE' : 'CHECK',
      detail: experiments.registered_experiments
        ? `${experiments.registered_experiments} tests · ${experiments.unresolved_experiments ?? 0} unresolved`
        : 'Experiment registry loading',
      tone: experiments.unresolved_experiments === 0 && experiments.registered_experiments ? 'violet' : 'amber',
    },
  ]

  return (
    <div className="flex gap-3 overflow-x-auto pb-1 md:grid md:grid-cols-4 md:overflow-visible">
      {cards.map((item) => (
        <div key={item.label} className="min-w-[185px] rounded-2xl border border-slate-200 bg-white p-3 shadow-soft md:min-w-0 md:p-4">
          <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">{item.label}</div>
          <div className={`mt-3 inline-flex rounded-full border px-3 py-1 text-xs font-extrabold ${toneClass[item.tone]}`}>
            {item.value}
          </div>
          <div className="mt-2 text-[11px] font-semibold text-slate-400">{item.detail}</div>
        </div>
      ))}
    </div>
  )
}

function EmptyPanel({ icon: Icon, title, text, action }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
      <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-600">
        <Icon size={21} />
      </div>
      <h3 className="mt-5 text-lg font-black text-slate-950">{title}</h3>
      <p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">{text}</p>
      {action && <button className="mt-5 text-sm font-extrabold text-blue-700">{action} →</button>}
    </div>
  )
}


function NflBoxScore({ game }) {
  const box = game.boxscore || {}
  const teams = [game.away_abbr || game.away, game.home_abbr || game.home]
  const teamStats = box.team_stats || {}
  const players = box.players || {}
  const statLabels = [
    ['firstDowns', '1st downs'], ['thirdDownEff', '3rd down'], ['totalYards', 'Total yards'],
    ['netPassingYards', 'Pass yards'], ['rushingYards', 'Rush yards'], ['turnovers', 'Turnovers'],
    ['possessionTime', 'Possession'], ['sacksYardsLost', 'Sacks']
  ]

  const playerTable = (abbr, group, labels) => {
    const rows = players?.[abbr]?.[group] || []
    if (!rows.length) return null
    return (
      <div className="mt-5 overflow-x-auto">
        <div className="mb-2 text-sm font-black text-slate-800">{abbr} {group}</div>
        <table className="min-w-full text-sm">
          <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-400"><th className="px-2 py-2">Player</th>{labels.map(x => <th key={x} className="px-2 py-2">{x}</th>)}</tr></thead>
          <tbody>{rows.map((r, i) => <tr key={`${r.name}-${i}`} className="border-b border-slate-100"><td className="px-2 py-2 font-bold text-slate-800">{r.name}</td>{labels.map(x => <td key={x} className="px-2 py-2">{r.stats?.[x] ?? '—'}</td>)}</tr>)}</tbody>
        </table>
      </div>
    )
  }

  return (
    <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Box score</div>
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full text-sm"><thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-400"><th className="px-2 py-2">Team</th>{statLabels.map(([,label]) => <th key={label} className="px-2 py-2">{label}</th>)}</tr></thead><tbody>{teams.map(abbr => <tr key={abbr} className="border-b border-slate-100"><td className="px-2 py-2 font-black text-slate-900">{abbr}</td>{statLabels.map(([key]) => <td key={key} className="px-2 py-2">{teamStats?.[abbr]?.[key] ?? '—'}</td>)}</tr>)}</tbody></table>
      </div>
      {teams.map(abbr => <div key={abbr}>{playerTable(abbr, 'passing', ['C/ATT','YDS','TD','INT','QBR','RTG'])}{playerTable(abbr, 'rushing', ['CAR','YDS','AVG','TD','LONG'])}{playerTable(abbr, 'receiving', ['REC','YDS','AVG','TD','LONG','TGTS'])}</div>)}
      {!!box.scoring_plays?.length && (
        <div className="mt-6">
          <div className="text-sm font-black text-slate-800">Scoring plays</div>
          <div className="mt-3 space-y-2">
            {box.scoring_plays.map((play, i) => (
              <div key={`${play.period}-${play.clock}-${i}`} className="rounded-xl border border-slate-200 bg-white p-3">
                <div className="text-xs font-black text-slate-400">Q{play.period ?? '—'} · {play.clock || '—'} · {play.away_score ?? '—'}-{play.home_score ?? '—'}</div>
                <div className="mt-1 text-sm font-semibold text-slate-700">{play.text || 'Scoring play'}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {!!box.leaders?.length && (
        <div className="mt-6">
          <div className="text-sm font-black text-slate-800">Game leaders</div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {box.leaders.map((lead, i) => (
              <div key={`${lead.team}-${lead.category}-${lead.player}-${i}`} className="rounded-xl border border-slate-200 bg-white p-3">
                <div className="text-xs font-black uppercase tracking-wide text-slate-400">{lead.team || ''} · {lead.category || ''}</div>
                <div className="mt-1 text-sm font-extrabold text-slate-900">{lead.player || '—'}</div>
                <div className="text-xs font-semibold text-slate-500">{lead.value || ''}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function Scoreboard() {
  const [snapshot, setSnapshot] = useState({ games: [], generated_at: null })
  const [openBox, setOpenBox] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const response = await fetch(`/nfl_scores.json?ts=${Date.now()}`, { cache: 'no-store' })
        if (!response.ok) throw new Error('score snapshot unavailable')
        const payload = await response.json()
        if (!cancelled) setSnapshot(payload)
      } catch {
        if (!cancelled) setSnapshot({ games: [], generated_at: null })
      }
    }
    load()
    const timer = window.setInterval(load, 30000)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [])

  const games = snapshot.games || []
  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Today</p>
          <h2>Live & final scores</h2>
        </div>
        <span className="health-pill">ESPN CORE · VERIFIED</span>
      </div>
      {games.length === 0 ? (
        <EmptyPanel icon={Radio} title="No NFL game in the active window" text="The score collector is connected and will show upcoming, live and final games automatically." />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {games.map((game) => (
            <div key={game.event_id} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
              <div className="flex items-center justify-between gap-3">
                <span className={`rounded-full px-3 py-1 text-xs font-black ${game.final ? 'bg-slate-100 text-slate-700' : game.live ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700'}`}>
                  {game.final ? 'FINAL' : game.live ? 'LIVE' : 'UPCOMING'}
                </span>
                <span className="text-xs font-bold text-slate-400">{game.status || ''}</span>
              </div>
              <div className="mt-5 space-y-3">
                <div className="flex items-center justify-between text-lg font-black text-slate-900">
                  <span>{game.away_abbr || game.away}</span><span>{game.away_score ?? '—'}</span>
                </div>
                <div className="flex items-center justify-between text-lg font-black text-slate-900">
                  <span>{game.home_abbr || game.home}</span><span>{game.home_score ?? '—'}</span>
                </div>
              </div>
              {game.boxscore && (
                <button onClick={() => setOpenBox(openBox === game.event_id ? null : game.event_id)} className="mt-5 text-sm font-extrabold text-blue-700">
                  {openBox === game.event_id ? 'Hide box score' : 'View box score'} →
                </button>
              )}
              {openBox === game.event_id && game.boxscore && <NflBoxScore game={game} />}
              <div className="mt-5 border-t border-slate-100 pt-3 text-xs font-semibold text-slate-400">Source: {game.source || 'ESPN Core'}</div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function DecisionPanel() {
  const data = useNflDecisions()
  const topGame = (data.games || [])[0]
  const topProp = (data.props || [])[0]
  const topParlay = (data.parlays || [])[0]
  const topSurvivor = [...(data.survivor || [])].sort((a,b) => (b.hulk_context_score || 0) - (a.hulk_context_score || 0))[0]
  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Decision engine</p>
          <h2>What matters now</h2>
        </div>
        <span className="health-pill emerald">CURRENT</span>
      </div>
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-700"><Target size={21} /></div>
          <div className="mt-5 text-xs font-black uppercase tracking-[0.14em] text-slate-400">Game research</div>
          <div className="mt-2 text-xl font-black text-slate-950">{topGame?.selection || 'Waiting for current board'}</div>
          {topGame && <><div className="mt-1 text-sm font-extrabold text-slate-700">Moneyline {topGame.line}</div><div className="mt-4 text-xs leading-5 text-slate-500">Evidence {topGame.hulk_market_score} · Market {topGame.market_implied_safety}% · {topGame.provider_agreement}</div></>}
        </div>
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700"><ShieldCheck size={21} /></div>
          <div className="mt-5 text-xs font-black uppercase tracking-[0.14em] text-slate-400">Survivor research</div>
          <div className="mt-2 text-xl font-black text-slate-950">{topSurvivor?.survivor_team || 'Waiting for current board'}</div>
          {topSurvivor && <><div className="mt-1 text-sm font-semibold text-slate-500">Context {topSurvivor.hulk_context_score} · Market {topSurvivor.market_prob_pct}%</div><div className="mt-4 text-xs leading-5 text-slate-500">{topSurvivor.positive_signals || 'No positive signals listed'}</div></>}
        </div>
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-50 text-sky-700"><Sparkles size={21} /></div>
          <div className="mt-5 text-xs font-black uppercase tracking-[0.14em] text-slate-400">Top prop research</div>
          <div className="mt-2 text-xl font-black text-slate-950">{topProp?.player_dfs || 'Waiting for current prop board'}</div>
          {topProp && <><div className="mt-1 text-sm font-extrabold text-slate-700">{topProp.side} {topProp.dfs_line} · {String(topProp.stat_type || topProp.market).replaceAll('_',' ')}</div><div className="mt-4 text-xs leading-5 text-slate-500">Evidence {topProp.hulk_prop_score} · {topProp.book_count} books · {topProp.context_coverage} context</div></>}
        </div>
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-violet-50 text-violet-700"><Zap size={21} /></div>
          <div className="mt-5 text-xs font-black uppercase tracking-[0.14em] text-slate-400">Qualified parlay research</div>
          {topParlay ? <><div className="mt-2 text-base font-black leading-6 text-slate-950">{topParlay.leg1_label}</div><div className="my-2 text-xs font-black text-slate-300">+</div><div className="text-base font-black leading-6 text-slate-950">{topParlay.leg2_label}</div><div className="mt-4 text-xs leading-5 text-slate-500">Different games verified · Probability not fabricated</div></> : <div className="mt-2 text-xl font-black text-slate-950">No qualified parlay</div>}
        </div>
      </div>
      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 text-xs font-semibold text-slate-500">Game selections are market-backed research from refreshed multi-provider fusion. Spreads and totals are not presented as validated predictive models.</div>
    </section>
  )
}

function SurvivorPanel() {
  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Survivor</p>
          <h2>Two-entry strategy center</h2>
        </div>
        <span className="health-pill emerald">ACCOUNTABLE</span>
      </div>
      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
        <div className="grid gap-4 lg:grid-cols-3">
          {[
            ['Entry-aware', 'Used teams and remaining options stay separate for every entry.'],
            ['Pool-aware', 'Ownership, future value and diversification belong beside raw survival probability.'],
            ['Evidence-aware', 'History, weather, injuries, surface, pressure and team strength stay traceable.'],
          ].map(([title, text]) => (
            <div key={title} className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
              <div className="font-black text-slate-900">{title}</div>
              <div className="mt-2 text-sm leading-6 text-slate-500">{text}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function LearningPanel() {
  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Learning loop</p>
          <h2>Prediction → result → review → lesson</h2>
        </div>
      </div>
      <div className="rounded-3xl border border-slate-200 bg-slate-950 p-6 text-white shadow-soft">
        <div className="grid gap-4 md:grid-cols-4">
          {[
            ['1', 'Freeze', 'Store exactly what was known before kickoff.'],
            ['2', 'Grade', 'Join only verified final results.'],
            ['3', 'Autopsy', 'Explain what changed and what was misread.'],
            ['4', 'Learn', 'Store validated lessons for future decisions.'],
          ].map(([n, title, text]) => (
            <div key={n} className="rounded-2xl border border-white/10 bg-white/5 p-5">
              <div className="text-xs font-black text-emerald-400">STEP {n}</div>
              <div className="mt-2 text-lg font-black">{title}</div>
              <div className="mt-2 text-sm leading-6 text-slate-300">{text}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}



function NflPanel() {
  const [data, setData] = useState({ games: [], next_games: [] })
  const [intel, setIntel] = useState({ overall_status: 'UNKNOWN', sources: {}, decision_gate: { blockers: [] } })
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const r = await fetch(`/nfl_scores.json?ts=${Date.now()}`, { cache: 'no-store' })
        if (!r.ok) throw new Error('NFL snapshot unavailable')
        const payload = await r.json()
        if (!cancelled) setData(payload)
        const ir = await fetch(`/nfl_intelligence.json?ts=${Date.now()}`, { cache: 'no-store' })
        if (ir.ok) {
          const ip = await ir.json()
          if (!cancelled) setIntel(ip)
        }
      } catch {
        if (!cancelled) setData({ games: [], next_games: [] })
      }
    }
    load()
    const timer = window.setInterval(load, 30000)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [])

  const next = data.next_games || []
  return (
    <div className="space-y-8">
      <SectionGrid title="NFL" items={nflSections} />
      <NflGamesPanel />
      <section>
        <div className="section-heading"><div><p className="eyebrow">Decision readiness</p><h2>Data health</h2></div><span className={`health-pill ${intel.overall_status === 'READY' ? 'emerald' : ''}`}>{intel.overall_status}</span></div>
        <div className="grid gap-3 md:grid-cols-4">
          {Object.entries(intel.sources || {}).map(([name, info]) => (
            <div key={name} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
              <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">{name.replace('_',' ')}</div>
              <div className={`mt-3 inline-flex rounded-full px-3 py-1 text-xs font-black ${info.status === 'CURRENT' ? 'bg-emerald-50 text-emerald-700' : info.status === 'STALE' ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-700'}`}>{info.status}</div>
              <div className="mt-2 text-xs font-semibold text-slate-400">{info.age_hours == null ? 'Age unknown' : `${info.age_hours}h old`}</div>
            </div>
          ))}
        </div>
        {!!intel.decision_gate?.blockers?.length && <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900">Current picks are withheld until the stale sources refresh. Score and box-score data remain live.</div>}
      </section>
      <section>
        <div className="section-heading"><div><p className="eyebrow">Next slate</p><h2>Upcoming NFL games</h2></div><span className="health-pill">ESPN CORE</span></div>
        {next.length ? (
          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
            {next.map(game => (
              <div key={game.event_id} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
                <div className="flex items-center justify-between"><span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-black text-blue-700">UPCOMING</span><span className="text-xs font-bold text-slate-400">{game.status || ''}</span></div>
                <div className="mt-5 space-y-3 text-lg font-black text-slate-900"><div>{game.away_abbr || game.away}</div><div>@ {game.home_abbr || game.home}</div></div>
                <div className="mt-5 border-t border-slate-100 pt-3 text-xs font-semibold text-slate-400">Source: {game.source || 'ESPN Core'}</div>
              </div>
            ))}
          </div>
        ) : <EmptyPanel icon={Trophy} title="No upcoming NFL games found" text="The next-slate collector is connected and will populate automatically when games are available." />}
      </section>
      <EmptyPanel icon={CloudSun} title="NFL evidence layer" text="Weather, wind, surface, home/away, injuries, offense, defense, pressure, historical analogs and market context stay behind each decision and never silently default to neutral." />
    </div>
  )
}

function MlbStatTable({ title, rows, pitching = false }) {
  if (!rows?.length) return null
  const headers = pitching
    ? ['Player', 'IP', 'H', 'R', 'ER', 'BB', 'SO', 'HR']
    : ['Player', 'AB', 'R', 'H', 'RBI', 'BB', 'SO', 'HR']
  return (
    <div className="mt-5 overflow-x-auto">
      <div className="mb-2 text-sm font-black text-slate-800">{title}</div>
      <table className="min-w-full text-sm">
        <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-400">{headers.map(h => <th key={h} className="px-2 py-2">{h}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={`${r.name}-${i}`} className="border-b border-slate-100">
              <td className="px-2 py-2 font-bold text-slate-800">{r.name}</td>
              {pitching ? (
                <><td className="px-2 py-2">{r.ip ?? '—'}</td><td className="px-2 py-2">{r.h ?? 0}</td><td className="px-2 py-2">{r.r ?? 0}</td><td className="px-2 py-2">{r.er ?? 0}</td><td className="px-2 py-2">{r.bb ?? 0}</td><td className="px-2 py-2">{r.so ?? 0}</td><td className="px-2 py-2">{r.hr ?? 0}</td></>
              ) : (
                <><td className="px-2 py-2">{r.ab ?? 0}</td><td className="px-2 py-2">{r.r ?? 0}</td><td className="px-2 py-2">{r.h ?? 0}</td><td className="px-2 py-2">{r.rbi ?? 0}</td><td className="px-2 py-2">{r.bb ?? 0}</td><td className="px-2 py-2">{r.so ?? 0}</td><td className="px-2 py-2">{r.hr ?? 0}</td></>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function MlbBoxScore({ game }) {
  const box = game.boxscore
  return (
    <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Box score</div>
      <MlbStatTable title={`${game.away} batting`} rows={box.away?.batting} />
      <MlbStatTable title={`${game.away} pitching`} rows={box.away?.pitching} pitching />
      <MlbStatTable title={`${game.home} batting`} rows={box.home?.batting} />
      <MlbStatTable title={`${game.home} pitching`} rows={box.home?.pitching} pitching />
    </div>
  )
}

function MlbPanel() {
  const [data, setData] = useState({ today_games: [], recent_games: [], next_games: [] })
  const [openBox, setOpenBox] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const response = await fetch(`/mlb_scores.json?ts=${Date.now()}`, { cache: 'no-store' })
        if (!response.ok) throw new Error('MLB snapshot unavailable')
        const payload = await response.json()
        if (!cancelled) setData(payload)
      } catch {
        if (!cancelled) setData({ today_games: [], recent_games: [], next_games: [] })
      }
    }
    load()
    const timer = window.setInterval(load, 30000)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [])

  const renderGame = (game, showBox = false) => (
    <div key={game.gamePk} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <span className={`rounded-full px-3 py-1 text-xs font-black ${game.final ? 'bg-slate-100 text-slate-700' : game.live ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700'}`}>
          {game.final ? 'FINAL' : game.live ? 'LIVE' : 'UPCOMING'}
        </span>
        <span className="text-xs font-bold text-slate-400">{game.status || ''}</span>
      </div>
      <div className="mt-5 space-y-3">
        <div className="flex items-center justify-between text-lg font-black"><span>{game.away}</span><span>{game.away_score ?? '—'}</span></div>
        <div className="flex items-center justify-between text-lg font-black"><span>{game.home}</span><span>{game.home_score ?? '—'}</span></div>
      </div>
      {showBox && game.boxscore && (
        <button onClick={() => setOpenBox(openBox === game.gamePk ? null : game.gamePk)} className="mt-5 text-sm font-extrabold text-blue-700">
          {openBox === game.gamePk ? 'Hide box score' : 'View box score'} →
        </button>
      )}
      {openBox === game.gamePk && game.boxscore && <MlbBoxScore game={game} />}
    </div>
  )

  return (
    <div className="space-y-8">
      <section>
        <div className="section-heading"><div><p className="eyebrow">MLB</p><h2>Today</h2></div><span className="health-pill">MLB STATSAPI</span></div>
        {data.today_games?.length ? <div className="grid gap-4 lg:grid-cols-2">{data.today_games.map(g => renderGame(g, true))}</div> : (
          <EmptyPanel icon={Trophy} title="No MLB games today" text="The feed is connected. MLB has no games scheduled today, so the dashboard shows the next postseason slate below instead of looking broken." />
        )}
      </section>
      <section>
        <div className="section-heading"><div><p className="eyebrow">Next slate</p><h2>Upcoming MLB games</h2></div></div>
        <div className="grid gap-4 lg:grid-cols-2">{(data.next_games || []).slice(0, 8).map(g => renderGame(g, false))}</div>
      </section>
      {!!data.recent_games?.length && (
        <section>
          <div className="section-heading"><div><p className="eyebrow">Recent finals</p><h2>Box scores</h2></div></div>
          <div className="grid gap-4">{data.recent_games.map(g => renderGame(g, true))}</div>
        </section>
      )}
    </div>
  )
}


function useNflDecisions() {
  const [data, setData] = useState({ health: {}, games: [], props: [], parlays: [], survivor: [] })
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const r = await fetch(`/nfl_decisions.json?ts=${Date.now()}`, { cache: 'no-store' })
        if (!r.ok) throw new Error('decision snapshot unavailable')
        const payload = await r.json()
        if (!cancelled) setData(payload)
      } catch {
        if (!cancelled) setData({ health: {}, games: [], props: [], parlays: [], survivor: [] })
      }
    }
    load()
    const timer = window.setInterval(load, 30000)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [])
  return data
}

function NflGamesPanel() {
  const data = useNflDecisions()
  const health = data.health?.game_bets || {}
  return (
    <section>
      <div className="section-heading">
        <div><p className="eyebrow">NFL game research</p><h2>Qualified moneyline board</h2></div>
        <span className={`health-pill ${health.status === 'CURRENT' ? 'emerald' : ''}`}>{health.status || 'UNKNOWN'}</span>
      </div>
      <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 text-sm font-semibold text-slate-600">Refreshed PropLine + SportWizzard fusion is live. These are evidence-backed moneyline research cards. ATS and totals remain research-only until those models are validated.</div>
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {(data.games || []).map((g, i) => (
          <div key={`${g.game_key}-${i}`} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="flex items-start justify-between gap-3">
              <div><div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">{g.game_key}</div><div className="mt-2 text-xl font-black text-slate-950">{g.selection}</div></div>
              <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-black text-blue-700">ML {g.line}</span>
            </div>
            <div className="mt-5 grid grid-cols-3 gap-2 text-center text-xs">
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{g.hulk_market_score}</div><div className="mt-1 text-slate-400">Evidence</div></div>
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{g.market_implied_safety}%</div><div className="mt-1 text-slate-400">Market</div></div>
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{g.sw_books}</div><div className="mt-1 text-slate-400">Books</div></div>
            </div>
            <div className="mt-4 text-xs leading-5 text-slate-500">Quality {g.market_data_quality} · Providers {g.provider_agreement} · {g.decision}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

function NflPropsPanel() {
  const data = useNflDecisions()
  const health = data.health?.props || {}
  return (
    <section>
      <div className="section-heading">
        <div><p className="eyebrow">NFL props</p><h2>Qualified player research</h2></div>
        <span className={`health-pill ${health.status === 'CURRENT' ? 'emerald' : ''}`}>{health.status || 'UNKNOWN'}</span>
      </div>
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {(data.props || []).map((p, i) => (
          <div key={`${p.player_dfs}-${p.market}-${i}`} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="flex items-start justify-between gap-4">
              <div><div className="text-lg font-black text-slate-950">{p.player_dfs}</div><div className="mt-1 text-xs font-semibold text-slate-400">{p.away_team} @ {p.home_team}</div></div>
              <span className={`rounded-full px-3 py-1 text-xs font-black ${p.side === 'OVER' ? 'bg-emerald-50 text-emerald-700' : 'bg-orange-50 text-orange-700'}`}>{p.side}</span>
            </div>
            <div className="mt-5 text-sm font-extrabold text-slate-700">{String(p.market || '').replaceAll('_',' ')}</div>
            <div className="mt-1 text-3xl font-black text-slate-950">{p.dfs_line}</div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{p.hulk_prop_score}</div><div className="mt-1 text-slate-400">Evidence</div></div>
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{p.book_count}</div><div className="mt-1 text-slate-400">Books</div></div>
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{p.meaningful_completed_games}</div><div className="mt-1 text-slate-400">Sample</div></div>
            </div>
            <div className="mt-4 text-xs leading-5 text-slate-500">Context: {p.context_direction} · Coverage: {p.context_coverage} · Injury screen: {p.espn_injury_gate}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

function NflParlaysPanel() {
  const data = useNflDecisions()
  const health = data.health?.parlays || {}
  return (
    <section>
      <div className="section-heading">
        <div><p className="eyebrow">NFL parlays</p><h2>Qualified two-leg combinations</h2></div>
        <span className={`health-pill ${health.status === 'CURRENT' ? 'emerald' : ''}`}>{health.status || 'UNKNOWN'}</span>
      </div>
      <div className="mb-4 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm font-semibold text-blue-900">Only prop-only and PrizePicks combinations are exposed right now. Game-leg parlays stay withheld until the refreshed game-fusion board is revalidated.</div>
      <div className="grid gap-4 lg:grid-cols-2">
        {(data.parlays || []).map((p, i) => (
          <div key={`${p.parlay_type}-${i}`} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="flex items-center justify-between gap-3"><span className="text-xs font-black uppercase tracking-[0.14em] text-violet-700">{String(p.parlay_type).replaceAll('_',' ')}</span><span className="rounded-full bg-violet-50 px-3 py-1 text-xs font-black text-violet-700">Evidence {p.parlay_score}</span></div>
            <div className="mt-5 space-y-3">
              <div className="rounded-2xl bg-slate-50 p-4"><div className="text-xs font-black text-slate-400">LEG 1</div><div className="mt-1 font-extrabold text-slate-900">{p.leg1_label}</div></div>
              <div className="rounded-2xl bg-slate-50 p-4"><div className="text-xs font-black text-slate-400">LEG 2</div><div className="mt-1 font-extrabold text-slate-900">{p.leg2_label}</div></div>
            </div>
            <div className="mt-4 text-xs font-semibold text-slate-500">{p.correlation_status} · Probability not fabricated · Payout verify at sportsbook</div>
          </div>
        ))}
      </div>
    </section>
  )
}

function SurvivorRoutePanel() {
  const data = useNflDecisions()
  const health = data.health?.survivor || {}
  const tierOrder = { TOP_TIER: 0, STRONG: 1, VIABLE: 2, WATCH: 3, CAUTION: 4 }

  const [profile, setProfile] = useState(() => {
    try {
      const saved = JSON.parse(window.localStorage.getItem('sports-hulk-survivor-preview') || '{}')
      return {
        usedTeams: Array.isArray(saved.usedTeams) ? saved.usedTeams : [],
        currentPicks: Array.isArray(saved.currentPicks) ? saved.currentPicks : [],
      }
    } catch {
      return { usedTeams: [], currentPicks: [] }
    }
  })
  const [usedChoice, setUsedChoice] = useState('')
  const [pickChoice, setPickChoice] = useState('')
  const [authoritative, setAuthoritative] = useState({ usedTeams: [], currentPicks: [], activeEntry: null, week: null, loaded: false })
  const [scoreSnapshot, setScoreSnapshot] = useState({ games: [], generated_at: null })

  useEffect(() => {
    window.localStorage.setItem('sports-hulk-survivor-preview', JSON.stringify(profile))
  }, [profile])

  useEffect(() => {
    let cancelled = false
    const loadSavedState = async () => {
      try {
        const r = await fetch(`/api/survivor/state?ts=${Date.now()}`, { cache: 'no-store' })
        if (!r.ok) throw new Error('saved Survivor state unavailable')
        const saved = await r.json()
        if (cancelled) return
        const next = {
          usedTeams: Array.isArray(saved.used_teams) ? saved.used_teams : [],
          currentPicks: Array.isArray(saved.current_picks) ? saved.current_picks : [],
          activeEntry: saved.active_entry || null,
          week: saved.pool_current_week || null,
          loaded: true,
        }
        setAuthoritative(next)
        setProfile({ usedTeams: next.usedTeams, currentPicks: next.currentPicks })
      } catch {
        if (!cancelled) setAuthoritative(prev => ({ ...prev, loaded: true }))
      }
    }
    loadSavedState()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    const loadScores = async () => {
      try {
        const r = await fetch(`/nfl_scores.json?ts=${Date.now()}`, { cache: 'no-store' })
        if (!r.ok) throw new Error('score snapshot unavailable')
        const payload = await r.json()
        if (!cancelled) setScoreSnapshot(payload)
      } catch {
        if (!cancelled) setScoreSnapshot({ games: [], generated_at: null })
      }
    }

    loadScores()
    const timer = window.setInterval(loadScores, 30000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  const allRows = [...(data.survivor || [])]
  const allTeams = Array.from(new Set(
    allRows.flatMap(r => [r.home_team, r.away_team, r.survivor_team]).filter(Boolean)
  )).sort()

  const rows = allRows
    .filter(r => !profile.usedTeams.includes(r.survivor_team))
    .sort((a,b) => (tierOrder[a.hulk_decision_tier] ?? 9) - (tierOrder[b.hulk_decision_tier] ?? 9) || (b.hulk_context_score || 0) - (a.hulk_context_score || 0))

  const addUsed = () => {
    if (!usedChoice || profile.usedTeams.includes(usedChoice)) return
    setProfile(prev => ({
      ...prev,
      usedTeams: [...prev.usedTeams, usedChoice],
      currentPicks: prev.currentPicks.filter(team => team !== usedChoice),
    }))
    setUsedChoice('')
  }

  const addPick = () => {
    if (!pickChoice || profile.usedTeams.includes(pickChoice) || profile.currentPicks.includes(pickChoice)) return
    setProfile(prev => ({ ...prev, currentPicks: [...prev.currentPicks, pickChoice] }))
    setPickChoice('')
  }

  return (
    <section>
      <div className="section-heading">
        <div><p className="eyebrow">Survivor</p><h2>My entry + current-week decision board</h2></div>
        <span className={`health-pill ${health.status === 'CURRENT' ? 'emerald' : ''}`}>{health.status || 'UNKNOWN'}</span>
      </div>

      <div className="mb-6 rounded-3xl border border-emerald-200 bg-emerald-50/50 p-5">
        <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
          <div>
            <div className="text-lg font-black text-slate-950">My Survivor Teams</div>
            <div className="mt-1 text-sm text-slate-500">
              Loaded from your saved entry{authoritative.activeEntry ? ` · ${authoritative.activeEntry}` : ''}{authoritative.week ? ` · Week ${authoritative.week}` : ''}.
              Browser edits below are draft-only until a protected write workflow is enabled.
            </div>
          </div>
          <button
            onClick={() => setProfile({ usedTeams: authoritative.usedTeams, currentPicks: authoritative.currentPicks })}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-black text-slate-600"
          >
            Reset draft to saved
          </button>
        </div>

        <div className="mt-5 grid gap-5 lg:grid-cols-2">
          <div>
            <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-500">Teams already used</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {profile.usedTeams.length ? profile.usedTeams.map(team => (
                <button
                  key={team}
                  onClick={() => setProfile(prev => ({ ...prev, usedTeams: prev.usedTeams.filter(x => x !== team) }))}
                  className="rounded-full bg-slate-950 px-3 py-1.5 text-xs font-black text-white"
                  title="Remove used team"
                >
                  {team} ×
                </button>
              )) : <span className="text-sm text-slate-400">None added yet.</span>}
            </div>
            <div className="mt-3 flex gap-2">
              <select value={usedChoice} onChange={e => setUsedChoice(e.target.value)} className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-bold text-slate-800">
                <option value="">Choose used team…</option>
                {allTeams.filter(team => !profile.usedTeams.includes(team)).map(team => <option key={team} value={team}>{team}</option>)}
              </select>
              <button onClick={addUsed} disabled={!usedChoice} className="rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-black text-white disabled:opacity-40">Add</button>
            </div>
          </div>

          <div>
            <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-500">Current week pick(s)</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {profile.currentPicks.length ? profile.currentPicks.map(team => (
                <button
                  key={team}
                  onClick={() => setProfile(prev => ({ ...prev, currentPicks: prev.currentPicks.filter(x => x !== team) }))}
                  className="rounded-full bg-emerald-600 px-3 py-1.5 text-xs font-black text-white"
                  title="Remove current pick"
                >
                  {team} ×
                </button>
              )) : <span className="text-sm text-slate-400">No pick saved yet.</span>}
            </div>
            <div className="mt-3 flex gap-2">
              <select value={pickChoice} onChange={e => setPickChoice(e.target.value)} className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-bold text-slate-800">
                <option value="">Choose current pick…</option>
                {allTeams.filter(team => !profile.usedTeams.includes(team) && !profile.currentPicks.includes(team)).map(team => <option key={team} value={team}>{team}</option>)}
              </select>
              <button onClick={addPick} disabled={!pickChoice} className="rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-black text-white disabled:opacity-40">Save</button>
            </div>
          </div>
        </div>

        <div className="mt-4 text-xs font-semibold text-slate-500">
          Saved state comes from your account. Changes made on this screen are browser drafts only and never submit picks to the external pool.
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {rows.map((r, i) => (
          <div key={`${r.survivor_team}-${i}`} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="flex items-center justify-between gap-3"><div className="text-lg font-black text-slate-950">{r.survivor_team}</div><span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-700">{r.hulk_decision_tier}</span></div>
            <div className="mt-1 text-xs font-semibold text-slate-400">vs {r.survivor_team === r.home_team ? r.away_team : r.home_team}</div>
            <div className="mt-5 grid grid-cols-3 gap-2 text-center text-xs">
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{r.market_prob_pct}%</div><div className="mt-1 text-slate-400">Market</div></div>
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{r.hulk_context_score}</div><div className="mt-1 text-slate-400">Context</div></div>
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{r.survivor_spread}</div><div className="mt-1 text-slate-400">Spread</div></div>
            </div>
            <div className="mt-4 text-xs leading-5 text-slate-500">{r.positive_signals || 'No positive signals listed'}{r.risk_signals ? ` · Risk: ${r.risk_signals}` : ''}</div>
            <div className="mt-3 text-xs font-semibold text-slate-400">Weather: {r.weather_status || 'UNKNOWN'}{r.wind_mph != null ? ` · Wind ${r.wind_mph} mph` : ''}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

function SurvivorCommercialPanel() {
  const { user, getAccessToken } = useAuth()
  const [linkRefresh, setLinkRefresh] = useState(0)
  const [claimEntry, setClaimEntry] = useState('')
  const [claimCode, setClaimCode] = useState('')
  const [linking, setLinking] = useState(false)
  const [linkMessage, setLinkMessage] = useState('')
  const survivor = useJsonEndpoint('/survivor_v2_current.json', {
    candidates: [],
    mode: 'GENERIC_RESEARCH_ONLY',
  })
  const saved = usePrivateSurvivorState(linkRefresh)

  const linkExistingEntry = async () => {
    if (!claimEntry.trim() || !claimCode.trim() || linking) return
    setLinking(true)
    setLinkMessage('')
    try {
      const token = await getAccessToken()
      if (!token) throw new Error('Please sign in again before linking your pool.')
      const response = await fetch('/api/survivor/link-entry', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          entry_name: claimEntry.trim(),
          claim_code: claimCode.trim(),
        }),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.message || 'Could not link that Survivor entry.')
      setClaimCode('')
      setLinkMessage('Entry linked successfully.')
      setLinkRefresh(value => value + 1)
    } catch (error) {
      setLinkMessage(error instanceof Error ? error.message : 'Could not link that Survivor entry.')
    } finally {
      setLinking(false)
    }
  }

  const isSignedIn = Boolean(user)
  const hasEntry = saved.status === 'READY' && saved.entry_linked
  const usedTeams = hasEntry ? (saved.used_teams || []) : []
  const currentPicks = hasEntry ? (saved.current_picks || []) : []
  const candidates = [...(survivor.candidates || [])]
    .filter((row) => !usedTeams.includes(row.team))
    .sort((a, b) => Number(b.strategy_index || 0) - Number(a.strategy_index || 0))
  const ruleConfirmed = hasEntry && Boolean(saved.rule_confirmed)
  const requiredPicks = hasEntry
    ? (saved.required_picks == null ? 'UNKNOWN' : saved.required_picks)
    : '—'
  const entryStatus = hasEntry
    ? (saved.entry_status || 'UNKNOWN')
    : isSignedIn
      ? 'ACCOUNT READY'
      : 'SIGN IN'

  const tierTone = (tier) => {
    const value = String(tier || '')
    if (value === 'TOP_TIER' || value === 'STRONG' || value === 'VIABLE') return 'bg-emerald-50 text-emerald-700'
    if (value === 'WATCH') return 'bg-amber-50 text-amber-700'
    return 'bg-slate-100 text-slate-600'
  }

  return (
    <div className="space-y-8">
      <section className="rounded-[30px] border border-slate-200 bg-white p-6 shadow-soft md:p-8">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="eyebrow">Survivor</p>
              <span className={`rounded-full px-2.5 py-1 text-[10px] font-black ${hasEntry && entryStatus === 'ALIVE' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{entryStatus}</span>
            </div>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-slate-950 md:text-4xl">
              {hasEntry ? saved.active_entry : isSignedIn ? 'No Survivor entry connected' : 'Your Survivor command center'}
            </h1>
            <p className="mt-2 text-sm font-semibold text-slate-500">
              {hasEntry
                ? `Pool week ${saved.pool_current_week ?? survivor.pool_current_week ?? '—'} · ${usedTeams.length} teams used · current pick ${currentPicks.length ? currentPicks.join(', ') : 'None'}`
                : isSignedIn
                  ? 'Your account is signed in. A personal pool can be linked without exposing it to anonymous visitors.'
                  : `Week ${survivor.pool_current_week ?? '—'} generic research is visible. Sign in to load private entries, used teams and pool rules.`}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div className="rounded-2xl bg-slate-50 p-4">
              <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Required picks</div>
              <div className="mt-2 text-xl font-black text-slate-950">{requiredPicks}</div>
            </div>
            <div className="rounded-2xl bg-slate-50 p-4">
              <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Research candidates</div>
              <div className="mt-2 text-xl font-black text-slate-950">{candidates.length}</div>
            </div>
            <div className="rounded-2xl bg-slate-50 p-4">
              <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Pool state</div>
              <div className="mt-2 text-sm font-black text-slate-950">{hasEntry ? humanize(saved.ownership?.status || 'WAITING') : 'PRIVATE'}</div>
            </div>
          </div>
        </div>
      </section>

      {!isSignedIn && (
        <section className="rounded-3xl border border-blue-200 bg-blue-50 p-5 md:p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex gap-4">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-blue-700"><ShieldCheck size={20} /></div>
              <div>
                <div className="text-lg font-black text-slate-950">Private pool data stays behind your account</div>
                <p className="mt-2 text-sm leading-6 text-blue-950">Passwordless sign-in unlocks your entries, used teams, saved picks and pool-specific rules. Anonymous visitors only see the generic research board.</p>
              </div>
            </div>
            <div className="shrink-0"><AccountButton /></div>
          </div>
        </section>
      )}

      {isSignedIn && !hasEntry && saved.status !== 'LOADING' && (
        <section className="rounded-3xl border border-blue-200 bg-blue-50 p-5 md:p-6">
          <div className="flex gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-blue-700"><CheckCircle2 size={20} /></div>
            <div className="min-w-0 flex-1">
              <div className="text-lg font-black text-slate-950">Connect your existing Survivor entry</div>
              <p className="mt-2 text-sm leading-6 text-blue-950">Your passwordless account is authenticated. Use the exact entry name and one-time claim code to attach the private pool record to this account.</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
                <input
                  value={claimEntry}
                  onChange={event => setClaimEntry(event.target.value)}
                  placeholder="Entry name"
                  autoCapitalize="characters"
                  className="min-w-0 rounded-xl border border-blue-200 bg-white px-3 py-2.5 text-sm font-bold text-slate-900 outline-none focus:border-blue-500"
                />
                <input
                  value={claimCode}
                  onChange={event => setClaimCode(event.target.value.toUpperCase())}
                  placeholder="One-time claim code"
                  autoCapitalize="characters"
                  className="min-w-0 rounded-xl border border-blue-200 bg-white px-3 py-2.5 text-sm font-bold uppercase text-slate-900 outline-none focus:border-blue-500"
                />
                <button
                  type="button"
                  onClick={linkExistingEntry}
                  disabled={linking || !claimEntry.trim() || !claimCode.trim()}
                  className="rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-black text-white disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {linking ? 'Linking…' : 'Link entry'}
                </button>
              </div>
              {linkMessage && (
                <div className={`mt-3 text-xs font-bold ${linkMessage.includes('successfully') ? 'text-emerald-700' : 'text-rose-700'}`}>
                  {linkMessage}
                </div>
              )}
              <div className="mt-3 text-[11px] font-semibold leading-5 text-blue-800">The claim code is single-use. Once linked, the entry cannot be claimed by another account.</div>
            </div>
          </div>
        </section>
      )}

      {hasEntry && !ruleConfirmed && (
        <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5 md:p-6">
          <div className="flex gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-amber-100 text-amber-700"><AlertTriangle size={20} /></div>
            <div>
              <div className="text-lg font-black text-slate-950">Week {saved.pool_current_week ?? survivor.pool_current_week ?? '—'} recommendation is locked</div>
              <p className="mt-2 text-sm leading-6 text-amber-950">Your current-week pool state has not cleared the official rule gate. The research board remains visible, but no candidate is promoted to a final personal recommendation.</p>
              <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-black">
                <span className="rounded-full bg-white px-3 py-1.5 text-amber-800">{humanize(saved.rule_status || 'AWAITING OFFICIAL POOL SHEET')}</span>
                <span className="rounded-full bg-white px-3 py-1.5 text-amber-800">{humanize(saved.ownership?.status || 'WAITING OWNERSHIP')}</span>
              </div>
            </div>
          </div>
        </section>
      )}

      {hasEntry && (
        <section>
          <div className="section-heading">
            <div><p className="eyebrow">My entry</p><h2>Teams already used</h2></div>
            <span className="health-pill">{usedTeams.length} USED</span>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="flex flex-wrap gap-2">
              {usedTeams.length ? usedTeams.map((team, index) => (
                <span key={team} className="rounded-full bg-slate-950 px-3 py-2 text-xs font-black text-white">{index + 1}. {team}</span>
              )) : <span className="text-sm text-slate-400">No teams have been recorded yet.</span>}
            </div>
            <div className="mt-4 text-xs font-semibold leading-5 text-slate-500">Used teams are private member state and are removed from your research board automatically.</div>
          </div>
        </section>
      )}

      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Week {survivor.pool_current_week ?? saved.pool_current_week ?? '—'} research</p>
            <h2>Survivor decision board</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
              Market survival, context, future value and risk are shown separately. {hasEntry ? 'Your used teams are removed privately.' : 'This is generic research until an authenticated pool context is linked.'}
            </p>
          </div>
          <span className={`health-pill ${hasEntry && ruleConfirmed ? 'emerald' : ''}`}>{hasEntry && ruleConfirmed ? 'PERSONAL RULE CONFIRMED' : 'RESEARCH ONLY'}</span>
        </div>

        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {candidates.slice(0, 9).map((row, index) => (
            <div key={row.team} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[10px] font-black uppercase tracking-[0.14em] text-slate-400">#{index + 1} research rank</div>
                  <div className="mt-2 text-xl font-black text-slate-950">{row.team}</div>
                  <div className="mt-1 text-xs font-semibold text-slate-400">vs {row.opponent}</div>
                </div>
                <span className={`rounded-full px-3 py-1 text-[10px] font-black ${tierTone(row.decision_tier)}`}>{humanize(row.decision_tier)}</span>
              </div>

              <div className="mt-5 grid grid-cols-3 gap-2 text-center text-xs">
                <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.market_prob_pct ?? '—'}%</div><div className="mt-1 text-slate-400">Market</div></div>
                <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.hulk_context_score ?? '—'}</div><div className="mt-1 text-slate-400">Context</div></div>
                <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.spread ?? '—'}</div><div className="mt-1 text-slate-400">Spread</div></div>
              </div>

              <div className="mt-4 flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-3 py-2 text-xs">
                <span className="font-black text-slate-600">Strategy {Number(row.strategy_index || 0).toFixed(1)}</span>
                <span className="font-bold text-slate-400">{humanize(row.future_value_label)}</span>
              </div>

              <div className="mt-4 text-xs leading-5 text-slate-500">
                <b className="text-slate-700">Positive:</b> {row.positive_signals ? humanize(row.positive_signals.replaceAll('|', ' · ')) : 'None listed'}
              </div>
              <div className="mt-2 text-xs leading-5 text-slate-500">
                <b className="text-slate-700">Risk:</b> {row.risk_signals ? humanize(row.risk_signals.replaceAll('|', ' · ')) : 'No additional risk signal'}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="text-xs font-black uppercase tracking-[0.14em] text-blue-700">Pool state</div>
          <div className="mt-3 text-lg font-black text-slate-950">{hasEntry ? humanize(saved.rule_status || 'UNKNOWN') : 'Authentication required for personal rules'}</div>
          <div className="mt-2 text-sm leading-6 text-slate-500">{hasEntry ? `Current pool week: ${saved.pool_current_week ?? '—'} · latest official sheet week: ${saved.ownership?.official_pool_week ?? '—'}.` : 'Generic Survivor research does not expose member pool rules or ownership.'}</div>
        </div>
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="text-xs font-black uppercase tracking-[0.14em] text-violet-700">Forward accountability</div>
          <div className="mt-3 text-lg font-black text-slate-950">Saved picks and model proof stay separate</div>
          <div className="mt-2 text-sm leading-6 text-slate-500">A personal recommendation only enters the model record after the authenticated pool rule state is confirmed and the recommendation is frozen before kickoff.</div>
        </div>
      </section>
    </div>
  )
}

function FantasyNewsPanel() {
  const [news, setNews] = useState({ generated_at: null, articles: [] })
  const [filter, setFilter] = useState('ALL')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const r = await fetch(`/fantasy_news.json?ts=${Date.now()}`, { cache: 'no-store' })
        if (!r.ok) throw new Error('fantasy news unavailable')
        const payload = await r.json()
        if (!cancelled) setNews(payload)
      } catch {
        if (!cancelled) setNews({ generated_at: null, articles: [] })
      }
    }
    load()
    const timer = window.setInterval(load, 300000)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [])

  const tabs = ['ALL', 'INJURY', 'WAIVER WATCH', 'START/SIT WATCH', 'TRADE', 'DEPTH CHART']
  const fantasyImpactTags = new Set(['INJURY', 'WAIVER WATCH', 'START/SIT WATCH', 'TRADE', 'DEPTH CHART', 'ROSTER MOVE', 'ROLE CHANGE'])
  const promoPattern = /promo code|bonus bets?|sportsbook|betmgm|fanduel promo|draftkings promo|betting promos?|best bets? for|odds, predictions/i
  const rows = (news.articles || [])
    .filter(article => {
      const tags = article.impact_tags || []
      const hasFantasyImpact = tags.some(tag => fantasyImpactTags.has(tag))
      const matchesFilter = filter === 'ALL' || tags.includes(filter)
      return hasFantasyImpact && matchesFilter && !promoPattern.test(String(article.title || ''))
    })
    .slice(0, 10)

  return (
    <section>
      <div className="section-heading">
        <div><p className="eyebrow">Fantasy intelligence</p><h2>News that changes lineups</h2></div>
        <span className="health-pill emerald">LIVE FEEDS</span>
      </div>
      <div className="mb-4 flex gap-2 overflow-x-auto pb-1">
        {tabs.map(tab => (
          <button key={tab} onClick={() => setFilter(tab)} className={`whitespace-nowrap rounded-full px-3 py-2 text-xs font-black ${filter === tab ? 'bg-slate-950 text-white' : 'border border-slate-200 bg-white text-slate-500'}`}>{tab}</button>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {rows.map((article, i) => (
          <a key={`${article.url}-${i}`} href={article.url} target="_blank" rel="noreferrer" className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft transition hover:-translate-y-0.5 hover:border-blue-200">
            <div className="flex flex-wrap gap-2">
              {(article.impact_tags || []).map(tag => <span key={tag} className="rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-black text-amber-700">{tag}</span>)}
            </div>
            <div className="mt-4 text-base font-black leading-6 text-slate-950">{article.title}</div>
            <div className="mt-3 flex items-center justify-between gap-3 text-xs font-semibold text-slate-400">
              <span>{article.source}</span>
              <span>{article.published_at ? new Date(article.published_at).toLocaleString() : ''}</span>
            </div>
          </a>
        ))}
      </div>
    </section>
  )
}

function SectionGrid({ title, items }) {
  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Product area</p>
          <h2>{title}</h2>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((item) => (
          <button key={item} className="group flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-soft transition hover:-translate-y-0.5 hover:border-blue-200">
            <span className="font-extrabold text-slate-800">{item}</span>
            <ChevronRight size={18} className="text-slate-300 transition group-hover:text-blue-600" />
          </button>
        ))}
      </div>
    </section>
  )
}

function useJsonEndpoint(path, fallback = {}) {
  const [data, setData] = useState(fallback)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const response = await fetch(`${path}?ts=${Date.now()}`, { cache: 'no-store' })
        if (!response.ok) throw new Error(`${path} unavailable`)
        const payload = await response.json()
        if (!cancelled) setData(payload)
      } catch {
        if (!cancelled) setData(fallback)
      }
    }
    load()
    const timer = window.setInterval(load, 30000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [path])

  return data
}

function usePrivateSurvivorState(refreshKey = 0) {
  const { user, getAccessToken } = useAuth()
  const [data, setData] = useState({
    status: user ? 'LOADING' : 'AUTH_REQUIRED',
    entry_linked: false,
    used_teams: [],
    current_picks: [],
  })

  useEffect(() => {
    let cancelled = false
    let timer = null

    if (!user) {
      setData({
        status: 'AUTH_REQUIRED',
        entry_linked: false,
        used_teams: [],
        current_picks: [],
      })
      return () => {}
    }

    const load = async () => {
      try {
        const token = await getAccessToken()
        if (!token) throw new Error('No authenticated session')
        const response = await fetch(`/api/survivor/state?ts=${Date.now()}`, {
          cache: 'no-store',
          headers: { Authorization: `Bearer ${token}` },
        })
        const payload = await response.json()
        if (!response.ok) throw new Error(payload.message || payload.error || 'Private Survivor state unavailable')
        if (!cancelled) setData(payload)
      } catch {
        if (!cancelled) {
          setData({
            status: 'AUTH_REQUIRED',
            entry_linked: false,
            used_teams: [],
            current_picks: [],
          })
        }
      }
    }

    load()
    timer = window.setInterval(load, 30000)
    return () => {
      cancelled = true
      if (timer) window.clearInterval(timer)
    }
  }, [user?.id, getAccessToken, refreshKey])

  return data
}

function humanize(value) {
  return String(value || '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function CommercialHero({ onNavigate }) {
  return (
    <section className="overflow-hidden rounded-[32px] border border-slate-200 bg-white shadow-soft">
      <div className="grid gap-8 p-7 md:p-10 lg:grid-cols-[1.35fr_.65fr] lg:items-end">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-3 py-1.5 text-xs font-black uppercase tracking-[0.16em] text-blue-700">
            <Activity size={14} /> Live sports intelligence
          </div>
          <h1 className="mt-5 max-w-4xl text-4xl font-black tracking-[-0.04em] text-slate-950 md:text-6xl">
            One place for the game.
            <span className="block text-blue-700">Answers first. Evidence underneath.</span>
          </h1>
          <p className="mt-5 max-w-3xl text-base font-medium leading-7 text-slate-500 md:text-lg">
            Scores, betting research, props, PrizePicks, parlays, Survivor, fantasy, DFS and news — organized around the decisions you actually need to make.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <button onClick={() => onNavigate('Best Bets')} className="rounded-2xl bg-slate-950 px-5 py-3 text-sm font-black text-white shadow-lg shadow-slate-950/10 transition hover:-translate-y-0.5">
              See today's intelligence
            </button>
            <button onClick={() => onNavigate('Ask')} className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-black text-slate-700 transition hover:border-blue-200 hover:text-blue-700">
              Ask the brain
            </button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="mini-metric"><Brain size={18} /><b>Learning</b><span>Forward tracked</span></div>
          <div className="mini-metric"><ShieldCheck size={18} /><b>Proof</b><span>Losses stay visible</span></div>
          <div className="mini-metric"><Radio size={18} /><b>Live</b><span>Scores + markets</span></div>
          <div className="mini-metric"><Sparkles size={18} /><b>Ask</b><span>Context aware</span></div>
        </div>
      </div>
    </section>
  )
}

function HomeDecisionPanel({ onNavigate }) {
  const { user } = useAuth()
  const bets = useJsonEndpoint('/betting_v2_all_markets_current.json', { summary: {}, picks: [] })
  const props = useJsonEndpoint('/prop_v2_current.json', { summary: {}, picks: [] })
  const parlays = useJsonEndpoint('/parlay_v2_current.json', { summary: {}, picks: [] })
  const survivor = useJsonEndpoint('/survivor_v2_current.json', {})
  const privateSurvivor = usePrivateSurvivorState()

  const propRows = (props.picks || []).filter((row) => row.lane === 'PROP')
  const prizeRows = (props.picks || []).filter((row) => row.lane === 'PRIZEPICKS')
  const prizeMonitor = prizeRows.find((row) => row.shadow_decision === 'SHADOW_MONITOR')
  const bestPlay = (bets.picks || []).find((row) => row.shadow_decision === 'SHADOW_PLAY')
  const hasPersonalSurvivor = Boolean(user && privateSurvivor.entry_linked)
  const survivorPick = hasPersonalSurvivor && Array.isArray(privateSurvivor.shadow_recommendation)
    ? privateSurvivor.shadow_recommendation[0]
    : null

  const cards = [
    {
      label: 'Best Bets',
      route: 'Best Bets',
      status: (bets.summary?.shadow_plays || 0) > 0 ? 'PLAY' : 'NO FORCED PLAY',
      title: bestPlay ? `${bestPlay.selection} · ${bestPlay.market}` : 'Nothing has cleared the play gate',
      detail: `${bets.summary?.candidates ?? 0} current candidates · ${bets.summary?.passes ?? 0} passed over`,
      tone: (bets.summary?.shadow_plays || 0) > 0 ? 'emerald' : 'blue',
    },
    {
      label: 'Props',
      route: 'Props',
      status: 'RESEARCH',
      title: `${propRows.length} current prop candidates`,
      detail: 'Independent edge and price proof are required before PLAY.',
      tone: 'blue',
    },
    {
      label: 'PrizePicks',
      route: 'PrizePicks',
      status: prizeMonitor ? 'MONITOR' : 'RESEARCH',
      title: prizeMonitor ? `${prizeMonitor.player} ${prizeMonitor.side} ${prizeMonitor.line}` : `${prizeRows.length} current entries checked`,
      detail: prizeMonitor
        ? `Model ${prizeMonitor.v2_probability_pct}% · market reference ${prizeMonitor.market_reference_probability_pct}%`
        : 'No entry is being forced without proof.',
      tone: prizeMonitor ? 'amber' : 'blue',
    },
    {
      label: 'Parlays',
      route: 'Parlays',
      status: 'PROOF GATE',
      title: 'No parlay has cleared source-leg proof',
      detail: `${parlays.summary?.candidates ?? 0} combinations checked · ${parlays.summary?.shadow_monitors ?? 0} monitors`,
      tone: 'violet',
    },
    {
      label: 'Survivor',
      route: 'Survivor',
      status: hasPersonalSurvivor
        ? (privateSurvivor.rule_confirmed ? 'READY' : 'WAITING')
        : (user ? 'NO POOL' : 'SIGN IN'),
      title: hasPersonalSurvivor
        ? (survivorPick?.team || `Week ${privateSurvivor.pool_current_week ?? survivor.pool_current_week ?? '—'} personal decision locked`)
        : user
          ? 'No Survivor pool linked'
          : `Week ${survivor.pool_current_week ?? '—'} generic research`,
      detail: hasPersonalSurvivor
        ? (privateSurvivor.rule_confirmed
            ? `${privateSurvivor.active_entry || 'Active entry'} · ${survivorPick?.market_prob_pct ?? '—'}% market survival`
            : humanize(privateSurvivor.rule_status || 'Personal pool rule is still waiting'))
        : user
          ? 'Your account is ready; personal pool state appears only after a secure link.'
          : 'Sign in for private used teams, saved picks and pool-specific guidance.',
      tone: hasPersonalSurvivor
        ? (privateSurvivor.rule_confirmed ? 'emerald' : 'amber')
        : 'blue',
    },
  ]

  const tone = {
    blue: 'border-blue-100 bg-blue-50 text-blue-700',
    emerald: 'border-emerald-100 bg-emerald-50 text-emerald-700',
    amber: 'border-amber-100 bg-amber-50 text-amber-700',
    violet: 'border-violet-100 bg-violet-50 text-violet-700',
  }

  return (
    <section>
      <div className="section-heading">
        <div><p className="eyebrow">Right now</p><h2>What matters now</h2></div>
        <button onClick={() => onNavigate('Brain Record')} className="text-sm font-black text-blue-700">How good is the brain? →</button>
      </div>
      <div className="flex snap-x gap-4 overflow-x-auto pb-2 xl:grid xl:grid-cols-5 xl:overflow-visible">
        {cards.map((card) => (
          <button key={card.label} onClick={() => onNavigate(card.route)} className="min-w-[270px] snap-start rounded-3xl border border-slate-200 bg-white p-5 text-left shadow-soft transition hover:-translate-y-0.5 hover:border-blue-200 xl:min-w-0">
            <div className="flex items-center justify-between gap-3">
              <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">{card.label}</div>
              <span className={`rounded-full border px-2.5 py-1 text-[10px] font-black ${tone[card.tone]}`}>{card.status}</span>
            </div>
            <div className="mt-4 text-lg font-black leading-6 text-slate-950">{card.title}</div>
            <div className="mt-3 text-xs font-semibold leading-5 text-slate-500">{card.detail}</div>
            <div className="mt-5 text-xs font-black text-blue-700">Open {card.label} →</div>
          </button>
        ))}
      </div>
    </section>
  )
}

function HomeScoreRail({ onNavigate }) {
  const nfl = useJsonEndpoint('/nfl_scores.json', { games: [] })
  const mlb = useJsonEndpoint('/mlb_scores.json', { today_games: [] })
  const nba = useJsonEndpoint('/nba_scores.json', { games: [] })
  const nhl = useJsonEndpoint('/nhl_scores.json', { games: [] })
  const cfb = useJsonEndpoint('/cfb_scores.json', { games: [] })
  const cbb = useJsonEndpoint('/cbb_scores.json', { games: [] })
  const normalize = (game, league) => ({
    id: game.event_id || game.gamePk || `${league}-${game.away}-${game.home}`,
    league,
    away: game.away_abbr || game.away || game.away_team || 'Away',
    home: game.home_abbr || game.home || game.home_team || 'Home',
    awayScore: (game.final || game.live) ? (game.away_score ?? game.awayScore ?? '—') : '—',
    homeScore: (game.final || game.live) ? (game.home_score ?? game.homeScore ?? '—') : '—',
    status: game.final ? 'FINAL' : game.live ? 'LIVE' : 'UPCOMING',
  })
  const games = [
    ...(nfl.games || []).map((game) => normalize(game, 'NFL')),
    ...(mlb.today_games || mlb.games || []).map((game) => normalize(game, 'MLB')),
    ...(nba.games || []).map((game) => normalize(game, 'NBA')),
    ...(nhl.games || []).map((game) => normalize(game, 'NHL')),
    ...(cfb.games || []).map((game) => normalize(game, 'CFB')),
    ...(cbb.games || []).map((game) => normalize(game, 'CBB')),
  ]
    .sort((a, b) => {
      const rank = (game) => game.status === 'LIVE' ? 0 : game.status === 'FINAL' ? 2 : 1
      return rank(a) - rank(b)
    })
    .slice(0, 12)

  return (
    <section>
      <div className="section-heading">
        <div><p className="eyebrow">Scores</p><h2>Across the sports world</h2><p className="mt-2 text-sm text-slate-500">NFL · MLB · NBA · NHL · CFB · CBB in one live rail.</p></div>
        <button onClick={() => onNavigate('Scores')} className="text-sm font-black text-blue-700">View all scores →</button>
      </div>
      {games.length ? (
        <div className="flex snap-x gap-3 overflow-x-auto pb-2">
          {games.map((game) => (
            <div key={game.id} className="min-w-[230px] snap-start rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
              <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-[0.14em]">
                <span className="text-blue-700">{game.league}</span>
                <span className={game.status === 'LIVE' ? 'text-red-600' : 'text-slate-400'}>{game.status}</span>
              </div>
              <div className="mt-4 space-y-2 text-sm font-black text-slate-900">
                <div className="flex items-center justify-between"><span>{game.away}</span><span>{game.awayScore}</span></div>
                <div className="flex items-center justify-between"><span>{game.home}</span><span>{game.homeScore}</span></div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyPanel icon={Radio} title="Score feeds are connected" text="There are no games in the current display window. Upcoming and live games will appear automatically." />
      )}
    </section>
  )
}

function HomeImpactNews({ onNavigate }) {
  const graph = useJsonEndpoint('/ask_retrieval.json', { news_events: [] })

  const impactTypes = new Set(['INJURY', 'TRANSACTION', 'LINEUP_ROLE', 'FANTASY', 'RECAP'])
  const promoPattern = /promo code|bonus bets?|sportsbook|deposit|free bet|betting promo/i
  const seen = new Set()
  const rows = (graph.news_events || [])
    .filter((row) => row.event_source_type === 'NEWS' && impactTypes.has(row.event_type) && row.title)
    .filter((row) => !promoPattern.test(String(row.title || '')))
    .sort((a, b) => String(b.published_or_effective_at || '').localeCompare(String(a.published_or_effective_at || '')))
    .filter((row) => {
      const key = String(row.title || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
      if (!key || seen.has(key)) return false
      seen.add(key)
      return true
    })
    .slice(0, 4)

  const why = (row) => {
    const type = String(row.event_type || '').toUpperCase()
    if (type === 'INJURY') return 'Availability can change fantasy roles, props and game expectations.'
    if (type === 'TRANSACTION') return 'Roster movement can change depth charts, usage and opportunity.'
    if (type === 'LINEUP_ROLE') return 'Role changes can alter volume, fantasy value and matchup assumptions.'
    if (type === 'FANTASY') return 'Fantasy context can affect waiver, Start/Sit and roster decisions.'
    if (type === 'RECAP') return 'Final results feed the learning loop and next-game context.'
    return 'This development may affect a current sports decision.'
  }

  const tone = (type) => {
    const value = String(type || '').toUpperCase()
    if (value === 'INJURY') return 'bg-rose-50 text-rose-700'
    if (value === 'TRANSACTION') return 'bg-violet-50 text-violet-700'
    if (value === 'LINEUP_ROLE' || value === 'FANTASY') return 'bg-emerald-50 text-emerald-700'
    return 'bg-blue-50 text-blue-700'
  }

  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">News & insights</p>
          <h2>What changed that could matter</h2>
        </div>
        <button onClick={() => onNavigate('News & Insights')} className="text-sm font-black text-blue-700">Open News & Insights →</button>
      </div>

      {rows.length ? (
        <div className="flex snap-x gap-4 overflow-x-auto pb-2 xl:grid xl:grid-cols-4 xl:overflow-visible">
          {rows.map((row) => (
            <button key={row.event_node_id} onClick={() => onNavigate('News & Insights')} className="min-w-[285px] snap-start rounded-3xl border border-slate-200 bg-white p-5 text-left shadow-soft transition hover:-translate-y-0.5 hover:border-blue-200 xl:min-w-0">
              <div className="flex items-center justify-between gap-3">
                <span className="rounded-full bg-slate-950 px-2.5 py-1 text-[10px] font-black text-white">{row.sport}</span>
                <span className={`rounded-full px-2.5 py-1 text-[10px] font-black ${tone(row.event_type)}`}>{humanize(row.event_type)}</span>
              </div>
              <div className="mt-4 line-clamp-3 text-base font-black leading-6 text-slate-950">{row.title}</div>
              <div className="mt-3 text-xs font-semibold leading-5 text-slate-500">{why(row)}</div>
              <div className="mt-4 flex items-center justify-between gap-3 border-t border-slate-100 pt-3 text-[10px] font-bold text-slate-400">
                <span>{row.source}</span>
                <span>{row.published_or_effective_at ? new Date(row.published_or_effective_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : ''}</span>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <EmptyPanel icon={Radio} title="Impact news is quiet" text="The reporting graph is connected. New injury, transaction, role and fantasy-impact events will appear here automatically." />
      )}
    </section>
  )
}

function HomeSnapshots({ onNavigate }) {
  const { user } = useAuth()
  const survivor = useJsonEndpoint('/survivor_v2_current.json', {})
  const privateSurvivor = usePrivateSurvivorState()
  const fantasy = useJsonEndpoint('/fantasy_v2_current.json', { lanes: {} })
  const performance = useJsonEndpoint('/performance_snapshot.json', { official: {} })
  const official = performance.official || {}
  const laneCount = Object.values(fantasy.lanes || {}).filter((lane) => lane.forward_grade_available).length
  const hasPersonalSurvivor = Boolean(user && privateSurvivor.entry_linked)

  return (
    <section className="grid gap-4 lg:grid-cols-3">
      <button onClick={() => onNavigate('Survivor')} className="rounded-3xl border border-slate-200 bg-white p-6 text-left shadow-soft transition hover:border-emerald-200">
        <div className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">{hasPersonalSurvivor ? 'My Survivor' : 'Survivor'}</div>
        <div className="mt-3 text-2xl font-black text-slate-950">
          {hasPersonalSurvivor
            ? privateSurvivor.active_entry
            : user
              ? 'No pool linked'
              : `Week ${survivor.pool_current_week ?? '—'} research`}
        </div>
        <div className="mt-2 text-sm font-semibold text-slate-500">
          {hasPersonalSurvivor
            ? `Week ${privateSurvivor.pool_current_week ?? survivor.pool_current_week ?? '—'} · ${(privateSurvivor.used_teams || []).length} teams used`
            : user
              ? 'Account ready for a private Survivor entry'
              : 'Sign in for private entries, used teams and pool rules'}
        </div>
        <div className="mt-5 text-xs font-black text-emerald-700">Open Survivor →</div>
      </button>
      <button onClick={() => onNavigate('Fantasy')} className="rounded-3xl border border-slate-200 bg-white p-6 text-left shadow-soft transition hover:border-blue-200">
        <div className="text-xs font-black uppercase tracking-[0.14em] text-blue-700">Fantasy + DFS</div>
        <div className="mt-3 text-2xl font-black text-slate-950">{laneCount} forward-tested lanes</div>
        <div className="mt-2 text-sm font-semibold text-slate-500">Start/Sit · FAAB · IR stash · Defense · IDP · DFS</div>
        <div className="mt-5 text-xs font-black text-blue-700">Open Fantasy →</div>
      </button>
      <button onClick={() => onNavigate('Brain Record')} className="rounded-3xl border border-slate-200 bg-slate-950 p-6 text-left text-white shadow-soft transition hover:-translate-y-0.5">
        <div className="text-xs font-black uppercase tracking-[0.14em] text-emerald-400">Brain Record</div>
        <div className="mt-3 text-3xl font-black">{official.wins ?? 0}-{official.losses ?? 0}-{official.pushes ?? 0}</div>
        <div className="mt-2 text-sm font-semibold text-slate-300">{official.published ?? 0} published · {official.pending ?? 0} pending · {official.roi_pct == null ? 'ROI waiting for settled priced picks' : `${official.units >= 0 ? '+' : ''}${Number(official.units || 0).toFixed(2)}u · ${Number(official.roi_pct).toFixed(1)}% ROI`}</div>
        <div className="mt-5 text-xs font-black text-emerald-300">See the proof →</div>
      </button>
    </section>
  )
}

function BettingSubnav({ active, onNavigate }) {
  return (
    <div className="flex gap-2 overflow-x-auto rounded-2xl border border-slate-200 bg-white p-2 shadow-soft">
      {bettingNavItems.map((item) => (
        <button key={item} onClick={() => onNavigate(item)} className={`whitespace-nowrap rounded-xl px-4 py-2.5 text-sm font-black transition ${active === item ? 'bg-slate-950 text-white' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'}`}>
          {item}
        </button>
      ))}
    </div>
  )
}

function SportFilter({ sports, active, onChange }) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {['ALL', ...sports].map((sport) => (
        <button key={sport} onClick={() => onChange(sport)} className={`whitespace-nowrap rounded-full px-3 py-2 text-xs font-black ${active === sport ? 'bg-blue-700 text-white' : 'border border-slate-200 bg-white text-slate-500'}`}>
          {sport === 'ALL' ? 'All sports' : sport}
        </button>
      ))}
    </div>
  )
}

function BestBetsV2Panel() {
  const data = useJsonEndpoint('/betting_v2_all_markets_current.json', { summary: {}, picks: [] })
  const [sport, setSport] = useState('ALL')
  const rows = data.picks || []
  const sports = Array.from(new Set(rows.map((row) => row.sport).filter(Boolean))).sort()
  const visible = rows
    .filter((row) => sport === 'ALL' || row.sport === sport)
    .sort((a, b) => (b.shadow_decision === 'SHADOW_PLAY') - (a.shadow_decision === 'SHADOW_PLAY') || (b.conservative_expected_value_pct ?? -999) - (a.conservative_expected_value_pct ?? -999))
    .slice(0, 12)
  const summary = data.summary || {}

  return (
    <section className="space-y-5">
      <div className="section-heading">
        <div><p className="eyebrow">Betting</p><h2>Best Bets</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">Every game market is compared with the market baseline first. A research candidate is not a PLAY unless the independent model, price and forward-proof gates all clear.</p></div>
        <span className="health-pill">{summary.candidates ?? 0} CURRENT</span>
      </div>
      <div className={`rounded-2xl border p-4 text-sm font-semibold ${(summary.shadow_plays || 0) > 0 ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-blue-200 bg-blue-50 text-blue-900'}`}>
        {(summary.shadow_plays || 0) > 0
          ? `${summary.shadow_plays} independently qualified play${summary.shadow_plays === 1 ? '' : 's'} are being tracked.`
          : `No independently proven PLAY right now. ${summary.candidates ?? 0} candidates were evaluated and ${summary.passes ?? 0} failed at least one proof gate.`}
      </div>
      <SportFilter sports={sports} active={sport} onChange={setSport} />
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {visible.map((row, i) => (
          <div key={`${row.game_key}-${row.market}-${row.selection_key}-${i}`} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="flex items-start justify-between gap-3">
              <div><div className="text-xs font-black uppercase tracking-[0.14em] text-blue-700">{row.sport} · {humanize(row.market)}</div><div className="mt-2 text-xl font-black text-slate-950">{row.selection}</div></div>
              <span className={`rounded-full px-3 py-1 text-[10px] font-black ${row.shadow_decision === 'SHADOW_PLAY' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{row.shadow_decision === 'SHADOW_PLAY' ? 'PLAY' : 'PASS'}</span>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.calibrated_win_probability_pct ?? '—'}%</div><div className="mt-1 text-slate-400">Probability</div></div>
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.market_reference_probability_pct ?? '—'}%</div><div className="mt-1 text-slate-400">Market fair</div></div>
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.conservative_expected_value_pct == null ? '—' : `${row.conservative_expected_value_pct}%`}</div><div className="mt-1 text-slate-400">Cons. EV</div></div>
            </div>
            <div className="mt-4 text-xs font-semibold leading-5 text-slate-500">{humanize(row.historical_edge_confidence)} · {row.book_count ?? '—'} books · quality {row.data_quality_grade || '—'}</div>
            <div className="mt-2 text-[11px] leading-5 text-slate-400">{humanize(row.selection_rule_status)}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

function PropsV2Panel({ lane = 'PROP' }) {
  const data = useJsonEndpoint('/prop_v2_current.json', { summary: {}, picks: [] })
  const [sport, setSport] = useState('ALL')
  const allRows = (data.picks || []).filter((row) => row.lane === lane)
  const sports = Array.from(new Set(allRows.map((row) => row.sport).filter(Boolean))).sort()
  const decisionRank = (row) => row.shadow_decision === 'SHADOW_PLAY' ? 3 : row.shadow_decision === 'SHADOW_MONITOR' ? 2 : 1
  const rows = allRows
    .filter((row) => sport === 'ALL' || row.sport === sport)
    .sort((a, b) =>
      decisionRank(b) - decisionRank(a)
      || (b.conservative_edge_pct_points ?? -999) - (a.conservative_edge_pct_points ?? -999)
      || (b.edge_pct_points ?? -999) - (a.edge_pct_points ?? -999)
    )
  const plays = allRows.filter((row) => row.shadow_decision === 'SHADOW_PLAY').length
  const monitors = allRows.filter((row) => row.shadow_decision === 'SHADOW_MONITOR').length
  const isPrize = lane === 'PRIZEPICKS'

  return (
    <section className="space-y-5">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{isPrize ? 'Pick-em research' : 'Player markets'}</p>
          <h2>{isPrize ? 'PrizePicks' : 'Props'}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">{isPrize ? 'Leg quality and entry profitability are separate. A strong leg never becomes a recommended entry without payout economics and forward proof.' : 'Player lines are evaluated by sport and market subtype. Model probability must beat the market reference before price/EV can matter.'}</p>
        </div>
        <span className="health-pill">{allRows.length} CURRENT</span>
      </div>
      <div className={`rounded-2xl border p-4 text-sm font-semibold ${monitors ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-blue-200 bg-blue-50 text-blue-900'}`}>
        {plays ? `${plays} PLAY${plays === 1 ? '' : 'S'} currently cleared.` : monitors ? `${monitors} shadow monitor${monitors === 1 ? '' : 's'} are promising but not proven PLAYs.` : 'No independently proven PLAY is being forced right now.'}
      </div>

      {isPrize && (
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
            <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Leg proof</div>
            <div className="mt-2 text-2xl font-black text-slate-950">{monitors}</div>
            <div className="mt-1 text-xs font-semibold text-slate-500">promising monitors · {plays} proven plays</div>
          </div>
          <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4">
            <div className="text-[10px] font-black uppercase tracking-[0.12em] text-violet-700">Entry economics</div>
            <div className="mt-2 text-lg font-black text-slate-950">Payout proof required</div>
            <div className="mt-1 text-xs leading-5 text-violet-900">A good leg does not automatically make a profitable multi-pick entry.</div>
          </div>
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
            <div className="text-[10px] font-black uppercase tracking-[0.12em] text-emerald-700">Card discipline</div>
            <div className="mt-2 text-lg font-black text-slate-950">No forced entries</div>
            <div className="mt-1 text-xs leading-5 text-emerald-900">If the proof gate does not clear, the correct recommendation is to pass.</div>
          </div>
        </div>
      )}

      <SportFilter sports={sports} active={sport} onChange={setSport} />
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {rows.slice(0, 12).map((row, i) => {
          const decision = row.shadow_decision || 'PASS'
          const statusClass = decision === 'SHADOW_PLAY' ? 'bg-emerald-50 text-emerald-700' : decision === 'SHADOW_MONITOR' ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-600'
          return (
            <div key={`${row.event_id}-${row.player_key}-${row.market_subtype}-${row.side}-${i}`} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
              <div className="flex items-start justify-between gap-3">
                <div><div className="text-xs font-black uppercase tracking-[0.14em] text-blue-700">{row.sport} · {humanize(row.market_subtype)}</div><div className="mt-2 text-xl font-black text-slate-950">{row.player}</div></div>
                <span className={`rounded-full px-3 py-1 text-[10px] font-black ${statusClass}`}>{decision === 'SHADOW_MONITOR' ? 'MONITOR' : decision === 'SHADOW_PLAY' ? 'PLAY' : 'PASS'}</span>
              </div>
              <div className="mt-4 text-2xl font-black text-slate-950">{row.side} {row.line}</div>
              <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
                <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.v2_probability_pct ?? '—'}%</div><div className="mt-1 text-slate-400">Model</div></div>
                <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.market_reference_probability_pct ?? '—'}%</div><div className="mt-1 text-slate-400">Market</div></div>
                <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.conservative_probability_pct ?? '—'}%</div><div className="mt-1 text-slate-400">Conservative</div></div>
              </div>
              <div className="mt-4 text-xs font-semibold leading-5 text-slate-500">Quality {row.data_quality_grade || '—'} · {row.data_quality_book_count ?? '—'} books · {humanize(row.historical_edge_confidence)}</div>
              <div className="mt-2 text-[11px] leading-5 text-slate-400">{humanize(row.selection_rule_status)}</div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function ParlaysV2Panel() {
  const data = useJsonEndpoint('/parlay_v2_current.json', { summary: {}, picks: [] })
  const summary = data.summary || {}
  const rows = (data.picks || [])
    .filter((row) => row.resolved_legs === row.leg_count)
    .sort((a, b) => (b.shadow_decision === 'SHADOW_MONITOR') - (a.shadow_decision === 'SHADOW_MONITOR') || (b.joint_v2_probability_pct ?? 0) - (a.joint_v2_probability_pct ?? 0))
    .slice(0, 10)

  return (
    <section className="space-y-5">
      <div className="section-heading">
        <div><p className="eyebrow">Betting</p><h2>Parlays</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">Parlays do not inherit confidence just because their individual legs look interesting. Source-leg proof, correlation and the actual combined payout all have to be known.</p></div>
        <span className="health-pill">{summary.candidates ?? 0} CURRENT</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {[
          ['Candidates', summary.candidates ?? 0],
          ['Exact V2 legs', summary.resolved_all_legs ?? 0],
          ['Source proof', summary.all_source_legs_forward_proven ?? 0],
          ['Captured price', summary.captured_parlay_price ?? 0],
          ['Monitors', summary.shadow_monitors ?? 0],
        ].map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft"><div className="text-2xl font-black text-slate-950">{value}</div><div className="mt-1 text-xs font-black uppercase tracking-[0.12em] text-slate-400">{label}</div></div>
        ))}
      </div>
      <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4 text-sm font-semibold text-violet-900">No parlay can become a PLAY while its source legs are unproven or the combined price is missing. Research joint probability is not being presented as a payout claim.</div>
      <div className="grid gap-4 lg:grid-cols-2">
        {rows.map((row, i) => (
          <div key={`${row.combo_signature}-${i}`} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
            <div className="flex items-center justify-between gap-3"><span className="text-xs font-black uppercase tracking-[0.14em] text-violet-700">{row.sport} · {humanize(row.correlation_status)}</span><span className="rounded-full bg-slate-100 px-3 py-1 text-[10px] font-black text-slate-600">PASS</span></div>
            <div className="mt-4 space-y-2">
              {(row.legs || []).map((leg, j) => (
                <div key={j} className="rounded-2xl bg-slate-50 p-4"><div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Leg {j + 1} · {humanize(leg.source_lane)}</div><div className="mt-1 font-black text-slate-900">{leg.player || leg.selection} {leg.selection} {leg.line ?? ''} {humanize(leg.market)}</div></div>
              ))}
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2 text-center text-xs">
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.joint_v2_probability_pct ?? '—'}%</div><div className="mt-1 text-slate-400">Research joint</div></div>
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.captured_parlay_american_odds ?? '—'}</div><div className="mt-1 text-slate-400">Captured price</div></div>
            </div>
            <div className="mt-4 text-xs font-semibold leading-5 text-slate-500">{humanize(row.shadow_decision)} · {humanize(row.payout_status)}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

function CrossSportBoxscore({ league, eventId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    fetch(`/api/boxscore?league=${encodeURIComponent(league)}&event=${encodeURIComponent(eventId)}`, { cache: 'no-store' })
      .then(async response => {
        const payload = await response.json()
        if (!response.ok) throw new Error(payload.error || 'Box score unavailable')
        return payload
      })
      .then(payload => { if (!cancelled) setData(payload) })
      .catch(err => { if (!cancelled) setError(err.message || 'Box score unavailable') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [league, eventId])

  if (loading) return <div className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm font-bold text-slate-500">Loading box score…</div>
  if (error) return <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900">{error}</div>
  if (!data) return null

  const teams = data.teams || []
  const statLabels = Array.from(new Set(teams.flatMap(team => (team.stats || []).map(stat => stat.label)))).slice(0, 8)
  const byTeam = team => Object.fromEntries((team.stats || []).map(stat => [stat.label, stat.value]))

  return (
    <div className="mt-4 space-y-4 border-t border-slate-100 pt-4">
      {!!statLabels.length && (
        <div className="overflow-x-auto rounded-2xl border border-slate-100">
          <table className="w-full min-w-[480px] text-xs">
            <thead className="bg-slate-50 text-slate-400">
              <tr>
                <th className="px-3 py-2 text-left font-black">Team</th>
                {statLabels.map(label => <th key={label} className="px-3 py-2 text-right font-black">{label}</th>)}
              </tr>
            </thead>
            <tbody>
              {teams.map(team => {
                const stats = byTeam(team)
                return (
                  <tr key={team.abbreviation || team.team} className="border-t border-slate-100">
                    <td className="px-3 py-2 font-black text-slate-800">{team.abbreviation || team.team}</td>
                    {statLabels.map(label => <td key={label} className="px-3 py-2 text-right font-semibold text-slate-600">{stats[label] ?? '—'}</td>)}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {!!data.leaders?.length && (
        <div>
          <div className="text-[10px] font-black uppercase tracking-[0.14em] text-slate-400">Game leaders</div>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {data.leaders.slice(0, 8).map((leader, index) => (
              <div key={`${leader.team}-${leader.category}-${index}`} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2">
                <div className="min-w-0">
                  <div className="truncate text-xs font-black text-slate-800">{leader.player || '—'}</div>
                  <div className="text-[10px] font-semibold text-slate-400">{leader.team} · {leader.category}</div>
                </div>
                <div className="shrink-0 text-xs font-black text-blue-700">{leader.value}</div>
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

function CrossSportScorePanel({ league }) {
  const data = useJsonEndpoint(`/${league.toLowerCase()}_scores.json`, { games: [], counts: {}, status: 'LOADING' })
  const [openId, setOpenId] = useState(null)
  const [showAll, setShowAll] = useState(false)
  const games = [...(data.games || [])]
    .sort((a, b) => {
      const rank = game => game.live ? 0 : game.final ? 2 : 1
      return rank(a) - rank(b) || String(a.start_time || '').localeCompare(String(b.start_time || ''))
    })
  const visible = showAll ? games : games.slice(0, 24)

  const formatStart = value => {
    if (!value) return 'Time TBD'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
  }

  if (!games.length) {
    return (
      <EmptyPanel
        icon={Trophy}
        title={`${league} — no games in the current window`}
        text={`The ${league} score feed is connected and healthy. There are no games from yesterday through tomorrow, so the app is showing an honest empty state instead of stale scores.`}
      />
    )
  }

  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">{league}</p>
          <h2>{league} scores</h2>
          <p className="mt-2 text-sm text-slate-500">Live, final and upcoming games from the current three-day window. Open any game for box-score detail.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="health-pill emerald">{data.counts?.live ?? 0} LIVE</span>
          <span className="health-pill">{data.counts?.final ?? 0} FINAL</span>
          <span className="health-pill">{data.counts?.upcoming ?? 0} UPCOMING</span>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {visible.map(game => {
          const pre = !game.live && !game.final
          const statusTone = game.live ? 'bg-rose-50 text-rose-700' : game.final ? 'bg-slate-100 text-slate-600' : 'bg-blue-50 text-blue-700'
          return (
            <div key={game.event_id} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
              <div className="flex items-center justify-between gap-3">
                <span className={`rounded-full px-3 py-1 text-[10px] font-black ${statusTone}`}>{game.live ? 'LIVE' : game.final ? 'FINAL' : 'UPCOMING'}</span>
                <span className="text-[11px] font-bold text-slate-400">{game.status || formatStart(game.start_time)}</span>
              </div>

              <div className="mt-5 space-y-3">
                {[
                  [game.away_abbr || game.away, game.away, game.away_score, game.away_record, game.away_logo],
                  [game.home_abbr || game.home, game.home, game.home_score, game.home_record, game.home_logo],
                ].map(([abbr, name, score, record, logo]) => (
                  <div key={name} className="flex items-center gap-3">
                    {logo ? <img src={logo} alt="" className="h-8 w-8 object-contain" /> : <div className="h-8 w-8 rounded-full bg-slate-100" />}
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-black text-slate-900">{name || abbr}</div>
                      {record && <div className="text-[10px] font-semibold text-slate-400">{record}</div>}
                    </div>
                    <div className="text-xl font-black text-slate-950">{pre ? '—' : (score ?? '—')}</div>
                  </div>
                ))}
              </div>

              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
                <div className="text-[11px] font-semibold text-slate-400">
                  {game.broadcasts?.length ? game.broadcasts.join(' · ') : formatStart(game.start_time)}
                </div>
                {game.boxscore_available && (
                  <button onClick={() => setOpenId(openId === game.event_id ? null : game.event_id)} className="text-xs font-black text-blue-700">
                    {openId === game.event_id ? 'Hide box score' : 'View box score'} →
                  </button>
                )}
              </div>

              {openId === game.event_id && <CrossSportBoxscore league={league} eventId={game.event_id} />}
            </div>
          )
        })}
      </div>

      {games.length > 24 && (
        <div className="mt-5 text-center">
          <button onClick={() => setShowAll(value => !value)} className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-black text-slate-700 shadow-soft">
            {showAll ? 'Show fewer games' : `Show all ${games.length} games`}
          </button>
        </div>
      )}
    </section>
  )
}

function ScoresHub() {
  const [league, setLeague] = useState('NFL')

  return (
    <div className="space-y-7">
      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Scores</p>
            <h2>Scores & box scores</h2>
            <p className="mt-2 text-sm text-slate-500">NFL, MLB, NBA, NHL, college football and college basketball in one score center.</p>
          </div>
          <span className="health-pill emerald">LIVE FEEDS</span>
        </div>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {scoreLeagues.map(item => (
            <button key={item} onClick={() => setLeague(item)} className={`rounded-full px-4 py-2 text-xs font-black ${league === item ? 'bg-slate-950 text-white' : 'border border-slate-200 bg-white text-slate-500'}`}>{item}</button>
          ))}
        </div>
      </section>

      {league === 'NFL' && <Scoreboard />}
      {league === 'MLB' && <MlbPanel />}
      {['NBA', 'NHL', 'CFB', 'CBB'].includes(league) && <CrossSportScorePanel league={league} />}
    </div>
  )
}

function NewsInsightsPanel() {
  const graph = useJsonEndpoint('/ask_retrieval.json', { news_events: [], counts: {}, truth_rules: {} })
  const survivor = useJsonEndpoint('/survivor_v2_current.json', {})
  const props = useJsonEndpoint('/prop_v2_current.json', { picks: [] })
  const editorial = useJsonEndpoint('/insight_drafts.json', { drafts: [], editorial_policy: {} })
  const [sport, setSport] = useState('ALL')
  const [view, setView] = useState('Impact')

  const news = (graph.news_events || []).filter((row) => row.event_source_type === 'NEWS' && row.title)
  const sports = ['ALL', ...Array.from(new Set(news.map((row) => row.sport).filter(Boolean))).sort()]
  const impactTypes = new Set(['INJURY', 'TRANSACTION', 'LINEUP_ROLE', 'FANTASY', 'RECAP'])

  const filtered = news
    .filter((row) => sport === 'ALL' || row.sport === sport)
    .filter((row) => {
      if (view === 'Latest') return true
      if (view === 'Injuries') return row.event_type === 'INJURY'
      if (view === 'Fantasy') return ['FANTASY', 'INJURY', 'LINEUP_ROLE', 'TRANSACTION'].includes(row.event_type)
      return impactTypes.has(row.event_type)
    })
    .sort((a, b) => String(b.published_or_effective_at || '').localeCompare(String(a.published_or_effective_at || '')))
    .slice(0, 18)

  const monitors = (props.picks || []).filter((row) => row.lane === 'PRIZEPICKS' && row.shadow_decision === 'SHADOW_MONITOR')
  const topInjury = news.find((row) => row.event_type === 'INJURY')
  const insightIdeas = [
    topInjury ? {
      label: 'Injury impact',
      title: topInjury.title,
      reason: 'Connect the reporting to role, matchup, fantasy and market changes before drafting a conclusion.',
    } : null,
    {
      label: 'Survivor strategy',
      title: `Week ${survivor.pool_current_week ?? '—'} pool decision`,
      reason: survivor.rule_confirmed
        ? 'Explain the recommended survival path, future value and risks.'
        : 'Explain why the recommendation is still locked and what official information is missing.',
    },
    monitors.length ? {
      label: 'Pick-em research',
      title: `${monitors.length} PrizePicks shadow monitor${monitors.length === 1 ? '' : 's'}`,
      reason: 'Explain why the legs are interesting, why they are not PLAYs yet, and which proof gate remains.',
    } : {
      label: 'Model learning',
      title: 'Why passing can be the right decision',
      reason: 'Use the Brain Record to explain why disciplined PASS decisions protect the public record.',
    },
  ].filter(Boolean)
  const editorialDrafts = (editorial.drafts || []).slice(0, 6)

  const eventTone = (type) => {
    if (type === 'INJURY') return 'bg-rose-50 text-rose-700'
    if (type === 'TRANSACTION') return 'bg-violet-50 text-violet-700'
    if (type === 'RECAP') return 'bg-blue-50 text-blue-700'
    if (type === 'FANTASY' || type === 'LINEUP_ROLE') return 'bg-emerald-50 text-emerald-700'
    return 'bg-slate-100 text-slate-600'
  }

  return (
    <div className="space-y-8">
      <section className="rounded-[30px] border border-slate-200 bg-white p-6 shadow-soft md:p-8">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <p className="eyebrow">News & Insights</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-slate-950 md:text-4xl">Know what changed — and why it matters</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-500">Cross-sport reporting is linked to the same structured facts used by the rest of the application. Source links stay visible, and reporting never silently becomes a model fact.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="health-pill emerald">{graph.counts?.news_events ?? news.length} EVENTS</span>
            <span className="health-pill">{graph.counts?.facts ?? 0} STRUCTURED FACTS</span>
          </div>
        </div>
      </section>

      <section>
        <div className="section-heading">
          <div><p className="eyebrow">Live reporting</p><h2>{view === 'Impact' ? 'What matters now' : view}</h2></div>
          <span className="health-pill emerald">SOURCE LINKS PRESERVED</span>
        </div>

        <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-soft lg:flex-row lg:items-center lg:justify-between">
          <div className="flex gap-2 overflow-x-auto">
            {['Impact', 'Latest', 'Injuries', 'Fantasy'].map((item) => (
              <button key={item} onClick={() => setView(item)} className={`whitespace-nowrap rounded-xl px-4 py-2.5 text-sm font-black ${view === item ? 'bg-slate-950 text-white' : 'text-slate-500 hover:bg-slate-50'}`}>{item}</button>
            ))}
          </div>
          <div className="flex gap-2 overflow-x-auto">
            {sports.map((item) => (
              <button key={item} onClick={() => setSport(item)} className={`whitespace-nowrap rounded-full px-3 py-2 text-xs font-black ${sport === item ? 'bg-blue-700 text-white' : 'border border-slate-200 bg-white text-slate-500'}`}>{item === 'ALL' ? 'All sports' : item}</button>
            ))}
          </div>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {filtered.map((item) => (
            <a key={item.event_node_id} href={item.source_url || undefined} target={item.source_url ? '_blank' : undefined} rel="noreferrer" className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft transition hover:-translate-y-0.5 hover:border-blue-200">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-slate-950 px-2.5 py-1 text-[10px] font-black text-white">{item.sport}</span>
                  <span className={`rounded-full px-2.5 py-1 text-[10px] font-black ${eventTone(item.event_type)}`}>{humanize(item.event_type)}</span>
                </div>
                <span className="text-[10px] font-black uppercase tracking-wide text-slate-400">{item.source}</span>
              </div>
              <div className="mt-4 text-lg font-black leading-6 text-slate-950">{item.title}</div>
              {item.detail && item.detail !== item.title && <div className="mt-2 line-clamp-3 text-sm leading-6 text-slate-500">{item.detail}</div>}
              <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-[11px] font-semibold text-slate-400">
                <span>{item.source_tier === 'EXTERNAL_NEWS' ? 'Attributed reporting' : humanize(item.source_tier)}</span>
                <span>{item.published_or_effective_at ? new Date(item.published_or_effective_at).toLocaleString() : ''}</span>
              </div>
            </a>
          ))}
        </div>

        {!filtered.length && <EmptyPanel icon={Radio} title="No matching news" text="There are no current reporting events for this filter. The feed will update automatically when new source events arrive." />}
      </section>

      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Sports Zenith Insights</p>
            <h2>Future original publishing engine</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">The brain can identify stories worth explaining, but publication should require evidence, sources and editorial approval.</p>
          </div>
          <span className="health-pill">MANUAL APPROVAL</span>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          {insightIdeas.map((idea) => (
            <div key={idea.label} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
              <div className="text-xs font-black uppercase tracking-[0.14em] text-blue-700">{idea.label}</div>
              <div className="mt-3 text-xl font-black leading-7 text-slate-950">{idea.title}</div>
              <div className="mt-3 text-sm leading-6 text-slate-500">{idea.reason}</div>
              <div className="mt-5 rounded-2xl bg-slate-50 p-3 text-xs font-bold leading-5 text-slate-600">Draft rule: what happened → why it matters → evidence → conclusion → confidence → what could change the conclusion → sources.</div>
            </div>
          ))}
        </div>

        {!!editorialDrafts.length && (
          <div className="mt-7">
            <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
              <div>
                <div className="text-xs font-black uppercase tracking-[0.14em] text-violet-700">Editorial queue</div>
                <div className="mt-1 text-2xl font-black text-slate-950">Evidence-locked draft briefs</div>
                <div className="mt-2 text-sm text-slate-500">These are structured briefs only. No article is published until a human approves the evidence, framing and sources.</div>
              </div>
              <span className="health-pill">{editorialDrafts.length} DRAFTS</span>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              {editorialDrafts.map((draft) => (
                <details key={draft.draft_id} className="group rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
                  <summary className="cursor-pointer list-none">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-full bg-violet-50 px-2.5 py-1 text-[10px] font-black text-violet-700">{draft.category}</span>
                          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-black text-slate-600">DRAFT ONLY</span>
                        </div>
                        <div className="mt-3 text-lg font-black leading-6 text-slate-950">{draft.title}</div>
                        <div className="mt-2 text-sm leading-6 text-slate-500">{draft.thesis}</div>
                      </div>
                      <div className="shrink-0 rounded-xl bg-slate-950 px-3 py-2 text-xs font-black text-white">P{draft.priority}</div>
                    </div>
                    <div className="mt-4 text-xs font-black text-blue-700 group-open:hidden">View evidence & guardrails →</div>
                  </summary>

                  <div className="mt-5 space-y-5 border-t border-slate-100 pt-5">
                    <div>
                      <div className="text-[10px] font-black uppercase tracking-[0.14em] text-slate-400">Evidence</div>
                      <div className="mt-2 grid gap-2 sm:grid-cols-2">
                        {(draft.evidence || []).slice(0, 8).map((item, index) => (
                          <div key={index} className="rounded-xl bg-slate-50 p-3">
                            <div className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{item.label}</div>
                            <div className="mt-1 text-sm font-black text-slate-900">{item.value == null ? '—' : String(item.value)}</div>
                            {item.note && <div className="mt-1 text-[10px] leading-4 text-slate-400">{item.note}</div>}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <div className="text-[10px] font-black uppercase tracking-[0.14em] text-emerald-700">Reasoning</div>
                        <ul className="mt-2 space-y-1.5 text-xs leading-5 text-slate-600">
                          {(draft.reasoning || []).map((item, index) => <li key={index}>• {item}</li>)}
                        </ul>
                      </div>
                      <div>
                        <div className="text-[10px] font-black uppercase tracking-[0.14em] text-amber-700">What could change it</div>
                        <ul className="mt-2 space-y-1.5 text-xs leading-5 text-slate-600">
                          {(draft.what_could_change_the_conclusion || []).map((item, index) => <li key={index}>• {item}</li>)}
                        </ul>
                      </div>
                    </div>

                    {!!draft.risks?.length && (
                      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3">
                        <div className="text-[10px] font-black uppercase tracking-[0.14em] text-amber-700">Risks / limitations</div>
                        <ul className="mt-2 space-y-1 text-xs leading-5 text-amber-950">
                          {draft.risks.map((item, index) => <li key={index}>• {item}</li>)}
                        </ul>
                      </div>
                    )}

                    <div className="border-t border-slate-100 pt-4">
                      <div className="text-[10px] font-black uppercase tracking-[0.14em] text-slate-400">Sources</div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {(draft.sources || []).map((item, index) => item.url ? (
                          <a key={index} href={item.url} target="_blank" rel="noreferrer" className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-black text-blue-700">{item.label} ↗</a>
                        ) : (
                          <span key={index} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-[11px] font-black text-slate-500">{item.label}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                </details>
              ))}
            </div>
          </div>
        )}

        <div className="mt-4 rounded-3xl border border-slate-200 bg-slate-950 p-6 text-white">
          <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-center">
            <div>
              <div className="text-xs font-black uppercase tracking-[0.14em] text-emerald-400">Publishing integrity</div>
              <div className="mt-2 text-xl font-black">Engagement can choose what to explain next. It cannot change prediction truth.</div>
              <div className="mt-2 text-sm leading-6 text-slate-300">Future articles can generate social and email variants after approval, while every analytical claim stays tied to the underlying evidence and proof status.</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-center text-xs font-black uppercase tracking-wide text-emerald-300">No auto-publish</div>
          </div>
        </div>
      </section>
    </div>
  )
}

function FantasyLaneCard({ lane, row }) {
  const base = "rounded-3xl border border-slate-200 bg-white p-5 shadow-soft"
  if (lane === 'weekly') {
    return (
      <div className={base}>
        <div className="flex items-start justify-between gap-3">
          <div><div className="text-xs font-black uppercase tracking-[0.14em] text-blue-700">{row.team} · {row.position}</div><div className="mt-2 text-xl font-black text-slate-950">{row.player}</div><div className="mt-1 text-xs font-semibold text-slate-400">vs {row.opponent || '—'}</div></div>
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-[10px] font-black text-emerald-700">{humanize(row.weekly_tier)}</span>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.weekly_research_score ?? '—'}</div><div className="mt-1 text-slate-400">Weekly</div></div>
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.ros_research_score ?? '—'}</div><div className="mt-1 text-slate-400">ROS</div></div>
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.snap_pct == null ? '—' : `${row.snap_pct}%`}</div><div className="mt-1 text-slate-400">Snaps</div></div>
        </div>
        <div className="mt-4 text-xs font-semibold leading-5 text-slate-500">{humanize(row.role_signal)} · {row.research_reasons || 'No extra research reason listed'}</div>
      </div>
    )
  }

  if (lane === 'faab') {
    return (
      <div className={base}>
        <div className="flex items-start justify-between gap-3">
          <div><div className="text-xs font-black uppercase tracking-[0.14em] text-violet-700">{row.sport} · {row.team || '—'} {row.position ? `· ${row.position}` : ''}</div><div className="mt-2 text-xl font-black text-slate-950">{row.player}</div></div>
          <span className="rounded-full bg-violet-50 px-3 py-1 text-[10px] font-black text-violet-700">{humanize(row.waiver_priority)}</span>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.waiver_research_score ?? '—'}</div><div className="mt-1 text-slate-400">Research</div></div>
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.adds_24h == null ? '—' : Number(row.adds_24h).toLocaleString()}</div><div className="mt-1 text-slate-400">Adds 24h</div></div>
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.suggested_faab_low_pct ?? '—'}–{row.suggested_faab_high_pct ?? '—'}%</div><div className="mt-1 text-slate-400">Research FAAB</div></div>
        </div>
        <div className="mt-4 text-xs leading-5 text-slate-500">This league-wide FAAB board is generic by design. Personalized roster need and saved-budget translation appear above for the active saved team; winning-bid prediction is still not claimed.</div>
      </div>
    )
  }

  if (lane === 'ir_stash') {
    return (
      <div className={base}>
        <div className="flex items-start justify-between gap-3">
          <div><div className="text-xs font-black uppercase tracking-[0.14em] text-amber-700">{row.sport} · {row.team || '—'}</div><div className="mt-2 text-xl font-black text-slate-950">{row.player}</div><div className="mt-1 text-xs font-semibold text-slate-400">{humanize(row.status)} · {row.injury_type || 'Injury type unavailable'}</div></div>
          <span className="rounded-full bg-amber-50 px-3 py-1 text-[10px] font-black text-amber-700">{humanize(row.stash_tier)}</span>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.stash_research_score ?? '—'}</div><div className="mt-1 text-slate-400">Stash score</div></div>
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.source_count ?? '—'}</div><div className="mt-1 text-slate-400">Sources</div></div>
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{humanize(row.return_window || 'UNKNOWN')}</div><div className="mt-1 text-slate-400">Window</div></div>
        </div>
        <div className="mt-4 text-xs leading-5 text-slate-500">{row.return_date ? `Reported return signal: ${row.return_date}. ` : ''}Return dates are never treated as guarantees{row.source_disagreement ? ' · sources disagree' : ''}.</div>
      </div>
    )
  }

  if (lane === 'defense_streaming') {
    return (
      <div className={base}>
        <div className="flex items-start justify-between gap-3">
          <div><div className="text-xs font-black uppercase tracking-[0.14em] text-emerald-700">NFL Defense</div><div className="mt-2 text-xl font-black text-slate-950">{row.dst_player || `${row.team} D/ST`}</div><div className="mt-1 text-xs font-semibold text-slate-400">{row.next_side || ''} vs {row.next_opponent || '—'}</div></div>
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-[10px] font-black text-emerald-700">{humanize(row.weekly_stream_tier)}</span>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.weekly_stream_score ?? '—'}</div><div className="mt-1 text-slate-400">This week</div></div>
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.multiweek_hold_score ?? '—'}</div><div className="mt-1 text-slate-400">Multiweek</div></div>
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.rest_days ?? '—'}</div><div className="mt-1 text-slate-400">Rest days</div></div>
        </div>
        <div className="mt-4 text-xs leading-5 text-slate-500">{humanize(row.future_schedule_signal)} · {humanize(row.multiweek_hold_tier)}</div>
      </div>
    )
  }

  return (
    <div className={base}>
      <div className="flex items-start justify-between gap-3">
        <div><div className="text-xs font-black uppercase tracking-[0.14em] text-sky-700">IDP · {row.idp_group || row.position || 'Defense'}</div><div className="mt-2 text-xl font-black text-slate-950">{row.player}</div><div className="mt-1 text-xs font-semibold text-slate-400">{row.team || '—'} · vs {row.next_opponent || '—'}</div></div>
        <span className="rounded-full bg-sky-50 px-3 py-1 text-[10px] font-black text-sky-700">{humanize(row.idp_usage_tier)}</span>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
        <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.idp_usage_score ?? '—'}</div><div className="mt-1 text-slate-400">Usage</div></div>
        <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.snap_pct == null ? '—' : `${Math.round(Number(row.snap_pct) * (Number(row.snap_pct) <= 1 ? 100 : 1))}%`}</div><div className="mt-1 text-slate-400">Snaps</div></div>
        <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.snap_pct_change == null ? '—' : `${Math.round(Number(row.snap_pct_change) * 100)} pts`}</div><div className="mt-1 text-slate-400">Snap change</div></div>
      </div>
      <div className="mt-4 text-xs leading-5 text-slate-500">{humanize(row.role_signal)} · usage research only until league-specific IDP scoring is connected.</div>
    </div>
  )
}






function LeagueSettingsPanel({ team, onSaved }) {
  const { user, getAccessToken } = useAuth()
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [scoringPreset, setScoringPreset] = useState('ppr')
  const [starterSlots, setStarterSlots] = useState({
    qb: 1, rb: 2, wr: 2, te: 1, flex: 1, superflex: 0, dst: 1, k: 1,
    dl: 0, lb: 0, db: 0, idp_flex: 0,
  })
  const [benchSlots, setBenchSlots] = useState(6)
  const [irSlots, setIrSlots] = useState(1)
  const [faabBudget, setFaabBudget] = useState('')
  const [faabRemaining, setFaabRemaining] = useState('')

  useEffect(() => {
    const scoring = team?.scoring && typeof team.scoring === 'object' ? team.scoring : {}
    const settings = team?.roster_settings && typeof team.roster_settings === 'object' ? team.roster_settings : {}
    const slots = settings.starting_slots && typeof settings.starting_slots === 'object' ? settings.starting_slots : {}

    const receptionPoints = Number(scoring.reception_points)
    const inferredPreset = scoring.preset
      || (receptionPoints === 0 ? 'standard' : receptionPoints === 0.5 ? 'half_ppr' : 'ppr')

    setScoringPreset(['ppr', 'half_ppr', 'standard'].includes(inferredPreset) ? inferredPreset : 'ppr')
    setStarterSlots({
      qb: Number.isFinite(Number(slots.qb)) ? Number(slots.qb) : 1,
      rb: Number.isFinite(Number(slots.rb)) ? Number(slots.rb) : 2,
      wr: Number.isFinite(Number(slots.wr)) ? Number(slots.wr) : 2,
      te: Number.isFinite(Number(slots.te)) ? Number(slots.te) : 1,
      flex: Number.isFinite(Number(slots.flex)) ? Number(slots.flex) : 1,
      superflex: Number.isFinite(Number(slots.superflex)) ? Number(slots.superflex) : 0,
      dst: Number.isFinite(Number(slots.dst)) ? Number(slots.dst) : 1,
      k: Number.isFinite(Number(slots.k)) ? Number(slots.k) : 1,
      dl: Number.isFinite(Number(slots.dl)) ? Number(slots.dl) : 0,
      lb: Number.isFinite(Number(slots.lb)) ? Number(slots.lb) : 0,
      db: Number.isFinite(Number(slots.db)) ? Number(slots.db) : 0,
      idp_flex: Number.isFinite(Number(slots.idp_flex)) ? Number(slots.idp_flex) : 0,
    })
    setBenchSlots(Number.isFinite(Number(settings.bench_slots)) ? Number(settings.bench_slots) : 6)
    setIrSlots(Number.isFinite(Number(settings.ir_slots)) ? Number(settings.ir_slots) : 1)

    const budget = scoring.faab_budget ?? settings.faab_budget
    const remaining = scoring.faab_remaining ?? settings.faab_remaining
    setFaabBudget(budget == null ? '' : String(budget))
    setFaabRemaining(remaining == null ? '' : String(remaining))
    setError('')
    setSaved(false)
  }, [team?.league_id])

  if (!user || !team?.league_id) return null

  const setSlot = (key, value) => {
    const parsed = Number(value)
    setStarterSlots((current) => ({
      ...current,
      [key]: Number.isFinite(parsed) ? Math.max(0, Math.min(30, Math.round(parsed))) : 0,
    }))
  }

  const save = async () => {
    setBusy(true)
    setError('')
    setSaved(false)
    try {
      const token = await getAccessToken()
      if (!token) throw new Error('Your session expired. Sign in again.')

      const response = await fetch('/api/fantasy/league-settings', {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          league_id: team.league_id,
          scoring_preset: scoringPreset,
          starter_slots: starterSlots,
          bench_slots: benchSlots,
          ir_slots: irSlots,
          faab_budget: faabBudget === '' ? null : Number(faabBudget),
          faab_remaining: faabRemaining === '' ? null : Number(faabRemaining),
        }),
      })

      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.message || payload.error || 'Could not save league settings.')

      onSaved?.({
        league_id: team.league_id,
        scoring: payload.scoring || {},
        roster_settings: payload.roster_settings || {},
      })
      setSaved(true)
    } catch (err) {
      setError(err?.message || 'Could not save league settings.')
    } finally {
      setBusy(false)
    }
  }

  const slotFields = [
    ['qb', 'QB'], ['rb', 'RB'], ['wr', 'WR'], ['te', 'TE'],
    ['flex', 'FLEX'], ['superflex', 'SUPERFLEX'], ['dst', 'D/ST'], ['k', 'K'],
    ['dl', 'DL'], ['lb', 'LB'], ['db', 'DB'], ['idp_flex', 'IDP FLEX'],
  ]

  return (
    <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <div>
          <div className="text-sm font-black text-slate-950">League settings</div>
          <div className="mt-1 text-[11px] font-semibold text-slate-500">Scoring · starter slots · bench/IR · FAAB budget</div>
        </div>
        <span className="rounded-full bg-white px-3 py-1 text-[10px] font-black uppercase tracking-[0.1em] text-blue-700">{open ? 'Close' : 'Edit'}</span>
      </button>

      {open && (
        <div className="mt-4 border-t border-slate-200 pt-4">
          <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Scoring format</div>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {[
              ['ppr', 'PPR'],
              ['half_ppr', 'Half-PPR'],
              ['standard', 'Standard'],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setScoringPreset(value)}
                className={`rounded-xl border px-3 py-2.5 text-xs font-black ${scoringPreset === value ? 'border-blue-300 bg-blue-50 text-blue-700' : 'border-slate-200 bg-white text-slate-600'}`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="mt-4 text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Starting lineup slots</div>
          <div className="mt-2 grid grid-cols-4 gap-2 sm:grid-cols-8">
            {slotFields.map(([key, label]) => (
              <label key={key} className="rounded-xl border border-slate-200 bg-white p-2 text-center">
                <div className="text-[9px] font-black uppercase tracking-wide text-slate-400">{label}</div>
                <input
                  aria-label={`${label} starter slots`}
                  type="number"
                  min="0"
                  max="30"
                  value={starterSlots[key]}
                  onChange={(event) => setSlot(key, event.target.value)}
                  className="mt-1 w-full bg-transparent text-center text-sm font-black text-slate-950 outline-none"
                />
              </label>
            ))}
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-4">
            <label>
              <span className="text-[10px] font-black uppercase tracking-[0.1em] text-slate-500">Bench</span>
              <input aria-label="Bench slots" type="number" min="0" max="30" value={benchSlots} onChange={(event) => setBenchSlots(Math.max(0, Math.min(30, Number(event.target.value) || 0)))} className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black outline-none" />
            </label>
            <label>
              <span className="text-[10px] font-black uppercase tracking-[0.1em] text-slate-500">IR</span>
              <input aria-label="IR slots" type="number" min="0" max="20" value={irSlots} onChange={(event) => setIrSlots(Math.max(0, Math.min(20, Number(event.target.value) || 0)))} className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black outline-none" />
            </label>
            <label>
              <span className="text-[10px] font-black uppercase tracking-[0.1em] text-slate-500">FAAB total</span>
              <input aria-label="FAAB total budget" type="number" min="0" max="100000" value={faabBudget} onChange={(event) => setFaabBudget(event.target.value)} placeholder="100" className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black outline-none" />
            </label>
            <label>
              <span className="text-[10px] font-black uppercase tracking-[0.1em] text-slate-500">FAAB left</span>
              <input aria-label="FAAB remaining" type="number" min="0" max="100000" value={faabRemaining} onChange={(event) => setFaabRemaining(event.target.value)} placeholder="100" className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black outline-none" />
            </label>
          </div>

          {error && <div className="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-xs font-bold text-rose-700">{error}</div>}
          {saved && <div className="mt-3 rounded-xl bg-emerald-50 px-3 py-2 text-xs font-bold text-emerald-700">League settings saved to your Sports Zenith account.</div>}

          <button type="button" onClick={save} disabled={busy} className="mt-4 flex h-11 w-full items-center justify-center rounded-xl bg-slate-950 px-4 text-sm font-black text-white disabled:opacity-40">
            {busy ? 'Saving…' : 'Save league settings'}
          </button>
          <div className="mt-2 text-[10px] font-semibold leading-4 text-slate-400">These settings stay private to this saved league and are used across personalized Start/Sit, Waivers, IR, Defense, IDP and Ask where applicable.</div>
        </div>
      )}
    </div>
  )
}

function RateMyTeamPanel({ preferredLeagueId = null, onSelectedLeagueChange, onTeamUpsert }) {
  const { user, getAccessToken } = useAuth()
  const [leagueName, setLeagueName] = useState('My Team')
  const [teamName, setTeamName] = useState('')
  const [rosterText, setRosterText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [savedTeams, setSavedTeams] = useState([])
  const [savedTeamsLoading, setSavedTeamsLoading] = useState(false)
  const [selectedLeagueId, setSelectedLeagueId] = useState(null)
  const [savedSummary, setSavedSummary] = useState(null)

  const rosterNames = useMemo(
    () => rosterText
      .split(/\n|,/)
      .map((value) => value.trim())
      .filter(Boolean)
      .slice(0, 60),
    [rosterText],
  )

  const selectedTeam = useMemo(
    () => savedTeams.find((team) => team.league_id === selectedLeagueId) || null,
    [savedTeams, selectedLeagueId],
  )

  const rosterItemName = (item) => {
    if (typeof item === 'string') return item.trim()
    if (item && typeof item === 'object') return String(item.name || item.player || '').trim()
    return ''
  }

  const loadSavedTeam = (team) => {
    if (!team) return
    const nextLeagueId = team.league_id || null
    setSelectedLeagueId(nextLeagueId)
    onSelectedLeagueChange?.(nextLeagueId)
    setLeagueName(team.league_name || 'My Team')
    setTeamName(team.team_name || '')
    setRosterText((team.roster || []).map(rosterItemName).filter(Boolean).join('\n'))
    setSavedSummary(team.last_analysis || null)
    setResult(null)
    setError('')
  }

  const updateSavedTeamSettings = ({ league_id, scoring, roster_settings }) => {
    const baseTeam = savedTeams.find((team) => team.league_id === league_id) || selectedTeam
    const updatedTeam = baseTeam
      ? { ...baseTeam, scoring: scoring || {}, roster_settings: roster_settings || {} }
      : null

    setSavedTeams((current) => current.map((team) => (
      team.league_id === league_id
        ? { ...team, scoring: scoring || {}, roster_settings: roster_settings || {} }
        : team
    )))

    if (updatedTeam) onTeamUpsert?.(updatedTeam)
  }

  useEffect(() => {
    if (!preferredLeagueId || preferredLeagueId === selectedLeagueId) return
    const preferred = savedTeams.find((team) => team.league_id === preferredLeagueId)
    if (preferred) loadSavedTeam(preferred)
  }, [preferredLeagueId, savedTeams, selectedLeagueId])

  useEffect(() => {
    let active = true

    if (!user) {
      setSavedTeams([])
      setSelectedLeagueId(null)
      setSavedSummary(null)
      return () => { active = false }
    }

    const load = async () => {
      setSavedTeamsLoading(true)
      try {
        const token = await getAccessToken()
        if (!token) throw new Error('No authenticated session')

        const response = await fetch('/api/fantasy/my-teams', {
          cache: 'no-store',
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!response.ok) throw new Error('Saved teams unavailable')

        const payload = await response.json()
        const teams = Array.isArray(payload?.teams) ? payload.teams : []
        if (!active) return

        setSavedTeams(teams)
        if (teams.length) {
          const preferred = teams.find((team) => team.league_id === preferredLeagueId) || teams[0]
          loadSavedTeam(preferred)
        } else {
          setSelectedLeagueId(null)
          setSavedSummary(null)
        }
      } catch {
        if (active) {
          setSavedTeams([])
          setSelectedLeagueId(null)
          setSavedSummary(null)
        }
      } finally {
        if (active) setSavedTeamsLoading(false)
      }
    }

    load()
    return () => { active = false }
  }, [user, getAccessToken])

  const analyze = async () => {
    if (!user || !rosterNames.length) return
    setBusy(true)
    setError('')
    setResult(null)

    try {
      const token = await getAccessToken()
      if (!token) throw new Error('Your session expired. Sign in again.')

      const response = await fetch('/api/fantasy/rate-my-team', {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          league_name: leagueName.trim() || 'My Team',
          team_name: teamName.trim() || leagueName.trim() || 'My Team',
          season: new Date().getUTCFullYear(),
          roster: rosterNames,
        }),
      })

      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.message || payload.error || 'Could not rate that roster.')

      const analysis = payload.analysis || null
      const savedLeagueId = payload?.league?.id || selectedLeagueId || null
      const latestSummary = analysis ? {
        generated_at: new Date().toISOString(),
        roster_size: analysis.roster_size ?? rosterNames.length,
        matched_count: analysis.matched_count ?? null,
        coverage_pct: analysis.coverage_pct ?? null,
        decision_coverage_pct: analysis.decision_coverage_pct ?? null,
        roster_research_index: analysis.roster_research_index ?? null,
        roster_research_band: analysis.roster_research_band || null,
        score_is_probability: false,
      } : null

      setResult(analysis)
      setSavedSummary(latestSummary)
      setSelectedLeagueId(savedLeagueId)

      if (savedLeagueId) {
        const savedTeam = {
          league_id: savedLeagueId,
          roster_id: payload.roster_id || null,
          platform: 'manual',
          league_name: payload?.league?.league_name || leagueName.trim() || 'My Team',
          team_name: payload?.league?.team_name || teamName.trim() || leagueName.trim() || 'My Team',
          season: payload?.league?.season || new Date().getUTCFullYear(),
          sync_status: 'manual',
          last_synced_at: latestSummary?.generated_at || null,
          roster: rosterNames,
          starters: [],
          bench: [],
          scoring: selectedTeam?.scoring || {},
          roster_settings: selectedTeam?.roster_settings || {},
          last_analysis: latestSummary,
        }
        setSavedTeams((current) => [
          savedTeam,
          ...current.filter((team) => team.league_id !== savedLeagueId),
        ])
        onTeamUpsert?.(savedTeam)
        onSelectedLeagueChange?.(savedLeagueId)
      }
    } catch (err) {
      setError(err?.message || 'Could not rate that roster.')
    } finally {
      setBusy(false)
    }
  }

  const indexValue = result?.roster_research_index
  const strengths = Array.isArray(result?.strengths) ? result.strengths : []
  const risks = Array.isArray(result?.risks) ? result.risks : []
  const unmatched = Array.isArray(result?.unmatched) ? result.unmatched : []
  const recognized = Array.isArray(result?.recognized_without_decision) ? result.recognized_without_decision : []

  return (
    <section className="grid gap-5 xl:grid-cols-[0.92fr_1.08fr]">
      <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-soft md:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="eyebrow">My Teams · Quick setup</p>
            <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950">Rate my team</h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              Paste your NFL roster and Sports Zenith will match it to current weekly, rest-of-season and defense-streaming research.
            </p>
          </div>
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
            <Users size={20} />
          </div>
        </div>

        {user && (
          <div className="mt-5">
            <div className="flex items-center justify-between gap-3">
              <div className="text-[11px] font-black uppercase tracking-[0.12em] text-slate-500">Saved teams</div>
              <button
                type="button"
                onClick={() => {
                  setSelectedLeagueId(null)
                  setLeagueName('My Team')
                  setTeamName('')
                  setRosterText('')
                  setSavedSummary(null)
                  setResult(null)
                  setError('')
                }}
                className="text-xs font-black text-blue-700"
              >
                + New team
              </button>
            </div>

            {savedTeamsLoading ? (
              <div className="mt-2 flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-xs font-bold text-slate-500">
                <Activity size={14} className="animate-pulse" /> Loading saved teams…
              </div>
            ) : savedTeams.length ? (
              <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
                {savedTeams.map((team) => {
                  const selected = selectedLeagueId === team.league_id
                  return (
                    <button
                      key={team.league_id}
                      type="button"
                      onClick={() => loadSavedTeam(team)}
                      className={`min-w-[190px] rounded-2xl border px-4 py-3 text-left transition ${selected ? 'border-blue-300 bg-blue-50' : 'border-slate-200 bg-white hover:border-blue-200'}`}
                    >
                      <div className="truncate text-sm font-black text-slate-950">{team.team_name || team.league_name || 'My Team'}</div>
                      <div className="mt-1 truncate text-[11px] font-semibold text-slate-400">{team.league_name || 'Manual league'} · {team.season || '—'}</div>
                      <div className="mt-2 text-[10px] font-black uppercase tracking-[0.1em] text-blue-700">
                        {team.last_analysis?.roster_research_index == null
                          ? 'Saved roster'
                          : `Index ${team.last_analysis.roster_research_index} · ${humanize(team.last_analysis.roster_research_band || 'NO_SCORE')}`}
                      </div>
                    </button>
                  )
                })}
              </div>
            ) : (
              <div className="mt-2 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-xs font-semibold text-slate-500">
                No saved teams yet. Your first analysis will appear here automatically.
              </div>
            )}
          </div>
        )}

        <LeagueSettingsPanel team={selectedTeam} onSaved={updateSavedTeamSettings} />

        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="text-[11px] font-black uppercase tracking-[0.12em] text-slate-500">League name</span>
            <input value={leagueName} onChange={(event) => setLeagueName(event.target.value)} maxLength={120} className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-bold text-slate-900 outline-none transition focus:border-blue-400 focus:ring-4 focus:ring-blue-50" />
          </label>
          <label className="block">
            <span className="text-[11px] font-black uppercase tracking-[0.12em] text-slate-500">Team name</span>
            <input value={teamName} onChange={(event) => setTeamName(event.target.value)} maxLength={120} placeholder="Optional" className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-bold text-slate-900 outline-none transition focus:border-blue-400 focus:ring-4 focus:ring-blue-50" />
          </label>
        </div>

        <label className="mt-4 block">
          <div className="flex items-center justify-between gap-3">
            <span className="text-[11px] font-black uppercase tracking-[0.12em] text-slate-500">Roster</span>
            <span className="text-[11px] font-bold text-slate-400">{rosterNames.length}/60</span>
          </div>
          <textarea
            value={rosterText}
            onChange={(event) => setRosterText(event.target.value)}
            rows={10}
            placeholder={'One player per line\nJosh Allen\nJahmyr Gibbs\nCeeDee Lamb\nTrey McBride\nDallas Cowboys D/ST'}
            className="mt-2 w-full resize-y rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold leading-6 text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-50"
          />
        </label>

        <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-xs font-semibold leading-5 text-blue-900">
          Quick Setup is provider-neutral. It does not require your fantasy-site password. League scoring and starter-slot rules are not applied yet, so the result is a research index—not a projected record or win probability.
        </div>

        {error && <div className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-xs font-bold text-rose-700">{error}</div>}

        <div className="mt-4">
          {user ? (
            <button
              type="button"
              onClick={analyze}
              disabled={busy || !rosterNames.length}
              className="flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-slate-950 px-4 text-sm font-black text-white shadow-lg shadow-slate-950/10 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy ? <><Activity size={17} className="animate-pulse" /> Analyzing…</> : <><Brain size={17} /> Analyze & save my team</>}
            </button>
          ) : (
            <div className="flex items-center justify-between gap-4 rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <div>
                <div className="text-sm font-black text-slate-950">Sign in to save a private team</div>
                <div className="mt-1 text-xs font-semibold leading-5 text-amber-900">Your roster stays attached only to your Sports Zenith account.</div>
              </div>
              <AccountButton />
            </div>
          )}
        </div>
      </div>

      <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-soft md:p-6">
        {!result ? (
          savedSummary ? (
            <div className="flex min-h-[420px] items-center justify-center">
              <div className="w-full max-w-md">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="eyebrow">Last saved snapshot</p>
                    <h3 className="mt-2 text-2xl font-black text-slate-950">{teamName || leagueName || 'My Team'}</h3>
                  </div>
                  <span className="rounded-full bg-blue-50 px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.12em] text-blue-700">Saved team</span>
                </div>

                <div className="mt-5 grid grid-cols-3 gap-3">
                  <div className="rounded-2xl bg-slate-950 p-4 text-white">
                    <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Research index</div>
                    <div className="mt-2 text-3xl font-black">{savedSummary.roster_research_index == null ? '—' : savedSummary.roster_research_index}</div>
                    <div className="mt-1 text-[10px] font-black text-blue-300">{humanize(savedSummary.roster_research_band || 'NO_SCORE')}</div>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Matched</div>
                    <div className="mt-2 text-2xl font-black text-slate-950">{savedSummary.matched_count ?? '—'}/{savedSummary.roster_size ?? rosterNames.length}</div>
                    <div className="mt-1 text-[11px] font-semibold text-slate-500">Last analysis</div>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Coverage</div>
                    <div className="mt-2 text-2xl font-black text-slate-950">{savedSummary.coverage_pct == null ? '—' : String(savedSummary.coverage_pct) + '%'}</div>
                    <div className="mt-1 text-[11px] font-semibold text-slate-500">Saved snapshot</div>
                  </div>
                </div>

                <div className="mt-5 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm leading-6 text-blue-950">
                  Your saved roster has been loaded. Press <span className="font-black">Analyze & save my team</span> to refresh it against the newest Sports Zenith fantasy signals.
                </div>
                <div className="mt-3 text-[11px] font-semibold leading-5 text-slate-400">The saved index is historical context only. Current research can change as roles, injuries, matchups and schedules update.</div>
              </div>
            </div>
          ) : (
            <div className="flex min-h-[420px] items-center justify-center text-center">
              <div className="max-w-sm">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-500"><Gauge size={25} /></div>
                <h3 className="mt-4 text-xl font-black text-slate-950">Your team report will appear here</h3>
                <p className="mt-2 text-sm leading-6 text-slate-500">Sports Zenith will show coverage, position research, strongest signals and actual risk flags. Missing data stays missing.</p>
              </div>
            </div>
          )
        ) : (
          <div>
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
              <div>
                <p className="eyebrow">Saved to your account</p>
                <h3 className="mt-2 text-2xl font-black text-slate-950">Team research report</h3>
              </div>
              <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.12em] text-emerald-700"><CheckCircle2 size={13} className="mr-1 inline" /> Private team saved</span>
            </div>

            <div className="mt-5 grid grid-cols-3 gap-3">
              <div className="rounded-2xl bg-slate-950 p-4 text-white">
                <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Research index</div>
                <div className="mt-2 text-3xl font-black">{indexValue == null ? '—' : indexValue}</div>
                <div className="mt-1 text-[10px] font-black text-blue-300">{humanize(result.roster_research_band || 'NO_SCORE')}</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Matched</div>
                <div className="mt-2 text-2xl font-black text-slate-950">{result.matched_count ?? 0}/{result.roster_size ?? 0}</div>
                <div className="mt-1 text-[11px] font-semibold text-slate-500">Decision players</div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Coverage</div>
                <div className="mt-2 text-2xl font-black text-slate-950">{result.coverage_pct ?? 0}%</div>
                <div className="mt-1 text-[11px] font-semibold text-slate-500">Recognized roster</div>
              </div>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4">
                <div className="text-xs font-black uppercase tracking-[0.12em] text-emerald-700">Strongest signals</div>
                <div className="mt-3 space-y-2">
                  {strengths.length ? strengths.map((row) => (
                    <div key={row.player_key || row.player} className="flex items-center justify-between gap-3 rounded-xl bg-white px-3 py-2.5">
                      <div className="min-w-0"><div className="truncate text-sm font-black text-slate-950">{row.player}</div><div className="text-[11px] font-semibold text-slate-400">{row.position} · {row.team || '—'}</div></div>
                      <div className="text-sm font-black text-emerald-700">{row.research_index ?? '—'}</div>
                    </div>
                  )) : <div className="text-xs font-semibold text-slate-500">No scored strengths yet.</div>}
                </div>
              </div>

              <div className="rounded-2xl border border-amber-100 bg-amber-50/60 p-4">
                <div className="text-xs font-black uppercase tracking-[0.12em] text-amber-700">Risk flags</div>
                <div className="mt-3 space-y-2">
                  {risks.length ? risks.map((row) => (
                    <div key={row.player_key || row.player} className="flex items-center justify-between gap-3 rounded-xl bg-white px-3 py-2.5">
                      <div className="min-w-0"><div className="truncate text-sm font-black text-slate-950">{row.player}</div><div className="text-[11px] font-semibold text-slate-400">{humanize(row.weekly_tier || row.research_band)}</div></div>
                      <div className="text-sm font-black text-amber-700">{row.research_index ?? '—'}</div>
                    </div>
                  )) : <div className="text-xs font-semibold text-slate-500">No sub-60 research flags in the matched roster.</div>}
                </div>
              </div>
            </div>

            {!!(unmatched.length || recognized.length) && (
              <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs font-black uppercase tracking-[0.12em] text-slate-500">Coverage notes</div>
                {recognized.length > 0 && <div className="mt-2 text-xs font-semibold leading-5 text-slate-600">Recognized but not currently scored: {recognized.map((row) => row.player).join(', ')}</div>}
                {unmatched.length > 0 && <div className="mt-2 text-xs font-semibold leading-5 text-rose-700">Needs review: {unmatched.map((row) => row.input).join(', ')}</div>}
              </div>
            )}

            <div className="mt-4 text-[11px] font-semibold leading-5 text-slate-400">{result.index_note}</div>
          </div>
        )}
      </div>
    </section>
  )
}

function FantasyCommercialPanel() {
  const { user, getAccessToken, loading: authLoading } = useAuth()
  const [mode, setMode] = useState('Season-Long')
  const [lane, setLane] = useState('my_teams')
  const [sport, setSport] = useState('NFL')
  const [teamOptions, setTeamOptions] = useState([])
  const [teamOptionsLoading, setTeamOptionsLoading] = useState(false)
  const [selectedLeagueId, setSelectedLeagueId] = useState(() => {
    try { return window.localStorage.getItem('sports-zenith-active-fantasy-league') || null }
    catch { return null }
  })
  const current = useJsonEndpoint('/fantasy_v2_current.json', { lanes: {} })
  const decisions = useJsonEndpoint('/fantasy_decisions.json', { personalization: {}, lanes: {} })
  const brain = useJsonEndpoint('/brain_performance.json', { fantasy_v2: {}, dfs: {} })

  const forward = brain.fantasy_v2?.forward || {}
  const dfs = brain.dfs || {}
  const laneBlock = decisions.lanes?.[lane] || { rows: [], source_rows: 0 }
  const allRows = laneBlock.rows || []
  const sports = Array.from(new Set(allRows.map((row) => row.sport).filter(Boolean))).sort()
  const effectiveSport = sports.includes(sport) ? sport : (sports[0] || 'ALL')
  const visibleRows = allRows.filter((row) => effectiveSport === 'ALL' || row.sport === effectiveSport).slice(0, 8)
  const forwardLanes = [
    ['Weekly', forward.weekly],
    ['FAAB', forward.faab],
    ['IR Stash', forward.ir_stash],
    ['Defense', forward.defense_streaming],
    ['IDP', forward.idp],
  ]
  const laneTabs = [
    ['my_teams', 'My Teams / Rate My Team'],
    ['weekly', 'Start / Sit'],
    ['faab', 'Waivers & FAAB'],
    ['ir_stash', 'IR Stash'],
    ['defense_streaming', 'Defense'],
    ['idp', 'IDP'],
  ]

  useEffect(() => {
    let active = true

    if (authLoading) {
      return () => { active = false }
    }

    if (!user) {
      setTeamOptions([])
      setSelectedLeagueId(null)
      setTeamOptionsLoading(false)
      return () => { active = false }
    }

    const load = async () => {
      setTeamOptionsLoading(true)
      try {
        const token = await getAccessToken()
        if (!token) throw new Error('No authenticated session')

        const response = await fetch('/api/fantasy/my-teams', {
          cache: 'no-store',
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!response.ok) throw new Error('Saved teams unavailable')

        const payload = await response.json()
        const teams = Array.isArray(payload?.teams) ? payload.teams : []
        if (!active) return

        setTeamOptions(teams)
        setSelectedLeagueId((currentLeagueId) => {
          if (currentLeagueId && teams.some((team) => team.league_id === currentLeagueId)) {
            return currentLeagueId
          }
          return teams[0]?.league_id || null
        })
      } catch {
        if (active) {
          setTeamOptions([])
          setSelectedLeagueId(null)
        }
      } finally {
        if (active) setTeamOptionsLoading(false)
      }
    }

    load()
    return () => { active = false }
  }, [user, getAccessToken, authLoading])

  const upsertTeamOption = (team) => {
    if (!team?.league_id) return
    setTeamOptions((current) => [
      team,
      ...current.filter((row) => row.league_id !== team.league_id),
    ])
    setSelectedLeagueId(team.league_id)
  }

  useEffect(() => {
    try {
      if (selectedLeagueId) window.localStorage.setItem('sports-zenith-active-fantasy-league', selectedLeagueId)
      else window.localStorage.removeItem('sports-zenith-active-fantasy-league')
    } catch {}
  }, [selectedLeagueId])

  const switchLane = (next) => {
    setLane(next)
    const laneSports = Array.from(new Set((decisions.lanes?.[next]?.rows || []).map((row) => row.sport).filter(Boolean))).sort()
    setSport(laneSports.includes('NFL') ? 'NFL' : (laneSports[0] || 'ALL'))
  }

  const dkTournament = (dfs.replay_modes || []).find((row) => row.platform === 'DRAFTKINGS' && row.mode === 'TOURNAMENT_UPSIDE')

  return (
    <div className="space-y-8">
      <section className="rounded-[30px] border border-slate-200 bg-white p-6 shadow-soft md:p-8">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <p className="eyebrow">Fantasy</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-slate-950 md:text-4xl">Fantasy command center</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-500">Weekly decisions, waivers, FAAB, IR stash, defense streaming, IDP and DFS — with research labels that stay separate from proven forward performance.</p>
          </div>
          <div className="flex gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-2">
            {['Season-Long','DFS Lineup Lab'].map((item) => (
              <button key={item} onClick={() => setMode(item)} className={`rounded-xl px-4 py-2.5 text-sm font-black ${mode === item ? 'bg-slate-950 text-white' : 'text-slate-500'}`}>{item}</button>
            ))}
          </div>
        </div>
      </section>

      {mode === 'Season-Long' ? (
        <>
          <section className="rounded-2xl border border-slate-200 bg-white p-2 shadow-soft">
            <div className="flex gap-2 overflow-x-auto">
              {laneTabs.map(([key,label]) => (
                <button key={key} onClick={() => switchLane(key)} className={`whitespace-nowrap rounded-xl px-4 py-2.5 text-sm font-black ${lane === key ? 'bg-slate-950 text-white' : 'text-slate-500'}`}>{label}</button>
              ))}
            </div>
          </section>

          {user && (
            <Suspense fallback={<LoadingSurface label="Loading Fantasy Team Control" />}>
              <FantasyTeamControl
                teams={teamOptions}
                selectedLeagueId={selectedLeagueId}
                loading={teamOptionsLoading}
                onSelect={setSelectedLeagueId}
                onManage={() => switchLane('my_teams')}
              />
            </Suspense>
          )}

          {lane === 'my_teams' ? (
            <RateMyTeamPanel
              preferredLeagueId={selectedLeagueId}
              onSelectedLeagueChange={setSelectedLeagueId}
              onTeamUpsert={upsertTeamOption}
            />
          ) : (
            <>
          {lane === 'weekly' && (
            <Suspense fallback={<LoadingSurface label="Loading your Start / Sit research" />}>
              <PersonalStartSitPanel leagueId={selectedLeagueId} onOpenMyTeams={() => switchLane('my_teams')} />
            </Suspense>
          )}
          {lane === 'faab' && (
            <Suspense fallback={<LoadingSurface label="Loading your waiver research" />}>
              <PersonalWaiverPanel leagueId={selectedLeagueId} onOpenMyTeams={() => switchLane('my_teams')} />
            </Suspense>
          )}
          {lane === 'ir_stash' && (
            <Suspense fallback={<LoadingSurface label="Loading your IR stash research" />}>
              <PersonalIrStashPanel leagueId={selectedLeagueId} onOpenMyTeams={() => switchLane('my_teams')} />
            </Suspense>
          )}
          {lane === 'defense_streaming' && (
            <Suspense fallback={<LoadingSurface label="Loading your defense streaming research" />}>
              <PersonalDefenseStreamingPanel leagueId={selectedLeagueId} onOpenMyTeams={() => switchLane('my_teams')} />
            </Suspense>
          )}
          {lane === 'idp' && (
            <Suspense fallback={<LoadingSurface label="Loading your IDP research" />}>
              <PersonalIdpPanel leagueId={selectedLeagueId} onOpenMyTeams={() => switchLane('my_teams')} />
            </Suspense>
          )}
          <section className="rounded-3xl border border-blue-200 bg-blue-50 p-5">
            <div className="flex gap-4">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-blue-700"><Users size={20} /></div>
              <div>
                <div className="flex flex-wrap items-center gap-2"><div className="text-lg font-black text-slate-950">League-wide intelligence</div><span className="rounded-full bg-white px-3 py-1 text-[10px] font-black text-blue-700">GENERIC RESEARCH</span></div>
                <p className="mt-2 text-sm leading-6 text-blue-950">The board below stays league-wide so you can compare your roster against the broader player pool. It never silently becomes personalized.</p>
                <p className="mt-2 text-xs font-semibold text-blue-800">
                  {lane === 'weekly'
                    ? 'Your active-team Start/Sit research appears above with saved scoring and starter-slot context when configured. The board below remains league-wide research.'
                    : lane === 'faab'
                      ? 'Your active-team waiver research appears above with roster need and saved-budget translation when configured. Actual league free-agent availability is still not verified.'
                      : lane === 'ir_stash'
                        ? 'Your active-team IR/Stash research appears above with saved IR capacity. Platform IR eligibility and outside-player availability are still not verified.'
                        : lane === 'defense_streaming'
                          ? 'Your active-team D/ST comparison appears above. Outside defenses remain research alternatives until league availability is actually verified.'
                          : lane === 'idp'
                            ? 'Your active-team IDP usage research appears above with saved IDP slots when configured. Custom IDP fantasy-point scoring and outside-player availability are not verified.'
                            : 'League-specific recommendations still require scoring and roster context.'}
                </p>
              </div>
            </div>
          </section>

          <section>
            <div className="section-heading">
              <div><p className="eyebrow">Forward proof</p><h2>Five fantasy lanes are being tested</h2></div>
              <span className="health-pill">NO AUTO-PROMOTION</span>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-2 xl:grid xl:grid-cols-5 xl:overflow-visible">
              {forwardLanes.map(([label, block]) => (
                <div key={label} className="min-w-[220px] rounded-2xl border border-slate-200 bg-white p-4 shadow-soft xl:min-w-0">
                  <div className="text-xs font-black uppercase tracking-[0.12em] text-slate-400">{label}</div>
                  <div className="mt-2 text-2xl font-black text-slate-950">{block?.tracked ?? 0}</div>
                  <div className="mt-1 text-xs font-bold text-slate-500">tracked · {block?.settled ?? 0} settled</div>
                  <div className="mt-3 text-[10px] font-black uppercase tracking-wide text-blue-700">{humanize(block?.proof_status || 'BUILDING_FORWARD_SAMPLE')}</div>
                </div>
              ))}
            </div>
          </section>

          <section>
            <div className="section-heading">
              <div><p className="eyebrow">This week</p><h2>Decision research</h2></div>
              <span className="health-pill">{laneBlock.source_rows || 0} SOURCE ROWS</span>
            </div>
            {!!sports.length && (
              <div className="mt-4 flex gap-2 overflow-x-auto">
                {sports.map((item) => (
                  <button key={item} onClick={() => setSport(item)} className={`rounded-full px-3 py-2 text-xs font-black ${effectiveSport === item ? 'bg-blue-700 text-white' : 'border border-slate-200 bg-white text-slate-500'}`}>{item}</button>
                ))}
              </div>
            )}
            <div className="mt-5 grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
              {visibleRows.map((row,index) => <FantasyLaneCard key={`${lane}-${row.player || row.team}-${index}`} lane={lane} row={row} />)}
            </div>
          </section>

          <FantasyNewsPanel />
            </>
          )}
        </>
      ) : (
        <>
          <section>
            <div className="section-heading">
              <div><p className="eyebrow">DFS V3</p><h2>Strategy proof before lineup hype</h2></div>
              <span className="health-pill">{dfs.forward_official_snapshots || 0} FORWARD SLATES</span>
            </div>
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
                <div className="text-xs font-black uppercase tracking-[0.14em] text-blue-700">Best Overall</div>
                <div className="mt-2 text-xl font-black text-slate-950">Projection + correlation</div>
                <div className="mt-2 text-sm leading-6 text-slate-500">A legal lineup can only be judged against meaningful salary-efficient and max-projection baselines.</div>
              </div>
              <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
                <div className="text-xs font-black uppercase tracking-[0.14em] text-violet-700">Tournament</div>
                <div className="mt-2 text-xl font-black text-slate-950">{dkTournament ? `${dkTournament.avg_random_baseline_percentile}th percentile replay` : 'Replay building'}</div>
                <div className="mt-2 text-sm leading-6 text-slate-500">{dkTournament ? `${dkTournament.replay_slates} DraftKings replay slates · ${dkTournament.avg_actual_minus_max_projection >= 0 ? '+' : ''}${dkTournament.avg_actual_minus_max_projection} vs Max Projection.` : 'Waiting for replay evidence.'} Replay is not forward proof.</div>
              </div>
              <div className="rounded-3xl border border-amber-200 bg-amber-50 p-5">
                <div className="text-xs font-black uppercase tracking-[0.14em] text-amber-700">Contrarian</div>
                <div className="mt-2 text-xl font-black text-slate-950">Ownership required</div>
                <div className="mt-2 text-sm leading-6 text-amber-950">Contrarian mode stays unavailable when slate ownership is missing. The optimizer will not fabricate low-owned percentages.</div>
              </div>
            </div>
          </section>
          <Suspense fallback={<LoadingSurface label="Loading DFS Lineup Lab" />}><DfsLineupLab /></Suspense>
        </>
      )}
    </div>
  )
}

function MobileBottomNav({ active, onNavigate }) {
  const items = [
    ['Home', 'Home', LayoutDashboard],
    ['Bets', 'Best Bets', Target],
    ['Fantasy', 'Fantasy', Users],
    ['Survivor', 'Survivor', ShieldCheck],
    ['Ask', 'Ask', Sparkles],
  ]

  return (
    <nav aria-label="Mobile primary navigation" className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/95 px-2 pb-[max(.5rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur md:hidden">
      <div className="grid grid-cols-5 gap-1">
        {items.map(([label, route, Icon]) => {
          const selected = route === 'Best Bets' ? bettingNavItems.includes(active) : active === route
          return (
            <button key={label} aria-current={selected ? 'page' : undefined} onClick={() => onNavigate(route)} className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl text-[10px] font-black ${selected ? 'bg-slate-950 text-white' : 'text-slate-500'}`}>
              <Icon size={18} /><span>{label}</span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}

function MoreMenu({ onNavigate, onClose }) {
  return (
    <div className="grid gap-2">
      {['Scores', 'News & Insights', 'Brain Record', 'Practice', 'Research'].map((item) => (
        <button key={item} onClick={() => { onNavigate(item); onClose?.() }} className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left text-sm font-black text-slate-800 hover:border-blue-200">
          <span>{item}</span><ChevronRight size={17} className="text-slate-300" />
        </button>
      ))}
    </div>
  )
}

const ROUTE_HASH = {
  Home: '',
  Scores: 'scores',
  'Best Bets': 'best-bets',
  Props: 'props',
  PrizePicks: 'prizepicks',
  Parlays: 'parlays',
  Fantasy: 'fantasy',
  Survivor: 'survivor',
  'News & Insights': 'news',
  'Brain Record': 'brain-record',
  Practice: 'practice',
  Research: 'research',
  Ask: 'ask',
}

const HASH_ROUTE = Object.fromEntries(Object.entries(ROUTE_HASH).map(([route, hash]) => [hash, route]))

function routeFromLocation() {
  const hash = window.location.hash.replace(/^#/, '').trim().toLowerCase()
  return HASH_ROUTE[hash] || 'Home'
}

export default function App() {
  const [active, setActive] = useState(() => routeFromLocation())
  const [assistantOpen, setAssistantOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const backendLabel = useMemo(() => insforgeConfigured ? 'DATA PLATFORM CONNECTED' : 'LIVE DATA CONNECTED', [])
  const isAsk = active === 'Ask'
  const isBetting = bettingNavItems.includes(active)

  useEffect(() => {
    const syncRoute = () => setActive(routeFromLocation())
    window.addEventListener('popstate', syncRoute)
    window.addEventListener('hashchange', syncRoute)
    return () => {
      window.removeEventListener('popstate', syncRoute)
      window.removeEventListener('hashchange', syncRoute)
    }
  }, [])

  useEffect(() => {
    document.title = active === 'Home'
      ? `${PUBLIC_BRAND} | ${PUBLIC_TAGLINE}`
      : `${active} | ${PUBLIC_BRAND}`
  }, [active])

  useEffect(() => {
    const closeOverlays = (event) => {
      if (event.key !== 'Escape') return
      setMoreOpen(false)
      setAssistantOpen(false)
    }
    window.addEventListener('keydown', closeOverlays)
    return () => window.removeEventListener('keydown', closeOverlays)
  }, [])

  const navigate = (item) => {
    const route = item === 'Betting' ? 'Best Bets' : item
    if (route !== active) {
      const hash = ROUTE_HASH[route] || ''
      const nextUrl = hash
        ? `${window.location.pathname}${window.location.search}#${hash}`
        : `${window.location.pathname}${window.location.search}`
      window.history.pushState({ route }, '', nextUrl)
      setActive(route)
    }
    setAssistantOpen(false)
    setMoreOpen(false)
    window.requestAnimationFrame(() => {
      window.scrollTo({ top: 0, behavior: 'smooth' })
      document.getElementById('main-content')?.focus({ preventScroll: true })
    })
  }

  const navSelected = (item) => item === 'Betting' ? isBetting : active === item

  return (
    <div className="min-h-screen bg-slate-50 pb-20 text-slate-900 md:pb-0">
      <a href="#main-content" onClick={(event) => { event.preventDefault(); document.getElementById('main-content')?.focus() }} className="skip-link">Skip to main content</a>
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4 px-4 py-3 md:px-5 md:py-4">
          <button type="button" aria-label="Sports Zenith home" onClick={() => navigate('Home')} className="text-left"><Brand /></button>

          <div className="hidden items-center gap-3 md:flex">
            <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-extrabold text-slate-600">
              <Activity size={15} className="text-emerald-500" />
              {backendLabel}
            </div>
            <AccountButton />
            <button onClick={() => setAssistantOpen(true)} className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-2.5 text-sm font-black text-white shadow-lg shadow-slate-950/10 transition hover:-translate-y-0.5">
              <Sparkles size={16} className="text-emerald-300" /> Ask
            </button>
          </div>

          <div className="flex items-center gap-2 md:hidden">
            <AccountButton compact />
            <button onClick={() => navigate('Ask')} aria-label="Ask" className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-white"><Sparkles size={17} /></button>
            <button aria-haspopup="dialog" aria-expanded={moreOpen} onClick={() => setMoreOpen((open) => !open)} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-black text-slate-700">More</button>
          </div>
        </div>
      </header>

      <nav aria-label="Primary navigation" className="hidden border-b border-slate-200 bg-white md:block">
        <div className="relative mx-auto flex max-w-[1500px] items-center gap-1 px-5 py-2.5">
          {navItems.map((item) => (
            <button
              key={item}
              onClick={() => navigate(item)}
              aria-current={navSelected(item) ? 'page' : undefined}
              className={`whitespace-nowrap rounded-xl px-3.5 py-2.5 text-sm font-extrabold transition ${navSelected(item) ? 'bg-slate-950 text-white' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'}`}
            >
              {item}
            </button>
          ))}
          <div className="relative ml-auto">
            <button aria-haspopup="menu" aria-expanded={moreOpen} onClick={() => setMoreOpen((open) => !open)} className={`rounded-xl px-3.5 py-2.5 text-sm font-extrabold ${['Practice', 'Research'].includes(active) ? 'bg-slate-950 text-white' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'}`}>More</button>
            {moreOpen && (
              <div className="absolute right-0 top-12 z-40 w-64 rounded-3xl border border-slate-200 bg-slate-50 p-3 shadow-2xl">
                <MoreMenu onNavigate={navigate} onClose={() => setMoreOpen(false)} />
              </div>
            )}
          </div>
        </div>
      </nav>

      <main id="main-content" tabIndex="-1" className="mx-auto max-w-[1500px] space-y-8 px-4 py-6 md:px-5 md:py-8">
        {isAsk ? (
          <Suspense fallback={<LoadingSurface label="Loading analyst" />}><AskSportsHulkPage /></Suspense>
        ) : (
          <>
            {active === 'Home' && (
              <>
                <CommercialHero onNavigate={navigate} />
                <StatusStrip />
                <HomeDecisionPanel onNavigate={navigate} />
                <HomeScoreRail onNavigate={navigate} />
                <HomeImpactNews onNavigate={navigate} />
                <HomeSnapshots onNavigate={navigate} />
                <LearningPanel />
              </>
            )}

            {active === 'Scores' && <ScoresHub />}

            {isBetting && (
              <>
                <BettingSubnav active={active} onNavigate={navigate} />
                {active === 'Best Bets' && <BestBetsV2Panel />}
                {active === 'Props' && <PropsV2Panel lane="PROP" />}
                {active === 'PrizePicks' && <PropsV2Panel lane="PRIZEPICKS" />}
                {active === 'Parlays' && <ParlaysV2Panel />}
              </>
            )}

            {active === 'Fantasy' && <FantasyCommercialPanel />}
            {active === 'Survivor' && <SurvivorCommercialPanel />}
            {active === 'News & Insights' && <NewsInsightsPanel />}
            {active === 'Brain Record' && <Suspense fallback={<LoadingSurface label="Loading Brain Record" />}><PerformancePanel /></Suspense>}
            {active === 'Practice' && <Suspense fallback={<LoadingSurface label="Loading Practice" />}><PracticeBetting /></Suspense>}

            {active === 'Research' && (
              <EmptyPanel
                icon={Brain}
                title="Research lab"
                text="Advanced diagnostics, experiment detail and model-development evidence live here so the consumer experience can stay clean. Research never silently becomes a public recommendation."
              />
            )}
          </>
        )}
      </main>

      {assistantOpen && !isAsk && (
        <Suspense fallback={null}>
          <AssistantDrawer
            active
            onClose={() => setAssistantOpen(false)}
            onOpenFull={() => navigate('Ask')}
            page={active}
          />
        </Suspense>
      )}

      {moreOpen && (
        <div className="fixed inset-0 z-50 flex items-end bg-slate-950/30 md:hidden" onClick={() => setMoreOpen(false)}>
          <div role="dialog" aria-modal="true" aria-label="More navigation" onClick={(event) => event.stopPropagation()} className="w-full rounded-t-[30px] bg-slate-50 p-5 pb-[calc(5.5rem+env(safe-area-inset-bottom))] shadow-2xl">
            <div className="mx-auto mb-5 h-1.5 w-12 rounded-full bg-slate-300" />
            <div className="mb-4 text-lg font-black text-slate-950">More</div>
            <MoreMenu onNavigate={navigate} onClose={() => setMoreOpen(false)} />
          </div>
        </div>
      )}

      <MobileBottomNav active={active} onNavigate={navigate} />

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-2 px-5 py-6 text-sm text-slate-400 sm:flex-row sm:items-center sm:justify-between">
          <span>{PUBLIC_BRAND} · {PUBLIC_TAGLINE}</span>
          <span>Real data · Unknown stays UNKNOWN · Stale stays STALE</span>
        </div>
      </footer>
    </div>
  )
}
