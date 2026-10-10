import React from 'react'
import {ArrowRight,BarChart3,CheckCircle2,Radio,Sparkles,Target} from 'lucide-react'
import ZenithRefAvatar from './ZenithRefAvatar.jsx'

export default function CommandCenterHero({onNavigate}){
 return <section aria-label="Sports Zenith game-day command center"
  className="relative isolate overflow-hidden rounded-[26px] border border-[#244663] bg-[#061729] px-4 py-4 text-white shadow-[0_20px_50px_rgba(2,18,36,.20)] sm:px-6 sm:py-6 lg:px-8 lg:py-8">
  <div aria-hidden="true" className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_92%_18%,rgba(25,181,238,.23),transparent_42%),linear-gradient(135deg,#092542_0%,#07172A_55%,#050E19_100%)]"/>
  <div aria-hidden="true" className="pointer-events-none absolute inset-0 opacity-20 [background-image:linear-gradient(rgba(125,195,233,.11)_1px,transparent_1px),linear-gradient(90deg,rgba(125,195,233,.11)_1px,transparent_1px)] [background-size:35px_35px]"/>
  <div className="relative grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(235px,.7fr)] lg:items-center lg:gap-8">
   <div className="min-w-0">
    <div className="flex items-center justify-between gap-2 lg:justify-start">
     <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-400/25 bg-sky-400/10 px-2.5 py-1 text-[10px] font-black uppercase tracking-[.14em] text-sky-200">
      <Radio size={12}/> Zenith Game Day
     </span>
     <span className="lg:hidden"><ZenithRefAvatar size={53} compact/></span>
    </div>
    <h1 className="mt-2 max-w-[680px] text-[clamp(1.75rem,5.6vw,3rem)] font-black leading-[1.07] tracking-[-.045em] text-white">
     The game. The numbers.
     <span className="block text-[#56D0FF]">The smarter call.</span>
    </h1>
    <p className="mt-2 max-w-xl text-[13px] font-medium leading-[1.5] text-[#B7CCE0] md:text-base">
     Real scores, bookmaker prices and evidence behind the calls. No forced picks.
    </p>
    <div className="mt-3 grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
     <button type="button" onClick={()=>onNavigate('Best Bets')}
      className="flex min-h-11 items-center justify-center gap-1.5 rounded-xl bg-[#3AC6F4] px-3 py-2.5 text-[12px] font-black text-[#061B31] shadow-lg shadow-sky-400/10 transition hover:bg-sky-200 sm:px-5 sm:text-sm">
      <Target size={15}/> Explore Bets <ArrowRight size={13}/>
     </button>
     <button type="button" onClick={()=>onNavigate('Ask')}
      className="flex min-h-11 items-center justify-center gap-1.5 rounded-xl border border-white/20 bg-white/10 px-3 py-2.5 text-[12px] font-black text-white transition hover:border-sky-400/50 hover:bg-white/15 sm:px-5 sm:text-sm">
      <Sparkles size={15}/> Ask The Ref
     </button>
    </div>
    <div className="mt-3 hidden flex-wrap items-center gap-x-3 gap-y-1.5 text-[10px] font-bold text-slate-400 sm:flex">
     <span className="inline-flex items-center gap-1.5"><CheckCircle2 size={12} className="text-sky-300"/> Game-first research</span>
     <span className="inline-flex items-center gap-1.5"><CheckCircle2 size={12} className="text-sky-300"/> Frozen predictions</span>
     <span className="inline-flex items-center gap-1.5"><CheckCircle2 size={12} className="text-sky-300"/> Errors stay visible</span>
    </div>
   </div>
   <div className="hidden items-center gap-4 rounded-[24px] border border-sky-400/15 bg-slate-950/45 p-5 lg:flex">
    <ZenithRefAvatar size={97}/>
    <div className="min-w-0">
     <p className="text-[10px] font-black uppercase tracking-[.16em] text-[#57CCFA]">The Ref · Zenith AI</p>
     <p className="mt-1 text-lg font-black leading-5">Get the call.<br/>Check the evidence.</p>
     <p className="mt-2 text-xs font-semibold leading-5 text-slate-400">
      Line, bookmaker, model disagreement, risk—explained.
     </p>
     <button type="button" onClick={()=>onNavigate('Brain Record')} className="mt-3 inline-flex items-center gap-1 text-xs font-black text-sky-300">
      <BarChart3 size={13}/> View Brain Record <ArrowRight size={12}/>
     </button>
    </div>
   </div>
  </div>
 </section>
}
