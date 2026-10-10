// Private, read-only NFL Survivor pregame source evidence. Never a certified pick,
// bookmaker offer, injury clearance, user-pick operation, or model promotion.
import {createHash} from 'node:crypto'
import {parseCsv} from './survivor_pool_leverage.js'

const NFL={
 'Arizona Cardinals':['ARI','22'],'Atlanta Falcons':['ATL','1'],
 'Baltimore Ravens':['BAL','33'],'Buffalo Bills':['BUF','2'],
 'Carolina Panthers':['CAR','29'],'Chicago Bears':['CHI','3'],
 'Cincinnati Bengals':['CIN','4'],'Cleveland Browns':['CLE','5'],
 'Dallas Cowboys':['DAL','6'],'Denver Broncos':['DEN','7'],
 'Detroit Lions':['DET','8'],'Green Bay Packers':['GB','9'],
 'Houston Texans':['HOU','34'],'Indianapolis Colts':['IND','11'],
 'Jacksonville Jaguars':['JAX','30'],'Kansas City Chiefs':['KC','12'],
 'Las Vegas Raiders':['LV','13'],'Los Angeles Chargers':['LAC','24'],
 'Los Angeles Rams':['LAR','14'],'Miami Dolphins':['MIA','15'],
 'Minnesota Vikings':['MIN','16'],'New England Patriots':['NE','17'],
 'New Orleans Saints':['NO','18'],'New York Giants':['NYG','19'],
 'New York Jets':['NYJ','20'],'Philadelphia Eagles':['PHI','21'],
 'Pittsburgh Steelers':['PIT','23'],'San Francisco 49ers':['SF','25'],
 'Seattle Seahawks':['SEA','26'],'Tampa Bay Buccaneers':['TB','27'],
 'Tennessee Titans':['TEN','10'],'Washington Commanders':['WAS','28'],
}
const ALIASES={JAC:'JAX',LA:'LAR',WSH:'WAS'}
const MAX_SOURCE_BYTES=750_000
const REPORTED=new Set(['Out','Doubtful','Questionable','Injured Reserve'])
const PRIORITY={Out:0,Doubtful:1,Questionable:2,'Injured Reserve':3}
// Within each reported designation, group offensive/skill roles before other
// roles for readability. This is NOT player value or matchup importance.
const POSITION_ORDER={QB:0,RB:1,WR:2,TE:3,OT:4,G:5,C:6}
const stamp=v=>{
 const millis=Date.parse(String(v||''))
 return Number.isFinite(millis)?millis:null
}
const canon=v=>ALIASES[String(v||'').toUpperCase()]||String(v||'').toUpperCase()
const privateFail=status=>({status,book:{status:'UNVERIFIED',selected_team_american:null,opponent_american:null},
 injuries:{status:'UNVERIFIED',selected_team:{players:[]},opponent:{players:[]}},qualified_survivor_pick:false})
const researchFallback=status=>({status,selected_team_american:null,opponent_american:null,
 book:null,source_updated_at:null,source_captured_at:null,source_sha256:null,
 live_offer_verified:false,qualified_pick:false,independent_model_edge_verified:false})
const implied=a=>a<0?-a/(100-a):100/(100+a)
const validAmerican=n=>Number.isInteger(n) && Math.abs(n)>=100 && Math.abs(n)<=10000

