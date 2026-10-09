import React, { useEffect, useMemo, useState } from 'react'
import { CalendarDays, ChevronDown, Database } from 'lucide-react'
import { nflUpcomingSchedule } from '../best_bets_market_availability.js'
import { describeQuote, sourceResearchForGame } from '../nfl_research_source_display.js'

const MARKETS = ['MONEYLINE', 'SPREAD', 'TOTAL']
const LABELS = { MONEYLINE: 'Moneyline', SPREAD: 'Spread', TOTAL: 'Game total' }

const localDate = value => {
  const time = Date.parse(value || '')
  if (!Number.isFinite(time)) return 'Time unverified'
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric',
    minute: '2-digit', timeZone: 'America/New_York', timeZoneName: 'short',
  }).format(time)
}

function Fixture({ game, market, reference }) {
  const available = reference ? (market === 'ALL' ? MARKETS : [market])
    .filter(m => Boolean(reference.markets[m])) : []
  return (
    <div className="min-w-0 rounded-xl border border-slate-200 px-3 py-2.5">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-xs font-black text-slate-900">
            {game.away_abbr || game.away} @ {game.home_abbr || game.home}
          </div>
          <div className="mt-0.5 text-[11px] text-slate-500">{localDate(game.start_time)}</div>
        </div>
        <span className={'shrink-0 text-right text-[10px] font-bold ' +
          (available.length ? 'text-blue-700' : 'text-amber-700')}>
          {available.length ? 'Research quote' : 'Quote unavailable'}
        </span>
      </div>
      {available.length > 0 && (
        <details className="group mt-2 border-t border-slate-100 pt-2 text-xs">
          <summary className="flex min-h-8 cursor-pointer items-center justify-between gap-2 font-black text-blue-700">
            View dated sportsbook references
            <ChevronDown size={15} className="shrink-0 transition-transform group-open:rotate-180"/>
          </summary>
          <div className="space-y-2 pb-1 pt-1">
            {available.map(m => {
              const q = reference.markets[m]
              return <div className="rounded-lg bg-slate-50 px-2.5 py-2" key={m}>
                <div className="text-[10px] font-black uppercase tracking-wider text-slate-500">{LABELS[m]}</div>
                <div className="mt-0.5 break-words font-semibold text-slate-800">{describeQuote(reference, m)}</div>
                <div className="mt-0.5 break-words text-[10px] text-slate-500">
                  {q.book} · source updated {localDate(q.source_updated_at)}
                </div>
              </div>
            })}
            <p className="text-[10px] leading-4 text-slate-500">
              Archived, paired research quotes only. Neither primary/main lines nor current executable offers are verified.
            </p>
          </div>
        </details>
      )}
    </div>
  )
}

export default function NFLBookResearch({ nflScores, market = 'ALL' }) {
  const [source, setSource] = useState(null)
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    let cancelled = false
    const refresh = async () => {
      try {
        const response = await fetch('/nfl_research_book_refs.json?ts=' + Date.now(), { cache: 'no-store' })
        const next = response.ok ? await response.json() : null
        if (!cancelled) setSource(next)
      } catch {
        if (!cancelled) setSource(null)
      }
      if (!cancelled) setNow(Date.now())
    }
    refresh()
    const handle = setInterval(refresh, 5 * 60 * 1000)
    return () => { cancelled = true; clearInterval(handle) }
  }, [])

  const games = useMemo(() => nflUpcomingSchedule(nflScores, now, 15), [nflScores, now])
  const refs = useMemo(() => games.map(game => {
    const reference = sourceResearchForGame(source, game, now)
    const shown = reference && (market === 'ALL' || reference.markets[market]) ? reference : null
    return { game, reference: shown }
  }), [games, market, source, now])
  const count = refs.filter(item => item.reference).length
  const preview = refs.slice(0, 4)
  const rest = refs.slice(4)
  return (
    <div className="mt-3 border-t border-slate-100 pt-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs font-black text-slate-900">
          <CalendarDays size={15} className="text-blue-700" />
          Upcoming NFL games · no betting recommendations
        </div>
        <span className="text-[10px] text-slate-500">
          {count} of {games.length} games with source-matched research quotes
        </span>
      </div>
      <div className="mt-2 flex items-start gap-2 rounded-lg bg-slate-50 p-2.5 text-[11px] leading-4 text-slate-600">
        <Database size={15} className="mt-0.5 shrink-0 text-blue-700"/>
        <p>
          Secondary sportsbook quotes can be viewed when their original event, both quoted sides,
          source timestamp and official kickoff agree. These dated snapshots are not live odds,
          verified main lines or profitable picks. The primary NFL source is still blocked separately.
        </p>
      </div>
      {preview.length > 0 ? (
        <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
          {preview.map(({ game, reference }) => (
            <Fixture key={game.event_id} game={game} market={market} reference={reference} />
          ))}
        </div>
      ) : <p className="mt-2 text-xs text-slate-500">No upcoming verified NFL fixtures are available.</p>}
      {rest.length > 0 && (
        <details className="mt-2">
          <summary className="cursor-pointer py-2 text-xs font-black text-blue-700">
            See {rest.length} more scheduled games
          </summary>
          <div className="mt-1 grid gap-1.5 sm:grid-cols-2">
            {rest.map(({ game, reference }) => (
              <Fixture key={game.event_id} game={game} market={market} reference={reference} />
            ))}
          </div>
        </details>
      )}
    </div>
  )
}
