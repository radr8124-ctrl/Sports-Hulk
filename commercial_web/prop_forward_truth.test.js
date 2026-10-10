import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {projectPropForwardTruth} from './prop_forward_truth.js'
const clock=Date.parse('2026-10-10T21:05:00Z')
const copy=x=>structuredClone(x)
const rec=(tracked,settled,blocks,market,v2,hit,roi,proof='NOT_PROVEN')=>({
 all_predictions:{tracked,settled,pending:tracked-settled,decisions:settled,
  wins:Math.round(settled*hit/100),losses:settled-Math.round(settled*hit/100),pushes:0,
  hit_rate_pct:hit,independent_blocks:blocks,market_brier:market,v2_brier:v2,
  v2_minus_market_brier:market==null?null:+(v2-market).toFixed(5),
  priced_settled:roi==null?0:Math.floor(settled*.95),roi_pct:roi,proof_status:proof},
 promotion:{recommendation:'HOLD_PROBABILITY_PROOF_REQUIRED',automatic_promotion:false,
  economics_gate:{status:'ENTRY_LEVEL_PAYOUT_PROOF_REQUIRED'}}
})
const model='PROP_V2_PHASE4_SUBTYPE_VETO_2026_10_05'
const current={status:'READY',generated_at:'2026-10-10T20:23:26Z',model_version:model,
 summary:{candidates:200,shadow_plays:0,shadow_monitors:0,passes:200}}
const forward={status:'READY',generated_at:'2026-10-10T20:23:52Z',model_version:model,
 by_lane:{
  NHL_PROP:rec(2200,1888,31,.201,.20674,58.6,-3.37),
  NHL_PRIZEPICKS:rec(188,143,29,.224,.22563,54.5,3.96,'BUILDING_FORWARD_SAMPLE'),
  NFL_PROP:rec(120,31,2,.25052,.25052,48.4,-14.22,'BUILDING_FORWARD_SAMPLE'),
  NFL_PRIZEPICKS:rec(72,26,2,.24648,.25111,46.2,null,'BUILDING_FORWARD_SAMPLE'),
  NBA_PROP:rec(120,0,0,null,null,null,null,'BUILDING_FORWARD_SAMPLE'),
  NBA_PRIZEPICKS:rec(68,0,0,null,null,null,null,'BUILDING_FORWARD_SAMPLE'),
  MLB_PROP:rec(1394,988,9,.194,.194,70.1,-.94,'BUILDING_FORWARD_SAMPLE'),
  MLB_PRIZEPICKS:rec(124,89,9,.205,.20648,55.1,8.27,'BUILDING_FORWARD_SAMPLE')
 }}
const call=(options={})=>projectPropForwardTruth({forward,current,lane:'PROP',sport:'NHL',atMs:clock,...options})

test('NHL Props separates a high raw hit rate from negative market-model Brier and paper ROI',()=>{
 const v=call()
 assert.equal(v.status,'SOURCE_TRACKED_RESEARCH_ONLY')
 assert.equal(v.lane,'PROP')
 assert.equal(v.scope,'NHL')
 assert.equal(v.settled,1888)
 assert.equal(v.independent_blocks,31)
 assert.equal(v.hit_rate_pct,58.6)
 assert.equal(v.market_brier,0.201)
 assert.equal(v.v2_brier,.20674)
 assert.equal(v.v2_minus_market_brier,.00574)
 assert.equal(v.relative_model_reading,'MODEL_WORSE_THAN_MARKET')
 assert.equal(v.paper_roi_pct,-3.37)
 assert.equal(v.payout_verified,false)
 assert.equal(v.qualifies_bet,false)
 assert.equal(v.proven_edge,false)
})

test('PrizePicks never displays leg-level pricing proxy as a full pick-em entry ROI',()=>{
 const v=call({lane:'PRIZEPICKS',sport:'NHL'})
 assert.equal(v.settled,143)
 assert.equal(v.independent_blocks,29)
 assert.equal(v.paper_roi_pct,null)
 assert.equal(v.payout_verified,false)
 assert.equal(v.entry_economics,'NOT_VERIFIED')
 assert.equal(v.qualifies_bet,false)
 assert.equal(v.relative_model_reading,'MODEL_WORSE_THAN_MARKET')
})

