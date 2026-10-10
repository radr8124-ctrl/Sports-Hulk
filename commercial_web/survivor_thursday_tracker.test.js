import test from 'node:test'
import assert from 'node:assert/strict'
import { parseDallasEntryList, reconcileDallasReport, summariseDallasReport } from './survivor_thursday_tracker.js'

const officialCsv=[
 'entry_name,participant,entry_suffix,status,weeks_recorded,used_teams,last_pick,page,source_filename,imported_at',
 'JANE SMITH 01,JANE SMITH,01,ACTIVE_OR_UNCONFIRMED,5,,,1,WEEK #4 PICKS .pdf,now',
 'JANE SMITH 02,JANE SMITH,02,ACTIVE_OR_UNCONFIRMED,5,,,1,WEEK #4 PICKS .pdf,now',
 'DAWN & MIKE BUCK 01YCHARGERS,DAWN & MIKE BUCK 01YCHARGERS,,ACTIVE_OR_UNCONFIRMED,4,,,1,WEEK #4 PICKS .pdf,now',
 'FORMER PLAYER 01,FORMER PLAYER,01,ELIMINATED,4,,,1,WEEK #4 PICKS .pdf,now',
].join('\n')
const meta={max_week_in_file:4,parsed_entries:4,source_filename:'WEEK #4 PICKS .pdf',source_sha256:'a'.repeat(64)}

test('numbered entries remain different tickets; Dallas label optional with explicit list attestation',()=>{
 const rows=parseDallasEntryList('1. JANE SMITH 01 COWBOYS\n- JANE SMITH 02 DAL\n• DAWN & MIKE BUCK 01')
 assert.equal(rows.length,3)
 assert.deepEqual(rows.map(row=>row.entry_name),['JANE SMITH 01','JANE SMITH 02','DAWN & MIKE BUCK 01'])
})

test('pasted scores, other teams or missing ticket suffix fail closed',()=>{
 for (const lines of ['JANE SMITH','JANE SMITH 01 BILLS','Dallas 24 Tampa Bay 16']) {
  assert.throws(()=>parseDallasEntryList(lines),/Duplicate|invalid|numbered|format/i)
 }
})

test('repeated exact names remain separate reported tickets but cannot consume one official match twice',()=>{
 const snapshot=reconcileDallasReport({reportedText:'JANE SMITH 01\nJANE SMITH 01',csvText:officialCsv,meta,currentWeek:5})
 assert.equal(snapshot.counts.uploaded,2)
 assert.equal(snapshot.counts.prior_active_exact,0)
 assert.equal(snapshot.counts.prior_manual_review,2)
 assert.deepEqual(snapshot.rows.map(r=>r.line),[1,2])
 assert.deepEqual(snapshot.rows.map(r=>r.match_status),['DUPLICATE_REPORTED_NAME_REVIEW','DUPLICATE_REPORTED_NAME_REVIEW'])
})

test('strict Week 4 roster join keeps the malformed Dawn Buck ticket as unresolved',()=>{
 const snapshot=reconcileDallasReport({reportedText:'JANE SMITH 01\nJANE SMITH 02\nDAWN & MIKE BUCK 01',
  csvText:officialCsv,meta,currentWeek:5})
 assert.equal(snapshot.counts.uploaded,3)
 assert.equal(snapshot.counts.prior_active_exact,2)
 assert.equal(snapshot.counts.prior_manual_review,1)
 assert.equal(snapshot.counts.not_found,0)
 assert.equal(snapshot.rows[2].match_status,'EXTRACTION_NAME_MISMATCH_REVIEW')
 assert.equal(snapshot.rows[2].official_candidate,'DAWN & MIKE BUCK 01YCHARGERS')
 assert.equal(snapshot.official_week,4)
 assert.equal(snapshot.certified_week5_eliminations,null)
})

test('already eliminated or missing names do not become new certified Thursday eliminations',()=>{
 const snapshot=reconcileDallasReport({reportedText:'FORMER PLAYER 01\nANOTHER PLAYER 03',
  csvText:officialCsv,meta,currentWeek:5})
 assert.equal(snapshot.counts.prior_already_eliminated,1)
 assert.equal(snapshot.counts.not_found,1)
 assert.equal(snapshot.counts.prior_active_exact,0)
 assert.equal(snapshot.certified_week5_eliminations,null)
})

test('reject stale or altered official baseline, forged week, missing provenance or row counts',()=>{
 for (const candidate of [
  {...meta,max_week_in_file:5},{...meta,parsed_entries:5},
  {...meta,source_sha256:''},{...meta,source_filename:'FAKE SHEET.pdf'},
 ]) assert.throws(()=>reconcileDallasReport({reportedText:'JANE SMITH 01',csvText:officialCsv,meta:candidate,currentWeek:5}),/official|baseline|mismatch|week|source|conflict/i)
})

test('private aggregate summary contains no competitor names and never invents remaining field',()=>{
 const snapshot=reconcileDallasReport({reportedText:'JANE SMITH 01\nDAWN & MIKE BUCK 01',csvText:officialCsv,meta,currentWeek:5})
 const s=summariseDallasReport({snapshot,officialMeta:meta})
 assert.equal(s.reported_count,147)
 assert.equal(s.list_imported_count,2)
 assert.equal(s.prior_week_matched,1)
 assert.equal(s.prior_week_needs_review,1)
 assert.equal(s.official_week,4)
 assert.equal(s.certified_week5_eliminations,null)
 assert.equal(s.official_remaining_count,null)
 assert.equal(JSON.stringify(s).includes('DAWN'),false)
 assert.equal(JSON.stringify(s).includes('JANE'),false)
})

test('without a report file the public claim remains 147 unverified, zero imported rows',()=>{
 const s=summariseDallasReport({snapshot:null,officialMeta:meta})
 assert.equal(s.reported_count,147)
 assert.equal(s.list_imported_count,0)
 assert.equal(s.status,'AWAITING_REPORTED_LIST')
 assert.equal(s.prior_week_matched,null)
 assert.equal(s.certified_week5_eliminations,null)
})
