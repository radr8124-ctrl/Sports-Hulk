import React from 'react'
import {ChevronRight,ShieldAlert,ShieldCheck} from 'lucide-react'

const content={
 AWAITING_OFFICIAL_WEEK5_SHEET:{
  title:'Week 5 organizer confirmation still needed',
  detail:'The official pool sheet on file covers an earlier week. Your original entry remains recorded ALIVE, but that does not certify Week 5 participation or survival.',
  next:'Week 6 is planned for two picks. Your record will not advance until the organizer ticket and prior-week result are confirmed.',
 },
 OFFICIAL_WEEK5_TICKET_ABSENT_REVIEW:{
  title:'Week 5 ticket needs organizer review',
  detail:'An official Week 5 source exists, but no matching team is confirmed in this entry record. Do not infer elimination or advance automatically.',
  next:'Verify the original organizer ticket before preparing Week 6.',
 },
 WAITING_WEEK5_GAME_FINAL:{
  title:'Week 5 pick recorded · awaiting Final',
  detail:'A Week 5 ticket is recorded in the imported official pool evidence. Its saved result has not reached a complete verified Final.',
  next:'The next round requires two unused teams, subject to official prior-week settlement.',
 },
 WEEK5_SURVIVAL_CERTIFIED_NEXT_ROUND_PENDING:{
  title:'Week 5 recorded as survived · Week 6 pending',
  detail:'The imported pool ticket and saved prior-week result agree. The current season week has not rolled forward yet.',
  next:'Once Week 6 is activated, two unused teams are required. No team has been chosen here.',
 },
 WEEK6_TWO_PICK_ROUND_READY:{
  title:'Week 6 activated · two picks required',
  detail:'The confirmed prior-week ticket and saved win agree, and the private entry has advanced to Week 6.',
  next:'Review verified source availability and exact submission deadlines. Zenith does not submit to the organizer.',
 },
 WAITING_PRIVATE_WEEK6_ACTIVATION:{
  title:'Week 6 calendar active · private entry awaiting rollover',
  detail:'The prior-week pool record shows a verified win, but this individual entry has not yet advanced to Week 6.',
  next:'Do not treat it as an open two-pick entry until its authenticated pool record is updated.',
 },
 OFFICIAL_WEEK5_ELIMINATED:{
  title:'Week 5 loss recorded on imported pool ticket',
  detail:'The saved Week 5 ticket and its losing result agree. Re-entry, if permitted by the organizer, requires separate evidence.',
  next:'Week 6 is not available for this ticket without a verified re-entry.',
 },
}
export default function SurvivorNextRoundStatus({proof}){
 const status=String(proof?.status||'SOURCE_UNAVAILABLE')
 const ready=proof?.ready_for_week6===true &&
    ['WEEK5_SURVIVAL_CERTIFIED_NEXT_ROUND_PENDING','WEEK6_TWO_PICK_ROUND_READY'].includes(status)
 const item=content[status]||{
  title:'Organizer result needs source review',
  detail:'The private entry or official source record is incomplete or inconsistent. No prior-week result or next-week eligibility has been assumed.',
  next:'Wait for verified organizer evidence before advancing the personal pool entry.',
 }
 const sourceWeek=Number.isInteger(proof?.official_source_week)?proof.official_source_week:'—'
 const currentSaved=Number.isInteger(proof?.saved_week5_picks)?proof.saved_week5_picks:'—'
 const required=Number.isInteger(proof?.required_next_week_picks)?proof.required_next_week_picks:'—'
 return (
  <section aria-label="Survivor next round readiness" data-survivor-next-round-readiness
   data-next-round-status={status} className="min-w-0 rounded-[22px] border border-[#B8D4D0] bg-[#EDF6F3] px-3.5 py-3 text-[#173E52] sm:px-5 sm:py-4">
   <div className="flex flex-wrap items-start justify-between gap-2">
    <div className="min-w-0 flex-1">
     <p className="text-[10px] font-black uppercase tracking-[.13em] text-[#0E7280]">NEXT ROUND WATCH · PRIVATE POOL</p>
     <h2 className="mt-1 text-sm font-black leading-5 sm:text-base">{item.title}</h2>
    </div>
    <span className={`shrink-0 rounded-lg border px-2 py-1 text-[9px] font-black ${ready?
      'border-[#91C8B1] bg-[#DDF7EA] text-[#216B57]':'border-[#E8C996] bg-[#FFF8E9] text-[#936027]'}`}>
     {ready?'PRIOR ROUND VERIFIED':'CONFIRMATION PENDING'}
    </span>
   </div>
   <div className="mt-2 grid grid-cols-3 gap-1.5 rounded-lg border border-[#DAE6E0] bg-white p-2 text-center">
    <div><div className="text-base font-black tabular-nums">{sourceWeek}</div><div className="text-[9px] font-bold text-[#5D7380]">Latest official week</div></div>
    <div><div className="text-base font-black tabular-nums">{currentSaved}</div><div className="text-[9px] font-bold text-[#5D7380]">Week 5 Zenith saved</div></div>
    <div><div className="text-base font-black tabular-nums">{required}</div><div className="text-[9px] font-bold text-[#5D7380]">Week 6 required</div></div>
   </div>
   <p className="mt-2 flex items-start gap-1.5 text-[11px] font-semibold leading-4 text-[#4D6671]">
     {ready?<ShieldCheck size={14} className="mt-0.5 shrink-0 text-[#18735D]"/>:
       <ShieldAlert size={14} className="mt-0.5 shrink-0 text-[#AF7140]"/>}
     <span>{item.detail}</span>
   </p>
   <details className="group mt-2 rounded-lg border border-[#D1DFD9] bg-white px-2.5 py-2">
    <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-[10px] font-black text-[#116979]">
     <span>What is needed before Week 6?</span>
     <ChevronRight size={14} className="shrink-0 transition group-open:rotate-90"/>
    </summary>
    <p className="mt-2 border-t border-[#E8EAE6] pt-2 text-[11px] font-semibold leading-5 text-slate-600">{item.next}</p>
    <p className="mt-1 text-[10px] font-medium leading-4 text-slate-500">
      Original 2026 rules and separately imported pool sheets are different proof sources. Reported Thursday losses and research-only scores cannot certify this entry. Zenith does not submit to the external organizer.
    </p>
   </details>
  </section>
 )
}
