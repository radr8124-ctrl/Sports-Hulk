// STRICTLY SYNTHETIC OWNER QA. This is not bundled into the production index.
// Every API call is intercepted by the acceptance test; no real pick is saved.
import React,{useState} from 'react'
import ReactDOM from 'react-dom/client'
import SurvivorPickEditor from '../src/SurvivorPickEditor.jsx'
import SurvivorPoolImport from '../src/SurvivorPoolImport.jsx'
import SurvivorScoreCards from '../src/SurvivorScoreCards.jsx'
import SurvivorPastPicks from '../src/SurvivorPastPicks.jsx'
import {buildSurvivorPastPickHistory} from '../survivor_past_picks.js'
import SurvivorCommandCover from '../src/SurvivorCommandCover.jsx'
import '../src/styles.css'
const burned=['Los Angeles Chargers','San Francisco 49ers','Kansas City Chiefs','Buffalo Bills','Minnesota Vikings']
const getAccessToken=async()=>'LOCAL_SYNTHETIC_REVIEW_TOKEN_NEVER_PRODUCTION'
const syntheticOpenWindow={
 status:'WINDOW_OPEN',pool_week:5,editable_teams:['Jacksonville Jaguars','Houston Texans','Cincinnati Bengals'],
 editable_team_cutoffs:{
  'Jacksonville Jaguars':'2099-10-10T22:00:00.000Z',
  'Houston Texans':'2099-10-10T22:00:00.000Z',
  'Cincinnati Bengals':'2099-10-10T22:00:00.000Z',
 },
 week_saturday_deadline:'2099-10-10T22:00:00.000Z',
 external_pool_result_verified:false,live_external_pool_submission_verified:false,
}
const syntheticClosedWindow={...syntheticOpenWindow,status:'WINDOW_CLOSED',
 reason:'SATURDAY_POOL_DEADLINE_PASSED',editable_teams:[],editable_team_cutoffs:{},
 week_saturday_deadline:'2026-10-10T22:00:00.000Z'}
// Synthetic linked-entry test history only. Original real member state is
// NEVER loaded in this public local browser QA harness.
const syntheticPast=buildSurvivorPastPickHistory({
 status:'ALIVE',current_week:5,current_picks:[],used_teams:burned,
 history:[
  {week:1,team:'Los Angeles Chargers',result:'SURVIVED',source:'SYNTHETIC_WEEK2_OFFICIAL.pdf'},
  {week:2,team:'San Francisco 49ers',result:'SURVIVED',source:'SYNTHETIC_WEEK2_OFFICIAL.pdf'},
  {week:3,team:'Kansas City Chiefs',result:'SURVIVED',source:'SYNTHETIC_SCHEDULE.csv'},
  {week:3,team:'Buffalo Bills',result:'SURVIVED',source:'SYNTHETIC_SCHEDULE.csv'},
  {week:4,team:'Minnesota Vikings',result:'SURVIVED',source:'SYNTHETIC_SCHEDULE.csv'},
 ],
 week_3:{required_picks:2,picks:[
  {team:'Kansas City Chiefs',result:'WIN',game_status:'FINAL: Kansas City Chiefs 24 - Miami Dolphins 10'},
  {team:'Buffalo Bills',result:'WIN',game_status:'FINAL: Los Angeles Chargers 16 - Buffalo Bills 24'},
 ],submitted:true,official_pool_sheet_confirmed:true},
 week_4:{required_picks:1,picks:[
  {team:'Minnesota Vikings',result:'WIN',game_status:'FINAL: Miami Dolphins 10 - Minnesota Vikings 15'},
 ],submitted:false,official_pool_sheet_confirmed:true},
 week_5:{picks:[],entry_result:'OPEN',submitted:false},
},5)

const cards=[{
 week:4,pick_number:1,team:'Minnesota Vikings',opponent:'Miami Dolphins',
 score_line:'Miami Dolphins 10 - Minnesota Vikings 15',game_clock:'FINAL',
 pool_result:'SURVIVED',game_state:'FINAL_SAVED_RESULT',pool_submitted:true,
}]
function ReviewHarness(){
 const [refresh,setRefresh]=useState(0)
 const [entryStatus,setEntryStatus]=useState('ALIVE')
 const [deadlineClosed,setDeadlineClosed]=useState(false)
 return <main className="mx-auto max-w-4xl space-y-3 p-3 sm:p-6">
   <div className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-black text-amber-900">SYNTHETIC OWNER QA · ZERO REAL ACCOUNT ACCESS OR WRITES</div>
   <SurvivorCommandCover signedIn={true} hasEntry={true} entryStatus={entryStatus}
     poolWeek={5} usedTeams={burned} currentPicks={[]} requiredPicks={1}
     ruleConfirmed={true} officialPoolWeek={4} recommendationStatus="WAIT_FOR_FRESH_VERIFIED_MARKET_QUOTES" shadowRecommendation={[]} />
   <section className="rounded-xl border border-slate-200 bg-white p-3 text-xs font-semibold text-slate-600">
     <button type="button" aria-label="Switch test entry activity" onClick={()=>setEntryStatus(s=>s==='ALIVE'?'ELIMINATED':'ALIVE')} className="rounded bg-slate-100 p-2">Toggle synthetic entry status</button>
     <button type="button" aria-label="Toggle synthetic pool deadline" onClick={()=>setDeadlineClosed(value=>!value)} className="ml-2 rounded bg-slate-100 p-2">Toggle synthetic pool deadline</button>
     <span className="ml-3">Synthetic session refreshes: {refresh}</span>
   </section>
   <SurvivorPastPicks history={syntheticPast} entryName="SYNTHETIC QA 01" />
   <SurvivorPickEditor entryName="SYNTHETIC QA 01" poolWeek={5} entryStatus={entryStatus}
     usedTeams={burned} currentPicks={[]} requiredPicks={1} ruleConfirmed={true}
     pickWindow={deadlineClosed?syntheticClosedWindow:syntheticOpenWindow}
     getAccessToken={getAccessToken} onSaved={()=>setRefresh(v=>v+1)} />
   <SurvivorScoreCards cards={cards} entryName="SYNTHETIC QA 01" />
   <SurvivorPoolImport getAccessToken={getAccessToken} onImported={()=>setRefresh(v=>v+1)} />
 </main>
}
ReactDOM.createRoot(document.getElementById('root')).render(<ReviewHarness/>)
