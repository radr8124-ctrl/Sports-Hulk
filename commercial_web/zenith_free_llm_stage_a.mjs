#!/usr/bin/env node
// Sports Zenith Stage A only: describe a frozen synthetic benchmark. No
// provider SDKs, network calls, API keys, wagers or production state changes.
import {readFileSync} from 'node:fs'
import {pilotManifest} from './zenith_free_llm_validation.js'

if(process.argv.length!==2){
 console.error('EXTERNAL_MODEL_INFERENCE_DISABLED: only an offline $0 dry-run is approved.')
 process.exit(2)
}

try{
 const fixture=JSON.parse(readFileSync(new URL('./zenith_free_llm_cases.json',import.meta.url),'utf8'))
 if(fixture.schema_version!=='zenith_synthetic_research_v1'||
    fixture.benchmark!=='FREE_LLM_STAGE_A_SYNTHETIC_ONLY'){
  throw new Error('fixture_not_approved')
 }
 const manifest=pilotManifest(fixture.cases)
 const sports={}
 const expected_statuses={}
 for(const entry of fixture.cases){
  sports[entry.sport]=(sports[entry.sport]||0)+1
  const status=entry.expected_status
  if(!['SUPPORTED','CONFLICT','STALE','INSUFFICIENT_EVIDENCE'].includes(status)){
   throw new Error('invalid_private_golden_status')
  }
  expected_statuses[status]=(expected_statuses[status]||0)+1
 }
 process.stdout.write(JSON.stringify({
  ...manifest,
  benchmark:fixture.benchmark,
  sports,
  expected_statuses,
  synthetic_only:true,
  connected_to_live_ask:false,
  external_model_inference_enabled:false,
 },null,2)+'\n')
}catch{
 // Deliberately no raw exceptions or case content in errors/logs.
 console.error('OFFLINE_BENCHMARK_INPUT_INVALID')
 process.exit(1)
}
