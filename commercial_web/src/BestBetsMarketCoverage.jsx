import React from 'react'
import { AlertTriangle, ArrowUpRight, CalendarDays, Database, ShieldCheck } from 'lucide-react'
import { sourceMarketStatus, nflUpcomingSchedule } from '../best_bets_market_availability.js'

const humanMarket = { MONEYLINE: 'Moneyline', SPREAD: 'Point spread', TOTAL: 'Game total' }
const readableTime = value => {
  const time=Date.parse(value||'')
  if(!Number.isFinite(time))return 'Kickoff pending'
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute:'2-digit',
    timeZone: 'America/New_York', timeZoneName:'short',
  }).format(time)
}

function LaneStatus({ item }) {
  const enough = item.independent >= 25
  return (
    <div className="flex min-w-0 items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs">
      <span className="min-w-0 truncate font-black text-slate-800">{humanMarket[item.market] || item.market}</span>
      <div className="flex shrink-0 items-center gap-2 text-slate-500">
        <span>{item.independent}/{25} games</span>
        <span className={`font-black ${enough ? 'text-slate-700' : 'text-amber-700'}`}>
          {item.approvedPlayCount ? `${item.approvedPlayCount} paper qualifier` : 'No proven edge'}
        </span>
      </div>
    </div>
  )
}

// No odds, probabilities or model-generated winners are synthesized here.
// This panel surfaces evidence gaps plus independently sourced fixtures only.
export default function BestBetsMarketCoverage({ sport, market, currentData, priorBoard, nflScores }) {
  const proof=sourceMarketStatus({
    sport,market,picks:currentData?.picks||[],
    byProofLane:currentData?.by_proof_lane||{},
    marketBoard:priorBoard?.market_board||[],
  })
  const focused=proof.categories.filter(row => row.sport === (sport==='ALL'?'NFL':sport))
  const relevant=focused.filter(row => market==='ALL'||row.market===market)
  const summaryMarket = market==='ALL' ? 'current markets' : humanMarket[market]?.toLowerCase()||'current markets'
  const nfl=(sport==='NFL') ? nflUpcomingSchedule(nflScores,Date.now(),15) : []
  const preview=nfl.slice(0,4)
  const hidden=nfl.slice(4)
  const totalCandidates=(Array.isArray(currentData?.picks)?currentData.picks:[]).length
  const rawTimestamp=currentData?.generated_at
  const updated=Number.isFinite(Date.parse(rawTimestamp||''))?
    readableTime(rawTimestamp):'Not verified'

  return (
    <section aria-label="Best Bets source proof and game intelligence" className="rounded-2xl border border-slate-200 bg-white p-3 shadow-soft md:p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs font-black text-slate-900">
          <ShieldCheck size={16} className="text-blue-700" />
          What the brain knows now
        </div>
        <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-black text-slate-600">
          Research only · {proof.approvedPlayCount} approved plays
        </span>
      </div>
      <p className="mt-2 text-sm leading-5 text-slate-700">
        {proof.candidateCount
          ? `${proof.candidateCount} ${summaryMarket} observations in this view. ${proof.researchCount} remain research-only; sportsbook probabilities alone are not a proven Zenith advantage.`
          : `No verified ${sport==='ALL'?'sports':sport} ${summaryMarket} selection currently clears the source and model proof gates.`}
      </p>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 text-[11px] text-slate-500">
        <span className="inline-flex items-center gap-1"><Database size={13} /> Current qualified feed: {totalCandidates} records · updated {updated}</span>
        <a href="#brain-record" className="inline-flex min-h-9 items-center gap-1 font-black text-blue-700 hover:underline">
          See Brain Record <ArrowUpRight size={13} />
        </a>
      </div>
      {(sport==='NFL' || (market!=='ALL' && proof.candidateCount===0)) && (
        <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3">
          <div className="flex items-center gap-2 text-xs font-black text-amber-950"><AlertTriangle size={15}/> Why this market is blocked</div>
          <p className="mt-1 text-xs leading-5 text-amber-900">
            {sport==='NFL'
              ? 'The NFL primary market source failed freshness checks. Older prices and point spreads are deliberately hidden—not presented as live picks.'
              : 'No current line was qualified for this sport and market. Existing historical research is not a substitute for a fresh, verifiable quote.'}
          </p>
          {sport==='NFL' && proof.nflStaleUpstreamMoneylineCount>0 && (
            <p className="mt-1 text-[11px] leading-4 text-amber-900">
              {proof.nflStaleUpstreamMoneylineCount} separate upstream NFL <b>moneyline</b> rows are labeled STALE. This does not prove fresh point-spread pricing is available.
            </p>
          )}
          <p className="mt-1 text-[11px] leading-4 text-amber-900">
            Next: verify the sportsbook capture time, exact matchup and line, then beat the market baseline in independent future games.
          </p>
        </div>
      )}
      {sport!=='ALL' && relevant.length>0 && (
        <div className="mt-3 grid gap-1.5">
          {relevant.map(item=><LaneStatus item={item} key={item.market}/>)}
          <p className="mt-1 text-[10px] leading-4 text-slate-500">Game counts are from the research ledger, not a promise of winning or a sportsbook payout.</p>
        </div>
      )}
      {sport==='NFL' && (
        <div className="mt-3 border-t border-slate-100 pt-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-xs font-black text-slate-900">
              <CalendarDays size={15} className="text-blue-700" /> Upcoming NFL games · no betting recommendations
            </div>
            <span className="shrink-0 text-[10px] text-slate-500">{nfl.length} shown from official feed</span>
          </div>
          {preview.length ? (
            <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
              {preview.map(game => (
                <div key={game.event_id} className="flex items-center justify-between gap-2 rounded-xl border border-slate-200 px-3 py-2.5">
                  <div className="min-w-0">
                    <div className="truncate text-xs font-black text-slate-900">{game.away_abbr || game.away} @ {game.home_abbr || game.home}</div>
                    <div className="mt-0.5 text-[11px] text-slate-500">{readableTime(game.start_time)}</div>
                  </div>
                  <span className="shrink-0 text-[10px] font-bold text-amber-700">Price pending</span>
                </div>
              ))}
            </div>
          ) : <p className="mt-2 text-xs text-slate-500">No upcoming verified NFL fixtures in the official current window.</p>}
          {hidden.length>0 && (
            <details className="mt-2 text-xs">
              <summary className="cursor-pointer py-2 font-black text-blue-700">See {hidden.length} more scheduled games</summary>
              <div className="mt-1 grid gap-1 sm:grid-cols-2">
                {hidden.map(g=><div key={g.event_id} className="rounded-lg bg-slate-50 px-3 py-2 text-slate-600"><b>{g.away_abbr} @ {g.home_abbr}</b> · {readableTime(g.start_time)}</div>)}
              </div>
            </details>
          )}
        </div>
      )}
    </section>
  )
}
