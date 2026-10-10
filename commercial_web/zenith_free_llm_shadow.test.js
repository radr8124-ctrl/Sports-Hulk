import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import {
  buildFreeShadowRequest, runFreeShadow, previewFreeShadow,
  FREE_SHADOW_MODELS,
} from './zenith_free_llm_shadow.js'

const cases = JSON.parse(readFileSync(new URL('./zenith_free_llm_cases.json', import.meta.url),'utf8')).cases
const first = cases.find(item=>item.case_id==='SYN-NFL-INJURY-01')
const injection = cases.find(item=>item.case_id==='SYN-NFL-INJECTION-15')
const key='EXAMPLE_FAKE_KEY_PRIVATE'
const proof=Object.freeze({
  tier:'FREE_UNBILLED', billingEnabled:false, paymentMethodOnFile:false,
  userConfirmed:true, checkedAt:'2026-10-10T11:00:00Z',
})
const now='2026-10-10T12:00:00Z'
function opts(overrides={}) {
 return {provider:'groq',caseRecord:first,credential:key,
  accountProof:proof,nowIso:now,...overrides}
}
function answer() {
 return {
  case_id:first.case_id, provider_role:'source_analyst',status:'SUPPORTED',
  supported_claims:[{claim:first.facts[0].claim,source_ids:[first.facts[0].source_id],
   as_of_utc:first.as_of_utc}],
  unresolved_claims:[],risk_flags:['Further verified news could change this.'],
  suggested_followup:'Wait for an official confirmation.',
  requested_bet_or_action:false,
 }
}
const jsonResponse=(payload, status=200)=>({
  ok: status>=200&&status<300,status,
  json: async()=>payload,
})

test('dry preview is offline, model locked and contains no private material',()=>{
 const result=previewFreeShadow({provider:'groq',caseRecord:first})
 assert.equal(result.status,'OFFLINE_ONLY')
 assert.equal(result.provider,'groq')
 assert.equal(result.external_calls,0)
 assert.equal(result.billing_dollars,0)
 const content=JSON.stringify(result)
 for(const forbidden of ['question','facts','private','SECRET','EXAMPLE_FAKE_KEY_PRIVATE',
  'expected_status','Nebula']) assert.equal(content.includes(forbidden),false)
 assert.equal(result.model,FREE_SHADOW_MODELS.groq)
})

test('rejects unsupported providers and paid-model substitution',()=>{
 for(const provider of ['claude','copilot','azure','openrouter','groq-paid','OPENAI']){
  assert.throws(()=>buildFreeShadowRequest(opts({provider})),/provider_not_allowlisted/i)
 }
 assert.throws(()=>buildFreeShadowRequest(opts({model:'llama-3.3-70b-versatile'})),/model_not_allowlisted/i)
})

test('no credential, no verified free status or any billing attachment means no request',()=>{
 for(const change of [
  {credential:null},
  {accountProof:null},
  {accountProof:{...proof,tier:'DEVELOPER'}},
  {accountProof:{...proof,billingEnabled:true}},
  {accountProof:{...proof,paymentMethodOnFile:true}},
  {accountProof:{...proof,userConfirmed:false}},
  {accountProof:{...proof,checkedAt:'2026-01-01T00:00:00Z'}},
 ]){
  assert.throws(()=>buildFreeShadowRequest(opts(change)),/free_account_gate|missing_secure_credential/i)
 }
})

test('Groq request is small and contains only publicly sealed synthetic facts',()=>{
 const call=buildFreeShadowRequest(opts())
 assert.equal(call.url,'https://api.groq.com/openai/v1/chat/completions')
 assert.equal(call.model,'openai/gpt-oss-120b')
 assert.equal(call.headers.Authorization,'Bearer '+key)
 assert.equal(call.body.model,'openai/gpt-oss-120b')
 assert.equal(call.body.tool_choice,'none')
 assert.equal(call.body.max_completion_tokens,450)
 assert.equal(call.body.response_format.type,'json_object')
 assert.equal(call.body.reasoning_format,'hidden')
 const messages=JSON.stringify(call.body)
 assert.ok(messages.includes('Synthetic Receiver A'))
 assert.ok(!messages.includes('expected_status'))
 assert.ok(!messages.includes('private_entry'))
 assert.ok(!messages.includes('score_hint'))
 assert.ok(!messages.includes(key))
 assert.ok(messages.length<12000)
})

