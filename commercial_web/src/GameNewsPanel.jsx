import React, { useEffect, useMemo, useState } from 'react'
import { Activity, AlertTriangle, ExternalLink, Newspaper, ShieldCheck } from 'lucide-react'

const compact = value => String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '')

const teamTerms = (game, side) => {
  const prefix = side === 'AWAY' ? 'away' : 'home'
  const full = String(game?.[prefix] || '').trim()
  const abbr = String(game?.[`${prefix}_abbr`] || '').trim()
  const last = full.split(/\s+/).filter(Boolean).at(-1) || ''
  return [full, abbr, last]
    .map(value => String(value || '').trim())
    .filter(value => value.length >= 2)
}

const exactTeamMatch = (value, game, side) => {
  const token = compact(value)
  return Boolean(token && teamTerms(game, side).some(term => compact(term) === token))
}

const textHasTeam = (text, game, side) => {
  const hay = String(text || '').toLowerCase()
  return teamTerms(game, side).some(term => {
    const needle = String(term || '').toLowerCase()
    if (needle.length < 3) return false
    return hay.includes(needle)
  })
}

const numericId = value => {
  if (value == null || value === '') return ''
  const number = Number(value)
  return Number.isFinite(number) ? String(Math.trunc(number)) : String(value)
}

const publishedTime = row => {
  const value = row?.published_or_effective_at || row?.generated_at
  const time = value ? new Date(value).getTime() : 0
  return Number.isFinite(time) ? time : 0
}

const impactTypes = new Set([
  'INJURY',
  'TRANSACTION',
  'LINEUP_ROLE',
  'DEPTH_CHART',
  'PROBABLE_PITCHER',
  'STARTER',
  'FANTASY',
  'RECAP',
])

function sourceLabel(row) {
  const tier = String(row?.source_tier || '').toUpperCase()
  const verified = String(row?.verified_status || '').toUpperCase()
  if (tier.includes('OFFICIAL') || verified.includes('OFFICIAL')) return 'OFFICIAL'
  if (verified.includes('ATTRIBUTED') || tier.includes('EXTERNAL_NEWS')) return 'ATTRIBUTED'
  return 'SOURCE LINKED'
}

function sourceTone(label) {
  if (label === 'OFFICIAL') return 'border-emerald-200 bg-emerald-50 text-emerald-700'
  if (label === 'ATTRIBUTED') return 'border-blue-200 bg-blue-50 text-blue-700'
  return 'border-slate-200 bg-slate-100 text-slate-600'
}

function matchBasis(row, links, game) {
  const gameId = numericId(game?.event_id ?? game?.gamePk)
  const rowGameId = numericId(row?.game_event_id)
  if (rowGameId) {
    if (gameId && gameId === rowGameId) return { rank: 3, label: 'DIRECT GAME' }
    return null
  }

  const linked = links.get(String(row?.event_node_id || '')) || []
  const awayLinked = linked.some(link =>
    exactTeamMatch(link.entity_team, game, 'AWAY')
    || (String(link.entity_type).toUpperCase() === 'TEAM' && exactTeamMatch(link.entity_name, game, 'AWAY'))
  )
  const homeLinked = linked.some(link =>
    exactTeamMatch(link.entity_team, game, 'HOME')
    || (String(link.entity_type).toUpperCase() === 'TEAM' && exactTeamMatch(link.entity_name, game, 'HOME'))
  )

  const combinedText = `${row?.title || ''} ${row?.detail || ''}`
  const awayText = textHasTeam(combinedText, game, 'AWAY')
  const homeText = textHasTeam(combinedText, game, 'HOME')

  if ((awayLinked && homeLinked) || (awayText && homeText)) {
    return { rank: 2, label: 'MATCHUP' }
  }

  const type = String(row?.event_type || '').toUpperCase()
  const oneTeamLinked = awayLinked || homeLinked
  const oneTeamText = awayText || homeText
  if ((oneTeamLinked || oneTeamText) && impactTypes.has(type)) {
    return { rank: 1, label: 'TEAM IMPACT' }
  }

  return null
}

