#!/usr/bin/env node
// Safe CLI: no network module, provider credentials, payment setup, or
// production routes. This is a readiness review only, never a model test.
import {readFileSync} from 'node:fs'
import {pilotManifest} from './zenith_free_llm_validation.js'
import {previewFreeShadow} from './zenith_free_llm_shadow.js'

if(process.argv.length!==2){
 console.error('OFFLINE_ONLY: no live inference, provider switching or paid requests.')
 process.exit(2)
}
try {
 const source=JSON.parse(readFileSync(new URL('./zenith_free_llm_cases.json',import.meta.url),'utf8'))
 if(source.schema_version!=='zenith_synthetic_research_v1'||
    source.benchmark!=='FREE_LLM_STAGE_A_SYNTHETIC_ONLY'){
  throw new Error('unexpected_fixture_version')
 }
 const manifest=pilotManifest(source.cases)
 const providers=['groq','gemini'].map(provider=>{
  const preview=previewFreeShadow({provider,caseRecord:source.cases[0]})
  return {
   provider:preview.provider,model:preview.model,
   readiness:'REQUIRES_USER_VERIFIED_FREE_UNBILLED_ACCOUNT',
   permitted_data:'PUBLIC_SYNTHETIC_ONLY',
   automatic_calls:false,
  }
 })
 const result={
  status:'WAITING_FOR_USER_VERIFIED_FREE_ACCOUNT',
  synthetic_cases:manifest.cases,
  frozen_sha256:manifest.frozen_sha256,
  provider_calls:0,
  billing_dollars:0,
  candidate_models_tested:0,
  providers,
  production_the_ref_changed:false,
  existing_scores_or_picks_changed:false,
 }
 process.stdout.write(JSON.stringify(result,null,2)+'\n')
}catch{
 console.error('OFFLINE_ONLY: readiness source invalid.')
 process.exit(1)
}
