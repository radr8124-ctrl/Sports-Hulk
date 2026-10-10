// STRICTLY SYNTHETIC OWNER QA. This is not bundled into the production index.
// Every API call is intercepted by the acceptance test; no real pick is saved.
import React,{useState} from 'react'
import ReactDOM from 'react-dom/client'
import SurvivorPickEditor from '../src/SurvivorPickEditor.jsx'
import SurvivorPoolImport from '../src/SurvivorPoolImport.jsx'
import SurvivorScoreCards from '../src/SurvivorScoreCards.jsx'
import SurvivorCommandCover from '../src/SurvivorCommandCover.jsx'
import '../src/styles.css'
const burned=['Los Angeles Chargers','San Francisco 49ers','Kansas City Chiefs','Buffalo Bills','Minnesota Vikings']
const getAccessToken=async()=>'LOCAL_SYNTHETIC_REVIEW_TOKEN_NEVER_PRODUCTION'
const cards=[{
 week:4,pick_number:1,team:'Minnesota Vikings',opponent:'Miami Dolphins',
 score_line:'Miami Dolphins 10 - Minnesota Vikings 15',game_clock:'FINAL',
 pool_result:'SURVIVED',game_state:'FINAL_SAVED_RESULT',pool_submitted:true,
}]
function ReviewHarness(){
 const [refresh,setRefresh]=useState(0)
 const [entryStatus,setEntryStatus]=useState('ALIVE')
 return <main className="mx-auto max-w-4xl space-y-3 p-3 sm:p-6">
   <div className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-black text-amber-900">SYNTHETIC OWNER QA · ZERO REAL ACCOUNT ACCESS OR WRITES</div>
   <SurvivorCommandCover signedIn={true} hasEntry={true} entryStatus={entryStatus}
     poolWeek={5} usedTeams={burned} currentPicks={[]} requiredPicks={1}
     ruleConfirmed={true} officialPoolWeek={4} recommendationStatus="WAIT_FOR_FRESH_VERIFIED_MARKET_QUOTES" shadowRecommendation={[]} />
   <section className="rounded-xl border border-slate-200 bg-white p-3 text-xs font-semibold text-slate-600">
     <button type="button" aria-label="Switch test entry activity" onClick={()=>setEntryStatus(s=>s==='ALIVE'?'ELIMINATED':'ALIVE')} className="rounded bg-slate-100 p-2">Toggle synthetic entry status</button>
     <span className="ml-3">Synthetic session refreshes: {refresh}</span>
   </section>
   <SurvivorPickEditor entryName="SYNTHETIC QA 01" poolWeek={5} entryStatus={entryStatus}
     usedTeams={burned} currentPicks={[]} requiredPicks={1} ruleConfirmed={true}
     getAccessToken={getAccessToken} onSaved={()=>setRefresh(v=>v+1)} />
   <SurvivorScoreCards cards={cards} entryName="SYNTHETIC QA 01" />
   <SurvivorPoolImport getAccessToken={getAccessToken} onImported={()=>setRefresh(v=>v+1)} />
 </main>
}
ReactDOM.createRoot(document.getElementById('root')).render(<ReviewHarness/>)
