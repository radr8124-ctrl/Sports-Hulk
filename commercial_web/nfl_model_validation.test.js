import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import {assessNflForwardModelProof} from './nfl_model_validation.js'

const base='../intelligence_warehouse/nfl_advanced_pregame/'
const forecastsText=readFileSync(base+'NFL_FIRST_PREKICKOFF_NINE_FEATURE_SCORE_FORM_SHADOW.jsonl','utf8')
const finalText=readFileSync(base+'NFL_2026_FIRST_FUTURE_EVENT_ESPN_FINAL_ORIGINAL_SOURCE.jsonl','utf8')
const gradedText=readFileSync(base+'NFL_NINE_FEATURE_SAME_BOOK_OFFICIAL_FINAL_SCORES.jsonl','utf8')
const summary=JSON.parse(readFileSync(base+'NFL_NINE_FEATURE_OFFICIAL_FINAL_COMPARISON_SUMMARY.json','utf8'))
const originalPublic=JSON.parse(readFileSync('./public/nfl_frozen_game_intelligence.json','utf8'))
const sha=text=>createHash('sha256').update(text).digest('hex')
const source={forecastsText,finalText,gradedText,summary,originalPublic}
const first=JSON.parse(forecastsText.split('\n').filter(Boolean)[0])
const nowMs=Date.parse('2026-10-10T20:10:00Z')
const view=(x={})=>assessNflForwardModelProof({...source,nowMs,...x})

const buildSynthetic=(forecast=first,{result='HOME_WIN'}={})=>{
 const win=result==='HOME_WIN'?1:0
 const forecastStart=Date.parse(forecast.official_first_pitch_utc)
 const after=new Date(forecastStart+3*60*60*1000).toISOString()
 const homeScore=win?24:17,awayScore=win?16:24
 const finale={schema:'NFL_2026_ESPN_GAME_ID_SCORE_FINAL_SOURCE_MATCH_V1',
  official_espn_game_id:forecast.official_espn_event_id,official_espn_final_confirmed:true,
  season:forecast.season,week:forecast.week,home_team:forecast.home_team,away_team:forecast.away_team,
  source_first_pitch_utc:forecast.official_first_pitch_utc,final_observed_at_utc:after,
  home_points:homeScore,away_points:awayScore,
  source_weekly_espn_payload_sha256:'a'.repeat(64),source_season_schedule_sha256:'b'.repeat(64),
 }
 const grade={schema:'NFL_2026_RESEARCH_NINE_FEATURE_SAME_BOOK_VS_INDEPENDENT_ESPN_FINAL_SCORE_V1',
  official_espn_event_id:forecast.official_espn_event_id,season:forecast.season,week:forecast.week,
  home_team:forecast.home_team,away_team:forecast.away_team,
  official_home_points:homeScore,official_away_points:awayScore,
  original_home_moneyline_win_binary_outcome:win,
  independent_game_block_id:forecast.official_espn_event_id,
  source_real_original_final_observed_at_utc:after,
  source_original_espn_final_scoreboard_sha256:finale.source_weekly_espn_payload_sha256,
  one_NFL_match_counts_as_one_independent_source_event:true,
  source_first_original_model_frozen_at_utc:forecast.source_first_real_future_prediction_frozen_at_utc,
  original_model_sha256:forecast.source_frozen_model_sha256,
  not_sportsbook_settlement_or_wager_win:true,research_only:true,
  live_play_approved:false,profitable_market_edge_proven:false,sportsbook_wager_executed:false,
 }
 for(const [label,key] of [['raw_book','original_raw_book_home_fair'],
  ['market_only','market_only_calibrated_home_win_prob'],
  ['score_form','nine_feature_score_form_home_win_prob']]){
  const p=forecast[key]; grade[label+'_original_pregame_home_win_probability']=p
  grade[label+'_squared_error']=Math.round((p-win)**2*1e12)/1e12
  grade[label+'_log_loss']=Math.round(-Math.log(win?p:1-p)*1e12)/1e12
 }
 return {finale,grade}
}
function withSynthetic(items){
 const finals=items.map(i=>i.finale).map(x=>JSON.stringify(x)+'\n').join('')
 const grades=items.map(i=>i.grade).map(x=>JSON.stringify(x)+'\n').join('')
 const statuses={...summary,source_independent_original_ESPN_Final_game_sha256:sha(finals),
  source_pairs_scored:items.length,independent_final_game_blocks:items.length,
  ungraded_future_game_forecasts:13-items.length,
  original_source_model_game_forecasts:13,
  status:'FORWARD_MARKET_VS_MODEL_GAME_SCORES_ACCUMULATING_NOT_PROFITABILITY_PROOF'}
 for(const model of ['raw_book','market_only','score_form'])for(const [name,property] of [['brier','squared_error'],['logloss','log_loss']]){
  const values=items.map(i=>i.grade[model+'_'+property]);
  statuses[model+'_'+name]=values.length?Math.round(values.reduce((a,b)=>a+b,0)/values.length*1e9)/1e9:null
 }
 return {finalText:finals,gradedText:grades,summary:statuses,nowMs:Date.parse('2026-10-15T12:00:00Z')}
}

