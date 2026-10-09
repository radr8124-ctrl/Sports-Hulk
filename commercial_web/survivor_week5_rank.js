// Display-order helper only: never promotes research into a pool recommendation.
const tier = row => {
 const action=String(row?.strategy_action||'').toUpperCase()
 if(action==='VIABLE') return 0
 if(action==='WATCH') return 1
 if(action==='AVOID') return 3
 return 2
}
export function rankSurvivorCandidates(rows = [], usedTeams = []) {
 const burned=new Set(usedTeams)
 return (Array.isArray(rows)?rows:[])
   .filter(row=>row?.team && !burned.has(row.team))
   .sort((a,b)=>tier(a)-tier(b) || Number(b.strategy_index||0)-Number(a.strategy_index||0))
}

// Private Ask selects the governed shadow candidate only after rule +
// model gates clear. AVOID/CAUTION are never represented as picks.
export function selectSurvivorAskChoice(source = {}) {
 if (source.recommendation_status === 'WAIT_FOR_FRESH_VERIFIED_MARKET_QUOTES') {
   return { candidates: [], shadowRec: null, top: null, modelReady: false }
 }
 const burned = Array.isArray(source.used_teams) ? source.used_teams : []
 const candidates = rankSurvivorCandidates(source.candidates || [], burned)
   .filter(row => String(row.strategy_action || '').toUpperCase() !== 'AVOID'
     && String(row.decision_tier || '').toUpperCase() !== 'CAUTION'
     && row.eligible_for_shadow !== false)
 const modelReady = Boolean(source.rule_confirmed && source.recommendation_status === 'SHADOW_RECOMMENDATION_READY')
 const shadow = Array.isArray(source.shadow_recommendation)
   ? source.shadow_recommendation
   : source.shadow_recommendation?.team ? [source.shadow_recommendation] : []
 const shadowRec = modelReady
   ? shadow.find(row => candidates.some(candidate => candidate.team === row?.team)) || null
   : null
 return { candidates, shadowRec, top: shadowRec || candidates[0] || null, modelReady: Boolean(shadowRec) }
}