function verifiedInjuries(text,home,away,nowMs,kickoff) {
 const empty={status:'INJURY_SOURCE_STALE_OR_UNVERIFIED',selected_team:{players:[]},opponent:{players:[]},
 source_observed_at:null,clearance_verified:false,starting_lineup_verified:false,coverage_limited:true}
 if(typeof text!=='string'||text.length>MAX_SOURCE_BYTES)return empty
 try{
  const rows=parseCsv(text)
  const header=rows.shift()
  const needed=['player','team','position','status','injury_type','espn_team_id',
    'espn_team_name','team_source_status','source_record_at','source_observed_at','source']
  if(!header||new Set(header).size!==header.length||!needed.every(name=>header.includes(name))||
      rows.length<2||rows.length>3000)return empty
  const indexes=Object.fromEntries(header.map((field,i)=>[field,i]))
  const get=(row,name)=>row[indexes[name]]
  const selected=[home,away]
  const relevant=rows.filter(row=>{
    if(row.length!==header.length)return false
    const team=selected.find(name=>NFL[name]?.[0]===get(row,'team'))
    if(!team)return false
    return get(row,'espn_team_id')===NFL[team][1]&&
      get(row,'espn_team_name')===team&&
      get(row,'team_source_status')==='VERIFIED_ESPN_TEAM_ID_AND_NAME'&&
      get(row,'source')==='ESPN_PUBLIC_GROUPED_NFL_INJURIES'
  })
  const first=nowMs<=kickoff&&kickoff-nowMs<=24*60*60*1000?6:24
  const observed=new Set(relevant.map(row=>get(row,'source_observed_at')))
  if(observed.size!==1)return empty
  const asOf=[...observed][0]
  const observedMs=stamp(asOf)
  if(observedMs==null ||observedMs>nowMs||nowMs-observedMs>first*60*60*1000 ||
     !selected.every(name=>relevant.some(row=>get(row,'team')===NFL[name][0])))return empty
  const result={status:'RECENT_LIMITED_ESPN_REPORTS_NOT_STARTER_CONFIRMATION',
    source_observed_at:new Date(observedMs).toISOString(),coverage_limited:true,
    clearance_verified:false,starting_lineup_verified:false,
    text:'ESPN status reports are not a verified game-day active list. Absent and Active players are never assumed cleared.'}
  const sides=new Set()
  for(const [key,name] of [['selected_team',home],['opponent',away]]){
    const reports=[]
    for(const row of relevant){
      if(get(row,'team')!==NFL[name][0])continue
      const status=get(row,'status')
      if(!REPORTED.has(status))continue
      const player=get(row,'player')
      const reportAt=stamp(get(row,'source_record_at'))
      if(!player||player.length>100||reportAt==null||reportAt>nowMs||
        nowMs-reportAt>72*60*60*1000)continue
      const statusText=get(row,'injury_type')||'Not specified'
      reports.push({player,position:get(row,'position')||'',reported_status:status,
        injury:statusText.slice(0,75),reported_at:new Date(reportAt).toISOString()})
    }
    reports.sort((a,b)=>PRIORITY[a.reported_status]-PRIORITY[b.reported_status]||
      (POSITION_ORDER[a.position]??20)-(POSITION_ORDER[b.position]??20)||
      stamp(b.reported_at)-stamp(a.reported_at)||a.player.localeCompare(b.player))
    result[key]={team:name,players:reports.slice(0,9),reported_count_in_source:reports.length,
      note:'Recent reported statuses only. ESPN group may be limited and omits full lineup verification.'}
    sides.add(name)
  }
  return result
 }catch{return empty}
}

function verifiedBook({bookRef,archiveBytes,fixture,team,home,nowMs,kickoff}) {
 const fallback=reason=>researchFallback(reason)
 if(!bookRef ||bookRef.status!=='RESEARCH_ONLY'||
   bookRef.book_prices_live_or_executable_verified!==false||
   bookRef.model_advantage_proven!==false||bookRef.main_line_verified!==false)return fallback('ORIGINAL_PRIMARY_MARKET_UNVERIFIED')
 const root=bookRef.original_archive
 if(!root||typeof root.archive!=='string'||
   !/^nfl_live\/game_fusion\/history\/NFL_GAME_SPORTWIZZARD_\d{8}T\d{6}Z\.csv$/.test(root.archive)||
   !/^[a-f0-9]{64}$/i.test(String(root.sha256||''))||
   !Buffer.isBuffer(archiveBytes)||
   createHash('sha256').update(archiveBytes).digest('hex')!==root.sha256){
   return fallback('ARCHIVE_SHA_UNVERIFIED')
 }
 const matches=(bookRef.fixtures||[]).filter(x=>x?.game_key===`${canon(fixture.away_abbr)}@${canon(fixture.home_abbr)}`)
 if(matches.length!==1)return fallback('SAME_EVENT_BOOK_PAIR_UNVERIFIED')
 const matched=matches[0]
 const ml=matched.markets?.MONEYLINE
 if(matched.approved_play!==false||matched.official_espn_event_id!==fixture.event_id ||
   matched.home!==canon(fixture.home_abbr)||matched.away!==canon(fixture.away_abbr)||
   stamp(matched.official_start)!==kickoff||!ml||
   ml.quote_type!=='TWO_SIDED_ARCHIVED_RESEARCH_SNAPSHOT'||
   ml.is_executable_current_offer!==false||ml.is_approved_bet!==false||
   ml.is_verified_main_line!==false||typeof ml.book!=='string'||!ml.book.trim()){
   return fallback('SAME_EVENT_BOOK_PAIR_UNVERIFIED')
 }
 const homePrice=Number(ml.home_price),awayPrice=Number(ml.away_price)
 if(!validAmerican(homePrice)||!validAmerican(awayPrice))return fallback('SAME_EVENT_BOOK_PAIR_UNVERIFIED')
 const margin=implied(homePrice)+implied(awayPrice)-1
 if(margin<0||margin>.16)return fallback('SAME_EVENT_BOOK_PAIR_UNVERIFIED')
 const captured=stamp(ml.source_captured_at),updated=stamp(ml.source_updated_at)
 if(captured===null||updated===null||updated>captured+300000||
   updated>nowMs||captured>nowMs)return fallback('SOURCE_CLOCK_CONFLICT')
 if(nowMs>=kickoff)return fallback('GAME_STARTED_NO_CURRENT_BOOK_PRICES')
 const maxAgeHours=kickoff-nowMs<=24*60*60*1000?6:24
 if(nowMs-updated>maxAgeHours*3600000||nowMs-captured>maxAgeHours*3600000){
  return fallback('EXPIRED_RESEARCH_SNAPSHOT')
 }
 return {status:'RECENT_DATED_RESEARCH_NOT_EXECUTABLE',
   book:ml.book,selected_team_american:team===home?homePrice:awayPrice,
   opponent_american:team===home?awayPrice:homePrice,
   source_updated_at:new Date(updated).toISOString(),
   source_captured_at:new Date(captured).toISOString(),source_sha256:root.sha256,
   margin_pct:Math.round(margin*1000)/10,
   source_type:'SPORTWIZZARD_ARCHIVED_SAME_BOOK_PAIRED_RESEARCH',
   live_offer_verified:false,qualified_pick:false,independent_model_edge_verified:false,
   note:'Recent, same-book, two-sided dated research; not live bookmaker pricing, an executable offer, or Zenith model advantage.'}
}

