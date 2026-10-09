import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {showFrozenNFLResearch} from './nfl_frozen_forecast_presentation.js'

const data=JSON.parse(readFileSync(new URL('./public/nfl_frozen_game_intelligence.json',import.meta.url),'utf8'))
const now=Date.parse('2026-10-09T18:50:00Z')

test('source-verifiable 13 NFL score-form forecasts are research only, not new official bets',()=>{
 const result=showFrozenNFLResearch(data,now)
 assert.equal(result.status,'FROZEN_RESEARCH')
 assert.equal(result.blocked,true)
 assert.equal(result.rows.length,13)
 assert.equal(new Set(result.rows.map(x=>x.event_id)).size,13)
 assert.equal(result.originalLedgerSha,'b74351d24c0cf591624a74c8dc2d33f84ea34f1374c65d782219bc5d95b60602')
 for(const r of result.rows) {
  assert.equal(r.approved_play,false)
  assert.equal(r.model_beats_market_out_of_sample_proven,false)
  assert.equal(r.actual_sportsbook_executable_current_price_verified,false)
  assert.equal(r.score_form_model_historical_2025_worse_than_market_baseline,true)
  assert.equal(r.originalPriceTooOldForLiveContext,false)
  assert.equal(r.priceAgeHours>0,true)
 }
})

test('quote age increases after new day without ever rewriting quote time',()=>{
 const at=Date.parse('2026-10-10T06:00:00Z')
 const later=showFrozenNFLResearch(data,at)
 assert.equal(later.rows.length,13)
 assert.ok(later.rows.every(x=>x.originalPriceTooOldForLiveContext))
 assert.equal(data.rows[0].original_book_price_under_24_hour_recency_limit_at_publication,true)
 assert.equal(later.rows[0].book_quote_last_updated_at_utc,data.rows[0].book_quote_last_updated_at_utc)
})

test('original games disappear after kickoff; no old game silently appears as next bet',()=>{
 const at=Date.parse('2026-10-12T02:00:00Z')
 const a=showFrozenNFLResearch(data,at)
 assert.equal(a.rows.length,0)
 assert.equal(a.blocked,true)
})

test('refuse tampered source claiming invented winning edge or fresh sportsbook executable',()=>{
 for(const [key,value] of [
  ['historic_2025_holdout_model_better_than_market',true],
  ['wagers_created_or_bets_promoted',true],
  ['real_book_executability_verified',true],
  ['market_source_cannot_upgrade_stale_primary_NFL_live_best_bets',false],
 ]){
  const mutated={...data,[key]:value}
  const result=showFrozenNFLResearch(mutated,now)
  assert.deepEqual(result.rows,[],key)
  assert.equal(result.status,'UNVERIFIED_SOURCE')
 }
})

test('skip future-dated quote, false bookmaker, and invalid probabilities',()=>{
 for(const patch of [
  {book_quote_last_updated_at_utc:'2026-10-10T20:00:00Z'},
  {book_name:'Unknown wager'},
  {model_beats_market_out_of_sample_proven:true},
  {forecast_home_pct:105},
  {original_home_american_price:0},
  {model_uses_market_input:false}
 ]){
  const mutated={...data,rows:data.rows.map((r,i)=>i===0?{...r,...patch}:r)}
  const result=showFrozenNFLResearch(mutated,now)
  assert.equal(result.rows.length,12,JSON.stringify(patch))
 }
})

test('published research features and original price are not fabricated as bets',()=>{
 const r=showFrozenNFLResearch(data,now).rows
 assert.ok(r.every(x=>x.forecast_frozen_at_utc && x.source_model_version))
 assert.ok(r.every(x=>Number.isFinite(x.source_sample_actual_home_away_previous_three_game_margin_diff_scaled14)))
 assert.equal(r.filter(x=>x.delta_model_minus_book_home_pp>=4).length,0)
 assert.ok(r.some(x=>x.delta_model_minus_book_home_pp< -3))
})
