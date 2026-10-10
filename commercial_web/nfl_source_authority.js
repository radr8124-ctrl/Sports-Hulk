// Aggregate-only NFL sportsbook source integrity audit. Reads, never modifies,
// historic original Propline vs archived SportWizzard references. These are NOT
// interchangeable, executable offers, proven edges or approved pool picks.
import {createHash} from 'node:crypto'
import {parseCsv} from './survivor_pool_leverage.js'

const MAX_BUFFER_BYTES=9_000_000
const ARCHIVE_NAME=/^nfl_live\/game_fusion\/history\/NFL_GAME_SPORTWIZZARD_(\d{8}T\d{6}Z)\.csv$/
const aliases={JAC:'JAX',LA:'LAR',WSH:'WAS'}
const canon=x=>aliases[String(x||'').toUpperCase()]||String(x||'').toUpperCase()
const timestamp=s=>{
 if(typeof s!=='string'|| !/(?:Z|[+-]\d{2}:\d{2})$/i.test(s.trim()))return null
 const t=Date.parse(s)
 return Number.isFinite(t)?t:null
}
const validAmerican=v=>{
 const n=Number(v)
 return Number.isFinite(n)&&Math.abs(n)>=100&&Math.abs(n)<=10000
}
const implied=v=>{
 const n=Number(v)
 return n<0?(-n/(100-n)):100/(100+n)
}
const iso=t=>t==null?null:new Date(t).toISOString()
const empty=(status,nowMs)=>({
 status,checked_at:Number.isFinite(nowMs)?iso(nowMs):null,
 official_upcoming_games:null,original_primary_matching_games:null,
 primary_fresh_game_count:0,primary_stale_game_count:null,
 primary_live_label_but_stale_count:null,primary_identity_conflicts:0,
 primary_latest_provider_at:null,research_recent_paired_games:0,
 research_archive_verified:false,research_capture_at:null,
 alternate_quota_status:'UNVERIFIED',qualified_selection_count:0,
 executability_verified:false,independent_model_edge_verified:false,
 no_approved_bet_or_survivor_pick_created:true,
 status_note:'Insufficient original-source evidence. Do not infer current sportsbook offers or qualified selections.',
})
const trustedScoreboard=(scoreboard,nowMs)=>{
 const captured=timestamp(scoreboard?.generated_at)
 if(captured==null||captured>nowMs+5*60*1000||nowMs-captured>50*60*1000||
    !Array.isArray(scoreboard?.next_games)||!Array.isArray(scoreboard?.games))return null
 const games=scoreboard.next_games.filter(row=>{
  const kickoff=timestamp(row?.start_time)
  return kickoff!=null&&kickoff>nowMs&&row?.state==='pre'&&row?.final===false&&
    /^\d{7,12}$/.test(String(row?.event_id||''))&&
    typeof row?.away==='string'&&row.away.length>2&&
    typeof row?.home==='string'&&row.home.length>2&&
    canon(row?.home_abbr)!==canon(row?.away_abbr)&&
    /^(?:[A-Z]{2,3})$/.test(canon(row?.away_abbr))&&
    /^(?:[A-Z]{2,3})$/.test(canon(row?.home_abbr))
 }).map(row=>({...row,kickoff:timestamp(row.start_time)}))
 if(!games.length||games.length>20||
   new Set(games.map(x=>String(x.event_id))).size!==games.length||
   new Set(games.map(x=>`${x.away}|${x.home}|${x.kickoff}`)).size!==games.length)return null
 return games
}
const primaryHeaderFields=['start','away_team','home_team','home_moneyline','away_moneyline',
 'collected_at','source_event_last_update','market_status','market_source']
