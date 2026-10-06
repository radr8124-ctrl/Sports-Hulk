# Sports HULK Shared Layouts

## Application Shell
- Source: `src/App.jsx`
- Description: Single-page state-driven shell containing sticky brand header, horizontally scrolling top navigation, shared command-center hero, active feature panels, assistant launcher/drawer, and footer.

```jsx
import React, { useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertTriangle, BarChart3, Brain, ChevronRight, CloudSun,
  Gauge, LayoutDashboard, Radio, ShieldCheck, Sparkles, Target,
  Trophy, Users, Zap,
} from 'lucide-react'
import { insforgeConfigured } from './insforge'
import { AskSportsHulkPage, AssistantDrawer, AssistantLauncher } from './AskSportsHulk'
import DfsLineupLab from './DfsLineupLab'
import PerformancePanel from './PerformancePanel'
import PracticeBetting from './PracticeBetting'
import { fantasySections, navItems, nflSections, statusCards } from './dashboardConfig'

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
        SPORTS <span className="text-emerald-600">HULK</span>
      </div>
      <div className="mt-1 text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
        Sports intelligence
      </div>
    </div>
  )
}

function StatusStrip() {
  return (
    <div className="grid gap-3 md:grid-cols-4">
      {statusCards.map((item) => (
        <div key={item.label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
          <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">{item.label}</div>
          <div className={`mt-3 inline-flex rounded-full border px-3 py-1 text-xs font-extrabold ${toneClass[item.tone]}`}>
            {item.value}
          </div>
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
              Loaded from the Sports HULK saved entry{authoritative.activeEntry ? ` · ${authoritative.activeEntry}` : ''}{authoritative.week ? ` · Week ${authoritative.week}` : ''}.
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
          Saved state comes from Sports HULK. Changes made on this screen are browser drafts only and never submit picks to the external pool.
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
  const rows = (news.articles || []).filter(a => filter === 'ALL' || (a.impact_tags || []).includes(filter)).slice(0, 18)

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

function FantasyCommandCenter() {
  const [mode, setMode] = useState('Season-Long')

  return (
    <div className="space-y-8">
      <section>
        <div className="section-heading">
          <div><p className="eyebrow">Fantasy</p><h2>Fantasy command center</h2></div>
          <span className="health-pill emerald">SEASON-LONG + DFS</span>
        </div>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {['Season-Long', 'DFS Lineup Lab'].map(item => (
            <button
              key={item}
              type="button"
              onClick={() => setMode(item)}
              className={`whitespace-nowrap rounded-xl px-4 py-2 text-sm font-black transition ${mode === item ? 'bg-slate-950 text-white' : 'border border-slate-200 bg-white text-slate-600'}`}
            >
              {item}
            </button>
          ))}
        </div>
      </section>

      {mode === 'DFS Lineup Lab' ? (
        <DfsLineupLab />
      ) : (
        <>
          <section>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft"><div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Start / Sit</div><div className="mt-2 text-lg font-black text-slate-950">Use news + usage + matchup</div><div className="mt-2 text-sm leading-6 text-slate-500">Late injury news, practice status, snap trends, targets and opponent context should change recommendations immediately.</div></div>
              <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft"><div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Waivers</div><div className="mt-2 text-lg font-black text-slate-950">Find opportunity before rankings</div><div className="mt-2 text-sm leading-6 text-slate-500">Roster moves, injuries, depth-chart changes and usage spikes feed the waiver watch instead of relying on generic ranks.</div></div>
              <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft"><div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Trades</div><div className="mt-2 text-lg font-black text-slate-950">Value changes with context</div><div className="mt-2 text-sm leading-6 text-slate-500">News, role changes, schedule and league settings become part of trade analysis rather than a static chart.</div></div>
            </div>
          </section>
          <SectionGrid title="Fantasy tools" items={fantasySections} />
          <FantasyNewsPanel />
        </>
      )}
    </div>
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

export default function App() {
  const initialActive = window.location.hash === '#ask' ? 'Ask Sports HULK' : 'Home'
  const [active, setActive] = useState(initialActive)
  const [assistantOpen, setAssistantOpen] = useState(false)
  const backendLabel = useMemo(() => insforgeConfigured ? 'INSFORGE CONNECTED' : 'SPORTS HULK LIVE DATA', [])
  const isAsk = active === 'Ask Sports HULK'

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-6 px-5 py-4">
          <Brand />
          <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-extrabold text-slate-600 md:flex">
            <Activity size={15} className="text-emerald-500" />
            {backendLabel}
          </div>
        </div>
      </header>
      <nav className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] gap-2 overflow-x-auto px-5 py-3">
          {navItems.map((item) => (
            <button
              key={item}
              onClick={() => {
                setActive(item)
                setAssistantOpen(false)
                window.history.replaceState(null, '', item === 'Ask Sports HULK' ? '#ask' : '#')
              }}
              className={`whitespace-nowrap rounded-xl px-4 py-2 text-sm font-extrabold transition ${
                active === item
                  ? 'bg-slate-950 text-white'
                  : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              {item}
            </button>
          ))}
        </div>
      </nav>

      <main className="mx-auto max-w-[1500px] space-y-8 px-5 py-8">
        {isAsk ? (
          <AskSportsHulkPage />
        ) : (
          <>
        <section className="rounded-[30px] border border-slate-200 bg-white p-7 shadow-soft md:p-9">
          <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
            <div>
              <p className="eyebrow">Command Center</p>
              <h1 className="mt-2 max-w-4xl text-4xl font-black tracking-tight text-slate-950 md:text-5xl">
                Simple answer on top.
                <span className="block text-blue-700">Everything accountable underneath.</span>
              </h1>
              <p className="mt-4 max-w-3xl text-base leading-7 text-slate-500">
                Scores, decisions, props, parlays, Survivor and fantasy in one stable product.
                No invented data, no hidden stale feeds and no forced picks.
              </p>
            </div>
            <div className="grid min-w-[260px] grid-cols-2 gap-3">
              <div className="mini-metric"><Brain size={18} /><b>Learning</b><span>Persistent</span></div>
              <div className="mini-metric"><ShieldCheck size={18} /><b>Evidence</b><span>Traceable</span></div>
            </div>
          </div>
        </section>

        <StatusStrip />
        {active === 'Home' && (
          <>
            <Scoreboard />
            <DecisionPanel />
            <SurvivorPanel />
            <LearningPanel />
          </>
        )}

        {active === 'NFL' && <NflPanel />}

        {active === 'MLB' && <MlbPanel />}

        {active === 'Props' && <NflPropsPanel />}

        {active === 'Parlays' && <NflParlaysPanel />}

        {active === 'Survivor' && <SurvivorRoutePanel />}

        {active === 'Fantasy' && <FantasyCommandCenter />}

        {active === 'Practice' && <PracticeBetting />}

        {active === 'Brain Record' && <PerformancePanel />}

        {!['Home', 'NFL', 'MLB', 'Props', 'Parlays', 'Survivor', 'Fantasy', 'Practice', 'Brain Record'].includes(active) && (
          <EmptyPanel
            icon={LayoutDashboard}
            title={active}
            text="This route is reserved in the permanent navigation. The next build will wire its validated data contract without changing the product shell."
          />
        )}
          </>
        )}
      </main>

      {!isAsk && <AssistantLauncher onClick={() => setAssistantOpen(true)} />}
      <AssistantDrawer
        active={assistantOpen && !isAsk}
        onClose={() => setAssistantOpen(false)}
        onOpenFull={() => {
          setActive('Ask Sports HULK')
          setAssistantOpen(false)
          window.history.replaceState(null, '', '#ask')
        }}
      />

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-2 px-5 py-6 text-sm text-slate-400 sm:flex-row sm:items-center sm:justify-between">
          <span>Sports HULK · Sports Intelligence</span>
          <span>Real data · Unknown stays UNKNOWN · Stale stays STALE</span>
        </div>
      </footer>
    </div>
  )
}

```
