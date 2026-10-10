import {readFileSync,lstatSync} from 'node:fs'
import {open,mkdir} from 'node:fs/promises'
import {dirname} from 'node:path'
import {pilotManifest} from './zenith_free_llm_validation.js'
import {runFreeShadow} from './zenith_free_llm_shadow.js'

// Exactly one hand-triggered $0 Free-plan synthetic Groq request lifetime.
// No daemon, cron, browser, paid provider, private content or scheduled replay.
const FROZEN_HASH='c23540369860727d16d35639ff753e037f901c5f4cb98ff17a600abd4145954b'
const DEFAULT_SECRET='/home/ubuntu/sports-hulk/commercial_web/.env.groq_shadow'
const DEFAULT_STATE='/home/ubuntu/.local/state/sports-zenith/groq-free-onecase-attempt.json'
const fail=(status)=>({status,provider_calls:0,billing_dollars:0,synthetic_only:true})

function parseProtectedSecret(location) {
 const st=lstatSync(location)
 if(!st.isFile()||(st.mode&0o077)!==0||
    (typeof process.getuid==='function'&&st.uid!==process.getuid())){
  throw new Error('unprotected_credential_file')
 }
 const lines=readFileSync(location,'utf8').split(/\r?\n/).filter(Boolean)
 const vars={}
 for(const line of lines) {
  const pos=line.indexOf('=')
  if(pos<=0)throw new Error('malformed_credential_file')
  const k=line.slice(0,pos)
  const val=line.slice(pos+1)
  if(!/^[A-Z_]+$/.test(k) || Object.hasOwn(vars,k)) {
   throw new Error('malformed_credential_file')
  }
  vars[k]=val
 }
 if(vars.ZENITH_GROQ_ACCOUNT_TIER!=='FREE_UNBILLED'||
    vars.ZENITH_GROQ_ACCOUNT_NO_PAYMENT_METHOD!=='1'||
    vars.ZENITH_GROQ_ACCOUNT_USER_CONFIRMED!=='1'||
    !/^gsk_[A-Za-z0-9_-]{16,196}$/.test(vars.GROQ_API_KEY??'')){
  throw new Error('unverified_free_account')
 }
 return vars
}

function frozenBank(bank) {
 const parsed=bank??JSON.parse(readFileSync(new URL('./zenith_free_llm_cases.json',import.meta.url),'utf8'))
 if(parsed?.schema_version!=='zenith_synthetic_research_v1' ||
    parsed?.benchmark!=='FREE_LLM_STAGE_A_SYNTHETIC_ONLY'||
    !Array.isArray(parsed.cases)||parsed.cases[0]?.case_id!=='SYN-NFL-INJURY-01'||
    pilotManifest(parsed.cases).frozen_sha256!==FROZEN_HASH){
  throw new Error('frozen_synthetic_fixture_mismatch')
 }
 return parsed.cases[0]
}

export async function runGroqOneCase({
 enabled=false,
 secretPath=DEFAULT_SECRET,
 statePath=DEFAULT_STATE,
 nowIso=new Date().toISOString(),
 bank,
 transport,
}={}){
 if(enabled!==true)return fail('DISABLED')
 if(typeof transport!=='function')return fail('NO_TRANSPORT')
 let vars,caseRecord
 try{
  vars=parseProtectedSecret(secretPath)
  caseRecord=frozenBank(bank)
  const now=Date.parse(nowIso)
  const checked=Date.parse(vars.ZENITH_GROQ_ACCOUNT_CHECKED_AT||'')
  if(!Number.isFinite(now)||!Number.isFinite(checked)||checked>now||
     now-checked>24*60*60*1000)throw new Error('stale_free_attestation')
 }catch{
  return fail('BLOCKED')
 }

 // Reserve a single lifetime attempt BEFORE any network call; no retry or
 // upgrade path even after 429/timeout/process crash.
 try{
  await mkdir(dirname(statePath),{recursive:true,mode:0o700})
  const state=await open(statePath,'wx',0o600)
  try {
   await state.writeFile(JSON.stringify({
    attempted_at:nowIso,
    case_id:caseRecord.case_id,
    synthetic_only:true,
    provider:'groq',
    max_lifetime_calls:1,
    fee_tier:'USER_ATTESTED_FREE_UNBILLED_NOT_INDEPENDENTLY_VERIFIED',
   })+'\n',{encoding:'utf8'})
   await state.sync()
  }finally{await state.close()}
 }catch(error){
  if(error?.code==='EEXIST')return fail('ALREADY_TESTED')
  return fail('BLOCKED')
 }
 const proof={
  tier:'FREE_UNBILLED',billingEnabled:false,paymentMethodOnFile:false,
  userConfirmed:true,checkedAt:vars.ZENITH_GROQ_ACCOUNT_CHECKED_AT,
 }
 const assessment=await runFreeShadow({
  provider:'groq',
  caseRecord,
  credential:vars.GROQ_API_KEY,
  accountProof:proof,
  nowIso,
  enabled:true,
  transport,
 })
 return {
  status:assessment.status,
  provider:'groq',
  model:'openai/gpt-oss-120b',
  case_id:caseRecord.case_id,
  validator_passed:assessment.validator_passed,
  errors:Array.isArray(assessment.errors)?assessment.errors:[],
  provider_calls:assessment.external_calls,
  billing_dollars:assessment.billing_dollars,
  synthetic_only:true,
  no_retries:true,
  free_plan_user_attested:true,
  account_billing_independently_verified:false,
 }
}

// This imported file never calls fetch itself. Only the explicit CLI supplies
// a transport once and only after the user's no-payment Free confirmation.
