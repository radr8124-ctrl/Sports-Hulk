import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity, AlertTriangle, BarChart3, Bot, Brain, ChevronRight,
  MessageCircle, Send, ShieldCheck, Sparkles, Target, ThumbsDown, ThumbsUp, Trophy, Users, X, Zap,
} from 'lucide-react'
import { useAuth } from './AuthShell'
import { claimEvidenceRows } from './claimEvidence'
import ZenithRefAvatar from './ZenithRefAvatar'
import RefSignalDesk from './RefSignalDesk'
import {refereeQuickPrompts} from '../ref_market_review.js'

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

function AskCard({ answer, compact = false, onFollowUp = null }) {
  const [feedback, setFeedback] = useState('')
  const [feedbackBusy, setFeedbackBusy] = useState(false)
  if (!answer) return null
  const evidenceRows = claimEvidenceRows(answer.claim_sources, compact ? 2 : 4)

  const recordSourceClick = (label, href) => {
    if (!href) return
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
            <Sparkles size={15} /> ANALYST TAKE <span className="text-sky-300">· THE REF</span>
          </div>
          <div className={`mt-2 font-black tracking-tight text-white ${compact ? 'text-lg' : 'text-2xl'}`}>
            {answer.take || 'No current take.'}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full border px-3 py-1.5 text-[11px] font-black uppercase tracking-wide ${tone(answer.confidence)}`}>
            {answer.confidence || 'RESEARCH'}
          </span>
          {!!answer.status && (
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-black uppercase tracking-wide text-slate-400">
              {String(answer.status).replaceAll('_', ' ')}
            </span>
          )}
        </div>
      </div>

      {answer.personalization?.status === 'OPT_IN' && (
        <div className="mt-4 rounded-2xl border border-sky-400/15 bg-sky-400/5 px-3 py-2.5 text-xs leading-5 text-slate-300">
          <span className="font-black text-sky-300">Personalized:</span>{' '}
          {[
            ...(answer.personalization.matched_watched_players || []).map(name => `watching ${name}`),
            ...(answer.personalization.matched_favorite_teams || []).map(name => `favorite team ${name}`),
            `risk style ${String(answer.personalization.risk_preference || 'BALANCED').toLowerCase()}`,
          ].join(' · ')}
          <span className="text-slate-500"> · model unchanged</span>
        </div>
      )}

      {!!answer.personalization?.watchlist_hits?.length && (
        <div className="mt-3 rounded-2xl border border-white/10 bg-white/5 p-3">
          <div className="text-[10px] font-black uppercase tracking-[0.14em] text-slate-500">Also on your watchlist</div>
          <div className="mt-2 space-y-2">
            {answer.personalization.watchlist_hits.slice(0, 3).map((item, index) => {
              const href = safeSourceUrl(item.url)
              return (
                <div key={`${item.title}-${index}`} className="text-xs leading-5 text-slate-300">
                  <span className="font-black text-sky-300">{item.matched_preference}</span>{' · '}
                  {href ? (
                    <a href={href} target="_blank" rel="noreferrer noopener" className="font-bold text-slate-200 underline decoration-slate-500/40 underline-offset-2 hover:text-white">
                      {item.title}
                    </a>
                  ) : (
                    <span className="font-bold text-slate-200">{item.title}</span>
                  )}
                  {item.source ? <span className="text-slate-500"> · {item.source}</span> : null}
                </div>
              )
            })}
          </div>
        </div>
      )}

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

      {!!evidenceRows.length && (
        <details className="mt-4 rounded-2xl border border-sky-400/15 bg-sky-400/5 p-3">
          <summary className="cursor-pointer list-none text-xs font-black uppercase tracking-[0.14em] text-sky-300">
            <span className="inline-flex items-center gap-2"><ShieldCheck size={14} /> Evidence · {evidenceRows.length} claim{evidenceRows.length === 1 ? '' : 's'}</span>
          </summary>
          <div className="mt-3 space-y-2">
            {evidenceRows.map((item, index) => {
              const href = safeSourceUrl(item.url)
              return (
                <div key={`${item.evidence_id || item.source}-${index}`} className="rounded-xl border border-white/10 bg-slate-950/30 px-3 py-2.5">
                  <div className="text-xs leading-5 text-slate-200">{item.claim}</div>
                  <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] font-bold text-slate-500">
                    {href ? (
                      <a
                        href={href}
                        target="_blank"
                        rel="noreferrer noopener"
                        onClick={() => recordSourceClick(item.source, href)}
                        className="font-black text-sky-300 underline decoration-sky-400/40 underline-offset-2 hover:text-sky-200"
                      >
                        {item.source}
                      </a>
                    ) : (
                      <span className="font-black text-sky-300">{item.source}</span>
                    )}
                    {item.evidence_type ? <span>{item.evidence_type}</span> : null}
                    {item.updated_at ? <span>{relativeTime(item.updated_at)}</span> : null}
                  </div>
                </div>
              )
            })}
          </div>
        </details>
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
              {card.type==='ref_market_research' && (
                <div className="mt-2 grid grid-cols-2 gap-2 rounded-xl border border-sky-400/15 bg-sky-400/[.06] p-2">
                  <div>
                    <span className="block text-[10px] font-bold text-slate-400">Book no-vig</span>
                    <span className="text-sm font-black text-white">{card.market_probability ?? '—'}%</span>
                  </div>
                  <div>
                    <span className="block text-[10px] font-bold text-slate-400">Zenith research</span>
                    <span className="text-sm font-black text-sky-200">{card.model_probability==null?'Unproven':card.model_probability+'%'}</span>
                  </div>
                  <p className="col-span-2 text-[10px] font-semibold leading-4 text-slate-400">
                    Observed {card.line} · {card.book} · no proven betting edge
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {!!answer.followups?.length && typeof onFollowUp==='function' && (
        <div className="mt-4 border-t border-white/10 pt-3">
          <p className="mb-2 text-[10px] font-black uppercase tracking-widest text-sky-300">Ask a follow-up</p>
          <div className="flex flex-wrap gap-2">
            {answer.followups.slice(0,compact?2:3).map((question,i)=>(
              <button key={i} type="button" onClick={()=>onFollowUp(question)}
                className="min-h-9 rounded-xl border border-sky-400/25 bg-sky-400/10 px-2.5 py-1.5 text-left text-xs font-bold text-sky-100 hover:border-sky-300/50 hover:bg-sky-400/20">
                {question}
              </button>
            ))}
          </div>
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
                return href ? (
                  <a
                    key={`${label}-${href}`}
                    href={href}
                    target="_blank"
                    rel="noreferrer noopener"
                    onClick={() => recordSourceClick(label, href)}
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

function compactSessionHistory(messages = []) {
  return messages.slice(-8).map(message => {
    if (message.role === 'user') {
      return { role: 'user', text: String(message.text || '').slice(0, 300) }
    }
    const answer = message.answer || {}
    return {
      role: 'assistant',
      answer: {
        intent: answer.intent || null,
        status: answer.status || null,
        confidence: answer.confidence || null,
        take: String(answer.take || '').slice(0, 300),
        cards: Array.isArray(answer.cards)
          ? answer.cards.slice(0, 4).map(card => ({
              type: card.type || null,
              title: card.title || null,
              position: card.position || null,
              team: card.team || null,
              league: card.league || null,
              away: card.away || null,
              home: card.home || null,
              opponent: card.opponent || null,
            }))
          : [],
      },
    }
  })
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
  const {user,getAccessToken}=useAuth()
  const [messages,setMessages]=useState([])
  const [input,setInput]=useState('')
  const [activeGame,setActiveGame]=useState(null)
  const [loading,setLoading]=useState(false)
  const conversationRef=useRef(null)
  const jumpToAnswerRef=useRef(false)

  useEffect(()=>{
    if(!messages.length)return
    const transcript=conversationRef.current
    if(transcript)transcript.scrollTop=transcript.scrollHeight
    // This movement is only after the person explicitly taps "Ask the Ref"
    // on a game card; never jump the page while mounting the Ask route.
    if(jumpToAnswerRef.current && transcript){
      transcript.scrollIntoView({behavior:'auto',block:'start'})
      jumpToAnswerRef.current=false
    }
  },[messages,loading])

  const send=async(question,gameContext=null)=>{
    const q=String(question||'').trim()
    if(!q||loading)return
    const scoped=gameContext||activeGame
    if(gameContext){
      setActiveGame(gameContext)
      jumpToAnswerRef.current=true
    }
    setMessages(prev=>[...prev,{role:'user',text:q}])
    setInput('')
    setLoading(true)
    try{
      const token=user?await getAccessToken():null
      const answer=await askQuestion(q,{
        page:'Ask',
        game_context:scoped||undefined,
        session_history:compactSessionHistory(messages),
      },token)
      setMessages(prev=>[...prev,{role:'assistant',answer}])
    }catch(error){
      setMessages(prev=>[...prev,{role:'assistant',answer:{
        take:'The Ref cannot complete this review from the connected sources right now.',
        confidence:'WAITING',status:'SOURCE_UNAVAILABLE',
        risk:[error.message],sources:[],
      }}])
    }finally{
      setLoading(false)
    }
  }

  const selectedLabel=activeGame
    ?[activeGame.away||'Away',activeGame.home||'Home'].join(' @ ')
    :null

  return <div className="rounded-[26px] border border-slate-800 bg-[#061222] p-3.5 text-white shadow-2xl md:p-6">
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_305px]">
      <div className="min-w-0">
        <header className="relative overflow-hidden rounded-2xl border border-sky-400/20 bg-gradient-to-br from-[#0C2742] via-[#071629] to-[#06101F] p-4 md:p-6">
          <div aria-hidden="true" className="pointer-events-none absolute -right-10 -top-16 h-44 w-44 rounded-full bg-sky-400/10 blur-3xl"/>
          <div className="relative flex items-center gap-3.5">
            <div className="relative shrink-0">
              <ZenithRefAvatar size={76}/>
              <span className="absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full border-2 border-[#081B30] bg-sky-400 text-slate-950">
                <ShieldCheck size={12}/>
              </span>
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-black uppercase tracking-[0.17em] text-sky-300">Meet The Ref · Zenith AI</p>
              <h1 className="mt-1 text-2xl font-black tracking-tight text-white sm:text-3xl">
                Ask <span className="text-sky-300">the Brain</span>
              </h1>
              <p className="mt-1 text-xs leading-5 text-slate-300">
                Get the call, then see the evidence. Odds, matchups, props and Survivor.
              </p>
            </div>
          </div>
          <div className="relative mt-3 flex flex-wrap gap-2 text-[10px] font-black">
            <span className="rounded-full border border-sky-300/20 bg-sky-400/10 px-2.5 py-1.5 text-sky-200">GAME INTELLIGENCE</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1.5 text-slate-300">REAL SOURCES · NO FAKE PICKS</span>
          </div>
          <div aria-label="Ask the Ref quick questions" className="relative mt-4 grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
            {refereeQuickPrompts('Ask',activeGame).map(([label,prompt])=>
              <button key={label} type="button" disabled={loading}
                onClick={()=>send(prompt)}
                className="min-h-10 rounded-xl border border-white/10 bg-white/[.07] px-3 py-2 text-left text-[11px] font-black leading-4 text-slate-200 transition hover:border-sky-400/40 hover:bg-sky-400/15 disabled:opacity-40">
                {label}
              </button>
            )}
          </div>
        </header>

        <form aria-label="Ask the Ref question" onSubmit={event=>{event.preventDefault();send(input)}}
          className="mt-3 flex gap-2 rounded-2xl border border-sky-400/20 bg-slate-950/95 p-2 shadow-lg">
          <input value={input} onChange={event=>setInput(event.target.value)}
            aria-label="Ask the Ref"
            placeholder="Ask about a game, odds, prop or Survivor…"
            className="min-h-11 min-w-0 flex-1 bg-transparent px-2.5 text-sm font-semibold text-white outline-none placeholder:text-slate-500"/>
          <button type="submit" disabled={loading||!input.trim()} aria-label="Send referee question"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-sky-400 text-slate-950 transition hover:bg-sky-300 disabled:opacity-40">
            <Send size={18}/>
          </button>
        </form>

        {selectedLabel&&<div className="mt-2 flex items-center justify-between gap-2 rounded-xl border border-sky-400/20 bg-sky-400/5 px-3 py-2 text-[11px]">
          <span className="min-w-0 truncate font-bold text-sky-200">Reviewing: {selectedLabel}</span>
          <button type="button" className="shrink-0 font-black text-slate-300 underline underline-offset-2"
            onClick={()=>setActiveGame(null)}>Clear matchup</button>
        </div>}

        <div ref={conversationRef} role="log" aria-label="Referee conversation"
          aria-live="polite"
          className={messages.length?'mt-3 max-h-[620px] space-y-3 overflow-y-auto rounded-2xl border border-white/10 bg-slate-950/60 p-3':'hidden'}>
          {messages.map((message,i)=>message.role==='user'
            ?<div key={i} className="ml-auto w-fit max-w-[91%] break-words rounded-2xl rounded-br-md bg-blue-600 px-3.5 py-2.5 text-sm font-semibold text-white">
              {message.text}
            </div>
            :<AskCard key={i} answer={message.answer} onFollowUp={send}/>
          )}
          {loading&&<div className="flex items-center gap-2 rounded-xl bg-white/5 px-3 py-2 text-xs font-bold text-slate-300">
            <span className="h-2 w-2 animate-pulse rounded-full bg-sky-400"/> The Ref is checking saved market evidence…
          </div>}
        </div>

        <div className="mt-3">
          <RefSignalDesk disabled={loading} onReview={(question,game)=>send(question,game)}/>
        </div>
      </div>
      <aside className="hidden xl:block"><LiveRail/></aside>
    </div>
  </div>
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
        session_history: compactSessionHistory(messages),
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
      <div onClick={e => e.stopPropagation()} role="dialog" aria-modal="true" aria-label="Ask the Ref on this page" className="absolute bottom-3 right-3 top-3 flex w-[min(430px,calc(100vw-1.5rem))] flex-col rounded-2xl border border-sky-400/20 bg-[#071526] p-3 text-white shadow-2xl shadow-slate-950/50 md:bottom-4 md:right-4 md:top-4 md:rounded-[28px] md:p-4">
        <div className="flex items-center justify-between">
          <button onClick={onOpenFull} className="flex items-center gap-2 text-left" title="Open full analyst">
            <ZenithRefAvatar size={44}/>
            <div>
              <div className="font-black text-sky-100">The Ref <span className="ml-1 text-[10px] font-bold text-sky-300">AI</span></div>
              <div className="text-[11px] font-semibold text-slate-500">
                {gameContext?.surface === 'GAME_CENTER'
                  ? `${gameContext.league} · ${gameContext.away || gameContext.away_abbr} @ ${gameContext.home || gameContext.home_abbr}`
                  : `Reviewing: ${page}`}
              </div>
            </div>
            <span className="mt-0.5 block text-[10px] font-bold text-sky-300">Open full analyst</span>
          </button>
          <button onClick={onClose} aria-label="Close the Ref chat" className="rounded-xl p-2 text-slate-400 hover:bg-white/5 hover:text-white"><X size={18} /></button>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {refereeQuickPrompts(page,gameContext).slice(0, 6).map(([label, prompt]) => (
            <button key={label} onClick={() => send(prompt)} className="rounded-full border border-white/10 px-2.5 py-1.5 text-[11px] font-black text-slate-300 hover:border-emerald-400/40">{label}</button>
          ))}
        </div>

        <div className="mt-4 flex-1 space-y-3 overflow-y-auto">
          {!messages.length && <div className="rounded-2xl bg-white/5 p-4 text-sm leading-6 text-slate-400">Ask about the current page, a player, a bet, Survivor, waivers or a score.</div>}
          {messages.map((m, i) => m.role === 'user'
            ? <div key={i} className="ml-auto max-w-[88%] rounded-2xl rounded-br-md bg-blue-600 px-3 py-2 text-sm font-semibold">{m.text}</div>
            : <AskCard key={i} answer={m.answer} compact onFollowUp={send} />
          )}
          {loading && <div className="text-xs font-bold text-emerald-300">Checking current data…</div>}
        </div>

        <form onSubmit={(e) => { e.preventDefault(); send(input) }} className="mt-3 flex gap-2 rounded-2xl border border-white/10 bg-slate-950 p-2">
          <input value={input} onChange={e => setInput(e.target.value)} placeholder="Ask the Ref about this page…" aria-label="Ask the Ref from this page" className="min-w-0 flex-1 bg-transparent px-2 py-2 text-sm outline-none placeholder:text-slate-600" />
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
      aria-label="Open the Ref sports assistant"
      title="The Ref — Zenith sports intelligence"
      className="fixed bottom-[calc(5.7rem+env(safe-area-inset-bottom))] right-3 z-40 flex items-center gap-3 rounded-2xl border border-sky-300/30 bg-slate-950 p-1.5 text-white shadow-xl shadow-slate-950/40 transition hover:border-sky-300/60 md:bottom-5 md:right-5 md:rounded-[22px] md:p-2 md:pr-3"
    >
      <span className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#0C2036] md:h-12 md:w-12">
        <ZenithRefAvatar size={48} compact/>
        <span className="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-slate-950 bg-sky-400"/>
      </span>
      <span className="hidden text-left sm:block">
        <span className="block text-[10px] font-black uppercase tracking-[0.16em] text-sky-300">Sports Zenith AI</span>
        <span className="mt-0.5 block text-sm font-black">The Ref</span>
      </span>
    </button>
  )
}
