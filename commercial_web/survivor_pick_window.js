// Server-only, read-only 2026 original-rules pool window. Always evaluates
// official NFLverse calendar + matching ESPN game/kickoff. Never invents a pick,
// organizer submission, result, new rule, market probability or betting edge.
import {createHash} from 'node:crypto'
import {parseCsv} from './survivor_pool_leverage.js'
const EASTERN='America/New_York'
const MS_HOUR=3600000
const ABBR={JAC:'JAX',LA:'LAR',LAR:'LAR',WSH:'WAS'}
const canon=v=>ABBR[String(v||'').trim().toUpperCase()]||String(v||'').trim().toUpperCase()
const millis=v=>{
 if(typeof v!=='string'||!/(?:Z|[+-]\d\d:\d\d)$/i.test(v))return null
 const n=Date.parse(v);return Number.isFinite(n)?n:null
}
const unavailable=(status,reason,poolWeek,saturday=null)=>({
 status,reason,pool_week:poolWeek,
 week_saturday_deadline:saturday==null?null:new Date(saturday).toISOString(),
 local_deadline_label:saturday==null?null:label(saturday),
 checked_at:null,total_week_schedule_games:null,scoreboard_verified_games:null,
 schedule_source_sha256:null,editable_teams:[],editable_team_cutoffs:{},current_saved_pick_count:0,
 saved_in_zenith_only:false,external_pool_result_verified:false,
 live_external_pool_submission_verified:false,
 explanation:'Original pool rules, scheduled game identities and private owner status must agree before a team can be saved.',
})
const label=utc=>new Intl.DateTimeFormat('en-US',{
 timeZone:EASTERN,weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',
 hour12:true,timeZoneName:'short',
}).format(new Date(utc)).replace(',','')
function offsetMinutes(date){
 const zone=new Intl.DateTimeFormat('en-US',{timeZone:EASTERN,timeZoneName:'shortOffset'})
 const marker=zone.formatToParts(date).find(part=>part.type==='timeZoneName')?.value
 const m=/^GMT([+-])(\d{1,2})(?::(\d{2}))?$/.exec(marker||'')
 if(!m)throw Error('Original Eastern timezone offset unavailable')
 const sign=m[1]==='+'?1:-1
 return sign*(Number(m[2])*60+Number(m[3]||0))
}
function easternStart(day,clock){
 if(!/^2026-\d{2}-\d{2}$/.test(day)||!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(clock)){
  throw Error('Original NFLverse local schedule date invalid')
 }
 const [year,month,d]=day.split('-').map(Number)
 const [hour,min]=clock.split(':').map(Number)
 const noonUtc=new Date(Date.UTC(year,month-1,d,12,0,0))
 if(noonUtc.toISOString().slice(0,10)!==day)throw Error('Original date invalid')
 return Date.UTC(year,month-1,d,hour,min)-offsetMinutes(noonUtc)*60000
}
function sourceSchedule(csv,week){
 if(typeof csv!=='string'||csv.length<300||csv.length>3_000_000)throw Error('Official calendar source not verified')
 const records=parseCsv(csv),fields=records.shift()
 const keys=['season','game_type','week','game_id','gameday','gametime','home_team','away_team','espn']
 if(!fields||new Set(fields).size!==fields.length||!keys.every(k=>fields.includes(k)))throw Error('NFLverse original fields missing')
 const idx=Object.fromEntries(fields.map((f,i)=>[f,i]))
 const out=[]
 for(const cells of records){
  if(cells.length!==fields.length)throw Error('NFLverse schedule CSV changed structure')
  const get=k=>cells[idx[k]]
  if(get('season')!=='2026'||get('game_type')!=='REG'||get('week')!==String(week))continue
  const away=get('away_team'),home=get('home_team'),key=get('game_id'),espn=get('espn')
  if(!/^[A-Z]{2,3}$/.test(away)||!/^[A-Z]{2,3}$/.test(home)||away===home||
    key!==`2026_${String(week).padStart(2,'0')}_${away}_${home}`||!/^[0-9]{7,12}$/.test(espn)){
    throw Error('NFLverse fixture/event source conflict')
  }
  out.push({id:espn,home:canon(home),away:canon(away),start:easternStart(get('gameday'),get('gametime')),
    day:get('gameday'),code:key})
 }
 if(out.length<12||out.length>16||new Set(out.map(x=>x.id)).size!==out.length||
   new Set(out.flatMap(x=>[x.home,x.away])).size!==out.length*2){
  throw Error('Original NFLverse week incomplete or conflicting')
 }
 const sundays=out.filter(x=>new Date(x.day+'T12:00:00Z').getUTCDay()===0)
 if(!sundays.length||new Set(sundays.map(x=>x.day)).size!==1){
  throw Error('Cannot establish verified season-week Sunday')
 }
 const sunday=sundays[0].day
 const saturdayMs=Date.parse(sunday+'T00:00:00Z')-24*MS_HOUR
 const saturday=new Date(saturdayMs).toISOString().slice(0,10)
 const saturdayDeadline=easternStart(saturday,'18:00')
 return {fixtures:out,saturdayDeadline}
}
export function survivorVerifiedPickWindow({scheduleCsv,scoreboard,poolWeek,entryStatus,usedTeams=[],currentPicks=[],
 nowMs=Date.now(),ruleConfirmed=false}={}){
 const week=Number(poolWeek)
 if(!Number.isInteger(week)||week<1||week>18||!Number.isFinite(nowMs))return unavailable('SOURCE_UNVERIFIED','POOL_WEEK_OR_CLOCK_UNVERIFIED',poolWeek)
 let fixtures,deadline
 try{({fixtures,saturdayDeadline:deadline}=sourceSchedule(scheduleCsv,week))}
 catch{return unavailable('SOURCE_UNVERIFIED','ORIGINAL_CALENDAR_UNVERIFIED',week)}
 if(ruleConfirmed!==true)return unavailable('RULE_NOT_VERIFIED','ORIGINAL_POOL_RULE_CONFLICT',week,deadline)
 if(!Array.isArray(usedTeams)||!Array.isArray(currentPicks)||
    usedTeams.some(x=>typeof x!=='string')||currentPicks.some(x=>typeof x!=='string')){
  return unavailable('SOURCE_UNVERIFIED','PRIVATE_ENTRY_STATE_UNVERIFIED',week,deadline)
 }
 if(entryStatus!=='ALIVE')return unavailable('ENTRY_NOT_ACTIVE','MEMBER_NOT_ACTIVE_IN_SOURCE',week,deadline)
 const savedCount=currentPicks.length
 const main={
  pool_week:week,week_saturday_deadline:new Date(deadline).toISOString(),
  local_deadline_label:label(deadline),
  checked_at:new Date(nowMs).toISOString(),
  total_week_schedule_games:fixtures.length,
  scoreboard_verified_games:0,
  schedule_source_sha256:createHash('sha256').update(scheduleCsv).digest('hex'),
  current_saved_pick_count:savedCount,
  saved_in_zenith_only:savedCount>0,
  external_pool_result_verified:false,
  live_external_pool_submission_verified:false,
  editable_teams:[],editable_team_cutoffs:{},
  explanation:'Sports Zenith only saves a private pick; it does not transmit to the outside pool, establish a model edge, or certify an organizer result.',
 }
 // Regardless of sports research feed freshness, a verified original weekly
 // cutoff has passed. Never reopen the edit box after the Saturday deadline.
 if(nowMs>=deadline)return {...main,status:'WINDOW_CLOSED',reason:'SATURDAY_POOL_DEADLINE_PASSED'}
 const captured=millis(scoreboard?.generated_at)
 if(captured==null||captured>nowMs+2*60000||nowMs-captured>45*60000||
   !Array.isArray(scoreboard?.games)||!Array.isArray(scoreboard?.next_games)){
  return {...main,status:'SOURCE_SCOREBOARD_UNVERIFIED',reason:'SCORE_SOURCE_STALE_OR_MISSING'}
 }
 const games=[...scoreboard.games,...scoreboard.next_games]
 const byId=new Map()
 for(const game of games){
  if(!game||!/^\d{7,12}$/.test(String(game.event_id||'')))continue
  const id=String(game.event_id)
  if(byId.has(id))return {...main,status:'SOURCE_EVENT_CONFLICT',reason:'DUPLICATE_ESPN_EVENT'}
  byId.set(id,game)
 }
 const checked=[],matched=[]
 for(const fixture of fixtures){
  const g=byId.get(fixture.id)
  if(!g)continue
  if(millis(g.start_time)!==fixture.start||canon(g.home_abbr)!==fixture.home||canon(g.away_abbr)!==fixture.away||
     typeof g.home!=='string'||typeof g.away!=='string'||!g.home.trim()||!g.away.trim()||
     g.home===g.away){
    return {...main,status:'SOURCE_EVENT_CONFLICT',reason:'ORIGINAL_SCHEDULE_VS_ESPN_DISAGREE'}
  }
  checked.push({...fixture,home_name:g.home,away_name:g.away,state:g.state,final:g.final})
  matched.push(fixture)
 }
 // Two hours before the first event on the same New York local game day.
 // Saturday 6pm is the overarching deadline for later games.
 const byDay=new Map()
 for(const fixture of fixtures){
  const old=byDay.get(fixture.day)
  if(old==null||fixture.start<old)byDay.set(fixture.day,fixture.start)
 }
 const used=new Set(usedTeams)
 const editable=new Set(),cutoffs={}
 for(const game of checked){
  const first=byDay.get(game.day)
  const earlierDeadline=Math.min(deadline,first-2*MS_HOUR)
  if(nowMs>=game.start||nowMs>=earlierDeadline||game.state!=='pre'||game.final!==false)continue
  for(const team of [game.home_name,game.away_name])if(!used.has(team)){
    editable.add(team);cutoffs[team]=new Date(earlierDeadline).toISOString()
  }
 }
 const names=[...editable].sort()
 if(!names.length)return {...main,status:'WINDOW_SOURCE_INCOMPLETE',reason:'NO_VERIFIED_EDITABLE_WEEK_TEAMS',
  scoreboard_verified_games:matched.length}
 return {...main,status:'WINDOW_OPEN',reason:'VERIFIED_GAME_AND_POOL_WINDOW',
  scoreboard_verified_games:matched.length,editable_teams:names,editable_team_cutoffs:cutoffs}
}
