// Read-only official pool field observer for Sunday of 2026 NFL Week 5.
// Source: the verified 333 original organizer PDF rows imported as a faithful
// CSV extraction. ESPN scores are temporary context, NEVER official standings.
import {parseCsv} from './survivor_pool_leverage.js'
const empty=status=>({status,week:5,total_entries:null,
 marked_eliminated_before_sunday:null,in_contention_before_sunday:null,
 scoreboard_status:'UNVERIFIED',teams:[],owner:null,
 pool_result_certified:false,external_submission_verified_by_zenith:false})
const insideWeek=g=>{
 const start=Date.parse(String(g?.start_time||''))
 return Number.isFinite(start)&&start>=Date.parse('2026-10-08T00:00:00Z')&&start<Date.parse('2026-10-14T00:00:00Z')
}
function gameFor(team,scoreboard,fresh){
 const none={status:'SCORE_NOT_VERIFIED',opponent:null,score_line:null,kickoff_utc:null,game_clock:null}
 if(!fresh)return none
 const games=[...(scoreboard.games||[]),...(scoreboard.next_games||[])]
 const matches=games.filter(g=>insideWeek(g)&&(g.away===team||g.home===team))
 if(matches.length!==1)return none
 const g=matches[0]
 const away=g.away===team
 const opponent=away?g.home:g.away
 const state=String(g.state||'').toLowerCase()
 const live=Boolean(g.live||state==='in')
 const final=Boolean(g.final||state==='post')
 const awayPts=Number(g.away_score),homePts=Number(g.home_score)
 const valid=Number.isFinite(awayPts)&&Number.isFinite(homePts)
 const diff=away?(awayPts-homePts):(homePts-awayPts)
 const status=final?'FINAL_AWAITING_ORGANIZER':live?(valid?diff>0?'LIVE_AHEAD':diff<0?'LIVE_BEHIND':'LIVE_TIED':'LIVE_SCORE_WAITING'):'UPCOMING'
 return {status,opponent,kickoff_utc:g.start_time,
 score_line:(live||final)&&valid?`${g.away} ${awayPts} – ${g.home} ${homePts}`:null,
 game_clock:String(g.status||'').slice(0,75)||null}
}
export function buildSurvivorWeek5FieldWatch({csvText,meta,scoreboard,linkedEntry=null,zenithPicks=[],at=Date.now()}={}){
 if(meta?.max_week_in_file!==5||meta?.whole_pool_import!==true||
    !/^[0-9a-f]{64}$/i.test(String(meta?.source_sha256||'')))return empty('OFFICIAL_WEEK5_SOURCE_UNAVAILABLE')
 let rows=[]
 try{const parsed=parseCsv(csvText);const fields=parsed.shift();if(!fields||!['entry_name','team','marker','week_position'].every(x=>fields.includes(x)))throw Error('Missing original columns');rows=parsed.map(a=>Object.fromEntries(fields.map((key,i)=>[key,a[i]])))}catch{return empty('FIELD_INTEGRITY_CONFLICT')}
 const week=rows.filter(row=>row.week_position==='5')
 const names=new Set(week.map(row=>row.entry_name))
 const lost=week.filter(row=>row.marker==='X')
 const survivors=week.filter(row=>row.marker!=='X')
 if(week.length!==333||names.size!==333||lost.length!==148||survivors.length!==185||Number(meta.parsed_entries)!==333){return empty('FIELD_INTEGRITY_CONFLICT')}
 const stamp=Date.parse(scoreboard?.generated_at||'')
 const fresh=Number.isFinite(stamp)&&stamp<=at+2*60000&&at-stamp<=20*60000&&Array.isArray(scoreboard?.games)&&Array.isArray(scoreboard?.next_games)
 const counts=new Map()
 for(const row of survivors)counts.set(row.team,(counts.get(row.team)||0)+1)
 const teams=[...counts].map(([team,entries])=>({team,entries,game:gameFor(team,scoreboard,fresh)})).sort((a,b)=>b.entries-a.entries||a.team.localeCompare(b.team))
 const live_exposure={
  currently_ahead:teams.filter(t=>t.game.status==='LIVE_AHEAD').reduce((n,t)=>n+t.entries,0),
  currently_behind:teams.filter(t=>t.game.status==='LIVE_BEHIND').reduce((n,t)=>n+t.entries,0),
  currently_tied:teams.filter(t=>t.game.status==='LIVE_TIED').reduce((n,t)=>n+t.entries,0),
  final_games_pending_pool_grade:teams.filter(t=>t.game.status==='FINAL_AWAITING_ORGANIZER').reduce((n,t)=>n+t.entries,0),
  waiting_or_unverified:teams.filter(t=>!['LIVE_AHEAD','LIVE_BEHIND','LIVE_TIED','FINAL_AWAITING_ORGANIZER'].includes(t.game.status)).reduce((n,t)=>n+t.entries,0),
 }
 const ownerRow=typeof linkedEntry==='string'?week.find(row=>row.entry_name===linkedEntry):null
 const owner=linkedEntry?{
  entry_name:linkedEntry,official_teams:ownerRow?[ownerRow.team]:[],
  organizer_marked_loss:ownerRow?.marker==='X',
  zenith_saved_teams:Array.isArray(zenithPicks)?[...zenithPicks]:[],
  synchronization:ownerRow?(zenithPicks.includes(ownerRow.team)?'ORGANIZER_AND_ZENITH_AGREE':'ORGANIZER_PDF_ONLY_NOT_ZENITH_SAVED'):'ORGANIZER_TICKET_NOT_MATCHED',
 }:null
 return {status:'VERIFIED_OFFICIAL_FIELD',week:5,total_entries:333,
  marked_eliminated_before_sunday:148,in_contention_before_sunday:185,
  scoreboard_status:fresh?'ESPN_CURRENT':'STALE_SCOREBOARD',scoreboard_updated_at:scoreboard?.generated_at||null,
  teams,owner,live_exposure,pool_result_certified:false,external_submission_verified_by_zenith:false,
  source_format:meta.source_format||'CSV',
  source_description:'Full Week 5 organizer PDF extracted to verified CSV; standings are pre-Sunday and live scores are provisional.',
 }
}