test('actual source has 13 original prospective paper games, zero official Final grades, and 2025 was worse than raw market',()=>{
 const a=view()
 assert.equal(a.status,'AWAITING_INDEPENDENT_FINALS')
 assert.equal(a.frozen_games,13)
 assert.equal(a.official_final_games,0)
 assert.equal(a.compared_games,0)
 assert.equal(a.remaining_to_first_review,30)
 assert.equal(a.review_floor,30)
 assert.equal(a.scores.raw_book_brier,null)
 assert.equal(a.scores.score_form_brier,null)
 assert.equal(a.improvement_over_book,null)
 assert.equal(a.independent_edge_proven,false)
 assert.equal(a.official_bet_approved,false)
 assert.equal(a.actual_executable_price_verified,false)
 assert.equal(a.retro_2025_result,'NINE_FEATURE_MODEL_WORSE_THAN_RAW_BOOK')
 assert.match(a.forecast_source_sha256,/^[a-f0-9]{64}$/)
 assert.ok(!JSON.stringify(a).includes('ANNIE G'))
 assert.ok(!JSON.stringify(a).includes('hulk_picks'))
})

test('two independently Final game blocks have paired Brier and log loss, but stay a tiny sample',()=>{
 const lines=forecastsText.split('\n').filter(Boolean).slice(0,2).map(x=>JSON.parse(x))
 const input=withSynthetic([buildSynthetic(lines[0],{result:'HOME_WIN'}),buildSynthetic(lines[1],{result:'AWAY_WIN'})])
 const a=view(input)
 assert.equal(a.status,'TINY_FORWARD_SAMPLE_NOT_MARKET_EDGE')
 assert.equal(a.compared_games,2)
 assert.equal(a.remaining_to_first_review,28)
 assert.ok(a.scores.raw_book_brier>0 && a.scores.raw_book_brier<1)
 assert.ok(a.scores.score_form_brier>0 && a.scores.score_form_brier<1)
 assert.ok(a.scores.score_form_logloss>0)
 assert.ok(a.improvement_over_book!==null)
 assert.equal(a.independent_edge_proven,false)
 assert.equal(a.review_eligible,false)
 assert.equal(a.confidence_interval_95,null)
 assert.equal(a.roi_pct,null)
})

test('verified final without a matching official graded result displays an honest scoring backlog',()=>{
 const item=buildSynthetic(first)
 const input=withSynthetic([item])
 const a=view({...input,gradedText:'',summary:{...input.summary,source_pairs_scored:0,independent_final_game_blocks:0,
  ungraded_future_game_forecasts:13,status:'WAITING_FOR_INDEPENDENT_OFFICIAL_FINAL_NFL_GAME',
  raw_book_brier:null,market_only_brier:null,score_form_brier:null,raw_book_logloss:null,market_only_logloss:null,score_form_logloss:null}})
 assert.equal(a.status,'OFFICIAL_FINAL_AWAITING_VALIDATED_GRADE')
 assert.equal(a.official_final_games,1)
 assert.equal(a.compared_games,0)
 assert.equal(a.scores.raw_book_brier,null)
 assert.equal(a.independent_edge_proven,false)
})

