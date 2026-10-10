import React, { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity, AlertTriangle, BarChart3, Brain, CheckCircle2, ChevronRight, CloudSun,
  Gauge, LayoutDashboard, Radio, ShieldCheck, Sparkles, Target,
  Trophy, Users, Zap,
} from 'lucide-react'
import { insforgeConfigured } from './insforge'
import { AccountButton, useAuth } from './AuthShell'
import { bettingNavItems, navItems, nflSections, scoreLeagues, statusCards } from './dashboardConfig'
import { PUBLIC_BRAND, PUBLIC_BRAND_WORD_1, PUBLIC_BRAND_WORD_2, PUBLIC_TAGLINE } from './brandConfig'
import BetMeaning, { betDisplayLabel } from './BetMeaning'
import BestBetsMarketCoverage from './BestBetsMarketCoverage'
import { BET_SPORT_FILTERS, BET_MARKET_FILTERS } from '../best_bets_market_availability.js'
import { explainBetProof, organizeBetResearch } from '../betting_proof_presentation.js'
import { survivorHomeSummary } from '../survivor_home_summary.js'
import { homeBrainSnapshot } from '../home_brain_presentation.js'
import CommandCenterHero from './CommandCenterHero.jsx'
const ZenithRefCompanion = lazy(() => import('./ZenithRefCompanion.jsx'))
import HomeGameDayDeck from './HomeGameDayDeck.jsx'
import HomeTopNews from './HomeTopNews.jsx'
import HomeRefStage from './HomeRefStage.jsx'
import HomeSignalCard from './HomeSignalCard.jsx'
import SportsNewsHub from './SportsNewsHub.jsx'

const AskSportsHulkPage = lazy(() => import('./AskSportsHulk').then(module => ({ default: module.AskSportsHulkPage })))
const AssistantDrawer = lazy(() => import('./AskSportsHulk').then(module => ({ default: module.AssistantDrawer })))
const AssistantLauncher = lazy(() => import('./AskSportsHulk').then(module => ({ default: module.AssistantLauncher })))
const DfsLineupLab = lazy(() => import('./DfsLineupLab'))
const PerformancePanel = lazy(() => import('./PerformancePanel'))
const PracticeBetting = lazy(() => import('./PracticeBetting'))
const ParlaysV2Panel = lazy(() => import('./ParlaysV2Panel'))
const PropsV2Panel = lazy(() => import('./PropsV2Panel'))
const BettingOddsBoard = lazy(() => import('./BettingOddsBoard'))
const BetToolsPanel = lazy(() => import('./BetToolsPanel'))
const NFLPlayerPropResearchPanel = lazy(() => import('./NFLPlayerPropResearchPanel'))
const ScoreGameCenter = lazy(() => import('./ScoreGameCenter'))
const PersonalIdpPanel = lazy(() => import('./PersonalIdpPanel'))
const PersonalDefenseStreamingPanel = lazy(() => import('./PersonalDefenseStreamingPanel'))
const PersonalIrStashPanel = lazy(() => import('./PersonalIrStashPanel'))
const PersonalWaiverPanel = lazy(() => import('./PersonalWaiverPanel'))
const PersonalStartSitPanel = lazy(() => import('./PersonalStartSitPanel'))
const FantasyTeamControl = lazy(() => import('./FantasyTeamControl'))
const FantasyPlatformConnections = lazy(() => import('./FantasyPlatformConnections'))
const FantasyRosterLocalImport = lazy(() => import('./FantasyRosterLocalImport'))
const FantasyTradeResearch = lazy(() => import('./FantasyTradeResearch'))
const ResearchLab = lazy(() => import('./ResearchLab'))
import SurvivorCommandCover from './SurvivorCommandCover'
const SurvivorPickEditor = lazy(() => import('./SurvivorPickEditor'))
const SurvivorMarketReview = lazy(() => import('./SurvivorMarketReview'))
const SurvivorRiskLens = lazy(() => import('./SurvivorRiskLens'))
const SurvivorPreflightEvidence = lazy(() => import('./SurvivorPreflightEvidence'))
const SurvivorWeek6Planner = lazy(() => import('./SurvivorWeek6Planner'))
const SurvivorPoolImport = lazy(() => import('./SurvivorPoolImport'))
const SurvivorThursdayTracker = lazy(() => import('./SurvivorThursdayTracker'))
import { rankSurvivorCandidates } from '../survivor_week5_rank'
const SurvivorScoreCards = lazy(() => import('./SurvivorScoreCards'))
const SurvivorPastPicks = lazy(() => import('./SurvivorPastPicks'))

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
  blue: 'bg-sky-400/10 text-sky-200 border-sky-400/25',
  amber: 'bg-amber-400/10 text-amber-200 border-amber-400/25',
  emerald: 'bg-emerald-400/10 text-emerald-200 border-emerald-400/25',
  violet: 'bg-violet-400/10 text-violet-200 border-violet-400/25',
}

