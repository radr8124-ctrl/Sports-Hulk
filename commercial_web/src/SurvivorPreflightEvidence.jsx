import React,{useEffect,useMemo,useState} from 'react'
import {Activity,ChevronRight,Clock3,FileCheck2,ShieldAlert} from 'lucide-react'

const dateET=iso=>{
 const ts=Date.parse(iso||'')
 return Number.isFinite(ts)?new Intl.DateTimeFormat('en-US',{
  month:'short',day:'numeric',hour:'numeric',minute:'2-digit',
  timeZone:'America/New_York',timeZoneName:'short',
 }).format(new Date(ts)):'Source time unavailable'
}
const american=n=>n>0?`+${n}`:`${n}`
const statusTone=status=>status==='Out'?'bg-rose-100 text-rose-800':
 status==='Doubtful'?'bg-orange-100 text-orange-800':
 status==='Questionable'?'bg-amber-100 text-amber-800':'bg-slate-100 text-slate-700'

function TeamInjuryNotes({group,heading,coverage}) {
 const list=Array.isArray(group?.players)?group.players:[]
 return (
  <article className="min-w-0 rounded-xl border border-[#D8DCE1] bg-white p-3">
   <h3 className="text-xs font-black text-[#173E52]">{heading}</h3>
   <p className="mt-0.5 text-[10px] font-semibold text-slate-500">{coverage?'Recent ESPN reported statuses':'Recent verified injury source unavailable'}</p>
   {!coverage||!list.length?(
    <p className="mt-2 text-[11px] font-medium leading-4 text-slate-500">
     {coverage?'No qualifying recent injury designations in this limited feed. That does not mean cleared or healthy.':'Do not infer health or game availability from missing source data.'}
    </p>
   ):(
    <>
     <div className="mt-2 space-y-1.5">
      {list.slice(0,3).map((r,i)=>(
       <div key={r.player+':'+i} className="min-w-0 rounded-lg bg-[#F8F6F1] px-2.5 py-1.5">
        <div className="flex min-w-0 flex-wrap items-start justify-between gap-1">
         <div className="min-w-0 text-[11px] font-black text-slate-800">{r.player} <span className="font-medium text-slate-500">{r.position}</span></div>
         <span className={`rounded px-1.5 py-0.5 text-[9px] font-black ${statusTone(r.reported_status)}`}>{r.reported_status}</span>
        </div>
        <div className="mt-0.5 text-[10px] font-medium text-slate-500">{r.injury} · {dateET(r.reported_at)}</div>
       </div>
      ))}
     </div>
     {list.length>3&&(
      <details className="mt-2 rounded-lg border border-[#DEE4E5] bg-white px-2.5 py-1.5">
       <summary className="cursor-pointer text-[10px] font-black text-[#126978]">View {list.length-3} more reports</summary>
       <div className="mt-1.5 space-y-1.5 border-t border-slate-100 pt-1.5">
        {list.slice(3).map((r,i)=>(
         <p key={r.player+':'+i} className="text-[10px] font-semibold leading-4 text-slate-600">{r.player} ({r.position}) · {r.reported_status} · {r.injury} · {dateET(r.reported_at)}</p>
        ))}
       </div>
      </details>
     )}
    </>
   )}
  </article>
 )
}

