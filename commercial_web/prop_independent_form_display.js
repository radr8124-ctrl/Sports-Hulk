// Source-only NFL player four-game context.
// This does not constitute a validated projection, player availability, or a
// PrizePicks payout/entry recommendation.
export const RECORD_SCHEMA='ZENITH_NFL_PROP_PP_RESEARCH_PUBLIC_V1'

const norm=x=>String(x||'').toLowerCase().replace(/[^a-z0-9]/g,'')
const num=x=>{
  if(x===null||x===undefined||x==='')return null
  const n=Number(x)
  return Number.isFinite(n)?n:null
}
const clock=x=>{
  const d=Date.parse(x||'')
  return Number.isFinite(d)?d:null
}
const key=x=>[
  norm(x.player),norm(x.market_subtype||x.market),norm(x.side),num(x.line)
].join('|')

export function validateIndependentForm(source, nowMs=Date.now()) {
  if(source?.schema!==RECORD_SCHEMA||source?.real_wagers_placed!==false
    ||source?.unproven_model_not_recommendations!==true
    ||source?.must_verify_sportsbook_quote_and_game_day_injuries_before_any_bet!==true
    ||source?.prizepicks_payout_not_sportsbook_american_odds!==true
    ||!Array.isArray(source.rows)||!Number.isFinite(nowMs))return []
  const entries=[]
  for(const row of source.rows){
    const start=clock(row.start_utc)
    const quote=clock(row.source_latest_book_quote_updated_at_utc)
    const hit=num(row.prior_week_hit_count)
    const mean=num(row.prior_week_average)
    const total=num(row.history_games)
    const side=String(row.side||'').toUpperCase()
    if(!row.player||!row.source_game_id||!start||start<=nowMs||!quote
      ||quote>nowMs||quote>=start||total!==4
      ||!Number.isInteger(hit)||hit<0||hit>4||mean===null
      ||num(row.line)===null||!['OVER','UNDER'].includes(side)
      ||!Array.isArray(row.historical_previous_four_regular_2026_week_stats)
      ||row.historical_previous_four_regular_2026_week_stats.length!==4
      ||!row.historical_previous_four_regular_2026_week_stats.every(x=>num(x)!==null)
      ||row.approved_play!==false
      ||row.independent_model_beats_sportsbook_proven!==false
      ||row.official_pre_kickoff_player_injury_and_active_confirmation_verified!==false
      ||!Array.isArray(row.same_player_prop_opportunity_source_lanes))continue
    entries.push({...row, form_key:key(row),start_ms:start,
      quote_ms:quote,form_support_count:hit})
  }
  return entries
}

export function matchIndependentForm(row, lane, form, nowMs=Date.now()) {
  if(row?.sport!=='NFL'||!['PROP','PRIZEPICKS'].includes(lane)
    ||!Array.isArray(form))return null
  const start=clock(row.event_start)
  if(!start||start<=nowMs)return null
  const matches=form.filter(entry=>entry.form_key===key(row)
    &&Math.abs(entry.start_ms-start)<=15*60*1000
    &&entry.same_player_prop_opportunity_source_lanes.some(item=>
       item.lane==='NFL_'+lane
       &&item.original_line_was_approved_play===false))
  if(matches.length!==1)return null
  const evidence=matches[0]
  return {
    player:evidence.player,game_id:evidence.source_game_id,
    historical_stats:evidence.historical_previous_four_regular_2026_week_stats,
    hit_count:evidence.form_support_count,
    average:evidence.prior_week_average,
    line:evidence.line,
    side:evidence.side,
    quote_updated_at:evidence.source_latest_book_quote_updated_at_utc,
    quote_age_hours:Math.round((nowMs-evidence.quote_ms)/360000)/10,
    source_verification:'PLAYER_MARKET_SIDE_LINE_AND_START_MATCH_NO_FULL_PROVIDER_UUID_CROSSCHECK',
    source_only:true,
    projection_calibrated:false,
    official_injury_active_status_confirmed:false,
    independently_proven_edge:false,
    approved_pick:false,
  }
}

export function recentFormDescription(form) {
  if(!form)return {label:'Market price only',summary:'No independently verified player-form history linked',tone:'neutral'}
  const n=form.hit_count
  if(n>=3)return {
    label:'Recent-form watch',
    summary:n+'/4 previous games finished on this exact '+form.side+' side.',
    tone:'watch',
  }
  if(n<=1)return {
    label:'Recent form cautions',
    summary:'Only '+n+'/4 previous games finished on this '+form.side+' side.',
    tone:'caution',
  }
  return {
    label:'Recent form mixed',
    summary:'2/4 previous games cleared this '+form.side+' line.',
    tone:'neutral',
  }
}
