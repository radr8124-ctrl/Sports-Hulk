// Display-only proof projection for Props/PrizePicks. Source snapshots are not
// executable quotes, approved wagers, personal winnings, or entry-payout proof.
// Do not pool different sports' Brier scores or promote an isolated high hit rate.
const SPORTS=['NFL','NBA','NHL','MLB']
const MAX_SOURCE_AGE_MS=36*60*60*1000
const MAX_FUTURE_SKEW_MS=5*60*1000
const isCount=v=>Number.isSafeInteger(v)&&v>=0
const isFiniteNumber=v=>typeof v==='number'&&Number.isFinite(v)
const validRate=v=>v===null || (isFiniteNumber(v)&&v>=0&&v<=100)
const statusOnly=(status,lane,sport)=>({
 status,lane,sport,scope:sport||'ALL',settled:null,tracked:null,independent_blocks:null,
 market_brier:null,v2_brier:null,v2_minus_market_brier:null,hit_rate_pct:null,
 paper_roi_pct:null,relative_model_reading:'UNVERIFIED',sport_breakdown:[],
 entry_economics:'NOT_VERIFIED',qualifies_bet:false,proven_edge:false,
 payout_verified:false,live_book_offer_verified:false,real_cash_profit_verified:false,
 source_generated_at:null,
})

function readOne(row,sport,lane){
 const a=row?.all_predictions
 if(!a||!isCount(a.tracked)||!isCount(a.pending)||!isCount(a.settled)||
    !isCount(a.decisions)||!isCount(a.wins)||!isCount(a.losses)||!isCount(a.pushes)||
    !isCount(a.independent_blocks)||a.pending+a.settled!==a.tracked||
    a.wins+a.losses+a.pushes!==a.settled||a.decisions!==a.settled||
    a.independent_blocks>a.settled||!validRate(a.hit_rate_pct))return null
 if(a.settled>0&&(
    !isFiniteNumber(a.market_brier)||a.market_brier<0||a.market_brier>1||
    !isFiniteNumber(a.v2_brier)||a.v2_brier<0||a.v2_brier>1||
    !isFiniteNumber(a.v2_minus_market_brier)||
    Math.abs(a.v2_minus_market_brier-(a.v2_brier-a.market_brier))>0.00003
 ))return null
 if(a.settled===0&&(a.market_brier!==null||a.v2_brier!==null||a.v2_minus_market_brier!==null||a.hit_rate_pct!==null))return null
 if(a.roi_pct!==null&&!isFiniteNumber(a.roi_pct))return null
 const relative=a.settled===0?'AWAITING_SETTLEMENT'
   :a.v2_minus_market_brier>0.00003?'MODEL_WORSE_THAN_MARKET'
     :a.v2_minus_market_brier< -0.00003?'MODEL_BETTER_THAN_MARKET_IN_RESEARCH_ONLY'
       :'NO_DEMONSTRATED_MARKET_DIFFERENCE'
 return {
  sport,lane,tracked:a.tracked,settled:a.settled,independent_blocks:a.independent_blocks,
  hit_rate_pct:a.settled?a.hit_rate_pct:null,
  market_brier:a.settled?a.market_brier:null,
  v2_brier:a.settled?a.v2_brier:null,
  v2_minus_market_brier:a.settled?a.v2_minus_market_brier:null,
  relative_model_reading:relative,
  // These are ONLY source-reported paper performance on historical book references.
  // Pick-em legs never have a verified whole-entry payout/ROI in this feed.
  paper_roi_pct:lane==='PROP'&&a.priced_settled>0&&isFiniteNumber(a.roi_pct)
    ?a.roi_pct:null,
  proof_status:String(a.proof_status||'UNVERIFIED'),
 }
}

export function projectPropForwardTruth({forward,current,lane='PROP',sport='ALL',atMs=Date.now()}={}){
 const invalid=status=>statusOnly(status,lane,sport)
 if(!['PROP','PRIZEPICKS'].includes(lane))return invalid('UNSUPPORTED_LANE')
 if(!['ALL',...SPORTS].includes(sport))return invalid('UNSUPPORTED_SPORT')
 if(!forward||!current)return invalid('SOURCE_NOT_AVAILABLE')
 if(forward.status!=='READY'||current.status!=='READY'||
    !forward.model_version||forward.model_version!==current.model_version)return invalid('SOURCE_VERSION_CONFLICT')
 const sourceTime=Date.parse(forward.generated_at||'')
 const currentTime=Date.parse(current.generated_at||'')
 if(!Number.isFinite(atMs)||!Number.isFinite(sourceTime)||!Number.isFinite(currentTime)||
  sourceTime>atMs+MAX_FUTURE_SKEW_MS||currentTime>atMs+MAX_FUTURE_SKEW_MS||
  atMs-sourceTime>MAX_SOURCE_AGE_MS||atMs-currentTime>MAX_SOURCE_AGE_MS){
  return invalid('SOURCE_STALE_OR_CLOCK_CONFLICT')
 }
 const wanted=sport==='ALL'?SPORTS:[sport]
 const rows=[]
 for(const league of wanted){
  const r=readOne(forward.by_lane?.[league+'_'+lane],league,lane)
  if(!r)return invalid(forward.by_lane?.[league+'_'+lane]?'SOURCE_COUNT_CONFLICT':'SOURCE_NOT_AVAILABLE')
  rows.push(r)
 }
 const select=sport==='ALL'?null:rows[0]
 const total=rows.reduce((n,r)=>n+r.settled,0)
 return {
  status:'SOURCE_TRACKED_RESEARCH_ONLY',lane,sport,scope:sport,
  settled:total,tracked:rows.reduce((n,r)=>n+r.tracked,0),
  independent_blocks:rows.reduce((n,r)=>n+r.independent_blocks,0),
  hit_rate_pct:select?.hit_rate_pct??null,
  market_brier:select?.market_brier??null,
  v2_brier:select?.v2_brier??null,
  v2_minus_market_brier:select?.v2_minus_market_brier??null,
  relative_model_reading:select?.relative_model_reading||'SPORT_SEGMENTS_NOT_POOLED',
  paper_roi_pct:select?.paper_roi_pct??null,
  source_generated_at:new Date(sourceTime).toISOString(),
  sport_breakdown:rows,
  // Never promote even a forged PROVEN marker into personal picks or claims.
  entry_economics:'NOT_VERIFIED',qualifies_bet:false,proven_edge:false,
  payout_verified:false,live_book_offer_verified:false,real_cash_profit_verified:false,
  note:'Forward shadow research, not an approved wager, independent live offer, or verified profitable bet.',
 }
}
