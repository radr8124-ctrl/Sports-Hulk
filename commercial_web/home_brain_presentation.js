// Explicitly different from shadow research, paper bankroll and model win rate.
// Only authentic published/settled official picks go into this small-sample card.
const count=x=>Number.isSafeInteger(x)&&x>=0?x:null
const formatOdds=x=>{
 const n=Number(x)
 return Number.isFinite(n) && Math.abs(n)>=100 ? (n>0?'+':'')+n : 'price unverified'
}
export function homeBrainSnapshot(snapshot={}){
 const o=snapshot?.official||{}
 const wins=count(o.wins),losses=count(o.losses),pushes=count(o.pushes)
 const settled=count(o.settled),published=count(o.published),pending=count(o.pending)
 const ready=[wins,losses,pushes,settled,published,pending].every(x=>x!==null)
   &&wins+losses+pushes===settled&&settled+pending===published
 if(!ready)return {status:'SOURCE_UNVERIFIED',headline:'Official picks not verified',summary:'Waiting for consistent published results.',lastResult:null,graded:0,pending:null}
 const records=Array.isArray(snapshot.official_recent)?snapshot.official_recent:[]
 const reviewed=records.filter(row=>
   row?.official===true && row.event_type==='SETTLED'
   && ['WIN','LOSS','PUSH'].includes(String(row.grade))
   && typeof row.selection==='string' && row.selection.trim()
   && Number.isFinite(Date.parse(row.settled_at||'')))
   .sort((a,b)=>Date.parse(b.settled_at)-Date.parse(a.settled_at))
 const last=reviewed[0]||null
 const lastResult=last?{
   pick:`${last.selection} to win (${formatOdds(last.american_odds)})`,
   outcome:last.grade==='WIN'?'Won':last.grade==='LOSS'?'Lost':'Push',
   score:typeof last.result==='string'?last.result:null,
   event:typeof last.game_key==='string'?last.game_key:null,
 }:null
 const result=settled===1? '1 pick graded' : `${settled} picks graded`
 return {
   status:'READY',
   headline:result,
   summary:`${wins} win${wins===1?'':'s'} · ${losses} loss${losses===1?'':'es'} · ${pending} pending`,
   clarity: 'Official published picks only—not every Zenith model or research test.',
   sampleWarning: settled<20?'Too few graded picks to judge performance yet.':'Open Brain Record for the full verified sample.',
   lastResult,
   graded:settled,pending, published,
 }
}
