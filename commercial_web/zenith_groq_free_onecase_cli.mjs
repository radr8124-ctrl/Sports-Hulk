#!/usr/bin/env node
// Explicit offline-safe operator command. This code has no auto-scheduling,
// no paid tier, no retries, no browser data, no user prompts, no site routes.
import {runGroqOneCase} from './zenith_groq_free_onecase.js'

if(process.argv.length!==3||process.argv[2]!=='--one-synthetic-free-call'){
 console.error('EXPLICIT_FREE_ONE_CASE_ONLY: no automatic model use; use only after verified Free/no-payment setup.')
 process.exit(2)
}

try{
 const result=await runGroqOneCase({
  enabled:true,
  // The adapter accepts only one fixed synthetic fixture and one lifetime call.
  // No network occurs if account attestation is missing, old or not owner-only.
  transport:(url,init)=>fetch(url,init),
 })
 // Metadata only; no prompt, account token, real names, or provider text.
 process.stdout.write(JSON.stringify(result)+'\n')
 if(result.status!=='EVALUATED')process.exitCode=2
}catch{
 console.error('GROQ_FREE_ONECASE_ABORTED')
 process.exitCode=2
}
