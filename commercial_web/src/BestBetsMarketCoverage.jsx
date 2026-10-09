import React from 'react'
import NFLBookResearch from './NFLBookResearch'
import NFLFrozenModelPanel from './NFLFrozenModelPanel'
import { AlertTriangle, ArrowUpRight, Database, ShieldCheck } from 'lucide-react'
import { sourceMarketStatus } from '../best_bets_market_availability.js'

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
  const totalCandidates=(Array.isArray(currentData?.picks)?currentData.picks:[]).length
  const rawTimestamp=currentData?.generated_at
  const updated=Number.isFinite(Date.parse(rawTimestamp||''))?
    readableTime(rawTimestamp):'Not verified'

  return (
    <section aria-label="Best Bets source proof and game intelligence" className="rounded-2xl border border-slate-200 bg-white p-3.5 shadow-soft md:p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs font-black text-slate-900">
          <ShieldCheck size={16} className="text-blue-700" />
          What the brain knows now
        </div>
        <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-black text-slate-600">
          {proof.approvedPlayCount ? `${proof.approvedPlayCount} paper qualifiers · no wagers` : '0 verified plays · research only'}
        </span>
      </div>
      <p className="mt-2 text-sm leading-5 text-slate-700">
        {proof.candidateCount
          ? `${proof.candidateCount} ${summaryMarket} checked · ${proof.researchCount} research only. No independent edge claimed.`
          : `No verified ${sport==='ALL'?'sports':sport} ${summaryMarket} selection currently clears the source and model proof gates.`}
      </p>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 text-[11px] text-slate-500">
        <span className="inline-flex items-center gap-1"><Database size={13} /> Research feed: {totalCandidates} records · {updated}</span>
        <a href="#brain-record" className="inline-flex min-h-9 items-center gap-1 font-black text-blue-700 hover:underline">
          See Brain Record <ArrowUpRight size={13} />
        </a>
      </div>
      {(sport==='NFL' || (market!=='ALL' && proof.candidateCount===0)) && (
        <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5">
          <div className="flex items-center gap-2 text-xs font-black text-amber-950"><AlertTriangle size={15}/> Why this market is blocked</div>
          <p className="mt-1 text-xs leading-5 text-amber-900">
            {sport==='NFL'
              ? 'The NFL primary market source failed freshness checks. Dated quotes remain research, not live picks.'
              : 'No fresh, source-qualified line clears this market. Historical research is not a current quote.'}
          </p>
          <details className="group mt-1.5 border-t border-amber-200/60 pt-1">
            <summary className="flex min-h-9 cursor-pointer list-none items-center text-[11px] font-black text-amber-900">
              View source verification details
            </summary>
            <div className="pb-1 text-[11px] leading-5 text-amber-900">
              <p>Older prices and point spreads are excluded from live recommendations.</p>
              {sport==='NFL' && proof.nflStaleUpstreamMoneylineCount>0 && (
                <p className="mt-1">{proof.nflStaleUpstreamMoneylineCount} upstream NFL moneyline rows are STALE. This does not establish fresh spread pricing.</p>
              )}
              <p className="mt-1">A market reference needs an exact event, valid sportsbook quote time and independent future model proof.</p>
            </div>
          </details>
        </div>
      )}
      {sport!=='ALL' && relevant.length>0 && (
        <div className="mt-3 grid gap-1.5">
          {relevant.map(item=><LaneStatus item={item} key={item.market}/>)}
          <p className="mt-1 text-[10px] leading-4 text-slate-500">Game counts are from the research ledger, not a promise of winning or a sportsbook payout.</p>
        </div>
      )}
      {sport==='NFL' && (market==='ALL' || market==='MONEYLINE') && (
        <div className="mt-3"><NFLFrozenModelPanel /></div>
      )}
      {sport==='NFL' && <NFLBookResearch nflScores={nflScores} market={market} />}
    </section>
  )
}