export default function SurvivorPreflightEvidence({entryName,candidates=[],usedTeams=[],getAccessToken}) {
 const [team,setTeam]=useState('')
 const [evidence,setEvidence]=useState(null)
 const [status,setStatus]=useState('CHOOSE_TEAM')
 const options=useMemo(()=>{
  const burned=new Set(usedTeams)
  return candidates.filter(row=>row?.team&&row?.opponent&&!burned.has(row.team))
   .map(row=>row.team).filter((name,index,all)=>all.indexOf(name)===index)
 },[candidates,usedTeams])
 useEffect(()=>{setTeam('');setEvidence(null);setStatus('CHOOSE_TEAM')},[entryName])
 useEffect(()=>{
  if(!team||!entryName||!options.includes(team)){
   setEvidence(null);setStatus('CHOOSE_TEAM');return undefined
  }
  let cancelled=false
  const load=async()=>{
   if(!cancelled)setStatus('LOADING')
   try{
    const token=await getAccessToken()
    if(!token)throw Error('Sign in to see your private Survivor research.')
    const query=new URLSearchParams({entry:entryName,team,ts:String(Date.now())})
    const response=await fetch('/api/survivor/preflight?'+query,{cache:'no-store',
     headers:{Authorization:'Bearer '+token}})
    const data=await response.json()
    if(cancelled)return
    if(!response.ok||data.status!=='SOURCE_EVIDENCE_ONLY'){
     setEvidence(null);setStatus(data.status||'SOURCE_UNAVAILABLE');return
    }
    setEvidence(data);setStatus('READY')
   }catch{if(!cancelled){setEvidence(null);setStatus('SOURCE_UNAVAILABLE')}}
  }
  load()
  const timer=window.setInterval(load,120*1000)
  return()=>{cancelled=true;window.clearInterval(timer)}
 },[team,entryName,getAccessToken,options])

 const ready=status==='READY'&&evidence?.status==='SOURCE_EVIDENCE_ONLY'
 const books=ready&&evidence.book?.status==='RECENT_DATED_RESEARCH_NOT_EXECUTABLE'
 const injuries=ready&&evidence.injuries?.status==='RECENT_LIMITED_ESPN_REPORTS_NOT_STARTER_CONFIRMATION'
 return (
  <section aria-label="Survivor source-verified injury and odds evidence" data-survivor-preflight-evidence
   className="min-w-0 overflow-hidden rounded-[24px] border border-[#C4D8D9] bg-[#FFF8ED] p-4 shadow-soft md:p-5">
   <div className="flex flex-wrap items-start justify-between gap-2">
    <div className="min-w-0 flex-1">
     <p className="text-[10px] font-black uppercase tracking-[.15em] text-[#AF574B]">THE MATCHUP EVIDENCE FILE · NFL</p>
     <h2 className="mt-1 text-lg font-black tracking-tight text-[#173E52] md:text-xl">Player news. Source prices. Proof.</h2>
     <p className="mt-1 max-w-2xl text-[11px] font-medium leading-[1.45] text-[#536D7A]">
      Inspect verified source records for any unused team. Research only — none is a validated winning pick.
     </p>
    </div>
    <span className="hidden rounded-lg border border-[#C8DFDA] bg-white px-2 py-1 text-[9px] font-black uppercase text-[#116977] sm:inline">RESEARCH NOT RECOMMENDATION</span>
   </div>

   <label className="mt-3 block text-[11px] font-black text-[#173E52]">
    Which unused team should we inspect?
    <span className="relative mt-1.5 block">
     <select aria-label="Inspect Survivor team's source evidence" value={team}
      onChange={e=>setTeam(e.target.value)}
      className="w-full min-w-0 appearance-none rounded-xl border border-[#BCD5D9] bg-white px-3 py-2.5 pr-10 text-xs font-bold text-[#173E52]">
      <option value="">Choose a team — does not save a pick</option>
      {options.map(name=><option key={name} value={name}>{name}</option>)}
     </select>
     <ChevronRight size={16} className="pointer-events-none absolute right-3 top-3 rotate-90 text-[#627C86]" />
    </span>
   </label>

   {!ready?(
    <p data-evidence-status className="mt-3 rounded-xl border border-[#DCDDD9] bg-white px-3 py-2.5 text-xs font-semibold leading-5 text-slate-600">
     {status==='CHOOSE_TEAM'?'Choose an eligible Week 5 team above to inspect its matchup evidence. No selections are saved.':
      status==='LOADING'?'Checking verified NFL event, original bookmaker source bytes and ESPN player status records…':
      'Source evidence is missing, expired or inconsistent. No player clearance or betting edge will be inferred.'}
    </p>
   ):(
    <>
     <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[#C8D8DD] bg-white px-3 py-2.5">
      <div className="min-w-0 text-xs font-black text-[#173E52]">{evidence.team} <span className="font-medium text-slate-600">vs {evidence.opponent}</span></div>
      <span className="text-[10px] font-semibold text-slate-500">Kickoff {dateET(evidence.kickoff_at)}</span>
     </div>
     <div className="mt-2 grid gap-2 sm:grid-cols-2">
      <article data-evidence-book-status={evidence.book?.status} className="rounded-xl border border-[#D7DFDE] bg-white p-3">
       <div className="flex items-center gap-1 text-[10px] font-black uppercase tracking-wider text-[#166A79]"><FileCheck2 size={13}/>Two-sided bookmaker source</div>
       {books?(
        <>
         <div className="mt-1 text-xl font-black tabular-nums text-[#173E52]">{american(evidence.book.selected_team_american)}</div>
         <p className="mt-0.5 text-[11px] font-semibold leading-4 text-slate-700">{evidence.book.book} · opponent {american(evidence.book.opponent_american)}</p>
         <p className="mt-1 text-[10px] font-medium leading-4 text-slate-500">Original source time {dateET(evidence.book.source_updated_at)} · SHA verified</p>
        </>
       ):(<p className="mt-2 text-xs font-semibold text-amber-900">No usable recent paired research quote ({String(evidence.book?.status||'UNAVAILABLE').replaceAll('_',' ').toLowerCase()}).</p>)}
       <p className="mt-2 rounded-lg bg-[#FFF1DD] px-2.5 py-2 text-[10px] font-black leading-4 text-amber-950">NOT LIVE OR EXECUTABLE · NOT A QUALIFIED PICK</p>
      </article>
      <article data-evidence-injury-status={evidence.injuries?.status} className="rounded-xl border border-[#D7DFDE] bg-white p-3">
       <div className="flex items-center gap-1 text-[10px] font-black uppercase tracking-wider text-[#166A79]"><Activity size={13}/>ESPN injury observation</div>
       <p className="mt-1.5 text-sm font-black text-[#173E52]">{injuries?'Recent team reports':'Verified recent status unavailable'}</p>
       <p className="mt-1 text-[11px] font-semibold text-slate-600">{injuries?dateET(evidence.injuries.source_observed_at):'No verified current source time'}</p>
       <p className="mt-2 text-[10px] font-semibold leading-4 text-amber-900">Never treats “Active,” absence, or an injury listing as starter/clearance confirmation.</p>
      </article>
     </div>
     <details className="group mt-2 rounded-xl border border-[#D7DFDE] bg-white p-3">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-[11px] font-black text-[#173E52]">
       <span className="min-w-0">Review reported player details · {evidence.injuries?.selected_team?.reported_count_in_source??0} {evidence.team.split(' ').at(-1)} · {evidence.injuries?.opponent?.reported_count_in_source??0} {evidence.opponent.split(' ').at(-1)}</span>
       <ChevronRight size={16} className="shrink-0 text-[#166A79] transition group-open:rotate-90" />
      </summary>
      <div className="mt-2 grid gap-2 border-t border-slate-100 pt-2 sm:grid-cols-2">
       <TeamInjuryNotes heading={evidence.team} group={evidence.injuries?.selected_team} coverage={injuries}/>
       <TeamInjuryNotes heading={evidence.opponent} group={evidence.injuries?.opponent} coverage={injuries}/>
      </div>
     </details>
     <p className="mt-2 flex items-start gap-1.5 text-[10px] font-medium leading-[1.55] text-slate-600">
      <ShieldAlert size={14} className="mt-0.5 shrink-0 text-amber-700"/>
      <span>Source records are time-stamped but not full active/inactive rosters. Original primary live book prices, independent Zenith advantage and pool selection remain unverified. No pick is saved here.</span>
     </p>
     <p className="mt-1 text-[10px] font-medium text-slate-400"><Clock3 size={12} className="mr-1 inline"/> Last evidence check: {dateET(evidence.checked_at)} · Official ESPN game ID {evidence.event_id}</p>
    </>
   )}
  </section>
 )
}
