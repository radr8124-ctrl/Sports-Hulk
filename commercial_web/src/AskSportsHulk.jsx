import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity, AlertTriangle, BarChart3, Bot, Brain, ChevronRight,
  MessageCircle, Send, ShieldCheck, Sparkles, Target, ThumbsDown, ThumbsUp, Trophy, Users, X, Zap,
} from 'lucide-react'
import { useAuth } from './AuthShell'

const quickPrompts = [
  ['Start / Sit', 'Who should I start this week?'],
  ['Survivor Pick', 'What Survivor team should I use?'],
  ['Live Scores', 'What are the live NFL scores?'],
  ['Waiver Adds', 'Who are the top waiver adds?'],
  ['Best Bet', 'What is the best NFL bet right now?'],
  ['Player News', 'What player news matters today?'],
]

function tone(confidence = '') {
  const value = String(confidence).toUpperCase()
  if (value.includes('TOP') || value.includes('STRONG') || value.includes('VERIFIED')) {
    return 'border-emerald-400/40 bg-emerald-400/10 text-emerald-300'
  }
  if (value.includes('WAIT') || value.includes('UNKNOWN')) {
    return 'border-amber-400/40 bg-amber-400/10 text-amber-200'
  }
  return 'border-sky-400/40 bg-sky-400/10 text-sky-200'
}

function relativeTime(value) {
  if (!value) return '—'
  try {
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return '—'
    return d.toLocaleString()
  } catch {
    return '—'
  }
}

function safeSourceUrl(value) {
  try {
    const url = new URL(String(value || ''))
    return ['http:', 'https:'].includes(url.protocol) ? url.toString() : null
  } catch {
    return null
  }
}

