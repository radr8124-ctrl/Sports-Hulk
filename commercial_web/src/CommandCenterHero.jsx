import React from 'react'
import {ArrowRight,BarChart3,CheckCircle2,Radio,Sparkles,Target} from 'lucide-react'
import ZenithRefAvatar from './ZenithRefAvatar.jsx'
import {AccountButton,useAuth} from './AuthShell.jsx'

export default function CommandCenterHero({onNavigate}){
 const {user}=useAuth()
 return <section aria-label="Sports Zenith game-day command center"
  className="relative isolate overflow-hidden rounded-[24px] border-2 border-[#173E52] bg-[#FFF5E4] px-4 py-4 text-[#173E52] shadow-[5px_5px_0_#173E5225] sm:px-6 sm:py-6 lg:px-8 lg:py-8">
  <div aria-hidden="true" className="pointer-events-none absolute left-0 right-0 top-0 h-2 bg-[linear-gradient(90deg,#FF7766_0%,#FF7766_28%,#FFD36A_28%,#FFD36A_54%,#46CDD2_54%,#46CDD2_84%,#173E52_84%)]"/>
  <div aria-hidden="true" className="pointer-events-none absolute -right-24 -top-28 hidden h-80 w-80 rotate-12 rounded-[90px] border-[28px] border-[#46CDD2]/20 lg:block"/>
  <div className="relative grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(235px,.7fr)] lg:items-center lg:gap-8">
   <div className="min-w-0">
    <div className="flex items-center justify-between gap-2 lg:justify-start">
     <span className="inline-flex items-center gap-1.5 rounded-lg border border-[#173E52] bg-[#46CDD2] px-2.5 py-1 text-[10px] font-black uppercase tracking-[.14em] text-[#173E52] shadow-[2px_2px_0_#173E52]">
      <Radio size={12}/> Zenith Game Day
     </span>
     <span className="lg:hidden"><ZenithRefAvatar size={53} compact/></span>
    </div>
    <h1 className="mt-2 max-w-[680px] text-[clamp(1.75rem,5.6vw,3.25rem)] font-black leading-[1.07] tracking-[-.045em] text-[#173E52]">
     The game. The numbers.
     <span className="block w-fit bg-[#FFD36A] px-1.5 text-[#173E52]">The smarter call.</span>
    </h1>
    <p className="mt-2 max-w-xl text-[13px] font-semibold leading-[1.5] text-[#405B69] md:text-base">
     Real scores, source-backed bookmaker research and evidence behind the calls. No forced picks.
    </p>
    <div className="mt-3 grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
     <button type="button" onClick={()=>onNavigate('Best Bets')}
      className="flex min-h-11 items-center justify-center gap-1.5 rounded-xl border-2 border-[#173E52] bg-[#FF7766] px-3 py-2.5 text-[12px] font-black text-[#173E52] shadow-[3px_3px_0_#173E52] transition hover:bg-[#FF968B] sm:px-5 sm:text-sm">
      <Target size={15}/> Explore Bets <ArrowRight size={13}/>
     </button>
     <button type="button" onClick={()=>onNavigate('Ask')}
      className="flex min-h-11 items-center justify-center gap-1.5 rounded-xl border-2 border-[#173E52] bg-white px-3 py-2.5 text-[12px] font-black text-[#173E52] transition hover:bg-[#E9F8F4] sm:px-5 sm:text-sm">
      <Sparkles size={15}/> Ask The Ref
     </button>
    </div>
    <div aria-label="Join Sports Zenith" className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1.5 text-[11px] font-bold text-[#536F76]">
      <AccountButton hero />
      <span>{user ? 'Your verified account is ready for private sports features.' : 'Use your email and a secure one-time code. No password.'}</span>
    </div>
    <div className="mt-3 hidden flex-wrap items-center gap-x-3 gap-y-1.5 text-[10px] font-bold text-[#536F76] sm:flex">
     <span className="inline-flex items-center gap-1.5"><CheckCircle2 size={12} className="text-[#178A83]"/> Game-first research</span>
     <span className="inline-flex items-center gap-1.5"><CheckCircle2 size={12} className="text-[#178A83]"/> Frozen predictions</span>
     <span className="inline-flex items-center gap-1.5"><CheckCircle2 size={12} className="text-[#178A83]"/> Errors stay visible</span>
    </div>
   </div>
   <div className="hidden items-center gap-4 rounded-[20px] border-2 border-[#173E52] bg-[#173E52] p-5 text-white shadow-[5px_5px_0_#46CDD2] lg:flex">
    <ZenithRefAvatar size={97}/>
    <div className="min-w-0">
     <p className="text-[10px] font-black uppercase tracking-[.16em] text-[#FFD36A]">The Ref · Zenith AI</p>
     <p className="mt-1 text-lg font-black leading-5">Get the call.<br/>Check the evidence.</p>
     <p className="mt-2 text-xs font-semibold leading-5 text-[#C7DAE4]">
      Line, bookmaker, model disagreement, risk—explained.
     </p>
     <button type="button" onClick={()=>onNavigate('Brain Record')} className="mt-3 inline-flex items-center gap-1 text-xs font-black text-[#7DE4E1]">
      <BarChart3 size={13}/> View Brain Record <ArrowRight size={12}/>
     </button>
    </div>
   </div>
  </div>
 </section>
}
