// Separate, evidence-gated Thursday Dallas research — never an official pool import.
// Reported counts are claims, not counted entry rows, until a manager uploads the list.
import { createHash } from 'node:crypto'
import { parseCsv } from './survivor_pool_leverage.js'

export const DALLAS_CLAIM = Object.freeze({
  report_week:5, losing_team:'Dallas Cowboys', opponent:'Tampa Bay Buccaneers',
  reported_count:147, reported_prior_matches:146, reported_prior_mismatches:1,
  source_status:'USER_REPORTED_CONVERSATION_SUMMARY_NOT_ROW_SOURCE',
})

const hash = text => createHash('sha256').update(text,'utf8').digest('hex')
const normalized = text => String(text||'').normalize('NFKC').replace(/\s+/g,' ').trim().toUpperCase()

export function parseDallasEntryList(text) {
  if (typeof text !== 'string' || text.length > 160_000) throw Error('Reported list is invalid or too large.')
  const lines = text.replace(/\r\n?/g,'\n').split('\n').map(row=>row.trim()).filter(Boolean)
  if (!lines.length || lines.length > 2000) throw Error('Supply numbered entry lines (up to 2,000).')
  const seen = new Set()
  return lines.map((raw_line,i)=>{
    const withoutBullet=raw_line.replace(/^(?:[-*•]\s*|\d{1,4}[.)]\s*)/u,'').trim()
    const m=/^([\p{L}\p{N}][\p{L}\p{N} &'’()./+\-#]{0,145}?\s+\d{2})(?:\s+(?:DALLAS|COWBOYS|DAL))?$/iu.exec(withoutBullet)
    if (!m) throw Error(`Invalid numbered entry format on line ${i+1}. Use NAME 01 or NAME 01 COWBOYS.`)
    const entry_name=normalized(m[1])
    // Reject scoreboards that happen to end in two-digit numbers.
    if (/\b\d{1,3}\b/.test(entry_name.replace(/\s+\d{2}$/, ''))) {
      throw Error(`Invalid numbered entry format on line ${i+1}: another number appears before the ticket suffix.`)
    }
    if (entry_name.length>150) throw Error(`Entry name too long on line ${i+1}.`)
    // Preserve every reported line, even duplicate printed identifiers. They may
    // represent separate pool tickets; only the organizer can resolve them.
    seen.add(entry_name)
    return {line:i+1,entry_name,raw_line}
  })
}

function officialWeek4(csvText,meta,currentWeek) {
  const official=Number(meta?.max_week_in_file)
  if (currentWeek!==5 || official!==4 || !/^[a-f\d]{64}$/i.test(String(meta?.source_sha256||'')) ||
      typeof meta?.source_filename!=='string' || !meta.source_filename.trim() ||
      !Number.isSafeInteger(Number(meta?.parsed_entries)) || Number(meta.parsed_entries)<1 ||
      Number(meta.parsed_entries)>20000) throw Error('Previous official Week 4 pool source unavailable or mismatched.')
  const rows=parseCsv(csvText)
  const header=rows.shift()
  if (!Array.isArray(header) || new Set(header).size!==header.length ||
      !['entry_name','status','source_filename'].every(key=>header.includes(key)) ||
      rows.length!==Number(meta.parsed_entries)) throw Error('Official baseline CSV conflicts with its source metadata.')
  const index=Object.fromEntries(header.map((key,i)=>[key,i]))
  const out=new Map()
  for(const row of rows){
    if (row.length!==header.length || row[index.source_filename]!==meta.source_filename ||
        !String(row[index.entry_name]||'').trim() ||
        !['ELIMINATED','ACTIVE_OR_UNCONFIRMED'].includes(row[index.status])){
      throw Error('Official baseline CSV conflicts with its source metadata.')
    }
    const key=normalized(row[index.entry_name])
    if(!out.has(key))out.set(key,[])
    out.get(key).push({entry_name:row[index.entry_name],status:row[index.status]})
  }
  return out
}

export function reconcileDallasReport({reportedText,csvText,meta,currentWeek=5}={}) {
  const input=parseDallasEntryList(reportedText)
  const roster=officialWeek4(csvText,meta,currentWeek)
  const counts={uploaded:input.length,prior_active_exact:0,prior_already_eliminated:0,
    prior_manual_review:0,not_found:0}
  const claimedCounts=new Map()
  for(const row of input)claimedCounts.set(row.entry_name,(claimedCounts.get(row.entry_name)||0)+1)
  const rows=input.map(row=>{
    const exact=roster.get(row.entry_name)
    let match_status='NOT_IN_PREVIOUS_SHEET', official_candidate=null
    if(claimedCounts.get(row.entry_name)>1){
      match_status='DUPLICATE_REPORTED_NAME_REVIEW'
    }else if(exact?.length===1){
      match_status=exact[0].status==='ACTIVE_OR_UNCONFIRMED'
        ? 'MATCHED_PREVIOUS_ACTIVE' : 'ALREADY_ELIMINATED_PREVIOUS_WEEK'
    }else if(exact?.length>1){
      match_status='AMBIGUOUS_DUPLICATE_PREVIOUS_SHEET'
    }else{
      // A candidate is not a match: malformed PDF token extraction requires organizer review.
      const candidates=[...roster.values()].flat().filter(old=>{
        const name=normalized(old.entry_name)
        return name.startsWith(row.entry_name) && /^(?:[YX])?[A-Z]{3,25}$/.test(name.slice(row.entry_name.length))
      })
      if(candidates.length===1){
        match_status='EXTRACTION_NAME_MISMATCH_REVIEW';official_candidate=candidates[0].entry_name
      }else if(candidates.length>1){match_status='AMBIGUOUS_EXTRACTION_REVIEW'}
    }
    if(match_status==='MATCHED_PREVIOUS_ACTIVE')counts.prior_active_exact++
    else if(match_status==='ALREADY_ELIMINATED_PREVIOUS_WEEK')counts.prior_already_eliminated++
    else if(match_status==='NOT_IN_PREVIOUS_SHEET')counts.not_found++
    else counts.prior_manual_review++
    return {...row,match_status,official_candidate}
  })
  return {
    version:1,kind:'THURSDAY_DALLAS_USER_REPORTED_EVIDENCE',week:5,
    report_sha256:hash(reportedText),
    prior_csv_sha256:hash(csvText),
    prior_official_pdf_sha256:meta.source_sha256,
    official_source_file:meta.source_filename,official_week:4,
    counts,rows, certified_week5_eliminations:null,
    // No per-entry certified result, pool-size deduction, or member-pick mutation.
    official_remaining_count:null,
  }
}

export function summariseDallasReport({snapshot=null,officialMeta=null}={}) {
  const currentOfficial=Number(officialMeta?.max_week_in_file)
  const officialWeek=Number.isSafeInteger(currentOfficial) && currentOfficial>=1 && currentOfficial<=25
    ?currentOfficial:null
  const good=snapshot?.kind==='THURSDAY_DALLAS_USER_REPORTED_EVIDENCE' &&
    snapshot?.week===5 && snapshot?.version===1 &&
    /^[a-f0-9]{64}$/i.test(String(snapshot.report_sha256||'')) &&
    Array.isArray(snapshot.rows) && snapshot.rows.length===snapshot.counts?.uploaded &&
    snapshot.rows.length>0
  return {
    status: !good?'AWAITING_REPORTED_LIST':officialWeek!==4?'NEW_OFFICIAL_SHEET_REVIEW_NEEDED':'REPORTED_LIST_RECONCILED_WITH_PRIOR_SHEET',
    report_week:5,reported_count:DALLAS_CLAIM.reported_count,
    reported_count_source:DALLAS_CLAIM.source_status,
    reported_prior_matches_claim:146,reported_prior_mismatches_claim:1,
    list_imported_count:good?snapshot.counts.uploaded:0,
    list_sha256:good?snapshot.report_sha256:null,
    source_name:good?snapshot.source_name:null,
    source_captured_at:good?snapshot.saved_at:null,
    prior_week_matched:good?snapshot.counts.prior_active_exact:null,
    prior_week_needs_review:good?snapshot.counts.prior_manual_review:null,
    already_eliminated_before_week5:good?snapshot.counts.prior_already_eliminated:null,
    not_found_in_prior_sheet:good?snapshot.counts.not_found:null,
    official_week:officialWeek,
    official_week5_sheet_loaded:officialWeek===5,
    certified_week5_eliminations:null,
    official_remaining_count:null,
    count_warning:'147 is conversation-reported, not confirmed by a current official Week 5 pool sheet. Do not subtract it from the field.',
    privacy:'AGGREGATE_ONLY_NO_PARTICIPANT_NAMES',
  }
}