function AskCard({ answer, compact = false }) {
  const [feedback, setFeedback] = useState('')
  const [feedbackBusy, setFeedbackBusy] = useState(false)
  if (!answer) return null

  const sendFeedback = async (rating) => {
    if (feedbackBusy || feedback) return
    setFeedbackBusy(true)
    try {
      const response = await fetch('/api/ask/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rating,
          answer_generated_at: answer.generated_at,
          intent: answer.intent,
          status: answer.status,
          confidence: answer.confidence,
          page: answer.context?.page,
        }),
      })
      if (!response.ok) throw new Error('Feedback unavailable')
      setFeedback(rating)
    } catch {
      setFeedback('ERROR')
    } finally {
      setFeedbackBusy(false)
    }
  }

  return (
    <div className={`rounded-3xl border border-emerald-400/20 bg-slate-950/80 shadow-2xl shadow-emerald-950/20 ${compact ? 'p-4' : 'p-5 md:p-6'}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-emerald-300">
            <Sparkles size={15} /> ANALYST TAKE
          </div>
          <div className={`mt-2 font-black tracking-tight text-white ${compact ? 'text-lg' : 'text-2xl'}`}>
            {answer.take || 'No current take.'}
          </div>
        </div>
        <span className={`rounded-full border px-3 py-1.5 text-[11px] font-black uppercase tracking-wide ${tone(answer.confidence)}`}>
          {answer.confidence || answer.status || 'RESEARCH'}
        </span>
      </div>

      {!!answer.why?.length && (
        <div className="mt-5">
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-emerald-300">
            <Zap size={14} /> Why
          </div>
          <ul className="mt-2 space-y-1.5 text-sm leading-6 text-slate-200">
            {answer.why.map((item, i) => <li key={i}>• {item}</li>)}
          </ul>
        </div>
      )}

      {!!answer.risk?.length && (
        <div className="mt-4 rounded-2xl border border-amber-400/15 bg-amber-400/5 p-3">
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-amber-300">
            <AlertTriangle size={14} /> Risk
          </div>
          <ul className="mt-2 space-y-1.5 text-sm leading-5 text-slate-300">
            {answer.risk.map((item, i) => <li key={i}>• {item}</li>)}
          </ul>
        </div>
      )}

      {!!answer.cards?.length && !compact && (
        <div className="mt-5 grid gap-2 md:grid-cols-2">
          {answer.cards.slice(0, 6).map((card, i) => (
            <div key={i} className="rounded-2xl border border-white/10 bg-white/5 p-3">
              <div className="text-xs font-black uppercase tracking-wide text-slate-500">
                {String(card.type || answer.intent || 'research').replaceAll('_', ' ')}
              </div>
              <div className="mt-1 text-sm font-extrabold text-white">{card.title || card.selection || 'Research'}</div>
              <div className="mt-1 text-xs leading-5 text-slate-400">
                {card.selection ? `${card.market || ''} · ${card.selection} ${card.line ?? ''}` :
                 card.side ? `${card.side} ${card.line ?? ''} · ${card.market || ''}` :
                 card.opponent ? `vs ${card.opponent}` :
                 card.projection != null ? `${card.projection} proj · $${card.salary ?? '—'}` :
                 card.source || ''}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-5 border-t border-white/10 pt-3">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="mr-1 text-[11px] font-bold text-slate-500">Was this helpful?</span>
          <button
            type="button"
            onClick={() => sendFeedback('HELPFUL')}
            disabled={feedbackBusy || Boolean(feedback)}
            className={`inline-flex min-h-9 items-center gap-1.5 rounded-xl border px-3 text-[11px] font-black transition ${feedback === 'HELPFUL' ? 'border-emerald-400/40 bg-emerald-400/10 text-emerald-300' : 'border-white/10 text-slate-400 hover:border-emerald-400/30 hover:text-emerald-300'} disabled:cursor-default`}
          >
            <ThumbsUp size={13} /> Helpful
          </button>
          <button
            type="button"
            onClick={() => sendFeedback('NEEDS_WORK')}
            disabled={feedbackBusy || Boolean(feedback)}
            className={`inline-flex min-h-9 items-center gap-1.5 rounded-xl border px-3 text-[11px] font-black transition ${feedback === 'NEEDS_WORK' ? 'border-amber-400/40 bg-amber-400/10 text-amber-200' : 'border-white/10 text-slate-400 hover:border-amber-400/30 hover:text-amber-200'} disabled:cursor-default`}
          >
            <ThumbsDown size={13} /> Needs work
          </button>
          {feedback === 'ERROR' && <span className="text-[11px] font-semibold text-amber-300">Feedback could not be saved.</span>}
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] font-semibold text-slate-500">
          {!!answer.sources?.length && (
            <span className="flex flex-wrap items-center gap-x-1.5 gap-y-1">
              <span>Sources:</span>
              {answer.sources.slice(0, 3).map((source, index) => {
                const label = source.source || source.label || `Source ${index + 1}`
                const href = safeSourceUrl(source.url)
                const trackSourceClick = () => {
                  fetch('/api/ask/source-click', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      url: href,
                      source_label: label,
                      answer_generated_at: answer.generated_at,
                      intent: answer.intent,
                      status: answer.status,
                      page: answer.context?.page,
                    }),
                    keepalive: true,
                  }).catch(() => {})
                }
                return href ? (
                  <a
                    key={`${label}-${href}`}
                    href={href}
                    target="_blank"
                    rel="noreferrer noopener"
                    onClick={trackSourceClick}
                    className="font-black text-sky-300 underline decoration-sky-400/40 underline-offset-2 hover:text-sky-200"
                  >
                    {label}
                  </a>
                ) : <span key={`${label}-${index}`}>{label}</span>
              })}
            </span>
          )}
          <span>Updated: {relativeTime(answer.updated_at || answer.generated_at)}</span>
        </div>
      </div>
    </div>
  )
}

function LiveRail() {
  const [scores, setScores] = useState({ games: [] })
  const [bets, setBets] = useState({ summary: {}, picks: [] })
  const [askContext, setAskContext] = useState({ datasets: {} })

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const [s, b, a] = await Promise.all([
          fetch(`/nfl_scores.json?ts=${Date.now()}`, { cache: 'no-store' }),
          fetch(`/betting_v2_all_markets_current.json?ts=${Date.now()}`, { cache: 'no-store' }),
          fetch(`/ask_context.json?ts=${Date.now()}`, { cache: 'no-store' }),
        ])
        const [sj, bj, aj] = await Promise.all([
          s.ok ? s.json() : { games: [] },
          b.ok ? b.json() : { summary: {}, picks: [] },
          a.ok ? a.json() : { datasets: {} },
        ])
        if (!cancelled) {
          setScores(sj)
          setBets(bj)
          setAskContext(aj)
        }
      } catch {
        if (!cancelled) {
          setScores({ games: [] })
          setBets({ summary: {}, picks: [] })
          setAskContext({ datasets: {} })
        }
      }
    }
    load()
    const timer = window.setInterval(load, 30000)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [])

  const games = (scores.games || []).slice(0, 4)
  const plays = [...(bets.picks || [])]
    .filter(row => row.shadow_decision === 'SHADOW_PLAY')
    .sort((a, b) => Number(b.conservative_expected_value_pct || -999) - Number(a.conservative_expected_value_pct || -999))
  const best = plays[0] || null
  const dfs = [...(askContext.datasets?.dfs || [])]
    .filter(x => String(x.platform).toUpperCase() === 'DRAFTKINGS' && x.projected_fantasy_points != null)
    .sort((a, b) => Number(b.projected_fantasy_points || 0) - Number(a.projected_fantasy_points || 0))
    .slice(0, 5)

  return (
    <div className="space-y-3">
      <div className="rounded-3xl border border-white/10 bg-slate-950/85 p-4">
        <div className="flex items-center justify-between">
          <div className="text-sm font-black text-white">Live Scores</div>
          <Activity size={16} className="text-emerald-400" />
        </div>
        <div className="mt-3 space-y-2">
          {games.length ? games.map(game => (
            <div key={game.event_id} className="rounded-xl bg-white/5 px-3 py-2">
              <div className="flex justify-between text-xs font-bold text-slate-300">
                <span>{game.away_abbr} {game.away_score ?? '—'}</span>
                <span>{game.home_abbr} {game.home_score ?? '—'}</span>
              </div>
              <div className="mt-1 text-[10px] font-bold text-slate-500">{game.live ? 'LIVE' : game.final ? 'FINAL' : game.status}</div>
            </div>
          )) : <div className="text-xs text-slate-500">No active NFL score snapshot.</div>}
        </div>
      </div>

      <div className="rounded-3xl border border-white/10 bg-slate-950/85 p-4">
        <div className="flex items-center gap-2 text-sm font-black text-white"><BarChart3 size={16} className="text-sky-400" /> Top Player Projections</div>
        <div className="mt-3 space-y-2">
          {dfs.length ? dfs.map((p, i) => (
            <div key={p.player_key || p.player} className="flex items-center justify-between gap-3 text-xs">
              <div className="min-w-0"><span className="mr-2 text-slate-600">{i + 1}</span><span className="font-extrabold text-slate-200">{p.player}</span></div>
              <div className="shrink-0 font-black text-emerald-300">{p.projected_fantasy_points}</div>
            </div>
          )) : <div className="text-xs text-slate-500">Projection feed waiting.</div>}
        </div>
      </div>

      <div className="rounded-3xl border border-emerald-400/20 bg-emerald-400/5 p-4">
        <div className="flex items-center gap-2 text-sm font-black text-white"><Target size={16} className="text-emerald-400" /> Best Bet Gate</div>
        {best ? (
          <div className="mt-3">
            <div className="text-lg font-black text-white">{best.selection} · {String(best.market || '').replaceAll('_',' ')}</div>
            <div className="mt-1 text-xs text-slate-400">V2 PLAY · model {best.calibrated_win_probability_pct ?? '—'}% · market {best.market_reference_probability_pct ?? '—'}%</div>
          </div>
        ) : (
          <div className="mt-3">
            <div className="text-base font-black text-white">No proven PLAY right now</div>
            <div className="mt-1 text-xs leading-5 text-slate-400">{bets.summary?.candidates ?? 0} current candidates checked · PASS is a valid decision.</div>
          </div>
        )}
      </div>
    </div>
  )
}

function activeFantasyLeagueId() {
  try { return window.localStorage.getItem('sports-zenith-active-fantasy-league') || null }
  catch { return null }
}

async function askQuestion(question, context = {}, accessToken = null) {
  const headers = { 'Content-Type': 'application/json' }
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`

  const response = await fetch('/api/ask', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      question,
      context: {
        ...context,
        fantasy_league_id: context.fantasy_league_id || activeFantasyLeagueId(),
      },
    }),
  })
  if (!response.ok) throw new Error('The sports analyst is unavailable')
  return response.json()
}