test('NBA unsettled shows no Brier or hit rate instead of zero-success sample',()=>{
 const v=call({sport:'NBA'})
 assert.equal(v.settled,0)
 assert.equal(v.hit_rate_pct,null)
 assert.equal(v.relative_model_reading,'AWAITING_SETTLEMENT')
 assert.equal(v.market_brier,null)
 assert.equal(v.v2_brier,null)
 assert.equal(v.paper_roi_pct,null)
})

test('All-sports shows segmented totals without pooling incomparable Brier and entry ROI',()=>{
 const p=call({sport:'ALL'})
 const pp=call({lane:'PRIZEPICKS',sport:'ALL'})
 assert.equal(p.status,'SOURCE_TRACKED_RESEARCH_ONLY')
 assert.equal(p.settled,2907)
 assert.equal(p.market_brier,null)
 assert.equal(p.v2_brier,null)
 assert.equal(p.paper_roi_pct,null)
 assert.equal(p.sport_breakdown.length,4)
 assert.equal(pp.settled,258)
 assert.equal(pp.market_brier,null)
 assert.equal(pp.paper_roi_pct,null)
 assert.equal(pp.sport_breakdown.length,4)
 assert.equal(p.proven_edge,false)
})

test('changed model version, stale timestamp, future timestamp and malformed counts fail closed',()=>{
 const x=copy(current);x.model_version='UNRELATED_MODEL'
 assert.equal(call({current:x}).status,'SOURCE_VERSION_CONFLICT')
 const old=copy(forward);old.generated_at='2026-10-02T12:00:00Z'
 assert.equal(call({forward:old}).status,'SOURCE_STALE_OR_CLOCK_CONFLICT')
 const future=copy(forward);future.generated_at='2026-10-11T12:00:00Z'
 assert.equal(call({forward:future}).status,'SOURCE_STALE_OR_CLOCK_CONFLICT')
 const tamper=copy(forward);tamper.by_lane.NHL_PROP.all_predictions.settled=2000
 assert.equal(call({forward:tamper}).status,'SOURCE_COUNT_CONFLICT')
 const fake=copy(forward);fake.by_lane.NHL_PROP.all_predictions.v2_minus_market_brier=-.08002
 assert.equal(call({forward:fake}).status,'SOURCE_COUNT_CONFLICT')
})

test('unsupported lane or missing source cannot produce an attractive proof claim',()=>{
 assert.equal(call({lane:'DFS'}).status,'UNSUPPORTED_LANE')
 assert.equal(call({forward:null}).status,'SOURCE_NOT_AVAILABLE')
 assert.equal(call({sport:'CBB'}).status,'UNSUPPORTED_SPORT')
 const missing=copy(forward);delete missing.by_lane.NHL_PROP
 assert.equal(call({forward:missing}).status,'SOURCE_NOT_AVAILABLE')
})

test('a forged PROVEN marker never turns research source into executable bet approval',()=>{
 const forged=copy(forward)
 forged.by_lane.NHL_PROP.all_predictions.proof_status='PROVEN'
 const v=call({forward:forged})
 assert.equal(v.status,'SOURCE_TRACKED_RESEARCH_ONLY')
 assert.equal(v.qualifies_bet,false)
 assert.equal(v.proven_edge,false)
 assert.equal(v.payout_verified,false)
})

test('live data readback uses original per-lane observations but never promotes shadow picks',()=>{
 const f=JSON.parse(readFileSync(new URL('./public/prop_v2_forward.json',import.meta.url),'utf8'))
 const c=JSON.parse(readFileSync(new URL('./public/prop_v2_current.json',import.meta.url),'utf8'))
 const at=Math.max(Date.parse(f.generated_at),Date.parse(c.generated_at))+60*1000
 for(const lane of ['PROP','PRIZEPICKS'])for(const sport of ['NFL','NBA','NHL','MLB','ALL']){
  const v=call({lane,sport,forward:f,current:c,atMs:at})
  assert.equal(v.status,'SOURCE_TRACKED_RESEARCH_ONLY',`${lane} ${sport}: ${v.status}`)
  assert.equal(v.qualifies_bet,false)
  assert.equal(v.proven_edge,false)
  assert.equal(v.payout_verified,false)
  assert.ok(v.settled>=0)
  if(lane==='PRIZEPICKS')assert.equal(v.paper_roi_pct,null)
 }
})
