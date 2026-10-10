// Read-only, auditable 2026 NFL model vs ORIGINAL same-book market evaluation.
// Never scores based on a self-reported "final", retrofits past features,
// places wagers, upgrades model coefficients, or writes a source ledger.
import {createHash} from 'node:crypto'

const FORECAST_SCHEMA='NFL_2026_FIRST_RESEARCH_NINE_FEATURE_SAME_NEW_QUOTE_MARKET_COMPARISON_V1'
const SCORE_SCHEMA='NFL_2026_RESEARCH_NINE_FEATURE_SAME_BOOK_VS_INDEPENDENT_ESPN_FINAL_SCORE_V1'
const FINAL_SCHEMA='NFL_2026_ESPN_GAME_ID_SCORE_FINAL_SOURCE_MATCH_V1'
const sha=text=>createHash('sha256').update(text,'utf8').digest('hex')
const validHash=v=>typeof v==='string'&&/^[0-9a-f]{64}$/i.test(v)
const positiveInt=n=>Number.isSafeInteger(Number(n))&&Number(n)>=0
const timestamp=v=>{
 if(typeof v!=='string'|| !/(Z|[+-]\d{2}:\d{2})$/i.test(v))throw Error('Offset-aware original source time required')
 const n=Date.parse(v)
 if(!Number.isFinite(n))throw Error('Original source timestamp invalid')
 return n
}
const probability=p=>typeof p==='number'&&Number.isFinite(p)&&p>.001&&p<.999
function jsonLines(text,label){
 if(typeof text!=='string'||text.length>10_000_000)throw Error(label+' source missing or too large')
 const lines=text.split('\n').filter(s=>s.trim())
 if(lines.length>3000)throw Error(label+' source too many records')
 return lines.map((line,i)=>{
  let value
  try{value=JSON.parse(line)}catch{throw Error(label+' contains invalid JSON row '+(i+1))}
  if(!value||Array.isArray(value)||typeof value!=='object')throw Error(label+' has invalid record')
  return value
 })
}
const average=(v)=>v.length?v.reduce((s,x)=>s+x,0)/v.length:null
const rounded=n=>n==null?null:Math.round(n*1e7)/1e7
const noneScores=()=>({raw_book_brier:null,market_only_brier:null,score_form_brier:null,
 raw_book_logloss:null,market_only_logloss:null,score_form_logloss:null})
const fail=()=>({status:'SOURCE_INTEGRITY_CONFLICT',frozen_games:0,official_final_games:0,compared_games:0,
 original_2026_model_blocks:0,review_floor:30,remaining_to_first_review:30,
 scores:noneScores(),improvement_over_book:null,confidence_interval_95:null,
 review_eligible:false,independent_edge_proven:false,official_bet_approved:false,
 actual_executable_price_verified:false,roi_pct:null,retro_2025_result:'UNVERIFIED',
 research_only:true,message:'The original model, market and independent Final sources disagree or cannot be verified. No performance metric will be displayed.'})

