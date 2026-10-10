// Week 6 two-pick research ONLY; exact source schedule, no odds/probabilities.
// No side effects: this module cannot save, submit, grade, or select pool picks.
import {createHash} from 'node:crypto'
import {parseCsv} from './survivor_pool_leverage.js'
import {resolveWeekPickRule} from './survivor_rules.js'

const TEAM_CODE={
  ARI:'Arizona Cardinals',ATL:'Atlanta Falcons',BAL:'Baltimore Ravens',BUF:'Buffalo Bills',
  CAR:'Carolina Panthers',CHI:'Chicago Bears',CIN:'Cincinnati Bengals',CLE:'Cleveland Browns',
  DAL:'Dallas Cowboys',DEN:'Denver Broncos',DET:'Detroit Lions',GB:'Green Bay Packers',
  HOU:'Houston Texans',IND:'Indianapolis Colts',JAX:'Jacksonville Jaguars',KC:'Kansas City Chiefs',
  LV:'Las Vegas Raiders',LAC:'Los Angeles Chargers',LA:'Los Angeles Rams',MIA:'Miami Dolphins',
  MIN:'Minnesota Vikings',NE:'New England Patriots',NO:'New Orleans Saints',NYG:'New York Giants',
  NYJ:'New York Jets',PHI:'Philadelphia Eagles',PIT:'Pittsburgh Steelers',SF:'San Francisco 49ers',
  SEA:'Seattle Seahawks',TB:'Tampa Bay Buccaneers',TEN:'Tennessee Titans',WAS:'Washington Commanders',
}
const TEAMS=new Set(Object.values(TEAM_CODE))
const sourceName='NFLVERSE_2026_SCHEDULE.csv'
// Original 2026 Knockout Pool: Week 5 Saturday, October 10, 6 PM Eastern.
const WEEK5_POOL_DEADLINE_ET='2026-10-10T18:00:00-04:00'
const unacceptable=status=>({status,pool_week:5,target_week:6,qualification:'NOT_A_MODEL_RECOMMENDATION',games:[],byes:[],week5_what_if_teams:[],source_sha256:null})
const digest=text=>createHash('sha256').update(text,'utf8').digest('hex')

// Both scoped NFL weeks are in October 2026, when Eastern time is UTC-04:00.
// We do not claim this fixed offset applies to other seasons/months.
function easternIso(row){
  if(!/^2026-10-(?:0[1-9]|[12][0-9]|3[01])$/.test(row.gameday)||
    !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(row.gametime))throw Error('Unverified kickoff date or clock')
  const iso=`${row.gameday}T${row.gametime}:00-04:00`
  if(!Number.isFinite(Date.parse(iso)))throw Error('Invalid schedule time')
  return iso
}

function parseVerifiedSchedule(csvText){
  if(typeof csvText!=='string'||csvText.length<1000||csvText.length>2_000_000)throw Error('NFL schedule source missing')
  const table=parseCsv(csvText)
  const header=table.shift()
  if(!header||header.length<8||new Set(header).size!==header.length)throw Error('Unverified NFLverse headers')
  const needed=['game_id','season','game_type','week','gameday','gametime','away_team','home_team']
  if(!needed.every(field=>header.includes(field)))throw Error('NFLverse fields missing')
  const ix=Object.fromEntries(header.map((h,i)=>[h,i]))
  const games=[]
  for(const cells of table){
    if(cells.length!==header.length)throw Error('NFLverse CSV malformed')
    const row=Object.fromEntries(needed.map(h=>[h,cells[ix[h]]]))
    if(row.season!=='2026'||row.game_type!=='REG'||!['5','6'].includes(row.week))continue
    if(!TEAM_CODE[row.away_team]||!TEAM_CODE[row.home_team]||row.away_team===row.home_team||
      !/^2026_0[56]_[A-Z]+_[A-Z]+$/.test(row.game_id))throw Error('Unverified NFLverse game identity')
    if(row.game_id!==`2026_0${row.week}_${row.away_team}_${row.home_team}`)throw Error('NFLverse ID/team mismatch')
    const kickoff_et=easternIso(row)
    games.push({week:Number(row.week),game_id:row.game_id,
      away:TEAM_CODE[row.away_team],home:TEAM_CODE[row.home_team],kickoff_et})
  }
  for(const week of [5,6]){
    const fixtures=games.filter(row=>row.week===week)
    if(fixtures.length<12||fixtures.length>16)throw Error('Incomplete official schedule')
    const teamNames=fixtures.flatMap(row=>[row.home,row.away])
    if(new Set(fixtures.map(row=>row.game_id)).size!==fixtures.length||
      new Set(teamNames).size!==teamNames.length)throw Error('Duplicate NFL game/team in schedule')
  }
  return games.sort((a,b)=>Date.parse(a.kickoff_et)-Date.parse(b.kickoff_et)||a.game_id.localeCompare(b.game_id))
}

