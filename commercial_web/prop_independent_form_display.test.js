import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {validateIndependentForm,matchIndependentForm,recentFormDescription} from './prop_independent_form_display.js'

const research=JSON.parse(fs.readFileSync(new URL('./public/nfl_prop_independent_research.json',import.meta.url)))
const props=JSON.parse(fs.readFileSync(new URL('./public/prop_v2_current.json',import.meta.url)))
const NOW=Date.parse('2026-10-09T23:41:00Z')
const form=validateIndependentForm(research,NOW)

test('Original independent NFL four-week research passes original source contracts',()=>{
 assert.equal(form.length,26)
 assert.ok(form.every(x=>x.history_games===4&&x.approved_play===false&&x.independent_model_beats_sportsbook_proven===false))
 assert.ok(form.every(x=>x.official_pre_kickoff_player_injury_and_active_confirmation_verified===false))
 assert.ok(form.every(x=>x.start_ms>NOW&&x.quote_ms<NOW))
})

test('Every existing NFL prop and PrizePicks current event joins uniquely by exact player market side line and clock',()=>{
 for(const [lane,count,strong] of [['PROP',26,15],['PRIZEPICKS',14,10]]){
  const current=props.picks.filter(x=>x.sport==='NFL'&&x.lane===lane)
  assert.equal(current.length,count)
  const merged=current.map(x=>matchIndependentForm(x,lane,form,NOW))
  assert.equal(merged.filter(Boolean).length,count)
  assert.equal(merged.filter(x=>x?.hit_count>=3).length,strong)
  assert.ok(merged.every(x=>!x||(!x.approved_pick&&!x.independently_proven_edge&&!x.projection_calibrated)))
 }
})

test('Wrong line, side, market, sport or kickoff is never attached',()=>{
 const row=props.picks.find(x=>x.sport==='NFL'&&x.lane==='PRIZEPICKS')
 assert.ok(matchIndependentForm(row,'PRIZEPICKS',form,NOW))
 for(const change of [
  {line:Number(row.line)+1},{side:row.side==='OVER'?'UNDER':'OVER'},
  {sport:'NHL'},{player:'unidentified player'},{market_subtype:'PLAYER_TOTAL_HOME_RUNS'},
  {event_start:'2026-10-14T13:30:00Z'},
 ]){
  assert.equal(matchIndependentForm({...row,...change},'PRIZEPICKS',form,NOW),null)
 }
 const duplicate=[...form,form.find(x=>x.player===row.player&&x.market===row.market_subtype&&x.side===row.side&&x.line===row.line)]
 assert.equal(matchIndependentForm(row,'PRIZEPICKS',duplicate,NOW),null)
})

test('Cannot elevate historical 4/4 results into proven profitability',()=>{
 const r=matchIndependentForm(props.picks.find(x=>x.player==='Trevor Lawrence'&&x.lane==='PRIZEPICKS'),
  'PRIZEPICKS',form,NOW)
 assert.equal(r.hit_count,4)
 assert.equal(recentFormDescription(r).label,'Recent-form watch')
 assert.equal(r.projection_calibrated,false)
 assert.equal(r.approved_pick,false)
 const weak=matchIndependentForm(props.picks.find(x=>x.player==='Jakobi Meyers'&&x.lane==='PRIZEPICKS'),
 'PRIZEPICKS',form,NOW)
 assert.equal(weak.hit_count,1)
 assert.equal(recentFormDescription(weak).label,'Recent form cautions')
})

test('Missing or fake original safeguards invalidate the entire form feed',()=>{
 for(const edit of [
  {schema:'UNKNOWN'},{real_wagers_placed:true},{unproven_model_not_recommendations:false},
  {prizepicks_payout_not_sportsbook_american_odds:false},
  {must_verify_sportsbook_quote_and_game_day_injuries_before_any_bet:false},
 ])assert.deepEqual(validateIndependentForm({...research,...edit},NOW),[])
})