const formatTime = value => {
  if (!value) return 'Time unavailable'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Time unavailable'
  return date.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function NewsCard({ row, basis }) {
  const provenance = sourceLabel(row)
  const isInjury = String(row.event_type || '').toUpperCase() === 'INJURY'

  return (
    <article className="min-w-0 max-w-full overflow-hidden rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full border px-2.5 py-1 text-[10px] font-black ${basis.rank === 3 ? 'border-violet-200 bg-violet-50 text-violet-700' : basis.rank === 2 ? 'border-blue-200 bg-blue-50 text-blue-700' : 'border-amber-200 bg-amber-50 text-amber-700'}`}>
          {basis.label}
        </span>
        <span className={`rounded-full border px-2.5 py-1 text-[10px] font-black ${sourceTone(provenance)}`}>
          {provenance}
        </span>
        {isInjury && <span className="rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-[10px] font-black text-rose-700">INJURY</span>}
      </div>

      <h3 className="mt-3 text-lg font-black leading-6 text-slate-950">{row.title || 'Game update'}</h3>
      {row.detail && <p className="mt-2 text-sm leading-6 text-slate-600">{row.detail}</p>}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
        <div className="text-[11px] font-semibold text-slate-400">
          {row.source || 'Source unavailable'} · {formatTime(row.published_or_effective_at)}
        </div>
        {row.source_url && (
          <a
            href={row.source_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-black text-blue-700"
          >
            Read source <ExternalLink size={14} />
          </a>
        )}
      </div>
    </article>
  )
}


export default function GameNewsPanel({ game, league }) {
  const [state, setState] = useState({
    loading: true,
    graph: { news_events: [], entity_links: [] },
    error: '',
  })

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      setState(current => ({ ...current, loading: true, error: '' }))
      try {
        const response = await fetch(`/ask_retrieval.json?ts=${Date.now()}`, { cache: 'no-store' })
        if (!response.ok) throw new Error('Current game news is unavailable')
        const graph = await response.json()
        if (!cancelled) setState({ loading: false, graph, error: '' })
      } catch (error) {
        if (!cancelled) {
          setState({
            loading: false,
            graph: { news_events: [], entity_links: [] },
            error: error?.message || 'Current game news is unavailable',
          })
        }
      }
    }

    load()
    return () => { cancelled = true }
  }, [game?.event_id, game?.gamePk, league])

  const matched = useMemo(() => {
    const links = new Map()
    for (const link of state.graph?.entity_links || []) {
      const key = String(link.event_node_id || '')
      if (!key) continue
      if (!links.has(key)) links.set(key, [])
      links.get(key).push(link)
    }

    const sport = String(league || '').toUpperCase()
    const rows = []

    for (const row of state.graph?.news_events || []) {
      if (String(row.sport || '').toUpperCase() !== sport) continue
      const basis = matchBasis(row, links, game)
      if (!basis) continue
      rows.push({ row, basis })
    }

    const seen = new Set()
    return rows
      .sort((a, b) => b.basis.rank - a.basis.rank || publishedTime(b.row) - publishedTime(a.row))
      .filter(item => {
        const key = String(item.row.event_node_id || item.row.source_record_id || item.row.title || '')
        if (!key || seen.has(key)) return false
        seen.add(key)
        return true
      })
      .slice(0, 12)
  }, [state.graph, game, league])

  if (state.loading) {
    return (
      <div role="status" className="flex items-center gap-3 rounded-3xl border border-slate-200 bg-white p-6 text-sm font-black text-slate-600">
        <Activity size={17} className="animate-pulse text-blue-600" /> Loading game news…
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

  if (!matched.length) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-200 bg-white p-6">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
          <ShieldCheck size={20} />
        </div>
        <h3 className="mt-4 text-xl font-black text-slate-950">No matchup-specific news is attached right now</h3>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Sports Zenith did not find a direct game item, a two-team matchup item, or a verified team-impact item that can be tied to this game. Generic league stories stay out of this tab.
        </p>
      </div>
    )
  }

  const direct = matched.filter(item => item.basis.rank === 3).length
  const matchup = matched.filter(item => item.basis.rank === 2).length
  const impact = matched.filter(item => item.basis.rank === 1).length

  return (
    <div className="min-w-0 max-w-full space-y-5 overflow-hidden">
      <section className="rounded-3xl border border-blue-100 bg-blue-50/70 p-5">
        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.14em] text-blue-700">
          <Newspaper size={15} /> Game news & impact
        </div>
        <h3 className="mt-2 text-xl font-black text-slate-950">Only context tied to this matchup</h3>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          {matched.length} relevant item{matched.length === 1 ? '' : 's'} · {direct} direct game · {matchup} matchup · {impact} team impact. Source attribution stays visible on every item.
        </p>
      </section>

      <div className="grid min-w-0 max-w-full gap-4 lg:grid-cols-2">
        {matched.map(({ row, basis }) => (
          <NewsCard
            key={String(row.event_node_id || row.source_record_id || row.title)}
            row={row}
            basis={basis}
          />
        ))}
      </div>
    </div>
  )
}
