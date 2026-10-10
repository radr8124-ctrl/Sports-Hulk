import test from 'node:test'
import assert from 'node:assert/strict'
import {mkdtempSync,writeFileSync,chmodSync,readFileSync,statSync} from 'node:fs'
import {tmpdir} from 'node:os'
import path from 'node:path'
import {rm} from 'node:fs/promises'
import {runGroqOneCase} from './zenith_groq_free_onecase.js'

const FIXTURE=JSON.parse(readFileSync(new URL('./zenith_free_llm_cases.json',import.meta.url),'utf8'))
const NOW='2026-10-10T12:30:00Z'
const KEY='gsk_SYNTHETIC_FAKE_TEST_ONLY_123456789'
const ANSWER={
 case_id:'SYN-NFL-INJURY-01',provider_role:'source_analyst',
 status:'SUPPORTED',
 supported_claims:[{
  claim:'Synthetic Receiver A attended limited practice.',
  source_ids:['SYN:NFL:EVIDENCE:001'],
  as_of_utc:'2026-10-07T12:00:00Z'
 }],
 unresolved_claims:[],risk_flags:['Report may change.'],
 suggested_followup:'Wait for the next official report.',
 requested_bet_or_action:false,
}

function protectedFixture(t,overrides={}) {
 const dir=mkdtempSync(path.join(tmpdir(),'zenith-groq-gate-'))
 t.after(async()=>{await rm(dir,{recursive:true,force:true})})
 const secret=path.join(dir,'.env.groq_shadow')
 const state=path.join(dir,'state.json')
 const lines={
  ZENITH_GROQ_ACCOUNT_TIER:'FREE_UNBILLED',
  ZENITH_GROQ_ACCOUNT_NO_PAYMENT_METHOD:'1',
  ZENITH_GROQ_ACCOUNT_USER_CONFIRMED:'1',
  ZENITH_GROQ_ACCOUNT_CHECKED_AT:'2026-10-10T12:00:00Z',
  GROQ_API_KEY:KEY,
  ...overrides,
 }
 writeFileSync(secret,Object.entries(lines).map(([k,v])=>k+'='+v).join('\n')+'\n',{mode:0o600})
 chmodSync(secret,0o600)
 return {secretPath:secret,statePath:state,nowIso:NOW}
}
function ok() {
 return {ok:true,status:200,json:async()=>({choices:[{message:{content:JSON.stringify(ANSWER)}}]})}
}

test('unenabled isolated shadow never opens a network connection',async(t)=>{
 const opts=protectedFixture(t);let count=0
 const result=await runGroqOneCase({...opts,transport:async()=>{count++;return ok()}})
 assert.equal(result.status,'DISABLED')
 assert.equal(count,0)
 assert.equal(result.provider_calls,0)
 assert.equal(result.billing_dollars,0)
})

test('one synthetic Groq request requires free account and consumes one lifetime slot',async(t)=>{
 const opts=protectedFixture(t);let count=0, sent
 const transport=async(url,init)=>{count++;sent={url,body:JSON.parse(init.body)};return ok()}
 const result=await runGroqOneCase({...opts,enabled:true,transport})
 assert.equal(result.status,'EVALUATED')
 assert.equal(result.validator_passed,true)
 assert.equal(result.provider_calls,1)
 assert.equal(result.billing_dollars,null)
 assert.equal(count,1)
 assert.equal(sent.url,'https://api.groq.com/openai/v1/chat/completions')
 assert.equal(sent.body.reasoning_format,'hidden')
 assert.equal(sent.body.model,'openai/gpt-oss-120b')
 assert.ok(!JSON.stringify(sent.body).includes('expected_status'))
 assert.equal(statSync(opts.statePath).mode&0o777,0o600)
 assert.equal(JSON.stringify(readFileSync(opts.statePath,'utf8')).includes(KEY),false)
 const next=await runGroqOneCase({...opts,enabled:true,transport})
 assert.equal(next.status,'ALREADY_TESTED')
 assert.equal(next.provider_calls,0)
 assert.equal(count,1)
})

test('free-tier attestation is mandatory and key must be owner-only',async(t)=>{
 for(const mutation of [
  {ZENITH_GROQ_ACCOUNT_TIER:'DEVELOPER'},
  {ZENITH_GROQ_ACCOUNT_NO_PAYMENT_METHOD:'0'},
  {ZENITH_GROQ_ACCOUNT_USER_CONFIRMED:'0'},
  {ZENITH_GROQ_ACCOUNT_CHECKED_AT:'2026-06-01T00:00:00Z'},
 ]) {
  const opts=protectedFixture(t,mutation)
  let calls=0
  const result=await runGroqOneCase({...opts,enabled:true,transport:async()=>{calls++;return ok()}})
  assert.equal(result.status,'BLOCKED')
  assert.equal(calls,0)
 }
 const opts=protectedFixture(t)
 chmodSync(opts.secretPath,0o644)
 const result=await runGroqOneCase({...opts,enabled:true,transport:async()=>ok()})
 assert.equal(result.status,'BLOCKED')
})

test('missing credential and missing transport result in no requests',async(t)=>{
 const opts=protectedFixture(t)
 let called=0
 const missing=await runGroqOneCase({...opts,secretPath:opts.secretPath+'.missing',enabled:true,
  transport:async()=>{called++;return ok()}})
 assert.equal(missing.status,'BLOCKED')
 const without=await runGroqOneCase({...opts,enabled:true})
 assert.equal(without.status,'NO_TRANSPORT')
 assert.equal(called,0)
})

test('rate limit and provider outage never retry or mutate production records',async(t)=>{
 for(const status of [429,401,500]) {
  const opts=protectedFixture(t)
  let calls=0
  const result=await runGroqOneCase({...opts,enabled:true,transport:async()=>{
   calls++;return {ok:false,status,json:async()=>({error:'PRIVATE_KEY_STRING_DO_NOT_LOG'})}
  }})
  assert.equal(result.provider_calls,1)
  assert.equal(calls,1)
  assert.equal(JSON.stringify(result).includes('PRIVATE_KEY_STRING_DO_NOT_LOG'),false)
  const next=await runGroqOneCase({...opts,enabled:true,transport:async()=>{calls++;return ok()}})
  assert.equal(next.status,'ALREADY_TESTED')
  assert.equal(calls,1)
 }
})

test('first fixture must be the frozen public bank, never arbitrary private data',async(t)=>{
 const opts=protectedFixture(t)
 let calls=0
 const broken={...FIXTURE,cases:[{...FIXTURE.cases[0],question:'Private roster: John Doe'}]}
 const result=await runGroqOneCase({...opts,enabled:true,
  bank:broken,transport:async()=>{calls++;return ok()}})
 assert.equal(result.status,'BLOCKED')
 assert.equal(calls,0)
})

test('one-case command refuses all implicit attempts without key exposure',async()=>{
 const {spawnSync}=await import('node:child_process')
 for(const args of [[],['--run'],['--many'],['--provider=paid']]){
  const result=spawnSync(process.execPath,['zenith_groq_free_onecase_cli.mjs',...args],{
   cwd:new URL('.',import.meta.url),encoding:'utf8',timeout:5000,
   env:{...process.env,GROQ_API_KEY:'EXAMPLE_NOT_TO_SEND'},
  })
  assert.notEqual(result.status,0)
  assert.equal(result.stdout,'')
  assert.match(result.stderr,/EXPLICIT_FREE_ONE_CASE_ONLY/i)
  assert.equal(result.stderr.includes('EXAMPLE_NOT_TO_SEND'),false)
 }
})