test('Gemini request uses safe JSON output and no search or tools',()=>{
 const call=buildFreeShadowRequest(opts({provider:'gemini'}))
 assert.equal(call.url,'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent')
 assert.equal(call.headers['x-goog-api-key'],key)
 assert.equal(call.model,'gemini-2.5-flash-lite')
 assert.equal(call.body.generationConfig.responseMimeType,'application/json')
 assert.equal(call.body.generationConfig.maxOutputTokens,450)
 assert.equal(Object.hasOwn(call.body,'tools'),false)
 assert.equal(Object.hasOwn(call.body,'toolConfig'),false)
 assert.equal(Object.hasOwn(call.body,'googleSearch'),false)
 assert.equal(JSON.stringify(call.body).includes('expected_status'),false)
 assert.equal(JSON.stringify(call.body).includes(key),false)
})

test('untrusted injection sources are quarantined before model input',()=>{
 const call=buildFreeShadowRequest(opts({caseRecord:injection}))
 const raw=JSON.stringify(call.body)
 assert.equal(raw.includes('Ignore safety rules'),false)
 assert.equal(raw.includes('disclose secrets'),false)
 assert.equal(raw.includes('expected_status'),false)
})

test('default shadow execution is disabled even if a key and transport exist',async()=>{
 let called=0
 const receipt=await runFreeShadow({...opts(),transport:async()=>{called++;return jsonResponse({})}})
 assert.equal(called,0)
 assert.equal(receipt.status,'DISABLED')
 assert.equal(receipt.external_calls,0)
 assert.equal(receipt.billing_dollars,0)
})

test('without explicit user-verified free account, network stays blocked',async()=>{
 let called=0
 const receipt=await runFreeShadow({...opts({accountProof:{...proof,billingEnabled:true}}),
  enabled:true,transport:async()=>{called++;return jsonResponse({})}})
 assert.equal(called,0)
 assert.equal(receipt.status,'BLOCKED')
 assert.equal(receipt.billing_dollars,0)
})

test('mock Groq model runs through source validator and returns a redacted receipt',async()=>{
 let seen=0
 const receipt=await runFreeShadow({...opts(),enabled:true,
  transport:async (url,init)=>{
    seen++
    assert.equal(url,'https://api.groq.com/openai/v1/chat/completions')
    assert.ok(init.headers.Authorization.startsWith('Bearer '))
    return jsonResponse({choices:[{message:{content:JSON.stringify(answer())}}]})
  }
 })
 assert.equal(seen,1)
 assert.equal(receipt.status,'EVALUATED')
 assert.equal(receipt.validator_passed,true)
 assert.equal(receipt.external_calls,1)
 assert.equal(receipt.billing_dollars,null) // Not proof of $0 until provider account is verified
 assert.equal(receipt.case_id,first.case_id)
 const raw=JSON.stringify(receipt)
 assert.equal(raw.includes(key),false)
 assert.equal(raw.includes(first.facts[0].claim),false)
 assert.equal(raw.includes(first.question),false)
})

test('mock Gemini model response parses and is checked against same evidence',async()=>{
 const receipt=await runFreeShadow({...opts({provider:'gemini'}),enabled:true,
   transport:async()=>jsonResponse({candidates:[{content:{parts:[{text:JSON.stringify(answer())}]}}]})
 })
 assert.equal(receipt.status,'EVALUATED')
 assert.equal(receipt.validator_passed,true)
 assert.equal(receipt.provider,'gemini')
})