export function buildSurvivorPreflightEvidence({team,opponent,usedTeams=[],scoreboard,bookRef,archiveBytes,injuryCsv,nowMs=Date.now()}={}) {
 if(!Object.hasOwn(NFL,String(team))||!Object.hasOwn(NFL,String(opponent))||team===opponent)return privateFail('TEAM_NOT_RECOGNIZED')
 if(!Array.isArray(usedTeams)||usedTeams.includes(team))return privateFail('TEAM_PREVIOUSLY_USED')
 if(!Number.isFinite(nowMs))return privateFail('UNVERIFIED_CLOCK')
 const official=[...(Array.isArray(scoreboard?.next_games)?scoreboard.next_games:[]),
   ...(Array.isArray(scoreboard?.games)?scoreboard.games:[])].filter(row=>
   row && ((row.home===team&&row.away===opponent)||(row.away===team&&row.home===opponent)))
 if(official.length!==1)return privateFail('OFFICIAL_FIXTURE_UNVERIFIED')
 const g=official[0]
 const start=stamp(g.start_time)
 if(!/^[0-9]{7,12}$/.test(String(g.event_id||''))||start===null ||
    canon(g.home_abbr)!==NFL[g.home]?.[0] ||canon(g.away_abbr)!==NFL[g.away]?.[0]){
   return privateFail('OFFICIAL_FIXTURE_UNVERIFIED')
 }
 const result={status:'SOURCE_EVIDENCE_ONLY',team,opponent,
   event_id:String(g.event_id),kickoff_at:new Date(start).toISOString(),
   home:g.home,away:g.away,checked_at:new Date(nowMs).toISOString(),
   qualified_survivor_pick:false,
   no_model_prediction:true,external_pool_submitted:false}
 if(nowMs>=start){
   return {...result,status:'GAME_STARTED_NO_PREGAME_RESEARCH',
     book:researchFallback('GAME_STARTED_NO_CURRENT_BOOK_PRICES'),
     injuries:{status:'GAME_STARTED',selected_team:{players:[]},opponent:{players:[]},clearance_verified:false}}
 }
 result.book=verifiedBook({bookRef,archiveBytes,fixture:g,team,home:g.home,nowMs,kickoff:start})
 result.injuries=verifiedInjuries(injuryCsv,team,opponent,nowMs,start)
 result.readiness={
   primary_live_book_verified:false,independent_model_edge_verified:false,
   game_day_starters_verified:false,
   referenced_injury_source_recent:result.injuries.status.startsWith('RECENT_'),
   dated_book_research_available:result.book.status==='RECENT_DATED_RESEARCH_NOT_EXECUTABLE',
   selectable_survivor_recommendation:false,
 }
 return result
}
