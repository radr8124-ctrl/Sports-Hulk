// Presentation-only Survivor status. Never infer a pool submission, an official
// current-week field, or a qualified pick from historical/anonymous research.
export function survivorCoverState({
  signedIn=false,hasEntry=false,entryStatus='',poolWeek=null,usedTeams=[],currentPicks=[],
  requiredPicks=null,ruleConfirmed=false,officialPoolWeek=null,
  recommendationStatus='',shadowRecommendation=[],
}={}) {
  const privateEntry=Boolean(signedIn && hasEntry)
  const active=String(entryStatus || '').toUpperCase()==='ALIVE'
  const savedCount=privateEntry && Array.isArray(currentPicks) ? currentPicks.length : 0
  const validRequired=ruleConfirmed && Number.isInteger(requiredPicks) && requiredPicks>=1 && requiredPicks<=4
  const validWeek=Number.isInteger(poolWeek) && poolWeek>=1 && poolWeek<=18
  const validOfficial=privateEntry && validWeek && Number.isInteger(officialPoolWeek)
    && officialPoolWeek>=1 && officialPoolWeek<=poolWeek
  const proofReady=privateEntry && active && ruleConfirmed
    && recommendationStatus==='SHADOW_RECOMMENDATION_READY'
    && Array.isArray(shadowRecommendation)
  const qualified=proofReady ? shadowRecommendation.filter(row=>row && typeof row.team==='string' && row.team.trim()).length : 0
  const status=!signedIn?'SIGN_IN_REQUIRED':!privateEntry?'LINK_ENTRY':!active?'NOT_ACTIVE'
    :savedCount>0?'SAVED_ZENITH_ONLY':'DECISION_OPEN'
  const labels={
    SIGN_IN_REQUIRED:'SIGN IN TO VIEW',LINK_ENTRY:'LINK YOUR ENTRY',
    NOT_ACTIVE:'ENTRY NOT ACTIVE',SAVED_ZENITH_ONLY:'SAVED IN ZENITH ONLY',
    DECISION_OPEN:'NOT YET CHOSEN',
  }
  const official=!signedIn?'SIGN IN':!privateEntry?'LINK ENTRY'
    :!validOfficial?'UNVERIFIED'
      :officialPoolWeek===poolWeek?`WEEK ${officialPoolWeek}`:`WEEK ${officialPoolWeek} ONLY`
  return {
    status,label:labels[status],
    week:validWeek?poolWeek:null,
    saved:privateEntry?`${savedCount} / ${validRequired?requiredPicks:'?'}`:'—',
    used:privateEntry && Array.isArray(usedTeams)?usedTeams.length:'—',
    qualified:privateEntry?String(qualified):'—',
    official,
    proof:proofReady && qualified>0
      ? 'Model shadow research is available; no win is guaranteed.'
      : 'Fresh bookmaker and independent model advantage are not verified.',
    external:'Sports Zenith does not submit to the external pool. Organizer acknowledgement is separate.',
  }
}
