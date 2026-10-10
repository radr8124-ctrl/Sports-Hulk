import React from 'react'
import {CheckCircle2,ChevronRight,History,ShieldAlert} from 'lucide-react'

const shortLabel=(result)=>result==='SURVIVED'?'SURVIVED':result==='LOST'?'LOST':'REVIEW'
const tone=(result)=>result==='SURVIVED'
  ?'border-[#A5DCC8] bg-[#E4F8EF] text-[#176B58]'
  :result==='LOST'?'border-[#F2BAB4] bg-[#FFF1EA] text-[#A33D36]'
    :'border-[#EDD39B] bg-[#FFF6DF] text-[#825A25]'
const submissionText=group=>group?.official_sheet_recorded===true
  ?'This pick is marked confirmed on the imported official pool sheet (not submitted by Zenith)'
  :group?.submission_status==='SUBMISSION_RECORDED_IN_ZENITH'
    ?'A prior submission is recorded in Zenith (external acknowledgement not independently verified)'
    :group?.submission_status==='SUBMISSION_NOT_RECORDED'
      ?'No submission confirmation is recorded in Zenith for this week'
      :'External submission information is unavailable in the saved record'

// Display ONLY an authorized /api/survivor/state past_picks payload.
// This is historical member data; never fetched from anonymous research feeds.
export default function SurvivorPastPicks({history,entryName=''}){
 const groups=Array.isArray(history?.week_groups)?history.week_groups:[]
 const confirmed=history?.status==='RECORDED_HISTORY_COMPLETE'
 const conflicts=history?.status==='HISTORY_CONFLICT_NEEDS_REVIEW'
 const total=Number.isInteger(history?.total_picks)?history.total_picks:0
 const currentWeek=Number.isInteger(history?.current_week)?history.current_week:null
 return (
  <section id="my-survivor-past-picks" aria-label="My Survivor past picks" data-survivor-past-picks
    data-past-history-status={history?.status||'HISTORY_UNAVAILABLE'}
    className="scroll-mt-24 min-w-0 overflow-hidden rounded-[22px] border-2 border-[#B9D2D1] bg-[#FFF8ED] p-3.5 text-[#173E52] shadow-soft sm:p-5">
    <div className="flex flex-wrap items-start justify-between gap-2">
      <div className="min-w-0">
        <div className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-[.14em] text-[#0E7280]">
          <History size={14}/>YOUR PRIVATE SURVIVOR HISTORY
        </div>
        <h2 className="mt-1 text-lg font-black tracking-tight text-[#173E52] sm:text-xl">My Past Picks</h2>
        <p className="mt-0.5 text-[11px] font-semibold text-[#617984]">{entryName?`${entryName} · `:''}Recorded picks, organized by week</p>
      </div>
      <div className="rounded-lg border border-[#D2C9AF] bg-white px-2.5 py-1.5 text-[10px] font-black tabular-nums text-[#173E52]">
        {total} {total===1?'PICK':'PICKS'} · {groups.length} {groups.length===1?'WEEK':'WEEKS'}
      </div>
    </div>
    {groups.length===0?(
      <p className="mt-3 rounded-xl bg-white px-3 py-2.5 text-xs font-medium leading-5 text-[#667783]">
        No original past-week pick records are available for this linked entry. Previously used-team counts alone are not enough to reconstruct which week a team was picked.
      </p>
    ):(
      <div className="mt-3 space-y-1.5">
        {groups.map(group=>(
          <div key={group.week} data-past-week={group.week}
            className="flex min-w-0 items-start gap-2 rounded-xl border border-[#E3E2D6] bg-white px-2.5 py-2 sm:gap-3 sm:px-3">
            <div className="flex h-9 w-11 shrink-0 flex-col items-center justify-center rounded-lg bg-[#173E52] text-[#FFF8ED]">
              <div className="text-[8px] font-black leading-none tracking-wider text-[#9ADBD5]">WEEK</div>
              <div className="mt-0.5 text-base font-black leading-none tabular-nums">{group.week}</div>
            </div>
            <div className="min-w-0 flex-1 space-y-1.5">
              {group.picks.map((pick,i)=>(
                <div key={pick.week+':'+pick.team+':'+i} data-past-pick={pick.team}
                  className="flex min-w-0 flex-wrap items-center justify-between gap-x-2 gap-y-1">
                  <div className="min-w-0 flex-1 text-[11px] font-black leading-4 text-[#173E52] sm:text-xs">
                    {pick.team}
                    {pick.game_score&&<span className="mt-0.5 block text-[10px] font-medium leading-4 text-slate-500">{pick.game_score}</span>}
                  </div>
                  <span className={`shrink-0 rounded-md border px-1.5 py-1 text-[9px] font-black leading-3 ${tone(pick.result)}`}>
                    {pick.result==='SURVIVED'&&<CheckCircle2 size={10} className="mr-0.5 inline"/>}
                    {shortLabel(pick.result)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    )}
    {conflicts&&(
      <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-[#FFF2D9] px-2.5 py-2 text-[11px] font-semibold leading-4 text-[#815222]">
        <ShieldAlert size={14} className="mt-0.5 shrink-0"/>Some saved history differs from the official entry record. Those picks are marked for source review instead of silently calling them wins.
      </p>
    )}
    {currentWeek&&(
      <p className="mt-2 text-[10px] font-semibold leading-4 text-[#576F7A]">
        Week {currentWeek}: {history.current_picks_saved===0?'No pick saved in Zenith.':`${history.current_picks_saved} pick(s) currently saved in Zenith.`}
        {' '}Earlier results are drawn from your existing private pool record—not a new pick or an external submission.
      </p>
    )}
    {confirmed&&groups.length>0&&(
      <details className="group mt-2 border-t border-[#DFE2DA] pt-2">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-[10px] font-bold text-[#166978]">
          <span>Recorded result sources and external-pool notes</span>
          <ChevronRight size={14} className="shrink-0 transition-transform group-open:rotate-90" />
        </summary>
        <div className="mt-2 space-y-1.5 text-[10px] font-medium leading-4 text-[#536A74]">
          {groups.map(group=>(
            <div key={group.week}>
              <b>Week {group.week}:</b> {group.picks.map(p=>p.original_source||'Source not recorded').filter((x,i,a)=>a.indexOf(x)===i).join(' · ')}.
              {' '}{submissionText(group)}.
            </div>
          ))}
        </div>
      </details>
    )}
  </section>
 )
}