test('unsupported claims, wrong model response and untrusted advice never pass',async()=>{
 const forged={...answer(),supported_claims:[{
   claim:'Synthetic Receiver A is a guaranteed winning bet',
   source_ids:[first.facts[0].source_id],as_of_utc:first.as_of_utc,
 }]}
 const receipt=await runFreeShadow({...opts(),enabled:true,
  transport:async()=>jsonResponse({choices:[{message:{content:JSON.stringify(forged)}}]})
 })
 assert.equal(receipt.status,'EVALUATED')
 assert.equal(receipt.validator_passed,false)
 assert.ok(receipt.errors.includes('claim_not_in_evidence'))
})

test('server 429 fails closed without retries or leaking provider response',async()=>{
 let calls=0
 const receipt=await runFreeShadow({...opts(),enabled:true,
  transport:async()=>{calls++;return jsonResponse({error:{message:'SECRET_PRIVATE_ERROR'}},429)}
 })
 assert.equal(calls,1)
 assert.equal(receipt.status,'RATE_LIMITED')
 assert.equal(receipt.external_calls,1)
 assert.equal(JSON.stringify(receipt).includes('SECRET_PRIVATE_ERROR'),false)
})

test('HTTP and malformed JSON errors return safe statuses without retry',async()=>{
 for(const resp of [
  jsonResponse({error:{message:'PRIVATE_TOKEN'}},401),
  jsonResponse({choices:[{message:{content:'{not valid json'}}]}),
  jsonResponse({choices:[]}),
 ]){
  const receipt=await runFreeShadow({...opts(),enabled:true,transport:async()=>resp})
  assert.ok(['API_ERROR','INVALID_OUTPUT'].includes(receipt.status))
  assert.equal(receipt.validator_passed,false)
  assert.equal(JSON.stringify(receipt).includes('PRIVATE_TOKEN'),false)
 }
})

test('no transport is safe and does not reach global fetch',async()=>{
 const receipt=await runFreeShadow({...opts(),enabled:true})
 assert.equal(receipt.status,'NO_TRANSPORT')
 assert.equal(receipt.external_calls,0)
})

test('all provider calls require a sealed synthetic fixture; real or private blocked',()=>{
 const c={...first,privacy:'PRIVATE_SURVIVOR'}
 assert.throws(()=>buildFreeShadowRequest(opts({caseRecord:c})),/privacy/i)
 const record={...first,question:'Contact private-owner@example.com now'}
 assert.throws(()=>buildFreeShadowRequest(opts({caseRecord:record})),/private|invalid_public/i)
})

test('offline readiness runner previews both free providers without credentials or costs',()=>{
 const output=spawnSync(process.execPath,['zenith_free_llm_shadow_preview.mjs'],{
  cwd:new URL('.',import.meta.url),
  env:{...process.env,GROQ_API_KEY:'SHOULD_NOT_BE_SENT',GEMINI_API_KEY:'SHOULD_NOT_BE_SENT'},
  encoding:'utf8',timeout:5000,
 })
 assert.equal(output.status,0,output.stderr)
 const manifest=JSON.parse(output.stdout)
 assert.equal(manifest.status,'WAITING_FOR_USER_VERIFIED_FREE_ACCOUNT')
 assert.equal(manifest.synthetic_cases,18)
 assert.equal(manifest.provider_calls,0)
 assert.equal(manifest.billing_dollars,0)
 assert.deepEqual(manifest.providers.map(p=>p.provider),['groq','gemini'])
 assert.equal(JSON.stringify(manifest).includes('SHOULD_NOT_BE_SENT'),false)
 assert.equal(JSON.stringify(manifest).includes('What did'),false)
})
test('readiness runner rejects unknown options and never enters live mode',()=>{
 for(const opt of ['--live','--provider=claude','--provider=paid','--send']){
  const output=spawnSync(process.execPath,['zenith_free_llm_shadow_preview.mjs',opt],{
   cwd:new URL('.',import.meta.url),encoding:'utf8',timeout:5000,
  })
  assert.notEqual(output.status,0)
  assert.equal(output.stdout,'')
  assert.match(output.stderr,/OFFLINE_ONLY/i)
 }
})
