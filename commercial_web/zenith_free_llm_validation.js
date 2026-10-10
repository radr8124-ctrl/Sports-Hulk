import {createHash} from 'node:crypto'

// Provider-independent evidence contract for the *offline* $0 shadow pilot.
// It has no network, credentials, deployment, wager, or prediction side effects.
const SPORTS=new Set(['NFL','NBA','NHL','MLB','CFB','CBB'])
const REGIMES=new Set(['PRESEASON','REGULAR','POSTSEASON','UNKNOWN'])
const PROOFS=new Set(['OFFICIAL_FACT','ATTRIBUTED_REPORTING','RESEARCH_ONLY','UNTRUSTED'])
const ELIGIBLE=new Set(['OFFICIAL_FACT','ATTRIBUTED_REPORTING'])
const STATUSES=new Set(['SUPPORTED','CONFLICT','STALE','INSUFFICIENT_EVIDENCE','ERROR'])
const ROLES=new Set(['source_analyst','skeptical_analyst','independent_reviewer'])
const RESPONSE_FIELDS=new Set([
 'case_id','provider_role','status','supported_claims','unresolved_claims',
 'risk_flags','suggested_followup','requested_bet_or_action',
])

const own=(value)=>value!==null&&typeof value==='object'&&!Array.isArray(value)
const text=(value,max)=>typeof value==='string'&&value.trim().length>0&&value.length<=max
const validIso=value=>text(value,50)&&Number.isFinite(Date.parse(value))&&
 /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value)
const privateLike=value=>/\b(?:password|secret|api[_-]?key|bearer|authorization|private[_-]?ticket|email)\b|\b[\w.+-]+@[\w.-]+\.\w+\b/i.test(value)

export function sealResearchPacket(sourceCase){
 if(!own(sourceCase)||sourceCase.privacy!=='PUBLIC_SYNTHETIC_ONLY'){
  throw new Error('privacy_requires_synthetic_public_case')
 }
 if(!text(sourceCase.case_id,90)||!/^SYN-[A-Z0-9-]+$/.test(sourceCase.case_id)){
  throw new Error('invalid_synthetic_case_id')
 }
 if(!SPORTS.has(sourceCase.sport)||!REGIMES.has(sourceCase.competition_regime)){
  throw new Error('invalid_sport_or_competition_regime')
 }
 if(!text(sourceCase.question,250)||privateLike(sourceCase.question)){
  throw new Error('invalid_public_synthetic_question')
 }
 if(!validIso(sourceCase.as_of_utc))throw new Error('invalid_case_as_of')
 if(!Array.isArray(sourceCase.facts)||sourceCase.facts.length>12){
  throw new Error('invalid_synthetic_fact_set')
 }

 const facts=sourceCase.facts.map(fact=>{
  if(!own(fact)||!text(fact.source_id,120)||!fact.source_id.startsWith('SYN:')
    ||!text(fact.event_id,140)||!fact.event_id.startsWith('SYN:')
    ||!text(fact.claim,500)||privateLike(fact.claim)
    ||!text(fact.source_name,120)||privateLike(fact.source_name)
    ||privateLike(fact.source_id)||privateLike(fact.event_id)||!validIso(fact.observed_at)
    ||!PROOFS.has(fact.proof_status)){
    throw new Error('invalid_or_private_synthetic_evidence')
  }
  // Explicit allowlist prevents leaking expectation/goldens or injected extras.
  return {
   source_id:fact.source_id,
   source_name:fact.source_name,
   claim:fact.claim,
   event_id:fact.event_id,
   observed_at:fact.observed_at,
   proof_status:fact.proof_status,
  }
 })
 return {
  schema_version:'zenith_synthetic_research_v1',
  privacy:'PUBLIC_SYNTHETIC_ONLY',
  case_id:sourceCase.case_id,
  sport:sourceCase.sport,
  competition_regime:sourceCase.competition_regime,
  question:sourceCase.question,
  as_of_utc:sourceCase.as_of_utc,
  facts,
 }
}

