// Browser-safe, source-independent scenario arithmetic. No picks saved or submitted.
export function projectWeek6WhatIf(plan,hypothetical='') {
  if(plan?.status!=='SCHEDULE_ONLY_UNRANKED')return {
    status:plan?.status||'SCHEDULE_UNAVAILABLE',games:[],changed_saved_picks:false,
  }
  const saved=plan.saved_week5_team
  const option=String(hypothetical||'').trim()
  if(saved && option && option!==saved)return {
    status:'OTHER_SCENARIO_BLOCKED_SAVED_PICK',games:[],changed_saved_picks:false,
  }
  if(!saved && option && !plan.week5_what_if_teams.includes(option))return {
    status:'INVALID_WEEK5_WHAT_IF',games:[],changed_saved_picks:false,
  }
  const selected=saved||option||null
  const excluded=new Set([...plan.used_teams,...(selected?[selected]:[])])
  const games=plan.games.map(row=>({
    ...row,eligible_teams:[row.away,row.home].filter(team=>!excluded.has(team)),
  }))
  let count=0
  for(let i=0;i<games.length;i++)for(let j=i+1;j<games.length;j++){
    // Two different games are required; both sides of one NFL fixture cannot both win.
    count+=games[i].eligible_teams.length*games[j].eligible_teams.length
  }
  return {
    status:saved?'SAVED_IN_ZENITH_ONLY':'WHAT_IF_ONLY',
    hypothetical_week5_team:selected,
    changed_saved_picks:false,external_pool_submission:false,
    eligible_week6_teams:games.reduce((n,row)=>n+row.eligible_teams.length,0),
    games_with_eligible_sides:games.filter(row=>row.eligible_teams.length>0).length,
    distinct_game_pair_options:count,
    // Counts are combinatorial possibilities, NOT projected wins or picks to use.
    games,
  }
}