const primaryRows=text=>{
 if(typeof text!=='string'||!text||text.length>1_000_000)return null
 const rows=parseCsv(text)
 const header=rows.shift()
 if(!header||new Set(header).size!==header.length||
   !primaryHeaderFields.every(h=>header.includes(h))||rows.length>500)return null
 const index=Object.fromEntries(header.map((key,i)=>[key,i]))
 return rows.filter(row=>row.length===header.length).map(row=>Object.fromEntries(primaryHeaderFields.map(h=>[h,row[index[h]]])))
}
function primaryAudit(csv,official,nowMs){
 const all=primaryRows(csv)
 if(!all)return null
 let matched=0,fresh=0,stale=0,liveStale=0,conflicts=0
 let lastProvider=null
 for(const game of official){
  const matches=all.filter(r=>r.home_team===game.home&&r.away_team===game.away&&
    timestamp(r.start)!=null&&Math.abs(timestamp(r.start)-game.kickoff)<=180_000)
  if(matches.length>1){conflicts++;continue}
  if(matches.length!==1)continue
  matched++
  const row=matches[0],collector=timestamp(row.collected_at),provider=timestamp(row.source_event_last_update)
  if(provider!=null&&(lastProvider==null||provider>lastProvider))lastProvider=provider
  const hoursToStart=(game.kickoff-nowMs)/3_600_000
  const ageCap=(hoursToStart<=24?6:24)*3_600_000
  const good=row.market_source==='propline'&&validAmerican(row.away_moneyline)&&
    validAmerican(row.home_moneyline)&&collector!=null&&provider!=null&&
    collector<=nowMs&&provider<=nowMs&&provider<=collector+5*60_000&&
    nowMs-collector<=ageCap&&nowMs-provider<=ageCap
  if(good)fresh++
  else {stale++;if(String(row.market_status).toUpperCase()==='LIVE')liveStale++}
 }
 return {matched,fresh,stale,liveStale,conflicts,lastProvider}
}
function researchAudit(reference,archiveBytes,official,nowMs){
 const none={verified:false,recents:0,capture:null}
 const loc=reference?.original_archive?.archive
 const match=typeof loc==='string'?ARCHIVE_NAME.exec(loc):null
 if(reference?.status!=='RESEARCH_ONLY'||
   reference?.book_prices_live_or_executable_verified!==false||
   reference?.main_line_verified!==false||reference?.model_advantage_proven!==false||
   reference?.betting_decision_created!==false||
   !match||!Array.isArray(reference?.fixtures)||reference.fixtures.length>25||
   !Buffer.isBuffer(archiveBytes)||archiveBytes.length===0||archiveBytes.length>MAX_BUFFER_BYTES||
   !/^[a-f0-9]{64}$/i.test(reference?.original_archive?.sha256||'')||
   createHash('sha256').update(archiveBytes).digest('hex')!==reference.original_archive.sha256)return none
 const nameTime=timestamp(match[1].replace(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/,'$1-$2-$3T$4:$5:$6Z'))
 if(nameTime==null||nameTime>nowMs)return none
 const fixtures=reference.fixtures
 const byGame=new Map()
 for(const q of fixtures){
  const key=String(q?.official_espn_event_id||'')
  byGame.set(key,[...(byGame.get(key)||[]),q])
 }
 let recents=0
 for(const g of official){
  const matches=byGame.get(String(g.event_id))||[]
  if(matches.length!==1)continue
  const fixture=matches[0],q=fixture?.markets?.MONEYLINE
  if(fixture.approved_play!==false||fixture.away!==canon(g.away_abbr)||
     fixture.home!==canon(g.home_abbr)||
     fixture.game_key!==`${canon(g.away_abbr)}@${canon(g.home_abbr)}`||
     timestamp(fixture.official_start)!==g.kickoff||
     !q||q.quote_type!=='TWO_SIDED_ARCHIVED_RESEARCH_SNAPSHOT'||
     q.is_approved_bet!==false||q.is_executable_current_offer!==false||
     q.is_verified_main_line!==false||typeof q.book!=='string'||!q.book.trim()||
     !validAmerican(q.home_price)||!validAmerican(q.away_price))continue
  const margin=implied(q.home_price)+implied(q.away_price)-1
  if(margin<0||margin>0.16)continue
  const capture=timestamp(q.source_captured_at),updated=timestamp(q.source_updated_at)
  const cutoff=(g.kickoff-nowMs<=24*3_600_000?6:24)*3_600_000
  if(capture===null||updated===null||capture!==nameTime||
     capture>nowMs||updated>nowMs||updated>capture+5*60_000||
     nowMs-updated>cutoff||nowMs-capture>cutoff)continue
  recents++
 }
 return {verified:true,recents,capture:nameTime}
}
export function auditNflBookSourceAuthority({primaryCsv,scoreboard,research,archiveBytes,fusion,nowMs=Date.now()}={}){
 if(!Number.isFinite(nowMs))return empty('SOURCE_VERIFICATION_UNAVAILABLE',nowMs)
 const official=trustedScoreboard(scoreboard,nowMs)
 if(!official)return empty('SOURCE_SCOREBOARD_STALE_OR_UNVERIFIED',nowMs)
 const p=primaryAudit(primaryCsv,official,nowMs)
 if(!p)return empty('ORIGINAL_PRIMARY_CSV_UNVERIFIED',nowMs)
 const r=researchAudit(research,archiveBytes,official,nowMs)
 const fusionTime=timestamp(fusion?.generated_at)
 const quota=fusionTime!=null&&fusionTime<=nowMs&&nowMs-fusionTime<=24*3_600_000&&
   Array.isArray(fusion?.therundown_receipts)&&
   fusion.therundown_receipts.some(x=>x?.http===429&&String(x.remaining)==='0')
 const status=p.fresh>0?'PRIMARY_TIME_FRESH_EXECUTION_UNVERIFIED':
   r.recents>0?'PRIMARY_STALE_RESEARCH_ONLY':'SOURCES_STALE_OR_UNVERIFIED'
 return {
  status,checked_at:iso(nowMs),official_upcoming_games:official.length,
  original_primary_matching_games:p.matched,primary_fresh_game_count:p.fresh,
  primary_stale_game_count:p.stale,
  primary_live_label_but_stale_count:p.liveStale,
  primary_identity_conflicts:p.conflicts,primary_latest_provider_at:iso(p.lastProvider),
  research_recent_paired_games:r.recents,research_archive_verified:r.verified,
  research_capture_at:iso(r.capture),
  alternate_quota_status:quota?'QUOTA_LIMITED_AT_LAST_CAPTURE':'UNVERIFIED',
  qualified_selection_count:0,executability_verified:false,
  independent_model_edge_verified:false,no_approved_bet_or_survivor_pick_created:true,
  status_note:'Original Propline provider timestamps are distinct from stale LIVE text. SportWizzard is separately archived paired research; it never substitutes for an independently verified executable offer or profitable model.',
 }
}
