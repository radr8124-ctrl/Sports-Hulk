// Aggregate-only immutable-source proof. Never writes, prices wagers, or reads member state.
import {readFile} from 'node:fs/promises'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import {assessNflForwardModelProof} from '../commercial_web/nfl_model_validation.js'
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..')
const vault=path.join(ROOT,'intelligence_warehouse/nfl_advanced_pregame')
const [forecastsText,finalText,gradedText,summaryJSON,publicJSON]=await Promise.all([
 readFile(path.join(vault,'NFL_FIRST_PREKICKOFF_NINE_FEATURE_SCORE_FORM_SHADOW.jsonl'),'utf8'),
 readFile(path.join(vault,'NFL_2026_FIRST_FUTURE_EVENT_ESPN_FINAL_ORIGINAL_SOURCE.jsonl'),'utf8'),
 readFile(path.join(vault,'NFL_NINE_FEATURE_SAME_BOOK_OFFICIAL_FINAL_SCORES.jsonl'),'utf8'),
 readFile(path.join(vault,'NFL_NINE_FEATURE_OFFICIAL_FINAL_COMPARISON_SUMMARY.json'),'utf8'),
 readFile(path.join(ROOT,'commercial_web/public/nfl_frozen_game_intelligence.json'),'utf8'),
])
const proof=assessNflForwardModelProof({forecastsText,finalText,gradedText,
 summary:JSON.parse(summaryJSON),originalPublic:JSON.parse(publicJSON),nowMs:Date.now()})
if(proof.status==='SOURCE_INTEGRITY_CONFLICT'||proof.research_only!==true||
   proof.independent_edge_proven!==false||proof.official_bet_approved!==false||
   proof.actual_executable_price_verified!==false){
 console.error('NFL_FORWARD_OBSERVER_ORIGINAL_SOURCE_INTEGRITY_CONFLICT')
 process.exit(2)
}
const fields=['status','frozen_games','official_final_games','compared_games',
 'scoring_backlog_games','remaining_to_first_review','forecast_source_sha256',
 'official_final_source_sha256','scored_game_source_sha256','research_only']
const aggregate=Object.fromEntries(fields.map(key=>[key,proof[key]]))
console.log(JSON.stringify(aggregate))