export function assessNflForwardModelProof({forecastsText,finalText,gradedText,summary,originalPublic,nowMs=Date.now()}={}) {
 try{
  if(!Number.isFinite(nowMs)||!summary||!originalPublic||
     summary.schema!==SCORE_SCHEMA||summary.market_advantage_statistically_proven!==false||
     summary.live_play_approved!==false||summary.real_wagers_submitted_or_profitable_payoffs_proven!==false||
     summary.model_2025_retrospective_validation_was_worse_than_raw_market!==true||
     summary.minimum_sample_does_not_imply_edge!==true||
     originalPublic.historic_2025_holdout_model_better_than_market!==false||
     originalPublic.real_book_executability_verified!==false||
     originalPublic.market_source_cannot_upgrade_stale_primary_NFL_live_best_bets!==true||
     !positiveInt(summary.independent_game_floor)||Number(summary.independent_game_floor)<30||
     !validHash(summary.source_original_predicted_game_sha256)||
     !validHash(summary.source_independent_original_ESPN_Final_game_sha256)||
     summary.source_original_predicted_game_sha256!==sha(forecastsText)||
     summary.source_independent_original_ESPN_Final_game_sha256!==sha(finalText))throw Error('Original-source receipt is inconsistent')
  const forecasts=jsonLines(forecastsText,'forward predictions')
  const finals=jsonLines(finalText,'independent ESPN Final')
  const grades=jsonLines(gradedText,'immutable scored model')
  if(!forecasts.length||forecasts.length>2000||
     Number(summary.original_source_model_game_forecasts)!==forecasts.length||
     Number(summary.source_pairs_scored)!==grades.length||
     Number(summary.independent_final_game_blocks)!==grades.length)throw Error('Original source row-count conflict')
  const forecastById=new Map()
  const modelHashes=new Set()
  const weeks=new Set()
  for(const p of forecasts){
   const id=String(p.official_espn_event_id||'')
   if(!/^\d{6,12}$/.test(id)||forecastById.has(id)||
     p.schema!==FORECAST_SCHEMA||
     !validHash(p.source_frozen_model_sha256)||
     p.research_only!==true||p.betting_play_approved!==false||
     p.sportsbook_wager_created!==false||
     p.source_is_game_moneyline_not_player_proposition!==true||
     p.same_game_result_used_for_features!==false||
     Number(p.season)!==2026||!Number.isInteger(p.week)||p.week<1||p.week>18||
     !p.home_team||!p.away_team||p.home_team===p.away_team||
     !probability(p.original_raw_book_home_fair)||
     !probability(p.market_only_calibrated_home_win_prob)||
     !probability(p.nine_feature_score_form_home_win_prob))throw Error('Original forecast integrity failed')
   const feature=timestamp(p.source_context_features_frozen_at_utc)
   const quote=timestamp(p.source_qualified_book_quote_updated_at_utc)
   const freeze=timestamp(p.source_first_real_future_prediction_frozen_at_utc)
   const start=timestamp(p.official_first_pitch_utc)
   if(!(feature<quote&&quote<=freeze&&freeze<start))throw Error('Pregame freeze or quote came after kickoff')
   modelHashes.add(p.source_frozen_model_sha256)
   weeks.add(p.week)
   forecastById.set(id,p)
  }
  if(modelHashes.size!==1)throw Error('More than one unregistered forward model')
  const finalById=new Map()
  for(const f of finals){
   const id=String(f.official_espn_game_id||'')
   const fore=forecastById.get(id)
   if(!fore||finalById.has(id)||f.schema!==FINAL_SCHEMA||f.official_espn_final_confirmed!==true||
      Number(f.season)!==fore.season||Number(f.week)!==fore.week||
      f.home_team!==fore.home_team||f.away_team!==fore.away_team||
      timestamp(f.source_first_pitch_utc)!==timestamp(fore.official_first_pitch_utc)||
      timestamp(f.final_observed_at_utc)<=timestamp(fore.official_first_pitch_utc)||
      timestamp(f.final_observed_at_utc)>nowMs||
      !Number.isInteger(f.home_points)||!Number.isInteger(f.away_points)||
      f.home_points<0||f.away_points<0||f.home_points>150||f.away_points>150||
      !validHash(f.source_weekly_espn_payload_sha256)||
      !validHash(f.source_season_schedule_sha256))throw Error('Independent official Final provenance invalid')
   finalById.set(id,f)
  }
  let ties=0
  const tied=new Set()
  for(const [id,f] of finalById){if(f.home_points===f.away_points){ties++;tied.add(id)}}
  const scored=new Map()
  const deltas=[]
  const squared={raw_book:[],market_only:[],score_form:[]}
  const logloss={raw_book:[],market_only:[],score_form:[]}
  for(const r of grades){
   const id=String(r.official_espn_event_id||'')
   const original=forecastById.get(id)
   const f=finalById.get(id)
   if(!original||!f||scored.has(id)||tied.has(id)||
      r.schema!==SCORE_SCHEMA||r.independent_game_block_id!==id||
      r.one_NFL_match_counts_as_one_independent_source_event!==true||
      r.research_only!==true||r.live_play_approved!==false||
      r.profitable_market_edge_proven!==false||r.sportsbook_wager_executed!==false||
      r.not_sportsbook_settlement_or_wager_win!==true||
      r.home_team!==original.home_team||r.away_team!==original.away_team||
      r.season!==original.season||r.week!==original.week||
      r.official_home_points!==f.home_points||r.official_away_points!==f.away_points||
      timestamp(r.source_real_original_final_observed_at_utc)!==timestamp(f.final_observed_at_utc)||
      r.source_original_espn_final_scoreboard_sha256!==f.source_weekly_espn_payload_sha256||
      timestamp(r.source_first_original_model_frozen_at_utc)!==timestamp(original.source_first_real_future_prediction_frozen_at_utc)||
      r.original_model_sha256!==original.source_frozen_model_sha256)throw Error('Paired Final model score is not source-grounded')
   const outcome=f.home_points>f.away_points?1:0
   if(r.original_home_moneyline_win_binary_outcome!==outcome)throw Error('Official home/away winner is wrong')
   for(const [label,key] of [['raw_book','original_raw_book_home_fair'],
     ['market_only','market_only_calibrated_home_win_prob'],
     ['score_form','nine_feature_score_form_home_win_prob']]){
      const prob=original[key],brier=(prob-outcome)**2,log=-Math.log(outcome?prob:1-prob)
      if(!probability(r[label+'_original_pregame_home_win_probability'])||
        Math.abs(r[label+'_original_pregame_home_win_probability']-prob)>1e-8||
        Math.abs(r[label+'_squared_error']-brier)>1e-8||
        Math.abs(r[label+'_log_loss']-log)>1e-8)throw Error('Original immutable Brier/log loss score changed')
      squared[label].push(brier);logloss[label].push(log)
   }
   deltas.push(squared.raw_book.at(-1)-squared.score_form.at(-1))
   scored.set(id,true)
  }
  const scoredGames=scored.size
  if(ties!==Number(summary.official_final_tie_games_held_separately||0)||
     Number(summary.ungraded_future_game_forecasts)!==forecasts.length-scoredGames-ties||
     finals.length<scoredGames)throw Error('Original source/score book counts differ')
  const scores={raw_book_brier:rounded(average(squared.raw_book)),
    market_only_brier:rounded(average(squared.market_only)),
    score_form_brier:rounded(average(squared.score_form)),
    raw_book_logloss:rounded(average(logloss.raw_book)),
    market_only_logloss:rounded(average(logloss.market_only)),
    score_form_logloss:rounded(average(logloss.score_form))}
  for(const [metric,value] of Object.entries(scores)){
    const expected=summary[metric]
    if(value!==null && (typeof expected!=='number'||Math.abs(value-expected)>1e-7)){
      throw Error('Original independently scored summary does not match pairwise games')
    }
    if(value===null&&expected!==null)throw Error('Cannot display metric without graded games')
  }
  const reviewFloor=Number(summary.independent_game_floor)
  const reviewEligible=scoredGames>=reviewFloor
  const improvement=reviewEligible||scoredGames>0?rounded(average(deltas)):null
  // Exploratory ±1.96 paired game-block standard-error interval; never proof
  // of repeatability, licensed executable prices, or profitability.
  let ci=null
  if(reviewEligible && scoredGames>1){
    const mean=average(deltas)
    const variance=deltas.reduce((sum,d)=>sum+(d-mean)**2,0)/(deltas.length-1)
    const radius=1.96*Math.sqrt(variance/deltas.length)
    ci={low:rounded(mean-radius),high:rounded(mean+radius),method:'EXPLORATORY_PAIRED_GAME_BLOCK_NORMAL_95'}
  }
  const ungraded=forecasts.length-scoredGames-ties
  const pendingAfterFinal=finalById.size-scoredGames-ties
  const status=pendingAfterFinal>0?'OFFICIAL_FINAL_AWAITING_VALIDATED_GRADE':
    scoredGames===0?'AWAITING_INDEPENDENT_FINALS':
    !reviewEligible?'TINY_FORWARD_SAMPLE_NOT_MARKET_EDGE':'DIAGNOSTIC_REVIEW_ONLY_NOT_PROVEN_EDGE'
  return {
   status,generated_at:new Date(nowMs).toISOString(),
   model_cohort:'2026_WEEK5_ORIGINAL_FROZEN_SAME_BOOK_9_FEATURE_CHALLENGER',
   model_training_period:'2016–2024; retrospective 2025 diagnostic',
   model_market_assisted:true,
   frozen_games:forecasts.length,official_final_games:finalById.size,
   compared_games:scoredGames,ungraded_games:ungraded,scoring_backlog_games:pendingAfterFinal,
   distinct_scored_game_blocks:scoredGames,review_floor:reviewFloor,
   remaining_to_first_review:Math.max(0,reviewFloor-scoredGames),
   first_review_threshold_is_not_edge_proof:true,
   scores,improvement_over_book:improvement,confidence_interval_95:ci,
   review_eligible:reviewEligible,independent_edge_proven:false,
   official_bet_approved:false,actual_executable_price_verified:false,roi_pct:null,
   retro_2025_result:'NINE_FEATURE_MODEL_WORSE_THAN_RAW_BOOK',
   forecast_source_sha256:sha(forecastsText),
   official_final_source_sha256:sha(finalText),
   scored_game_source_sha256:sha(gradedText),
   settled_earliest_week:scoredGames?Math.min(...[...scored.keys()].map(id=>forecastById.get(id).week)):null,
   observed_games_source:'ESPN_FINAL_AND_ORIGINAL_NFLVERSE_EXACT_GAME_MATCH_ONLY',
   research_only:true,
   message:'Original 2026 game model and original bookmaker prices are scored on the same future games. This is a market-assisted challenger. Without independently verified final scores and repeatability, no evidence of winning or profitability is claimed.',
  }
 }catch{return fail()}
}
