// Conservative, read-only fantasy trade research based on public weekly NFL
// research. Research indices are NOT scoring projections or fair-value prices.
export function normalizePlayerName(value) {
  return String(value || '').normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9 ]/g, ' ')
    .replace(/\s+/g,' ')
    .trim()
}

function takeNames(entries) {
  return (Array.isArray(entries) ? entries : [])
    .map(x => String(x || '').trim().slice(0,120))
    .filter(Boolean)
    .slice(0,4)
}

function metricScore(row) {
  if (row?.ros_research_score == null || row.ros_research_score === '') return null
  const v = Number(row.ros_research_score)
  return Number.isFinite(v) && v >= 0 && v <= 100 ? v : null
}

export function compareFantasyTrade({
  give, receive, weeklyRows, sourceGeneratedAt, nowMs=Date.now(),
  savedRoster,
} = {}) {
  const left = takeNames(give)
  const right = takeNames(receive)
  const latestMs=Date.parse(sourceGeneratedAt || '')
  const fresh = Number.isFinite(latestMs) && latestMs <= nowMs + 3*60000
    && (nowMs-latestMs) <= 7*24*3600*1000
  const catalogue = new Map()
  for (const row of Array.isArray(weeklyRows) ? weeklyRows : []) {
    if (!row || typeof row.player !== 'string') continue
    const id=normalizePlayerName(row.player)
    if (!id) continue
    const found=catalogue.get(id)
    if (found) { if (!found.some(x => x.team===row.team && x.position===row.position)) found.push(row) }
    else catalogue.set(id,[row])
  }

  const list = names => names.map(name => {
    const matched=catalogue.get(normalizePlayerName(name)) || []
    const ambiguous=matched.length > 1
    const row=ambiguous ? null : matched[0] || null
    return {
      input:name,
      found:Boolean(row),
      ambiguous,
      name:row?.player || name,
      team:row?.team || null,
      position:row?.position || null,
      ros:metricScore(row),
      weekly:metricScore({ros_research_score:row?.weekly_research_score}),
      role:row?.role_signal || null,
      tier:row?.ros_tier || null,
      snapshotAt:row?.generated_at || null,
    }
  })
  const giving=list(left)
  const getting=list(right)
  const availableRoster=new Set((Array.isArray(savedRoster) ? savedRoster : [])
    .map(item => normalizePlayerName(typeof item==='string'?item:item?.name||item?.player)))
  const rosterMembershipChecked=availableRoster.size>0
  const givingNotOnSavedRoster=rosterMembershipChecked
    ? giving.filter(item => !availableRoster.has(normalizePlayerName(item.input))).map(item=>item.input)
    : []
  const response={
    status:'WAITING',
    source:'FANTASY_WEEKLY_NFL_RESEARCH_ONLY',
    sourceGeneratedAt:sourceGeneratedAt || null,
    sourceFresh:fresh,
    giving,getting,
    deltaRos:null,
    comparable:false,
    rosterMembershipChecked,
    givingNotOnSavedRoster,
    explanation:'Enter at least one player on each side of a potential trade.',
  }

  if (!left.length || !right.length) return response
  const uniqueNames=new Set([...left,...right].map(normalizePlayerName))
  if (uniqueNames.size<left.length+right.length) {
    return {...response,status:'INVALID_COMPARISON',explanation:'A player cannot be listed twice or appear on both sides.'}
  }
  const all=[...giving,...getting]
  const anyUnknown=all.some(x=>!x.found || x.ambiguous || x.ros==null)
  if (anyUnknown) {
    return {...response,status:'INSUFFICIENT_PLAYER_COVERAGE',
      explanation:'At least one player is not uniquely covered by current NFL rest-of-season research. No comparative score will be calculated.'}
  }
  if (!fresh) {
    return {...response,status:'STALE_RESEARCH',
      explanation:'The available NFL research is older than seven days or has no valid timestamp. Scores are not compared until a fresh snapshot is available.'}
  }
  if (left.length!==right.length) {
    return {...response,status:'DIFFERENT_PLAYER_COUNTS',
      explanation:'Two-for-one and other uneven trades require roster-depth, replacement and league-scoring context. Research indices cannot be added as fair trade values.'}
  }
  const leftPos=giving.map(x=>x.position).sort().join('|')
  const rightPos=getting.map(x=>x.position).sort().join('|')
  const samePosition=giving.every(x=>x.position && x.position===giving[0].position)
    && getting.every(x=>x.position && x.position===getting[0].position)
  if (!samePosition || leftPos!==rightPos) {
    return {...response,status:'DIFFERENT_POSITION_CONTEXT',
      explanation:'Different fantasy positions require scoring, starter slots, scarcity and roster-needs adjustment. An index-to-index trade verdict would be misleading.'}
  }
  const leftMean=giving.reduce((acc,x)=>acc+x.ros,0)/giving.length
  const rightMean=getting.reduce((acc,x)=>acc+x.ros,0)/getting.length
  const deltaRos=Math.round((rightMean-leftMean)*10)/10
  return {...response,status:'DIRECTIONAL_RESEARCH_ONLY',comparable:true,deltaRos,
    explanation:'This difference is a direction-only, position-matched rest-of-season research index. It is not a fantasy-point forecast, trade fairness verdict, or recommendation; roster needs, league scoring, injuries and outside-team availability are not verified.'}
}