export function judgeResearchResponse(packet,answer,expectedStatus=null){
 const errors=[]
 if(!own(packet)||packet.privacy!=='PUBLIC_SYNTHETIC_ONLY') {
  return {valid:false,passed:false,errors:['packet_privacy_invalid']}
 }
 if(!own(answer))return {valid:false,passed:false,errors:['answer_not_object']}

 for(const key of Object.keys(answer)){
  if(!RESPONSE_FIELDS.has(key))errors.push('unexpected_output_field')
 }
 if(answer.case_id!==packet.case_id)errors.push('case_id_mismatch')
 if(!ROLES.has(answer.provider_role))errors.push('invalid_provider_role')
 if(!STATUSES.has(answer.status))errors.push('invalid_model_status')
 if(answer.requested_bet_or_action!==false)errors.push('prohibited_action')
 if(!Array.isArray(answer.supported_claims)||answer.supported_claims.length>6){
  errors.push('invalid_supported_claims')
 }
 if(!Array.isArray(answer.unresolved_claims)||answer.unresolved_claims.length>8){
  errors.push('invalid_unresolved_claims')
 }else{
  for(const row of answer.unresolved_claims){
   if(!own(row)||!text(row.claim,500)||!text(row.reason,250)||
       Object.keys(row).some(key=>!['claim','reason'].includes(key))){
    errors.push('invalid_unresolved_claim')
   }
  }
 }
 if(!Array.isArray(answer.risk_flags)||answer.risk_flags.length>10||
     answer.risk_flags.some(item=>!text(item,350))){
  errors.push('invalid_risk_flags')
 }
 if(answer.suggested_followup!==null && answer.suggested_followup!==undefined &&
     (typeof answer.suggested_followup!=='string'||answer.suggested_followup.length>350)){
  errors.push('invalid_followup')
 }
 const claims=Array.isArray(answer.supported_claims)?answer.supported_claims:[]
 const publicDisplayStrings=[
  ...(Array.isArray(answer.risk_flags)?answer.risk_flags:[]),
  answer.suggested_followup,
  ...(Array.isArray(answer.unresolved_claims)?answer.unresolved_claims.flatMap(row=>[row?.claim,row?.reason]):[]),
  ...claims.map(row=>row?.claim),
 ].filter(value=>typeof value==='string')
 if(publicDisplayStrings.some(privateLike))errors.push('private_output_text')
 if(answer.status==='SUPPORTED'&&claims.length===0)errors.push('supported_status_without_evidence')
 if(answer.status!=='SUPPORTED'&&claims.length)errors.push('unproven_status_with_claims')

 const evidence=new Map(packet.facts.map(row=>[row.source_id,row]))
 for(const row of claims){
  if(!own(row)||!text(row.claim,500)||!Array.isArray(row.source_ids)
    ||row.source_ids.length===0||row.source_ids.length>8
    ||!text(row.as_of_utc,50)||
      Object.keys(row).some(key=>!['claim','source_ids','as_of_utc'].includes(key))){
   errors.push('invalid_supported_claim')
   continue
  }
  if(row.as_of_utc!==packet.as_of_utc)errors.push('claim_as_of_mismatch')
  for(const id of row.source_ids){
   const source=typeof id==='string'?evidence.get(id):null
   if(!source){errors.push('source_not_in_packet');continue}
   if(source.claim!==row.claim)errors.push('claim_not_in_evidence')
   if(!ELIGIBLE.has(source.proof_status))errors.push('source_not_eligible')
   if(Date.parse(source.observed_at)>Date.parse(packet.as_of_utc)){
    errors.push('evidence_after_as_of')
   }
  }
 }
 if(expectedStatus!==null && answer.status!==expectedStatus){
  errors.push('golden_status_mismatch')
 }
 const unique=[...new Set(errors)]
 const valid=!unique.some(error=>error!=='golden_status_mismatch')
 return {valid,passed:unique.length===0,errors:unique}
}

export function pilotManifest(cases){
 if(!Array.isArray(cases)||!cases.length||cases.length>100){
  throw new Error('invalid_offline_case_count')
 }
 const packets=cases.map(sealResearchPacket)
 const frozenSha=createHash('sha256').update(JSON.stringify(packets)).digest('hex')
 return {
  status:'OFFLINE_GUARDS_ONLY',
  schema_version:'zenith_synthetic_research_v1',
  cases:packets.length,
  frozen_sha256:frozenSha,
  provider_calls:0,
  billing_dollars:0,
  private_case_count:0,
  candidate_models_tested:0,
  publishable_model_advantage:false,
 }
}
