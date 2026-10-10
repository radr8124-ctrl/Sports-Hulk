import React from 'react'
import { ShieldCheck, ShieldAlert } from 'lucide-react'
import { survivorCoverState } from '../survivor_cover_state.js'

// Read-only member status. It cannot save, recommend or submit a team.
export default function SurvivorCommandCover({
  signedIn,hasEntry,entryStatus,poolWeek,usedTeams,currentPicks,requiredPicks,
  ruleConfirmed,officialPoolWeek,recommendationStatus,shadowRecommendation,
}) {
  const state=survivorCoverState({
    signedIn,hasEntry,entryStatus,poolWeek,usedTeams,currentPicks,requiredPicks,
    ruleConfirmed,officialPoolWeek,recommendationStatus,shadowRecommendation,
  })
  const saved=state.status==='SAVED_ZENITH_ONLY'
  return (
    <section aria-label="Survivor premium command desk" data-premium-survivor-cover
      className="relative min-w-0 overflow-hidden rounded-[23px] border-2 border-[#173E52] bg-[#173E52] p-3 text-[#FFF5E4] shadow-[4px_4px_0_#46CDD24D] sm:p-5">
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-[5px] bg-[linear-gradient(90deg,#FF7766_0%,#FF7766_35%,#FFD36A_35%,#FFD36A_65%,#46CDD2_65%,#46CDD2_100%)]" />
      <div className="relative flex min-w-0 items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-black uppercase tracking-[.16em] text-[#7DE4E1]">THE SURVIVOR DESK</p>
          <h1 className="mt-1 text-[clamp(1.75rem,4vw,2.5rem)] font-black leading-[1.03] tracking-[-.04em] text-[#FFF5E4]">
            Survivor<span aria-hidden="true" className="text-[#FF7766]">.</span>
          </h1>
          <p className="mt-1 text-[11px] font-semibold leading-[1.4] text-[#DCE9E8] sm:text-xs">
            {!signedIn ? 'Sign in for your picks and used-team history.'
              : !hasEntry ? 'Connect your pool entry to see private Survivor status.'
                : 'Protect the entry. Compare the risks. Your choice stays yours.'}
          </p>
        </div>
        <span className="hidden shrink-0 rounded-lg border border-[#76CAC4]/60 bg-[#234F60] px-2 py-1 text-[9px] font-black uppercase tracking-wider text-[#FFD36A] sm:inline-flex">SURVIVOR INTELLIGENCE</span>
      </div>

      <div data-survivor-cover-status={state.status}
        className="relative mt-3 flex min-w-0 flex-wrap items-center justify-between gap-x-3 gap-y-1 rounded-xl border border-[#43728A] bg-[#234F60] px-3 py-2">
        <div className="flex min-w-0 items-center gap-1.5">
          {saved?<ShieldCheck size={15} className="shrink-0 text-[#7DE4E1]" />:<ShieldAlert size={15} className="shrink-0 text-[#FFD36A]" />}
          <span className="text-[10px] font-black uppercase tracking-[.09em] text-[#FFF5E4]">{state.label}</span>
        </div>
        <span className="text-[10px] font-bold text-[#DCE9E8]">{state.week?`Week ${state.week}`:'Season week pending'} · {hasEntry && signedIn?'Private entry':'Research only'}</span>
      </div>

      <div data-survivor-cover-metrics className="relative mt-2 grid grid-cols-3 gap-1.5 rounded-xl bg-[#FFF8ED] p-1.5 text-[#173E52] sm:gap-2 sm:p-2">
        {[
          ['saved',state.saved,'Zenith saved'],
          ['used',state.used,'Teams used'],
          ['qualified',state.qualified,'Model-qualified'],
        ].map(([id,value,label])=>(
          <div key={id} data-survivor-cover-metric={id} className="min-w-0 rounded-lg bg-white px-1 py-1.5 text-center sm:py-2">
            <div className="text-lg font-black leading-none tabular-nums text-[#173E52] sm:text-xl">{value}</div>
            <div className="mt-1 text-[9px] font-bold leading-tight text-[#4F6D77] sm:text-[10px]">{label}</div>
          </div>
        ))}
      </div>
      <p className="relative mt-2 text-[10px] font-semibold leading-[1.35] text-[#E3EEEA]">
        <span className="font-black text-[#FFD36A]">Official pool: {state.official}.</span>{' '}
        <span className="sm:hidden">{state.qualified !== '0' && state.qualified !== '—' ? 'Shadow research only.' : 'Model edge not verified.'}</span>
        <span className="hidden sm:inline">{state.proof} {state.external}</span>
      </p>
    </section>
  )
}