export function AskSportsHulkPage() {
  const { user, getAccessToken } = useAuth()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = async (question) => {
    const q = String(question || '').trim()
    if (!q || loading) return
    setMessages(prev => [...prev, { role: 'user', text: q }])
    setInput('')
    setLoading(true)
    try {
      const token = user ? await getAccessToken() : null
      const answer = await askQuestion(q, { page: 'Ask' }, token)
      setMessages(prev => [...prev, { role: 'assistant', answer }])
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', answer: {
        take: 'The sports analyst is temporarily unavailable.',
        confidence: 'WAITING',
        risk: [error.message],
        sources: [],
      }}])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-[30px] border border-slate-800 bg-[#061017] p-4 text-white shadow-2xl md:p-6">
      <div className="grid gap-5 xl:grid-cols-[1fr_320px]">
        <div className="min-w-0">
          <div className="rounded-3xl border border-emerald-400/20 bg-gradient-to-br from-slate-950 via-[#071821] to-[#071510] p-5 md:p-7">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-400/30 bg-emerald-400/10 text-emerald-300 shadow-lg shadow-emerald-950/30">
                <Brain size={25} />
              </div>
              <div>
                <div className="text-xs font-black uppercase tracking-[0.18em] text-emerald-300">Sports Intelligence Analyst</div>
                <h1 className="mt-1 text-3xl font-black tracking-tight md:text-4xl">Ask <span className="text-emerald-400">the Brain</span></h1>
                <p className="mt-1 text-sm text-slate-400">Live scores, fantasy, Survivor, props and betting intelligence.</p>
              </div>
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              {quickPrompts.map(([label, prompt]) => (
                <button key={label} onClick={() => send(prompt)} className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs font-extrabold text-slate-200 transition hover:border-emerald-400/40 hover:bg-emerald-400/10 hover:text-white">
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-4 max-h-[620px] space-y-4 overflow-y-auto pr-1">
            {!messages.length && (
              <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
                <div className="text-sm font-black text-white">Ask about scores, players, bets, Survivor, fantasy, DFS or news.</div>
                <div className="mt-2 text-sm leading-6 text-slate-400">Try a score, a player decision, a Survivor pick, the best current bet, a prop, a waiver add, a defense stream or a DFS question. UNKNOWN stays UNKNOWN.</div>
              </div>
            )}

            {messages.map((message, i) => message.role === 'user' ? (
              <div key={i} className="ml-auto max-w-[85%] rounded-3xl rounded-br-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-950/20">
                {message.text}
              </div>
            ) : (
              <AskCard key={i} answer={message.answer} />
            ))}

            {loading && (
              <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-bold text-slate-400">
                <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" /> Checking the current data…
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={(e) => { e.preventDefault(); send(input) }} className="mt-4 flex gap-2 rounded-2xl border border-white/10 bg-slate-950/90 p-2">
            <input value={input} onChange={e => setInput(e.target.value)} placeholder="Ask anything about sports…" className="min-w-0 flex-1 bg-transparent px-3 py-3 text-sm font-semibold text-white outline-none placeholder:text-slate-600" />
            <button disabled={loading || !input.trim()} className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-400 text-slate-950 transition hover:bg-emerald-300 disabled:opacity-40">
              <Send size={18} />
            </button>
          </form>
        </div>

        <LiveRail />
      </div>
    </div>
  )
}

export function AssistantDrawer({ active, onClose, onOpenFull, page = 'Home', gameContext = null }) {
  const { user, getAccessToken } = useAuth()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  if (!active) return null

  const send = async (question) => {
    const q = String(question || '').trim()
    if (!q || loading) return
    setMessages(prev => [...prev, { role: 'user', text: q }])
    setInput('')
    setLoading(true)
    try {
      const token = user ? await getAccessToken() : null
      const answer = await askQuestion(q, {
        page,
        game_context: gameContext || undefined,
      }, token)
      setMessages(prev => [...prev, { role: 'assistant', answer }])
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', answer: { take: 'Assistant unavailable.', confidence: 'WAITING', risk: [error.message] } }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/35 backdrop-blur-[2px]" onClick={onClose}>
      <div onClick={e => e.stopPropagation()} className="absolute bottom-4 right-4 top-4 flex w-[min(430px,calc(100vw-2rem))] flex-col rounded-[28px] border border-emerald-400/20 bg-[#071017] p-4 text-white shadow-2xl shadow-slate-950/50">
        <div className="flex items-center justify-between">
          <button onClick={onOpenFull} className="flex items-center gap-2 text-left">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-400/10 text-emerald-300"><Brain size={20} /></div>
            <div>
              <div className="font-black">Game Scout</div>
              <div className="text-[11px] font-semibold text-slate-500">
                {gameContext?.surface === 'GAME_CENTER'
                  ? `${gameContext.league} · ${gameContext.away || gameContext.away_abbr} @ ${gameContext.home || gameContext.home_abbr}`
                  : `Context: ${page}`}
              </div>
            </div>
          </button>
          <button onClick={onClose} className="rounded-xl p-2 text-slate-400 hover:bg-white/5 hover:text-white"><X size={18} /></button>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {quickPrompts.slice(0, 4).map(([label, prompt]) => (
            <button key={label} onClick={() => send(prompt)} className="rounded-full border border-white/10 px-2.5 py-1.5 text-[11px] font-black text-slate-300 hover:border-emerald-400/40">{label}</button>
          ))}
        </div>

        <div className="mt-4 flex-1 space-y-3 overflow-y-auto">
          {!messages.length && <div className="rounded-2xl bg-white/5 p-4 text-sm leading-6 text-slate-400">Ask about the current page, a player, a bet, Survivor, waivers or a score.</div>}
          {messages.map((m, i) => m.role === 'user'
            ? <div key={i} className="ml-auto max-w-[88%] rounded-2xl rounded-br-md bg-blue-600 px-3 py-2 text-sm font-semibold">{m.text}</div>
            : <AskCard key={i} answer={m.answer} compact />
          )}
          {loading && <div className="text-xs font-bold text-emerald-300">Checking current data…</div>}
        </div>

        <form onSubmit={(e) => { e.preventDefault(); send(input) }} className="mt-3 flex gap-2 rounded-2xl border border-white/10 bg-slate-950 p-2">
          <input value={input} onChange={e => setInput(e.target.value)} placeholder="Ask anything…" className="min-w-0 flex-1 bg-transparent px-2 py-2 text-sm outline-none placeholder:text-slate-600" />
          <button disabled={loading || !input.trim()} className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-400 text-slate-950 disabled:opacity-40"><Send size={16} /></button>
        </form>
      </div>
    </div>
  )
}

export function AssistantLauncher({ onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Open Game Scout"
      title="Game Scout"
      className="fixed bottom-5 right-5 z-40 hidden items-center md:flex gap-3 rounded-[22px] border border-emerald-300/30 bg-slate-950 p-2.5 pr-3 text-white shadow-2xl shadow-emerald-950/30 transition hover:-translate-y-1 hover:border-emerald-300/60"
    >
      <span className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-emerald-300/30 bg-gradient-to-br from-emerald-400/20 via-sky-400/10 to-violet-400/20">
        <Bot size={26} className="text-emerald-300" />
        <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full border border-slate-950 bg-emerald-400 text-slate-950">
          <Sparkles size={11} />
        </span>
        <span className="absolute -bottom-0.5 left-1/2 h-1.5 w-5 -translate-x-1/2 rounded-full bg-emerald-300/70" />
      </span>
      <span className="hidden text-left sm:block">
        <span className="block text-[10px] font-black uppercase tracking-[0.16em] text-emerald-300">Sports Zenith</span>
        <span className="mt-0.5 block text-sm font-black">Game Scout</span>
      </span>
    </button>
  )
}