export function buildSurvivorWeek6Plan(csvText,{poolWeek,entryStatus,usedTeams=[],currentPicks=[],nowMs=Date.now()}={}) {
  if(poolWeek!==5)return unacceptable('POOL_WEEK_NOT_FIVE')
  if(entryStatus!=='ALIVE')return unacceptable('ENTRY_NOT_ACTIVE')
  if(!Array.isArray(usedTeams)||!Array.isArray(currentPicks)||currentPicks.length>1||
    !usedTeams.every(team=>TEAMS.has(team))||!currentPicks.every(team=>TEAMS.has(team))||
    new Set(usedTeams).size!==usedTeams.length||
    currentPicks.some(team=>usedTeams.includes(team)))return unacceptable('PRIVATE_ENTRY_INVALID')
  const five=resolveWeekPickRule(5,{})
  const six=resolveWeekPickRule(6,{})
  if(five.rule_confirmed!==true||five.required_picks!==1||
    six.rule_confirmed!==true||six.required_picks!==2)return unacceptable('POOL_RULE_UNVERIFIED')
  if(!Number.isFinite(nowMs))return unacceptable('SCHEDULE_SOURCE_CONFLICT')
  try{
    const fixtures=parseVerifiedSchedule(csvText)
    const w5=fixtures.filter(row=>row.week===5)
    const w6=fixtures.filter(row=>row.week===6)
    const used=new Set(usedTeams)
    const unusedFutureW5=new Set(w5.filter(row=>Date.parse(row.kickoff_et)>nowMs && nowMs<Date.parse(WEEK5_POOL_DEADLINE_ET))
      .flatMap(row=>[row.home,row.away]).filter(team=>!used.has(team)))
    const saved=currentPicks[0]||null
    const allW5=new Set(w5.flatMap(row=>[row.home,row.away]))
    if(saved && !allW5.has(saved))return unacceptable('SAVED_PICK_NOT_ON_WEEK5_SCHEDULE')
    const gameTeams=new Set(w6.flatMap(row=>[row.home,row.away]))
    const byes=[...TEAMS].filter(team=>!gameTeams.has(team)).sort()
    if(byes.length>8)return unacceptable('SCHEDULE_SOURCE_CONFLICT')
    const earliest=w6[0]?.kickoff_et
    if(!earliest)return unacceptable('SCHEDULE_SOURCE_CONFLICT')
    const twoHoursBefore=Date.parse(earliest)-2*60*60*1000
    // UTC-04; for October only. Subtracting 4h from UTC gives ET clock representation.
    const earlyCutoff=new Date(twoHoursBefore-4*60*60*1000).toISOString().slice(0,19)+'-04:00'
    return {
      status:'SCHEDULE_ONLY_UNRANKED',pool_week:5,target_week:6,
      schedule_source:sourceName,source_sha256:digest(csvText),
      week5_required:five.required_picks,week6_required:six.required_picks,
      qualification:'NOT_A_MODEL_RECOMMENDATION',
      used_teams:usedTeams, saved_week5_team:saved,
      week5_what_if_teams:saved?[]:[...unusedFutureW5].sort(),
      week5_pool_deadline_et:WEEK5_POOL_DEADLINE_ET,week5_deadline_passed:nowMs>=Date.parse(WEEK5_POOL_DEADLINE_ET),
      byes, games:w6.map(row=>({game_id:row.game_id,home:row.home,away:row.away,kickoff_et:row.kickoff_et})),
      earliest_kickoff_et:earliest,early_game_cutoff_et:earlyCutoff,
      external_pool_submission:false,
      message:'NFLverse schedule and remaining eligibility only. Fresh odds, player availability and an independent win forecast are not verified.',
    }
  }catch{return unacceptable('SCHEDULE_SOURCE_CONFLICT')}
}

export {projectWeek6WhatIf} from './survivor_week6_projection.js'