function Brand() {
  return (
    <div>
      <div className="text-lg font-black tracking-tight text-[#173E52] md:text-xl">
        {PUBLIC_BRAND_WORD_1} <span className="text-[#C84D42]">{PUBLIC_BRAND_WORD_2}</span>
      </div>
      <div className="mt-0.5 text-[9px] font-bold uppercase tracking-[0.22em] text-[#476572] md:text-[10px]">
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
        <div key={item.label} className="min-w-[185px] rounded-2xl border border-[#25415D] bg-[#102840] p-3 text-white md:min-w-0 md:p-4">
          <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">{item.label}</div>
          <div className={`mt-3 inline-flex rounded-full border px-3 py-1 text-xs font-extrabold ${toneClass[item.tone]}`}>
            {item.value}
          </div>
          <div className="mt-2 text-[11px] font-semibold text-slate-300">{item.detail}</div>
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
  const [selectedGameId, setSelectedGameId] = useState(null)

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
  const selectedGame = games.find(game => String(game.event_id) === String(selectedGameId)) || null

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
              <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
                <div className="text-xs font-semibold text-slate-400">Source: {game.source || 'ESPN Core'}</div>
                <button
                  type="button"
                  onClick={() => {
                    const nextId = selectedGameId === game.event_id ? null : game.event_id
                    setSelectedGameId(nextId)
                    if (nextId) {
                      window.requestAnimationFrame(() => {
                        document.getElementById('score-game-center')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                      })
                    }
                  }}
                  className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-slate-950 px-4 text-xs font-black text-white"
                >
                  {selectedGameId === game.event_id ? 'Close Game Center' : 'Open Game Center'}
                  <ChevronRight size={15} className={selectedGameId === game.event_id ? 'rotate-90' : ''} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedGame && (
        <div className="mt-5">
          <Suspense fallback={<LoadingSurface label="Loading Game Center" />}>
            <ScoreGameCenter
              game={{ ...selectedGame, boxscore_available: Boolean(selectedGame.boxscore) }}
              league="NFL"
              onClose={() => setSelectedGameId(null)}
              boxScoreOverride={selectedGame.boxscore ? <NflBoxScore game={selectedGame} /> : null}
            />
          </Suspense>
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

function LearningPanel({ onNavigate }) {
  const [step,setStep]=useState(0)
  const steps=[
    {
      name:'Freeze',short:'Before kickoff',icon:'01',
      detail:'Zenith saves the original game, side, line, model and source time before a result exists. Later odds cannot rewrite that prediction.',
    },
    {
      name:'Grade',short:'After a verified final',icon:'02',
      detail:'The exact saved pick is compared with the official final score. Missing evidence stays pending, and a loss never disappears.',
    },
    {
      name:'Review',short:'Find why it missed',icon:'03',
      detail:'We check what the model predicted against the bookmaker baseline and the real result. A possible cause is not called proven without source evidence.',
    },
    {
      name:'Test',short:'Prove a better approach',icon:'04',
      detail:'Any proposed adjustment stays in a separate shadow trial until new future games show real improvement. A backtest alone cannot claim success.',
    },
  ]
  return (
    <section aria-label="Home learning loop">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Learning loop · interactive</p>
          <h2>How does Zenith get smarter?</h2>
          <p className="mt-1 text-xs font-semibold text-[#526D76]">Tap a step to see what happens. Open Brain Record to inspect the actual results.</p>
        </div>
        <button type="button" onClick={()=>onNavigate('Brain Record')}
          className="min-h-10 rounded-xl border border-[#173E52] bg-[#FFD36A] px-3 text-xs font-black text-[#173E52]">
          Open Brain Record →
        </button>
      </div>
      <HomeRefStage zone="learning" />
      <div className="rounded-[22px] border-2 border-[#173E52] bg-[#173E52] p-3 text-white shadow-[5px_5px_0_#46CDD2] md:p-5">
        <div role="group" aria-label="Choose a learning step" className="grid grid-cols-2 gap-2 md:grid-cols-4">
          {steps.map((item,index)=>(
            <button type="button" key={item.icon} aria-pressed={step===index}
              onClick={()=>setStep(index)}
              className={`min-h-[86px] rounded-xl border p-3 text-left transition hover:border-[#FFD36A] ${step===index?'border-[#FFD36A] bg-[#FFF5E4] text-[#173E52]':'border-[#476C7A] bg-white/[.045] text-white'}`}>
              <span className={`block text-[10px] font-black tracking-[.14em] ${step===index?'text-[#A65340]':'text-[#FFD36A]'}`}>STEP {item.icon}</span>
              <span className="mt-1 block text-lg font-black">{item.name}</span>
              <span className={`mt-1 block text-[11px] font-medium ${step===index?'text-[#536B73]':'text-[#BBD1DA]'}`}>{item.short}</span>
            </button>
          ))}
        </div>
        <div aria-live="polite" className="mt-3 rounded-xl border border-[#4C7180] bg-[#0E2A3C] p-3 md:p-4">
          <div className="text-xs font-black uppercase tracking-[.12em] text-[#FFD36A]">{steps[step].name} · What happens here</div>
          <p className="mt-1 max-w-4xl text-xs font-semibold leading-5 text-[#DFEBEF]">{steps[step].detail}</p>
          <button type="button" onClick={()=>onNavigate('Brain Record')}
            className="mt-2 inline-flex min-h-10 items-center gap-2 rounded-lg bg-[#46CDD2] px-3 text-xs font-black text-[#173E52]">
            See actual evidence and mistakes <ChevronRight size={14}/>
          </button>
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
  const [selectedGamePk, setSelectedGamePk] = useState(null)

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

  const allGames = [
    ...(data.today_games || []),
    ...(data.next_games || []),
    ...(data.recent_games || []),
  ]
  const selectedGame = allGames.find(game => String(game.gamePk) === String(selectedGamePk)) || null
  const selectedGameForCenter = selectedGame ? {
    ...selectedGame,
    event_id: String(selectedGame.gamePk),
    start_time: selectedGame.gameDate,
    boxscore_available: Boolean(selectedGame.boxscore),
  } : null

  const renderGame = game => (
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
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
        <div className="text-xs font-semibold text-slate-400">Source: {game.source || 'MLB StatsAPI'}</div>
        <button
          type="button"
          onClick={() => {
            const nextId = selectedGamePk === game.gamePk ? null : game.gamePk
            setSelectedGamePk(nextId)
            if (nextId) {
              window.requestAnimationFrame(() => {
                document.getElementById('score-game-center')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              })
            }
          }}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-slate-950 px-4 text-xs font-black text-white"
        >
          {selectedGamePk === game.gamePk ? 'Close Game Center' : 'Open Game Center'}
          <ChevronRight size={15} className={selectedGamePk === game.gamePk ? 'rotate-90' : ''} />
        </button>
      </div>
    </div>
  )

  return (
    <div className="space-y-8">
      <section>
        <div className="section-heading"><div><p className="eyebrow">MLB</p><h2>Today</h2></div><span className="health-pill">MLB STATSAPI</span></div>
        {data.today_games?.length ? <div className="grid gap-4 lg:grid-cols-2">{data.today_games.map(renderGame)}</div> : (
          <EmptyPanel icon={Trophy} title="No MLB games today" text="The feed is connected. MLB has no games scheduled today, so the dashboard shows the next postseason slate below instead of looking broken." />
        )}
      </section>

      {selectedGameForCenter && (
        <Suspense fallback={<LoadingSurface label="Loading Game Center" />}>
          <ScoreGameCenter
            game={selectedGameForCenter}
            league="MLB"
            onClose={() => setSelectedGamePk(null)}
            boxScoreOverride={selectedGame?.boxscore ? <MlbBoxScore game={selectedGame} /> : null}
          />
        </Suspense>
      )}

      <section>
        <div className="section-heading"><div><p className="eyebrow">Next slate</p><h2>Upcoming MLB games</h2></div></div>
        <div className="grid gap-4 lg:grid-cols-2">{(data.next_games || []).slice(0, 8).map(renderGame)}</div>
      </section>
      {!!data.recent_games?.length && (
        <section>
          <div className="section-heading"><div><p className="eyebrow">Recent finals</p><h2>Box scores</h2></div></div>
          <div className="grid gap-4">{data.recent_games.map(renderGame)}</div>
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
  const [selectedEntry, setSelectedEntry] = useState('')
  const [claimEntry, setClaimEntry] = useState('')
  const [claimCode, setClaimCode] = useState('')
  const [linking, setLinking] = useState(false)
  const [linkMessage, setLinkMessage] = useState('')
  const survivor = useJsonEndpoint('/survivor_v2_current.json', {
    candidates: [],
    mode: 'GENERIC_RESEARCH_ONLY',
  })
  const saved = usePrivateSurvivorState(linkRefresh, selectedEntry)

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
      setSelectedEntry(payload.active_entry || claimEntry.trim())
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
  const historyLoadError = saved.status === 'PRIVATE_STATE_UNAVAILABLE'
  const pastPickCount = hasEntry && Number.isInteger(saved.past_picks?.total_picks)
    ? saved.past_picks.total_picks : null
  const pastWeekCount = hasEntry && Number.isInteger(saved.past_picks?.total_weeks)
    ? saved.past_picks.total_weeks : null
  const linkedEntries = Array.isArray(saved.linked_entries) ? saved.linked_entries : []
  const diversifiedAllocations = Array.isArray(saved.diversified_allocations) ? saved.diversified_allocations : []
  const concentration = saved.diversification_concentration || {}
  const poolDynamics = saved.pool_dynamics || {}
  const usedTeams = hasEntry ? (saved.used_teams || []) : []
  const currentPicks = hasEntry ? (saved.current_picks || []) : []
  const candidates = rankSurvivorCandidates(survivor.candidates || [], usedTeams)
  const ruleConfirmed = hasEntry && Boolean(saved.rule_confirmed)
  const modelPickReady = ruleConfirmed && saved.recommendation_status === 'SHADOW_RECOMMENDATION_READY'
  const modelResearchPicks = modelPickReady && Array.isArray(saved.shadow_recommendation)
    ? saved.shadow_recommendation : []
  const personalShortlist = modelResearchPicks.length > 0
    ? modelResearchPicks : candidates.filter(row => String(row.strategy_action || '').toUpperCase() === 'VIABLE').slice(0, 3)
  const currentPoolSheetMissing = hasEntry && Number(saved.ownership?.official_pool_week || 0) !== Number(saved.pool_current_week || 0)
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
    <div className="space-y-5 md:space-y-7">
      <SurvivorCommandCover
        signedIn={isSignedIn}
        hasEntry={hasEntry}
        entryStatus={entryStatus}
        poolWeek={saved.pool_current_week ?? survivor.pool_current_week ?? null}
        usedTeams={usedTeams}
        currentPicks={currentPicks}
        requiredPicks={Number.isInteger(saved.required_picks) ? saved.required_picks : null}
        ruleConfirmed={ruleConfirmed}
        officialPoolWeek={saved.ownership?.official_pool_week ?? null}
        recommendationStatus={saved.recommendation_status || ''}
        shadowRecommendation={saved.shadow_recommendation || []}
      />

      <section aria-label="Survivor entry deadline" data-survivor-cutoff-status={hasEntry ? saved.pick_window?.status || 'UNVERIFIED' : 'PRIVATE_SIGN_IN_REQUIRED'}
        className="flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs font-semibold leading-5 text-amber-950">
        <div>
          <b className="block text-sm font-black">
            Week {saved.pool_current_week ?? survivor.pool_current_week ?? '—'} · {hasEntry && saved.pick_window?.status==='WINDOW_CLOSED'
              ? 'Pool pick deadline passed' : 'Pool deadline: Saturday 6 PM Eastern'}
          </b>
          <span>
            {hasEntry && saved.pick_window?.status==='WINDOW_CLOSED'
              ? `${currentPicks.length} pick(s) saved in Zenith at cutoff. Your saved pool status is ${entryStatus}, but the organizer's current-week result and external submission are not verified.`
              : hasEntry && saved.pick_window?.status!=='WINDOW_OPEN'
                ? 'Pick entry is locked until the verified schedule, deadline and pool rules agree. No existing picks have changed.'
                : `Earlier games are due two hours before that day's first kickoff. ${hasEntry ? `${currentPicks.length} privately saved in Zenith.` : 'Sign in to view the exact private pick window.'}`}
          </span>
        </div>
        <span className="rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-[10px] font-black text-amber-900">SPORTS ZENITH DOES NOT SUBMIT TO YOUR EXTERNAL POOL</span>
      </section>

      {(!isSignedIn || (saved.status !== 'LOADING' && !hasEntry)) && (
        <section aria-label="Survivor review access shortcut" className="rounded-2xl border-2 border-[#B5D5D3] bg-[#EAF7F4] px-4 py-3 shadow-soft">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-[10px] font-black uppercase tracking-[.12em] text-[#176773]">YOUR PRIVATE SURVIVOR REVIEW</p>
              <h2 className="mt-1 text-sm font-black text-[#173E52]">
                {!isSignedIn ? 'Sign in to see your entry' : saved.status==='PRIVATE_STATE_UNAVAILABLE' ? 'Your private entry is temporarily unavailable' : 'No entry assigned to this sign-in yet'}
              </h2>
              <p className="mt-1 text-[11px] font-semibold leading-[1.5] text-[#516E77]">
                {!isSignedIn
                  ? 'Only your signed-in account can display used teams, saved picks and personal scores.'
                  : saved.status==='PRIVATE_STATE_UNAVAILABLE'
                    ? 'We could not verify your assigned pool record right now. Refresh to try again; no picks have been changed.'
                    : 'Your pool organizer can preassign your entry to your verified email. When it is assigned, your entries, used teams and scores will appear automatically without a name or claim code.'}
              </p>
            </div>
            <div className="shrink-0">
              {!isSignedIn ? <AccountButton /> : (
                <button type="button" onClick={() => setLinkRefresh(value => value + 1)}
                  className="rounded-lg bg-[#173E52] px-4 py-2.5 text-[11px] font-black text-white hover:bg-[#26556B]">
                  Refresh my entries <ChevronRight size={14} className="ml-1 inline" />
                </button>
              )}
            </div>
          </div>
        </section>
      )}

      {isSignedIn && (
        <section aria-label="Survivor history status and refresh"
          className="rounded-xl border border-[#BAD6D3] bg-[#EAF7F4] px-3 py-2.5 text-[#173E52] sm:px-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="min-w-0 flex-1">
              <p className="text-xs font-black">My Past Picks</p>
              <p role="status" className="mt-0.5 text-[11px] font-semibold leading-4 text-[#526E78]">
                {saved.status === 'LOADING' ? 'Refreshing your private Survivor history…'
                  : historyLoadError ? 'Your past picks could not be loaded. Try refreshing your signed-in session.'
                    : !hasEntry ? 'No entry connected to this session yet. Refresh to check your verified account.'
                      : saved.past_picks?.status === 'HISTORY_UNAVAILABLE' ? 'History not found in the source record. Your used teams remain protected.'
                        : `${pastPickCount ?? '—'} past picks across ${pastWeekCount ?? '—'} recorded weeks. Your current pick is separate.`}
              </p>
            </div>
            {hasEntry && pastPickCount > 0 && (
              <button type="button" onClick={() => document.getElementById('my-survivor-past-picks')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
                className="rounded-lg bg-[#173E52] px-2.5 py-2 text-[10px] font-black text-white focus-visible:outline-2 focus-visible:outline-[#FF7766]">
                View all {pastPickCount} <ChevronRight size={13} className="ml-0.5 inline" />
              </button>
            )}
            <button type="button" onClick={() => setLinkRefresh(value => value + 1)}
              className="rounded-lg border border-[#B6CECA] bg-white px-2.5 py-2 text-[10px] font-black text-[#173E52] focus-visible:outline-2 focus-visible:outline-[#FF7766]">
              Refresh history
            </button>
          </div>
        </section>
      )}

      {hasEntry && (
        <Suspense fallback={<LoadingSurface label="Loading your past Survivor picks" />}>
          <SurvivorPastPicks history={saved.past_picks} entryName={saved.active_entry} />
        </Suspense>
      )}

      {hasEntry && (
        <Suspense fallback={<LoadingSurface label="Loading pick editor" />}>
          <SurvivorPickEditor
            entryName={saved.active_entry}
            poolWeek={saved.pool_current_week}
            usedTeams={usedTeams}
            currentPicks={currentPicks}
            entryStatus={entryStatus}
            requiredPicks={Number.isInteger(saved.required_picks) ? saved.required_picks : null}
            ruleConfirmed={ruleConfirmed}
            pickWindow={saved.pick_window}
            getAccessToken={getAccessToken}
            onSaved={() => setLinkRefresh(value => value + 1)}
          />
        </Suspense>
      )}

      {hasEntry && entryStatus === 'ALIVE' && (
        <Suspense fallback={<LoadingSurface label="Loading risk-first Survivor comparison" />}>
          <SurvivorRiskLens
            key={`${saved.active_entry}-${saved.pool_current_week}`}
            week={saved.pool_current_week}
            boardWeek={survivor.pool_current_week}
            ruleConfirmed={ruleConfirmed}
            candidates={survivor.candidates || []}
            usedTeams={usedTeams}
            historical={saved.historical_pool_availability || {}}
            currentPicks={currentPicks}
          />
        </Suspense>
      )}

      {hasEntry && entryStatus === 'ALIVE' && saved.pool_current_week === 5 && (
        <Suspense fallback={<LoadingSurface label="Loading NFL source evidence" />}>
          <SurvivorPreflightEvidence
            key={`${saved.active_entry}-${saved.pool_current_week}`}
            entryName={saved.active_entry}
            candidates={survivor.candidates||[]}
            usedTeams={usedTeams}
            getAccessToken={getAccessToken}
          />
        </Suspense>
      )}

      {hasEntry && entryStatus === 'ALIVE' && saved.pool_current_week === 5 && (
        <Suspense fallback={<LoadingSurface label="Loading Week 6 two-pick planning" />}>
          <SurvivorWeek6Planner
            key={`${saved.active_entry}-${saved.pool_current_week}`}
            entryName={saved.active_entry}
            getAccessToken={getAccessToken}
          />
        </Suspense>
      )}

      {isSignedIn && (
        <Suspense fallback={null}>
          <SurvivorThursdayTracker getAccessToken={getAccessToken} />
        </Suspense>
      )}

      {hasEntry && entryStatus === 'ALIVE' && (
        <section aria-label="Personal Survivor pick research" className="rounded-3xl border border-blue-200 bg-white p-5 shadow-soft md:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="eyebrow">Week {saved.pool_current_week ?? survivor.pool_current_week ?? '—'} · Your eligible teams</p>
              <h2 className="mt-2 text-xl font-black text-slate-950">
                {ruleConfirmed ? `${saved.required_picks} pick${saved.required_picks === 1 ? '' : 's'} required this week` : 'Personal picks pending rule review'}
              </h2>
            </div>
            <span className={`rounded-full px-3 py-2 text-[10px] font-black ${ruleConfirmed ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'}`}>
              {ruleConfirmed ? 'ORIGINAL 2026 RULES VERIFIED' : 'RULE REVIEW NEEDED'}
            </span>
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {ruleConfirmed
              ? 'Your original 2026 Knockout Pool rules confirm the pick count. Previously used teams are excluded. These are research choices, not picks submitted to the external pool.'
              : 'Your current-week rule sources conflict or are unavailable. The research candidates below are not approved picks.'}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {personalShortlist.map((row, index) => (
              <div key={row.team} className={`rounded-2xl border p-4 ${modelPickReady ? 'border-blue-200 bg-blue-50/50' : 'border-slate-200 bg-slate-50'}`}>
                <div className="text-[10px] font-black uppercase tracking-wider text-blue-700">
                  {modelPickReady ? `Model research choice ${index + 1}` : `Research option ${index + 1}`}
                </div>
                <div className="mt-2 text-lg font-black text-slate-950">{row.team}</div>
                <div className="mt-1 text-xs font-semibold text-slate-500">vs {row.opponent || 'Opponent pending'}</div>
                <div className="mt-2 text-xs font-bold text-blue-800">{row.market_prob_pct ?? '—'}% market-implied survival estimate</div>
                <div className="mt-2 text-xs text-slate-500">{humanize(row.strategy_action || row.decision_tier || 'RESEARCH')}</div>
              </div>
            ))}
          </div>
          {!personalShortlist.length && <p className="mt-3 text-sm font-semibold text-slate-600">No eligible current-week research choice is available yet.</p>}
          <div className="mt-4 space-y-2 text-xs font-semibold leading-5 text-slate-600">
            <p><b className="text-slate-800">Pool deadline:</b> Saturday 6 PM; games played earlier must be picked at least two hours before that day's first kickoff, per the original rules.</p>
            {currentPoolSheetMissing && <p className="text-amber-800"><b>Ownership data still pending:</b> The most recent imported picks sheet is for Week {saved.ownership?.official_pool_week ?? '—'}. This does not change the verified Week {saved.pool_current_week} pick count.</p>}
          </div>
        </section>
      )}

      <Suspense fallback={<LoadingSurface label="Loading Week 5 sportsbook comparison" />}>
        <SurvivorMarketReview
          week={survivor.pool_current_week ?? saved.pool_current_week ?? null}
          candidates={survivor.candidates || []}
          usedTeams={usedTeams}
          personal={hasEntry}
          recommendedStatus={hasEntry ? saved.recommendation_status : ''}
          requiredPicks={hasEntry && Number.isInteger(saved.required_picks) ? saved.required_picks : null}
        />
      </Suspense>

      {isSignedIn && (
        <Suspense fallback={null}>
          <SurvivorPoolImport
            getAccessToken={getAccessToken}
            onImported={() => setLinkRefresh(value => value + 1)}
          />
        </Suspense>
      )}

      {isSignedIn && linkedEntries.length > 0 && (
        <section>
          <div className="section-heading">
            <div>
              <p className="eyebrow">My Survivor entries</p>
              <h2>{linkedEntries.length} linked entr{linkedEntries.length === 1 ? 'y' : 'ies'}</h2>
            </div>
            <span className="health-pill">{linkedEntries.filter(entry => String(entry.entry_status || '').toUpperCase() === 'ALIVE').length} ALIVE</span>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {linkedEntries.map((entry) => {
              const entryUsed = Array.isArray(entry.used_teams) ? entry.used_teams : []
              const entryPicks = Array.isArray(entry.current_picks) ? entry.current_picks : []
              const alive = String(entry.entry_status || '').toUpperCase() === 'ALIVE'
              return (
                <button
                  key={entry.entry_name}
                  type="button"
                  onClick={() => setSelectedEntry(entry.entry_name)}
                  className={`rounded-3xl border bg-white p-5 text-left shadow-soft transition hover:border-blue-300 ${entry.entry_name === saved.active_entry ? 'border-blue-400 ring-2 ring-blue-50' : 'border-slate-200'}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-lg font-black text-slate-950">{entry.entry_name}</div>
                      <div className="mt-1 text-xs font-semibold text-slate-400">Week {entry.current_week ?? saved.pool_current_week ?? '—'}</div>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-[10px] font-black ${alive ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
                      {humanize(entry.entry_status || 'UNKNOWN')}
                    </span>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-2 text-center text-xs">
                    <div className="rounded-xl bg-slate-50 p-3">
                      <div className="font-black text-slate-950">{entryUsed.length}</div>
                      <div className="mt-1 text-slate-400">Teams used</div>
                    </div>
                    <div className="rounded-xl bg-slate-50 p-3">
                      <div className="truncate font-black text-slate-950">{entryPicks.length ? entryPicks.join(', ') : 'None'}</div>
                      <div className="mt-1 text-slate-400">Current pick</div>
                    </div>
                  </div>
                  {entry.last_completed_picks?.length > 0 && (
                    <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs font-semibold text-slate-700">
                      <span className="font-black">Week {entry.last_completed_week} saved result:</span>{' '}
                      {entry.last_completed_picks.map(pick => `${pick.team} — ${pick.result}`).join(' · ')}
                    </div>
                  )}
                  {entry.entry_name === saved.active_entry && (
                    <div className="mt-3 text-[10px] font-black uppercase tracking-[0.12em] text-blue-700">Primary detail view</div>
                  )}
                </button>
              )
            })}
          </div>
        </section>
      )}

      {isSignedIn && diversifiedAllocations.length > 1 && (
        <section className="rounded-[30px] border border-emerald-200 bg-emerald-50/60 p-5 md:p-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="eyebrow">Multi-entry strategy</p>
              <h2 className="mt-1">Diversified Survivor plan</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-emerald-950">
                Each entry is evaluated against its own burned teams. Duplicate-team and same-game exposure are avoided when another eligible governed option exists.
              </p>
            </div>
            <span className="health-pill emerald">MODEL SCORES UNCHANGED</span>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-4">
            <div className="rounded-xl bg-white/80 p-3">
              <div className={`font-black ${concentration.status === 'HIGH' ? 'text-rose-700' : 'text-emerald-700'}`}>{concentration.status || 'CLEAR'}</div>
              <div className="mt-1 text-slate-400">Concentration</div>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <div className="font-black text-slate-950">{concentration.unique_teams ?? '—'}/{concentration.actionable_entries ?? '—'}</div>
              <div className="mt-1 text-slate-400">Unique teams</div>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <div className="font-black text-slate-950">{concentration.same_game_collision_count ?? 0}</div>
              <div className="mt-1 text-slate-400">Same-game collisions</div>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <div className="font-black text-slate-950">{concentration.max_team_exposure_pct ?? 0}%</div>
              <div className="mt-1 text-slate-400">Max team exposure</div>
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {diversifiedAllocations.map((allocation) => {
              const actionable = Boolean(allocation.team)
              return (
                <div key={allocation.entry_name} className="rounded-3xl border border-emerald-100 bg-white p-4 shadow-soft">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-black text-slate-950">{allocation.entry_name}</div>
                      <div className="mt-1 text-[11px] font-semibold text-slate-400">{humanize(allocation.entry_status || allocation.status || 'UNKNOWN')}</div>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-[10px] font-black ${actionable ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                      {actionable ? 'DIVERSIFIED' : humanize(allocation.status || 'WAITING')}
                    </span>
                  </div>

                  {actionable ? (
                    <>
                      <div className="mt-4 text-xl font-black text-slate-950">{allocation.team}</div>
                      <div className="mt-1 text-xs font-semibold text-slate-400">vs {allocation.opponent || '—'}</div>
                      <div className="mt-4 grid grid-cols-2 gap-2 text-center text-xs">
                        <div className="rounded-xl bg-slate-50 p-3">
                          <div className="font-black text-slate-950">{allocation.market_prob_pct ?? '—'}%</div>
                          <div className="mt-1 text-slate-400">Market survival</div>
                        </div>
                        <div className="rounded-xl bg-slate-50 p-3">
                          <div className="font-black text-slate-950">{allocation.strategy_index ?? '—'}</div>
                          <div className="mt-1 text-slate-400">Strategy index</div>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="mt-4 rounded-2xl bg-amber-50 px-3 py-3 text-xs font-semibold leading-5 text-amber-900">
                      {allocation.reason || 'No current diversified recommendation is available for this entry.'}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      )}

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

      {isSignedIn && saved.status !== 'LOADING' && (
        <details id="survivor-link-entry" className="group rounded-2xl border border-[#D8E2E5] bg-white p-4">
          <summary className="cursor-pointer text-xs font-black text-[#527280]">Need to connect another entry? Optional pool-manager claim</summary>
          <div className="mt-4 flex gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-blue-700"><CheckCircle2 size={20} /></div>
            <div className="min-w-0 flex-1">
              <div className="text-lg font-black text-slate-950">Manual entry connection (optional)</div>
              <p className="mt-2 text-sm leading-6 text-blue-950">Assigned entries appear automatically after secure email sign-in. Only use this optional manager-issued claim form when connecting a separate entry that has not been preassigned to your verified account.</p>
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
        </details>
      )}


      {hasEntry && Array.isArray(saved.pick_scores) && saved.pick_scores.length > 0 && (
        <Suspense fallback={<LoadingSurface label="Loading My Pick Score" />}>
          <SurvivorScoreCards cards={saved.pick_scores} entryName={saved.active_entry} />
        </Suspense>
      )}

      {hasEntry && !ruleConfirmed && (
        <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5 md:p-6">
          <div className="flex gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-amber-100 text-amber-700"><AlertTriangle size={20} /></div>
            <div>
              <div className="text-lg font-black text-slate-950">Week {saved.pool_current_week ?? survivor.pool_current_week ?? '—'} recommendation is locked</div>
              <p className="mt-2 text-sm leading-6 text-amber-950">The original season rules are missing, or their required pick count conflicts with an entry record. The research board remains visible, but no candidate is promoted until this rule conflict is resolved.</p>
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

      <details className="group rounded-2xl border border-slate-200 bg-white p-3 shadow-soft md:p-4">
        <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 text-left">
          <span className="min-w-0">
            <span className="block text-sm font-black text-slate-900">Full Survivor research board</span>
            <span className="block text-[11px] font-medium text-slate-500">All {candidates.length} team signals · odds and model evidence shown separately</span>
          </span>
          <ChevronRight size={18} className="shrink-0 text-blue-700 transition-transform group-open:rotate-90" />
        </summary>
        <section className="mt-3 border-t border-slate-100 pt-4">
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

        <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm font-semibold leading-6 text-blue-950">
          Viable teams are listed first, followed by watchlist research. AVOID teams are moved to the end and are not recommended. {hasEntry && !ruleConfirmed ? 'Your final Week 5 selection remains locked until the official pool rules are confirmed.' : ''}
        </div>
        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {candidates.filter(row => String(row.strategy_action || '').toUpperCase() !== 'AVOID').slice(0, 9).map((row, index) => (
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
                <span className="font-black text-slate-600">Strategy {row.strategy_index == null ? '—' : Number(row.strategy_index).toFixed(1)}</span>
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
      </details>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
          <div className="text-xs font-black uppercase tracking-[0.14em] text-blue-700">Pool state</div>
          <div className="mt-3 text-lg font-black text-slate-950">{hasEntry ? humanize(saved.rule_status || 'UNKNOWN') : 'Authentication required for personal rules'}</div>
          <div className="mt-2 text-sm leading-6 text-slate-500">{hasEntry ? `Current pool week: ${saved.pool_current_week ?? '—'} · latest official sheet week: ${saved.ownership?.official_pool_week ?? '—'}.` : 'Generic Survivor research does not expose member pool rules or ownership.'}</div>
          {hasEntry && poolDynamics.alive_entries != null && (
            <div className="mt-3 rounded-2xl bg-slate-50 px-3 py-3 text-xs font-semibold leading-5 text-slate-600">
              <span className="font-black text-slate-900">{poolDynamics.alive_entries}/{poolDynamics.start_entries} alive · {poolDynamics.survival_pct}%</span>
              {' '}from verified Week {poolDynamics.source_week}. {poolDynamics.current ? 'This matches the active pool week.' : 'Historical only — current-week field size is still unverified.'}
            </div>
          )}
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

function usePrivateSurvivorState(refreshKey = 0, selectedEntry = '') {
  const { user, getAccessToken } = useAuth()
  const previousLinkedIdentity = useRef('')
  const [data, setData] = useState({
    status: user ? 'LOADING' : 'AUTH_REQUIRED',
    entry_linked: false,
    used_teams: [],
    current_picks: [],
  })

  useEffect(() => {
    let cancelled = false
    let timer = null
    let latestRequestId = 0

    if (!user) {
      previousLinkedIdentity.current = ''
      setData({
        status: 'AUTH_REQUIRED',
        entry_linked: false,
        used_teams: [],
        current_picks: [],
      })
      return () => {}
    }

    // Clear the previous owner's data on sign-in change / entry switching.
    // For an ordinary same-owner refresh, keep proven historical rows on
    // screen until the newer authorized response arrives.
    const privateIdentity = `${user.id}:${selectedEntry || ''}`
    if (previousLinkedIdentity.current !== privateIdentity) {
      previousLinkedIdentity.current = privateIdentity
      setData({status:'LOADING',entry_linked:false,used_teams:[],current_picks:[]})
    }
    const load = async () => {
      const requestId = ++latestRequestId
      try {
        const token = await getAccessToken()
        if (!token) throw new Error('No authenticated session')
        const entryQuery = selectedEntry ? `&entry=${encodeURIComponent(selectedEntry)}` : ''
        const response = await fetch(`/api/survivor/state?ts=${Date.now()}${entryQuery}`, {
          cache: 'no-store',
          headers: { Authorization: `Bearer ${token}` },
        })
        const payload = await response.json()
        if (!response.ok) throw new Error(payload.message || payload.error || 'Private Survivor state unavailable')
        if (!cancelled && requestId === latestRequestId) setData(payload)
      } catch {
        if (!cancelled && requestId === latestRequestId) {
          setData({
            status: 'PRIVATE_STATE_UNAVAILABLE',
            entry_linked: false,
            used_teams: [],
            current_picks: [],
          })
        }
      }
    }

    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') load()
    }
    const onPageshow = event => {
      // Mobile Safari may restore a stale tab from its back/forward cache.
      if (event.persisted) load()
    }
    load()
    timer = window.setInterval(load, 30000)
    document.addEventListener('visibilitychange', onVisibilityChange)
    window.addEventListener('pageshow', onPageshow)
    return () => {
      cancelled = true
      if (timer) window.clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisibilityChange)
      window.removeEventListener('pageshow', onPageshow)
    }
  }, [user?.id, getAccessToken, refreshKey, selectedEntry])

  return data
}

function humanize(value) {
  return String(value || '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
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
  const survivorSummary = survivorHomeSummary({
    signedIn: Boolean(user),
    privateState: privateSurvivor,
    genericState: survivor,
  })

  const cards = [
    {
      label: 'Best Bets',
      route: 'Best Bets',
      status: (bets.summary?.shadow_plays || 0) > 0 ? 'SHADOW RESEARCH' : 'NO VERIFIED PLAY',
      title: bestPlay ? `Research watch: ${bestPlay.selection} · ${bestPlay.market}` : 'No selection has cleared the proof check',
      metric: bets.summary?.candidates ?? '—',
      metricLabel: 'game-line candidates checked',
      detail: `${bets.summary?.passes ?? 0} passed over · research is not an approved bet`,
      tone: (bets.summary?.shadow_plays || 0) > 0 ? 'emerald' : 'blue',
    },
    {
      label: 'Props',
      route: 'Props',
      status: 'RESEARCH',
      title: 'Player props worth examining',
      metric: propRows.length,
      metricLabel: 'player prop candidates',
      detail: 'Independent player edge and source-price proof required.',
      tone: 'blue',
    },
    {
      label: 'PrizePicks',
      route: 'PrizePicks',
      status: prizeMonitor ? 'MONITOR' : 'RESEARCH',
      title: prizeMonitor ? `Research watch: ${prizeMonitor.player} ${prizeMonitor.side} ${prizeMonitor.line}` : 'Every pick-em line deserves proof',
      metric: prizeRows.length,
      metricLabel: 'pick-em entries checked',
      detail: prizeMonitor
        ? `Experimental model ${prizeMonitor.v2_probability_pct}% · market reference ${prizeMonitor.market_reference_probability_pct}%`
        : 'No entry forced without source-backed evidence.',
      tone: prizeMonitor ? 'amber' : 'blue',
    },
    {
      label: 'Parlays',
      route: 'Parlays',
      status: 'PROOF GATE',
      title: 'Combine legs only with evidence',
      metric: parlays.summary?.candidates ?? '—',
      metricLabel: 'combinations examined',
      detail: `${parlays.summary?.shadow_monitors ?? 0} research monitors · source-leg proof required`,
      tone: 'violet',
    },
    {
      label: 'Survivor',
      route: 'Survivor',
      status: survivorSummary.status,
      title: survivorSummary.title,
      metric: survivor.pool_current_week ? `W${survivor.pool_current_week}` : null,
      metricLabel: 'current pool week',
      detail: survivorSummary.detail,
      tone: survivorSummary.tone,
    },
  ]

  return (
    <section aria-label="Home decision overview">
      <div className="section-heading">
        <div><p className="eyebrow">The signal board · right now</p><h2>What matters now</h2><p className="mt-1 text-xs font-semibold text-[#536B73]">Five areas. Clearer decisions. Evidence before hype.</p></div>
        <button onClick={() => onNavigate('Brain Record')} className="text-sm font-black text-[#0F6977] hover:text-[#B74D46]">How good is the brain? →</button>
      </div>
      <HomeRefStage zone="signals"/>
      <div className="zenith-signal-rail flex snap-x gap-3 overflow-x-auto pb-3 xl:grid xl:grid-cols-5 xl:overflow-visible">
        {cards.map((card,index) => (
          <HomeSignalCard key={card.label} index={index} card={card} onNavigate={onNavigate}/>
        ))}
      </div>
    </section>
  )
}

function HomeSnapshots({ onNavigate }) {
  const { user } = useAuth()
  const survivor = useJsonEndpoint('/survivor_v2_current.json', {})
  const privateSurvivor = usePrivateSurvivorState()
  const fantasy = useJsonEndpoint('/fantasy_v2_current.json', { lanes: {} })
  const performance = useJsonEndpoint('/performance_snapshot.json', { official: {} })
  const brainSummary = homeBrainSnapshot(performance)
  const laneCount = Object.values(fantasy.lanes || {}).filter((lane) => lane.forward_grade_available).length
  const hasPersonalSurvivor = Boolean(user && privateSurvivor.entry_linked)

  return (
    <section aria-label="Home Fantasy Survivor and Brain Record" className="min-w-0">
      <HomeRefStage zone="picks" />
      <p className="mb-2 text-[10px] font-black uppercase tracking-[.13em] text-[#0C7182] lg:hidden">Your sports, one swipe at a time →</p>
      <div data-home-snapshots-rail role="group" aria-label="Survivor Fantasy and Brain shortcuts"
        className="flex min-w-0 snap-x snap-mandatory gap-3 overflow-x-auto pb-2 lg:grid lg:grid-cols-3 lg:overflow-visible">
      <button data-home-snapshot-card="survivor" onClick={() => onNavigate('Survivor')} className="w-[min(80vw,320px)] shrink-0 snap-start rounded-[22px] border-2 border-[#E6B8A5] bg-[#FFEBDC] p-5 text-left text-[#173E52] transition hover:border-[#D7755A] lg:w-auto">
        <div className="text-xs font-black uppercase tracking-[0.14em] text-[#AF4D43]">{hasPersonalSurvivor ? 'My Survivor' : 'Survivor'}</div>
        <div className="mt-3 text-2xl font-black text-[#173E52]">
          {hasPersonalSurvivor
            ? privateSurvivor.active_entry
            : user
              ? 'No pool linked'
              : `Week ${survivor.pool_current_week ?? '—'} research`}
        </div>
        <div className="mt-2 text-sm font-semibold text-[#536B73]">
          {hasPersonalSurvivor
            ? `Week ${privateSurvivor.pool_current_week ?? survivor.pool_current_week ?? '—'} · ${(privateSurvivor.used_teams || []).length} teams used`
            : user
              ? 'Account ready for a private Survivor entry'
              : 'Sign in for private entries, used teams and pool rules'}
        </div>
        <div className="mt-5 text-xs font-black text-[#A94F3C]">Open Survivor →</div>
      </button>
      <button data-home-snapshot-card="fantasy" onClick={() => onNavigate('Fantasy')} className="w-[min(80vw,320px)] shrink-0 snap-start rounded-[22px] border-2 border-[#B1D6D2] bg-[#D9F4EE] p-5 text-left text-[#173E52] transition hover:border-[#0F8B95] lg:w-auto">
        <div className="text-xs font-black uppercase tracking-[0.14em] text-[#0D6772]">Fantasy + DFS</div>
        <div className="mt-3 text-2xl font-black text-[#173E52]">{laneCount} forward-tested lanes</div>
        <div className="mt-2 text-sm font-semibold text-[#536B73]">Start/Sit · FAAB · IR stash · Defense · IDP · DFS</div>
        <div className="mt-5 text-xs font-black text-[#0E7380]">Open Fantasy →</div>
      </button>
      <button data-home-snapshot-card="brain" onClick={() => onNavigate('Brain Record')} className="w-[min(80vw,320px)] shrink-0 snap-start rounded-[22px] border-2 border-[#173E52] bg-[#173E52] p-5 text-left text-white shadow-[4px_4px_0_#FFD36A] transition hover:-translate-y-0.5 hover:border-[#FFD36A] lg:w-auto">
        <div className="text-xs font-black uppercase tracking-[0.14em] text-[#FFD36A]">Brain Record</div>
        <div className="mt-3 text-2xl font-black">{brainSummary.headline}</div>
        <div className="mt-1 text-sm font-black text-[#FFD36A]">{brainSummary.summary}</div>
        <div className="mt-2 text-xs font-semibold leading-5 text-[#CEDFE5]">{brainSummary.clarity || 'Official result verification still pending.'}</div>
        {brainSummary.lastResult && <p className="mt-2 text-[11px] font-semibold leading-4 text-[#E0E9E7]">Last graded: {brainSummary.lastResult.pick} — {brainSummary.lastResult.outcome.toLowerCase()}{brainSummary.lastResult.score ? ` · ${brainSummary.lastResult.score}` : ''}</p>}
        <div className="mt-1 text-[11px] font-medium leading-4 text-[#B8C9D1]">{brainSummary.sampleWarning}</div>
        <div className="mt-3 text-xs font-black text-[#FFD36A]">Review official record →</div>
      </button>
      </div>
    </section>
  )
}

function BettingSubnav({ active, onNavigate }) {
  const activeButtonRef = useRef(null)
  const tabRailRef = useRef(null)

  useEffect(() => {
    const rail = tabRailRef.current
    const button = activeButtonRef.current
    if (!rail || !button) return
    // Native scrollIntoView on a horizontally scrolling child also scrolls
    // its vertical ancestor: this was moving the entire page on iPhone.
    // Scroll ONLY this rail; never move the document to center a bet tab.
    const railRect = rail.getBoundingClientRect()
    const buttonRect = button.getBoundingClientRect()
    const target = rail.scrollLeft + buttonRect.left - railRect.left
      - (rail.clientWidth - buttonRect.width) / 2
    rail.scrollTo({ left: Math.max(0, target), behavior: 'auto' })
  }, [active])

  return (
    <section data-premium-market-board aria-label="Zenith market navigation"
      className="min-w-0 overflow-hidden rounded-[22px] border-2 border-[#173E52] bg-[#FFF5E4] shadow-[4px_4px_0_#173E5224]">
      <div ref={tabRailRef} role="group" aria-label="Betting sections"
        className="flex min-w-0 snap-x gap-2 overflow-x-auto px-2 py-1 sm:px-3 sm:py-2">
        <div data-market-board-heading
          className="relative flex min-h-11 w-[118px] shrink-0 flex-col justify-center overflow-hidden rounded-xl bg-[#173E52] px-2 py-1 text-[#FFF5E4] sm:w-[170px] sm:px-3">
          <div aria-hidden="true" className="absolute inset-x-0 top-0 h-[3px] bg-[linear-gradient(90deg,#FF7766_0%,#FF7766_34%,#FFD36A_34%,#FFD36A_67%,#46CDD2_67%,#46CDD2_100%)]"/>
          <span className="text-[9px] font-black uppercase leading-3 tracking-[.04em] text-[#7DE4E1] sm:text-[10px]">THE MARKET BOARD</span>
          <span className="mt-1 text-[9px] font-black leading-3 text-[#FFD36A] sm:text-[10px]">Proof before picks <span aria-hidden="true">↔</span></span>
        </div>
        {bettingNavItems.map((item) => (
          <button type="button"
            key={item}
            ref={active === item ? activeButtonRef : null}
            aria-current={active === item ? 'page' : undefined}
            onClick={() => onNavigate(item)}
            className={`min-h-11 shrink-0 snap-start whitespace-nowrap rounded-xl border-2 px-3.5 py-2 text-[12px] font-black transition sm:px-4 sm:text-sm ${active === item ?
              'border-[#173E52] bg-[#FFD36A] text-[#173E52] shadow-[2px_2px_0_#173E52]' :
              'border-[#D3DDDA] bg-white text-[#173E52] hover:border-[#46CDD2] hover:bg-[#E8F7F1]'}`}
          >
            {item}
          </button>
        ))}
      </div>
    </section>
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
  const priorBoard = useJsonEndpoint('/betting_v2_current.json', { market_board: [] })
  const nflScores = useJsonEndpoint('/nfl_scores.json', { next_games: [] })
  const [sport, setSport] = useState('ALL')
  const [market, setMarket] = useState('ALL')
  const [showAllResearch, setShowAllResearch] = useState(false)
  const rows = data.picks || []
  // Navigation is permanent; the research feed must not erase NFL or spreads
  // merely because none of the quotes is source-fresh and proven.
  const sports = BET_SPORT_FILTERS
  const grouped = organizeBetResearch(rows, sport, market)
  const byProofLane = data.by_proof_lane || {}
  const researched = [...grouped.research].sort((a, b) => {
    const ta = Date.parse(String(a.event_start || '').replace(' ', 'T'))
    const tb = Date.parse(String(b.event_start || '').replace(' ', 'T'))
    return (Number.isFinite(ta) ? ta : Infinity) - (Number.isFinite(tb) ? tb : Infinity)
      || (Number(b.book_count || 0) - Number(a.book_count || 0))
  })
  const visibleResearch = showAllResearch ? researched : researched.slice(0, 6)
  const summary = data.summary || {}
  const insufficientCount = grouped.research.filter(r => String(r.selection_rule_status || '').includes('INSUFFICIENT_HISTORY')).length
  const noEdgeCount = grouped.research.filter(r => r.selection_rule_status === 'NO_INDEPENDENT_MODEL_EDGE').length

  const renderBetCard = (row, i) => {
    const proof = explainBetProof(row, byProofLane)
    const isPlay = proof.isPlay
    return (
      <article data-premium-research-card={isPlay?'shadow':'research'} key={`${row.game_key}-${row.market}-${row.selection_key}-${i}`} className="min-w-0 rounded-[23px] border border-[#DCC9AF] border-t-[4px] border-t-[#FF7766] bg-[#FFF8ED] p-4 text-[#173E52] shadow-[0_5px_0_#173E5215] sm:p-5">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[11px] font-black uppercase tracking-[0.13em] text-[#0B7180]">{row.sport} · {humanize(row.market)}</div>
            <div className="mt-2 break-words text-xl font-black tracking-tight text-[#173E52] sm:text-2xl">{betDisplayLabel(row)}</div>
          </div>
          <span className={`shrink-0 rounded-full px-3 py-1 text-[10px] font-black ${isPlay ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
            {isPlay ? 'SHADOW PLAY' : 'RESEARCH'}
          </span>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-semibold text-slate-500">
          {row.american_odds != null && <span>Last observed quote {Number(row.american_odds) > 0 ? '+' : ''}{row.american_odds}</span>}
          {row.book_count != null && <span>· {row.book_count} books</span>}
          <span>· Paper research, not an approved bet</span>
        </div>
        <div className={`mt-3 rounded-xl border px-3 py-2 ${isPlay ? 'border-[#9ACFC7] bg-[#E5F8F2]' : 'border-[#E8C9A4] bg-[#FFF1DF]'}`}>
          <div className={`text-sm font-black ${isPlay ? 'text-emerald-800' : 'text-slate-800'}`}>{proof.label}</div>
          <p className="mt-1 line-clamp-2 text-[11px] font-semibold leading-4 text-slate-600">{proof.description}</p>
        </div>
        <details className="group mt-4 rounded-2xl border border-[#D4C9B7] bg-white">
          <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-xs font-black text-slate-700">
            <span>View evidence</span>
            <ChevronRight size={16} className="shrink-0 text-slate-400 transition-transform group-open:rotate-90" />
          </summary>
          <div className="border-t border-slate-100 px-4 pb-4 pt-4">
            <div className="mb-3"><BetMeaning row={row} /></div>
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.calibrated_win_probability_pct ?? '—'}%</div><div className="mt-1 text-slate-400">{proof.estimateLabel}</div></div>
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.market_reference_probability_pct ?? '—'}%</div><div className="mt-1 text-slate-400">Market fair</div></div>
              <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.conservative_expected_value_pct == null ? '—' : `${row.conservative_expected_value_pct}%`}</div><div className="mt-1 text-slate-400">Conservative EV</div></div>
            </div>
            <div className="mt-4 text-xs font-semibold leading-5 text-slate-500">{humanize(row.historical_edge_confidence)} · {row.book_count ?? '—'} books · quality {row.data_quality_grade || '—'}</div>
            {proof.historyCount != null && <p className="mt-2 text-xs text-slate-500">Pregame outcomes: {proof.historyCount} / 50{proof.independentGameCount == null ? '' : ` · Independent games: ${proof.independentGameCount} / 25`}</p>}
            <div className="mt-2 text-[11px] leading-5 text-slate-400">Model gate: {humanize(row.selection_rule_status)}</div>
          </div>
        </details>
      </article>
    )
  }

  return (
    <section className="space-y-5">
      <section data-bestbets-premium-brief aria-label="Best Bets premium evidence brief"
        className="relative overflow-hidden rounded-[24px] border-2 border-[#173E52] bg-[#173E52] p-3 text-[#FFF5E4] shadow-[4px_5px_0_#46CDD255] sm:p-5">
        <div aria-hidden="true" className="absolute inset-x-0 top-0 h-[5px] bg-[linear-gradient(90deg,#FF7766_0%,#FF7766_35%,#FFD36A_35%,#FFD36A_65%,#46CDD2_65%,#46CDD2_100%)]" />
        <div className="relative grid min-w-0 gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(260px,0.9fr)] sm:items-center">
          <div className="min-w-0">
            <p className="text-[10px] font-black uppercase tracking-[.18em] text-[#7DE4E1]">THE PRICE DESK</p>
            <h2 className="mt-1 text-[clamp(1.65rem,4vw,2.5rem)] font-black leading-[1.05] tracking-[-.04em] text-[#FFF5E4]">Best Bets<span aria-hidden="true" className="text-[#FF7766]">.</span></h2>
            <p className="mt-1 max-w-md text-[11px] font-semibold leading-[1.45] text-[#DCE9E8] sm:text-xs">
              Saved model research, not an approved bet. Compare observed prices first; independent proof decides what qualifies.
            </p>
          </div>
          <div data-bestbets-proof-stats className="grid grid-cols-3 gap-1.5 rounded-xl border border-[#7CB8BE]/50 bg-[#FFF8ED] p-2 text-[#173E52] sm:gap-2">
            {[
              ['reviewed','Reviewed',summary.candidates],
              ['shadow','Shadow',summary.shadow_plays],
              ['passed','PASS / HOLD',summary.passes],
            ].map(([id,label,count])=>
              <div data-proof-metric={id} key={id} className="min-w-0 rounded-lg bg-white px-1.5 py-2 text-center sm:px-2">
                <div className="text-[23px] font-black leading-none tabular-nums text-[#173E52]">{count ?? '—'}</div>
                <div className="mt-1 text-[9px] font-black uppercase leading-[1.2] tracking-wide text-[#526D76]">{label}</div>
              </div>)}
          </div>
        </div>
        <div data-bestbets-filter-context className="relative mt-2 border-t border-[#78ADB6]/35 pt-2 text-[10px] font-bold text-[#CFE5E8]">
          Viewing {sport==='ALL'?'All sports':sport} · {BET_MARKET_FILTERS.find(item=>item.id===market)?.label || 'All markets'} · {grouped.research.length} research rows
        </div>
      </section>

      <SportFilter sports={sports} active={sport} onChange={next => {setSport(next); setShowAllResearch(false)}} />
      <div role="group" aria-label="Betting market filter" className="flex gap-2 overflow-x-auto pb-1">
        {BET_MARKET_FILTERS.map(item => (
          <button type="button" key={item.id} onClick={() => {setMarket(item.id); setShowAllResearch(false)}}
            className={`min-h-10 whitespace-nowrap rounded-full border px-3 py-2 text-xs font-black ${market === item.id ? 'border-[#173E52] bg-[#46CDD2] text-[#173E52]' : 'border-[#D7D7D0] bg-white text-[#516B75] hover:border-[#46CDD2]'}`}>
            {item.label}
          </button>
        ))}
      </div>
      <Suspense fallback={<LoadingSurface label="Loading sportsbook odds and price comparisons" />}>
        <BettingOddsBoard sport={sport} market={market} />
      </Suspense>
      <BestBetsMarketCoverage sport={sport} market={market} currentData={data} priorBoard={priorBoard} nflScores={nflScores} />
      {grouped.plays.length > 0 && (
        <div className="space-y-3">
          <div className="section-heading"><div><p className="eyebrow">Forward paper testing</p><h3>Qualified shadow selections</h3></div></div>
          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">{grouped.plays.map(renderBetCard)}</div>
        </div>
      )}
      <div className="section-heading">
        <div>
          <p className="eyebrow">Not official picks</p>
          <h3>Research watchlist</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">Browse lines and explanations without mistaking research for a betting recommendation. Sorted by upcoming kickoff, not projected profit.</p>
        </div>
        <span className="health-pill">{grouped.research.length} RESEARCH</span>
      </div>
      <div className="flex flex-wrap gap-2 text-xs font-bold text-slate-600">
        {insufficientCount > 0 && <span className="rounded-full bg-amber-50 px-3 py-2 text-amber-800">{insufficientCount} still building history</span>}
        {noEdgeCount > 0 && <span className="rounded-full bg-slate-100 px-3 py-2 text-slate-700">{noEdgeCount} with no proven model edge</span>}
      </div>
      {visibleResearch.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">{visibleResearch.map(renderBetCard)}</div>
      ) : (
        <p className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-sm font-semibold text-slate-600">No research candidates match this filter.</p>
      )}
      {!showAllResearch && grouped.research.length > visibleResearch.length && (
        <button type="button" onClick={() => setShowAllResearch(true)} className="min-h-11 rounded-xl border border-blue-200 bg-white px-5 py-3 text-sm font-black text-blue-800 hover:bg-blue-50">
          Show all {grouped.research.length} research candidates
        </button>
      )}
    </section>
  )
}

function CrossSportScorePanel({ league }) {
  const data = useJsonEndpoint(`/${league.toLowerCase()}_scores.json`, { games: [], counts: {}, status: 'LOADING' })
  const [selectedGameId, setSelectedGameId] = useState(null)
  const [showAll, setShowAll] = useState(false)
  const games = [...(data.games || [])]
    .sort((a, b) => {
      const rank = game => game.live ? 0 : game.final ? 2 : 1
      return rank(a) - rank(b) || String(a.start_time || '').localeCompare(String(b.start_time || ''))
    })
  const visible = showAll ? games : games.slice(0, 24)
  const selectedGame = games.find(game => String(game.event_id) === String(selectedGameId)) || null

  useEffect(() => {
    setSelectedGameId(null)
  }, [league])

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
                <button
                  type="button"
                  onClick={() => {
                    const nextId = selectedGameId === game.event_id ? null : game.event_id
                    setSelectedGameId(nextId)
                    if (nextId) {
                      window.requestAnimationFrame(() => {
                        document.getElementById('score-game-center')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                      })
                    }
                  }}
                  className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-slate-950 px-4 text-xs font-black text-white"
                >
                  {selectedGameId === game.event_id ? 'Close Game Center' : 'Open Game Center'}
                  <ChevronRight size={15} className={selectedGameId === game.event_id ? 'rotate-90' : ''} />
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {selectedGame && (
        <div className="mt-5">
          <Suspense fallback={<LoadingSurface label="Loading Game Center" />}>
            <ScoreGameCenter
              game={selectedGame}
              league={league}
              onClose={() => setSelectedGameId(null)}
            />
          </Suspense>
        </div>
      )}

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
            <button key={item} onClick={() => setLeague(item)} className={`min-h-11 rounded-full px-4 py-2 text-xs font-black ${league === item ? 'bg-slate-950 text-white' : 'border border-slate-200 bg-white text-slate-500'}`}>{item}</button>
          ))}
        </div>
      </section>

      {league === 'NFL' && <Scoreboard />}
      {league === 'MLB' && <MlbPanel />}
      {['NBA', 'NHL', 'CFB', 'CBB'].includes(league) && <CrossSportScorePanel league={league} />}
    </div>
  )
}

function NewsEditorialWorkbench() {
  const graph = useJsonEndpoint('/ask_retrieval.json', { news_events: [], counts: {} })
  const survivor = useJsonEndpoint('/survivor_v2_current.json', {})
  const props = useJsonEndpoint('/prop_v2_current.json', { picks: [] })
  const editorial = useJsonEndpoint('/insight_drafts.json', { drafts: [], editorial_policy: {} })
  const news = (graph.news_events || []).filter(row => row.event_source_type === 'NEWS' && row.title)
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


  return (
    <div>
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

function NewsInsightsPanel() {
  const [showEditorial, setShowEditorial] = useState(false)
  return (
    <div className="min-w-0 space-y-6">
      <SportsNewsHub />
      <details aria-label="Sports Zenith editorial research drafts" onToggle={(event) => setShowEditorial(event.currentTarget.open)}
        className="rounded-[22px] border border-slate-200 bg-white p-4 shadow-soft md:p-5">
        <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-2 text-xs font-black text-blue-700">
          Editorial research lab · drafts only, no automatic publishing <ChevronRight size={16} className="transition-transform group-open:rotate-90" />
        </summary>
        {showEditorial && <div className="mt-4 border-t border-slate-100 pt-4"><NewsEditorialWorkbench /></div>}
      </details>
    </div>
  )
}

function FantasyLaneCard({ lane, row }) {
  const base = "rounded-3xl border border-slate-200 bg-white p-5 shadow-soft"
  const weeklyTierTone = (tier) => {
    const value = String(tier || '').toUpperCase()
    if (value.includes('CORE_START')) return 'bg-emerald-50 text-emerald-700'
    if (value.includes('START_LEAN')) return 'bg-blue-50 text-blue-700'
    if (value.includes('FLEX_START')) return 'bg-sky-50 text-sky-700'
    if (value.includes('MATCHUP')) return 'bg-amber-50 text-amber-700'
    if (value.includes('SIT') || value.includes('INACTIVE')) return 'bg-rose-50 text-rose-700'
    return 'bg-slate-100 text-slate-600'
  }
  if (lane === 'weekly') {
    return (
      <div className={base}>
        <div className="flex items-start justify-between gap-3">
          <div><div className="text-xs font-black uppercase tracking-[0.14em] text-blue-700">{row.team} · {row.position}</div><div className="mt-2 text-xl font-black text-slate-950">{row.player}</div><div className="mt-1 text-xs font-semibold text-slate-400">vs {row.opponent || '—'}</div></div>
          <span className={`rounded-full px-3 py-1 text-[10px] font-black ${weeklyTierTone(row.weekly_tier)}`}>{humanize(row.weekly_tier)}</span>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.weekly_research_score ?? '—'}</div><div className="mt-1 text-slate-400">Weekly research</div></div>
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
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.waiver_research_score ?? '—'}</div><div className="mt-1 text-slate-400">Waiver research</div></div>
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
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.stash_research_score ?? '—'}</div><div className="mt-1 text-slate-400">Stash research</div></div>
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
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.weekly_stream_score ?? '—'}</div><div className="mt-1 text-slate-400">Weekly stream</div></div>
          <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.multiweek_hold_score ?? '—'}</div><div className="mt-1 text-slate-400">Multi-week hold</div></div>
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
        <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.idp_usage_score ?? '—'}</div><div className="mt-1 text-slate-400">Usage research</div></div>
        <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.snap_pct == null ? '—' : `${Math.round(Number(row.snap_pct) * (Number(row.snap_pct) <= 1 ? 100 : 1))}%`}</div><div className="mt-1 text-slate-400">Snaps</div></div>
        <div className="rounded-xl bg-slate-50 p-3"><div className="font-black text-slate-950">{row.snap_pct_change == null ? '—' : `${Math.round(Number(row.snap_pct_change) * 100)} pts`}</div><div className="mt-1 text-slate-400">Snap change</div></div>
      </div>
      <div className="mt-4 text-xs leading-5 text-slate-500">{humanize(row.role_signal)} · usage research only until league-specific IDP scoring is connected.</div>
    </div>
  )
}






function LeagueSettingsPanel({ team, onSaved, autoOpen = false, onAutoOpened }) {
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

  useEffect(() => {
    if (!autoOpen || !team?.league_id) return
    setOpen(true)
    onAutoOpened?.()
    window.requestAnimationFrame(() => {
      const panel = document.getElementById('fantasy-league-settings')
      panel?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      panel?.focus({ preventScroll: true })
    })
  }, [autoOpen, team?.league_id, onAutoOpened])

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
    <div id="fantasy-league-settings" tabIndex="-1" className="mt-4 min-w-0 max-w-full scroll-mt-28 rounded-2xl border border-slate-200 bg-slate-50 p-4 outline-none">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="fantasy-league-settings-content"
        onClick={() => setOpen((value) => !value)}
        className="flex min-h-11 w-full items-center justify-between gap-3 text-left"
      >
        <div>
          <div className="text-sm font-black text-slate-950">League settings</div>
          <div className="mt-1 text-[11px] font-semibold text-slate-500">Scoring · starter slots · bench/IR · FAAB budget</div>
        </div>
        <span className="rounded-full bg-white px-3 py-1 text-[10px] font-black uppercase tracking-[0.1em] text-blue-700">{open ? 'Close' : 'Edit'}</span>
      </button>

      {open && (
        <div id="fantasy-league-settings-content" className="mt-4 border-t border-slate-200 pt-4">
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
                className={`min-h-11 rounded-xl border px-3 py-2.5 text-xs font-black ${scoringPreset === value ? 'border-blue-300 bg-blue-50 text-blue-700' : 'border-slate-200 bg-white text-slate-600'}`}
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
                  className="mt-1 h-11 w-full bg-transparent text-center text-sm font-black text-slate-950 outline-none"
                />
              </label>
            ))}
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-4">
            <label>
              <span className="text-[10px] font-black uppercase tracking-[0.1em] text-slate-500">Bench</span>
              <input aria-label="Bench slots" type="number" min="0" max="30" value={benchSlots} onChange={(event) => setBenchSlots(Math.max(0, Math.min(30, Number(event.target.value) || 0)))} className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black outline-none" />
            </label>
            <label>
              <span className="text-[10px] font-black uppercase tracking-[0.1em] text-slate-500">IR</span>
              <input aria-label="IR slots" type="number" min="0" max="20" value={irSlots} onChange={(event) => setIrSlots(Math.max(0, Math.min(20, Number(event.target.value) || 0)))} className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black outline-none" />
            </label>
            <label>
              <span className="text-[10px] font-black uppercase tracking-[0.1em] text-slate-500">FAAB total</span>
              <input aria-label="FAAB total budget" type="number" min="0" max="100000" value={faabBudget} onChange={(event) => setFaabBudget(event.target.value)} placeholder="100" className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black outline-none" />
            </label>
            <label>
              <span className="text-[10px] font-black uppercase tracking-[0.1em] text-slate-500">FAAB left</span>
              <input aria-label="FAAB remaining" type="number" min="0" max="100000" value={faabRemaining} onChange={(event) => setFaabRemaining(event.target.value)} placeholder="100" className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black outline-none" />
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

function RateMyTeamPanel({ preferredLeagueId = null, onSelectedLeagueChange, onTeamUpsert, openLeagueSettings = false, onLeagueSettingsOpened, refreshKey = 0 }) {
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
  }, [user, getAccessToken, refreshKey])

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
    <section className="grid min-w-0 max-w-full gap-5 xl:grid-cols-[0.92fr_1.08fr]">
      <div className="min-w-0 max-w-full overflow-x-hidden rounded-[28px] border border-slate-200 bg-white p-5 shadow-soft md:p-6">
        <div className="flex min-w-0 items-start justify-between gap-4">
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
              <div className="mt-2 flex w-full min-w-0 max-w-full gap-2 overflow-x-auto pb-1">
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

        <LeagueSettingsPanel
          team={selectedTeam}
          onSaved={updateSavedTeamSettings}
          autoOpen={openLeagueSettings}
          onAutoOpened={onLeagueSettingsOpened}
        />

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

        <Suspense fallback={<LoadingSurface label="Loading local roster import" />}>
          <FantasyRosterLocalImport
            existingCount={rosterNames.length}
            onApply={names => {
              setRosterText(names.join('\n'))
              setResult(null)
              setSavedSummary(null)
              setError('')
            }}
          />
        </Suspense>

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

      <div className="min-w-0 max-w-full overflow-x-hidden rounded-[28px] border border-slate-200 bg-white p-5 shadow-soft md:p-6">
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
  const [fantasyImportRefresh, setFantasyImportRefresh] = useState(0)
  const [openLeagueSettingsRequest, setOpenLeagueSettingsRequest] = useState(false)
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
    ['trades', 'Trades'],
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
  }, [user, getAccessToken, authLoading, fantasyImportRefresh])

  const onFantasyImported = (linked) => {
    if (linked?.league_id) setSelectedLeagueId(linked.league_id)
    setFantasyImportRefresh(value => value + 1)
    setLane('my_teams')
  }

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

  const openLeagueSettings = () => {
    if (teamOptions.length > 0) setOpenLeagueSettingsRequest(true)
    switchLane('my_teams')
  }

  const dkTournament = (dfs.replay_modes || []).find((row) => row.platform === 'DRAFTKINGS' && row.mode === 'TOURNAMENT_UPSIDE')

  return (
    <div className="space-y-8">
      <section className="rounded-[30px] border border-slate-200 bg-white p-6 shadow-soft md:p-8">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <p className="eyebrow">Fantasy</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-slate-950 md:text-4xl">Fantasy command center</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-500">Weekly decisions, trades, waivers, FAAB, IR stash, defense streaming, IDP and DFS — with research labels that stay separate from proven forward performance.</p>
          </div>
          <div className="flex w-full min-w-0 gap-1.5 rounded-2xl border border-slate-200 bg-slate-50 p-1.5 sm:w-auto sm:p-2">
            {['Season-Long','DFS Lineup Lab'].map((item) => (
              <button key={item} onClick={() => setMode(item)} className={`min-h-11 min-w-0 flex-1 rounded-xl px-2 py-2.5 text-xs font-black leading-4 sm:flex-none sm:whitespace-nowrap sm:px-4 sm:text-sm ${mode === item ? 'bg-slate-950 text-white' : 'text-slate-500'}`}>{item}</button>
            ))}
          </div>
        </div>
      </section>

      {mode === 'Season-Long' ? (
        <>
          <section className="rounded-2xl border border-slate-200 bg-white p-2 shadow-soft">
            <div className="flex gap-2 overflow-x-auto">
              {laneTabs.map(([key,label]) => (
                <button key={key} onClick={() => switchLane(key)} className={`min-h-11 whitespace-nowrap rounded-xl px-4 py-2.5 text-sm font-black ${lane === key ? 'bg-slate-950 text-white' : 'text-slate-500'}`}>{label}</button>
              ))}
            </div>
          </section>

          <Suspense fallback={<LoadingSurface label="Loading Fantasy league connections" />}>
            <FantasyPlatformConnections
              onImported={onFantasyImported}
              onManualSetup={() => switchLane('my_teams')}
            />
          </Suspense>

          {user && (
            <Suspense fallback={<LoadingSurface label="Loading Fantasy Team Control" />}>
              <FantasyTeamControl
                teams={teamOptions}
                selectedLeagueId={selectedLeagueId}
                loading={teamOptionsLoading}
                onSelect={setSelectedLeagueId}
                onManage={openLeagueSettings}
              />
            </Suspense>
          )}

          {lane === 'my_teams' ? (
            <RateMyTeamPanel
              preferredLeagueId={selectedLeagueId}
              onSelectedLeagueChange={setSelectedLeagueId}
              onTeamUpsert={upsertTeamOption}
              refreshKey={fantasyImportRefresh}
              openLeagueSettings={openLeagueSettingsRequest}
              onLeagueSettingsOpened={() => setOpenLeagueSettingsRequest(false)}
            />
          ) : lane === 'trades' ? (
            <Suspense fallback={<LoadingSurface label="Loading your trade research" />}>
              <FantasyTradeResearch
                weeklyRows={decisions.lanes?.weekly?.rows || []}
                generatedAt={decisions.generated_at || null}
                teams={teamOptions}
                selectedLeagueId={selectedLeagueId}
              />
            </Suspense>
          ) : (
            <>
          {lane === 'weekly' && (
            <Suspense fallback={<LoadingSurface label="Loading your Start / Sit research" />}>
              <PersonalStartSitPanel leagueId={selectedLeagueId} onOpenMyTeams={() => switchLane('my_teams')} onOpenLeagueSettings={openLeagueSettings} />
            </Suspense>
          )}
          {lane === 'faab' && (
            <Suspense fallback={<LoadingSurface label="Loading your waiver research" />}>
              <PersonalWaiverPanel leagueId={selectedLeagueId} onOpenMyTeams={() => switchLane('my_teams')} />
            </Suspense>
          )}
          {lane === 'ir_stash' && (
            <Suspense fallback={<LoadingSurface label="Loading your IR stash research" />}>
              <PersonalIrStashPanel leagueId={selectedLeagueId} onOpenMyTeams={() => switchLane('my_teams')} onOpenLeagueSettings={openLeagueSettings} />
            </Suspense>
          )}
          {lane === 'defense_streaming' && (
            <Suspense fallback={<LoadingSurface label="Loading your defense streaming research" />}>
              <PersonalDefenseStreamingPanel leagueId={selectedLeagueId} onOpenMyTeams={() => switchLane('my_teams')} />
            </Suspense>
          )}
          {lane === 'idp' && (
            <Suspense fallback={<LoadingSurface label="Loading your IDP research" />}>
              <PersonalIdpPanel leagueId={selectedLeagueId} onOpenMyTeams={() => switchLane('my_teams')} onOpenLeagueSettings={openLeagueSettings} />
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

          <section className="min-w-0">
            <div className="section-heading">
              <div><p className="eyebrow">Forward proof</p><h2>Five fantasy lanes are being tested</h2></div>
              <span className="health-pill">NO AUTO-PROMOTION</span>
            </div>
            <div className="flex w-full min-w-0 max-w-full gap-3 overflow-x-auto pb-2 xl:grid xl:grid-cols-5 xl:overflow-visible">
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
                  <button key={item} onClick={() => setSport(item)} className={`min-h-11 rounded-full px-3 py-2 text-xs font-black ${effectiveSport === item ? 'bg-blue-700 text-white' : 'border border-slate-200 bg-white text-slate-500'}`}>{item}</button>
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
    <nav aria-label="Mobile primary navigation" className="fixed inset-x-0 bottom-0 z-40 border-t-2 border-[#173E52] bg-[#FFF5E4]/95 px-2 pb-[max(.5rem,env(safe-area-inset-bottom))] pt-2 shadow-[0_-8px_28px_rgba(2,18,36,.13)] backdrop-blur lg:hidden">
      <div className="grid grid-cols-5 gap-1">
        {items.map(([label, route, Icon]) => {
          const selected = route === 'Best Bets' ? bettingNavItems.includes(active) : active === route
          return (
            <button key={label} aria-current={selected ? 'page' : undefined} onClick={() => onNavigate(route)} className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl text-[10px] font-black ${selected ? 'bg-[#46CDD2] text-[#173E52] ring-1 ring-[#173E52]' : 'text-[#476572]'}`}>
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
      {['Scores', 'News & Insights', 'Brain Record', 'Research'].map((item) => (
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
  Tools: 'tools',
  Parlays: 'parlays',
  'Bet Lab': 'bet-lab',
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
  if (hash === 'practice') return 'Bet Lab'
  return HASH_ROUTE[hash] || 'Home'
}

export default function App() {
  const [active, setActive] = useState(() => routeFromLocation())
  const [assistantOpen, setAssistantOpen] = useState(false)
  const [gameScoutContext, setGameScoutContext] = useState(null)
  const [moreOpen, setMoreOpen] = useState(false)
  const backendLabel = useMemo(() => 'SOURCE STATUS · VERIFY PER GAME', [])
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
    // Safari overscroll should match the page being viewed. Do not apply
    // the dark Home background to the site's detailed research pages.
    document.documentElement.style.backgroundColor = active === 'Home' ? '#FFF8ED' : '#f8fafc'
  }, [active])

  useEffect(() => {
    const syncGameScoutContext = (event) => {
      const next = event.detail || null
      if (next?.cleared) {
        setGameScoutContext(current => String(current?.event_id || '') === String(next.event_id || '') ? null : current)
        return
      }
      setGameScoutContext(next)
    }
    window.addEventListener('sports-zenith-game-context', syncGameScoutContext)
    return () => window.removeEventListener('sports-zenith-game-context', syncGameScoutContext)
  }, [])

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
      // Immediate route positioning avoids the long smooth-scroll rebound
      // beneath the iPhone's fixed bottom navigation and Safari toolbar.
      window.scrollTo({ top: 0, behavior: 'auto' })
      document.getElementById('main-content')?.focus({ preventScroll: true })
    })
  }

  const navSelected = (item) => item === 'Betting' ? isBetting : active === item

  return (
    <div className={`min-h-screen pb-[calc(6.5rem+env(safe-area-inset-bottom))] lg:pb-0 ${active === 'Home' ? 'bg-[#FFF8ED] text-[#173E52]' : 'bg-[#F1F5FA] text-slate-900'}`}>
      <a href="#main-content" onClick={(event) => { event.preventDefault(); document.getElementById('main-content')?.focus() }} className="skip-link">Skip to main content</a>
      <header className="sticky top-0 z-30 border-b-2 border-[#173E52] bg-[#FFF5E4]/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4 px-4 py-3 md:px-5 md:py-4">
          <button type="button" aria-label="Sports Zenith home" onClick={() => navigate('Home')} className="text-left"><Brand /></button>

          <div className="hidden items-center gap-3 lg:flex">
            <div className="flex items-center gap-2 rounded-full border border-[#B3DAD5] bg-[#DBF6ED] px-3 py-2 text-xs font-extrabold text-[#173E52]">
              <Activity size={15} className="text-sky-500" />
              {backendLabel}
            </div>
            <AccountButton />
            <button onClick={() => setAssistantOpen(true)} className="inline-flex items-center gap-2 rounded-xl border border-[#173E52] bg-[#FF7766] px-4 py-2.5 text-sm font-black text-[#173E52] shadow-[2px_2px_0_#173E52] transition hover:-translate-y-0.5">
              <Sparkles size={16} /> The Ref
            </button>
          </div>

          <div className="flex items-center gap-2 lg:hidden">
            <AccountButton compact />
            <button onClick={() => navigate('Ask')} aria-label="Ask" className="flex h-11 w-11 items-center justify-center rounded-xl border border-[#173E52] bg-[#FF7766] text-[#173E52]"><Sparkles size={17} /></button>
            <button aria-haspopup="dialog" aria-expanded={moreOpen} onClick={() => setMoreOpen((open) => !open)} className="min-h-11 rounded-xl border border-[#173E52] bg-white px-3 py-2 text-xs font-black text-[#173E52]">More</button>
          </div>
        </div>
      </header>

      <nav aria-label="Primary navigation" className="hidden border-b-[3px] border-[#46CDD2] bg-[#173E52] lg:block">
        <div className="relative mx-auto flex max-w-[1500px] items-center gap-1 px-5 py-2.5">
          {navItems.map((item) => (
            <button
              key={item}
              onClick={() => navigate(item)}
              aria-current={navSelected(item) ? 'page' : undefined}
              className={`whitespace-nowrap rounded-xl px-3.5 py-2.5 text-sm font-extrabold transition ${navSelected(item) ? 'bg-[#FFD36A] text-[#173E52]' : 'text-[#E0EEF0] hover:bg-white/10 hover:text-white'}`}
            >
              {item}
            </button>
          ))}
          <div className="relative ml-auto">
            <button aria-haspopup="menu" aria-expanded={moreOpen} onClick={() => setMoreOpen((open) => !open)} className={`rounded-xl px-3.5 py-2.5 text-sm font-extrabold ${active === 'Research' ? 'bg-[#FFD36A] text-[#173E52]' : 'text-[#E0EEF0] hover:bg-white/10 hover:text-white'}`}>More</button>
            {moreOpen && (
              <div className="absolute right-0 top-12 z-40 w-64 rounded-3xl border border-slate-200 bg-slate-50 p-3 shadow-2xl">
                <MoreMenu onNavigate={navigate} onClose={() => setMoreOpen(false)} />
              </div>
            )}
          </div>
        </div>
      </nav>

      <main id="main-content" tabIndex="-1" className={`mx-auto max-w-[1500px] px-4 md:px-5 md:py-8 ${active === 'Home' ? 'zenith-home space-y-5 py-5' : 'space-y-8 py-6'}`} >
        {isAsk ? (
          <Suspense fallback={<LoadingSurface label="Loading analyst" />}><AskSportsHulkPage /></Suspense>
        ) : (
          <>
            {active === 'Home' && (
              <>
                <CommandCenterHero onNavigate={navigate} />
                <HomeGameDayDeck onNavigate={navigate} />
                <HomeDecisionPanel onNavigate={navigate} />
                <HomeTopNews onNavigate={navigate} />
                <HomeSnapshots onNavigate={navigate} />
                <LearningPanel onNavigate={navigate} />
                <details className="group rounded-2xl border border-[#25415D] bg-[#0A2036] p-3 text-slate-100">
                  <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-2 px-2 text-xs font-black text-sky-300">
                    Source connections and system status <ChevronRight size={16} className="transition-transform group-open:rotate-90" />
                  </summary>
                  <div className="mt-3 border-t border-white/10 pt-3">
                    <p className="mb-3 text-xs font-medium leading-5 text-slate-300">A green collector is not proof its odds, lineup or model data are valid. Game-by-game evidence is checked separately.</p>
                    <StatusStrip />
                  </div>
                </details>
              </>
            )}

            {active === 'Scores' && <ScoresHub />}

            {isBetting && (
              <>
                <BettingSubnav active={active} onNavigate={navigate} />
                {active === 'Best Bets' && <BestBetsV2Panel />}
                {active === 'Props' && <Suspense fallback={<LoadingSurface label="Loading Props" />}><PropsV2Panel lane="PROP" /></Suspense>}
                {active === 'PrizePicks' && <Suspense fallback={<LoadingSurface label="Loading PrizePicks" />}><PropsV2Panel lane="PRIZEPICKS" /></Suspense>}
                {(active === 'Props' || active === 'PrizePicks') && (
                  <details className="group rounded-2xl border border-slate-200 bg-white p-3 shadow-soft md:p-4">
                    <summary className="flex min-h-10 cursor-pointer items-center justify-between gap-2 text-sm font-black text-blue-700">
                      See the complete NFL four-week player research
                      <ChevronRight size={17} className="shrink-0 transition-transform group-open:rotate-90" />
                    </summary>
                    <div className="mt-3 border-t border-slate-100 pt-3">
                      <Suspense fallback={<LoadingSurface label="Loading frozen NFL player-model research" />}>
                        <NFLPlayerPropResearchPanel lane={active === 'PrizePicks' ? 'PRIZEPICKS' : 'PROP'} />
                      </Suspense>
                    </div>
                  </details>
                )}
                {active === 'Tools' && <Suspense fallback={<LoadingSurface label="Loading pricing tools" />}><BetToolsPanel /></Suspense>}
                {active === 'Parlays' && <Suspense fallback={<LoadingSurface label="Loading Parlays" />}><ParlaysV2Panel /></Suspense>}
                {active === 'Bet Lab' && <Suspense fallback={<LoadingSurface label="Loading Bet Lab" />}><PracticeBetting /></Suspense>}
              </>
            )}

            {active === 'Fantasy' && <FantasyCommercialPanel />}
            {active === 'Survivor' && <SurvivorCommercialPanel />}
            {active === 'News & Insights' && <NewsInsightsPanel />}
            {active === 'Brain Record' && <Suspense fallback={<LoadingSurface label="Loading Brain Record" />}><PerformancePanel /></Suspense>}

            {active === 'Research' && <Suspense fallback={<LoadingSurface label="Loading Research Lab" />}><ResearchLab /></Suspense>}
          </>
        )}
      </main>

      {(active === 'Home' || active === 'News & Insights') && !assistantOpen && (
        <Suspense fallback={null}>
          <ZenithRefCompanion
            page={active}
            onOpenAsk={() => setAssistantOpen(true)}
            onOpenBrain={() => navigate('Brain Record')}
          />
        </Suspense>
      )}

      {!assistantOpen && !isAsk && active !== 'Home' && active !== 'News & Insights' && (
        <Suspense fallback={null}>
          <AssistantLauncher onClick={() => setAssistantOpen(true)} />
        </Suspense>
      )}

      {assistantOpen && !isAsk && (
        <Suspense fallback={null}>
          <AssistantDrawer
            active
            onClose={() => setAssistantOpen(false)}
            onOpenFull={() => navigate('Ask')}
            page={active}
            gameContext={gameScoutContext}
          />
        </Suspense>
      )}

      {moreOpen && (
        <div className="fixed inset-0 z-50 flex items-end bg-slate-950/30 lg:hidden" onClick={() => setMoreOpen(false)}>
          <div role="dialog" aria-modal="true" aria-label="More navigation" onClick={(event) => event.stopPropagation()} className="w-full rounded-t-[30px] bg-slate-50 p-5 pb-[calc(5.5rem+env(safe-area-inset-bottom))] shadow-2xl">
            <div className="mx-auto mb-5 h-1.5 w-12 rounded-full bg-slate-300" />
            <div className="mb-4 text-lg font-black text-slate-950">More</div>
            <MoreMenu onNavigate={navigate} onClose={() => setMoreOpen(false)} />
          </div>
        </div>
      )}

      <MobileBottomNav active={active} onNavigate={navigate} />

      <footer className={active === 'Home' ? 'border-t-2 border-[#173E52] bg-[#FFF1DB]' : 'border-t border-slate-200 bg-white'}>
        <div className="mx-auto flex max-w-[1500px] flex-col gap-2 px-5 py-6 text-sm font-semibold text-[#506B75] sm:flex-row sm:items-center sm:justify-between">
          <span>{PUBLIC_BRAND} · {PUBLIC_TAGLINE}</span>
          <span>Real data · Unknown stays UNKNOWN · Stale stays STALE</span>
        </div>
      </footer>
    </div>
  )
}