test('partial Final, duplicate ID, mutated frozen baseline or forged status fails closed',()=>{
 const item=buildSynthetic(first)
 const input=withSynthetic([item])
 for(const update of [
  {forecastsText:forecastsText.replace('"research_only":true','"research_only":false')},
  {forecastsText:forecastsText+forecastsText.split('\n')[0]+'\n'},
  {finalText:input.finalText+input.finalText},
  {gradedText:input.gradedText.replace('"original_home_moneyline_win_binary_outcome":1','"original_home_moneyline_win_binary_outcome":0')},
  {finalText:input.finalText.replace('"official_espn_final_confirmed":true','"official_espn_final_confirmed":false')},
  {summary:{...input.summary,source_original_predicted_game_sha256:'0'.repeat(64)}},
  {gradedText:input.gradedText.replace('"score_form_squared_error":','"score_form_squared_error":0.000000001, "tampered_original":')},
 ]){
  const v=view({...input,...update})
  assert.equal(v.status,'SOURCE_INTEGRITY_CONFLICT',JSON.stringify(update).slice(0,125))
  assert.equal(v.independent_edge_proven,false)
  assert.equal(v.compared_games,0)
  assert.equal(v.scores.score_form_brier,null)
 }
})

test('official side score mismatch or grade captured before kickoff can never produce a Brier metric',()=>{
 const item=buildSynthetic(first)
 for(const bad of [
  {finale:{...item.finale,home_team:'SOME_OTHER_TEAM'},grade:item.grade},
  {finale:{...item.finale,home_points:34},grade:item.grade},
  {finale:{...item.finale,final_observed_at_utc:first.official_first_pitch_utc},grade:item.grade},
 ]){
  const audit=view(withSynthetic([bad]))
  assert.equal(audit.status,'SOURCE_INTEGRITY_CONFLICT')
  assert.equal(audit.compared_games,0)
 }
})

test('source assertions of a proven edge or an approved wager are rejected, even with scores',()=>{
 const x=withSynthetic([buildSynthetic(first)])
 for(const changes of [{market_advantage_statistically_proven:true},{live_play_approved:true},
  {real_wagers_submitted_or_profitable_payoffs_proven:true},
  {model_2025_retrospective_validation_was_worse_than_raw_market:false}]){
  const z=view({...x,summary:{...x.summary,...changes}})
  assert.equal(z.status,'SOURCE_INTEGRITY_CONFLICT')
  assert.equal(z.independent_edge_proven,false)
 }
})

test('30 independent games unlocks only diagnostic review, never automatic approval',()=>{
 const prototypes=forecastsText.trim().split('\n').map(JSON.parse)
 const all=Array.from({length:30},(_,i)=>{
  const src=prototypes[i%prototypes.length]
  const copy={...src,official_espn_event_id:String(500000000+i),independent_game_block_id:String(500000000+i)}
  return {...copy}
 })
 const futureText=all.map(r=>JSON.stringify(r)+'\n').join('')
 const scored=all.map((r,i)=>buildSynthetic(r,{result:i%2?'AWAY_WIN':'HOME_WIN'}))
 const input=withSynthetic(scored)
 const other={...input,forecastsText:futureText,summary:{...input.summary,
  source_original_predicted_game_sha256:sha(futureText),
  original_source_model_game_forecasts:30,ungraded_future_game_forecasts:0,
  independent_game_floor:30}}
 const a=view(other)
 assert.equal(a.compared_games,30)
 assert.equal(a.remaining_to_first_review,0)
 assert.equal(a.review_eligible,true)
 assert.equal(a.status,'DIAGNOSTIC_REVIEW_ONLY_NOT_PROVEN_EDGE')
 assert.equal(a.independent_edge_proven,false)
 assert.equal(a.official_bet_approved,false)
 assert.equal(a.actual_executable_price_verified,false)
 assert.equal(a.roi_pct,null)
 assert.ok(a.confidence_interval_95===null || typeof a.confidence_interval_95.low==='number')
})
