# Sports Zenith — Free LLM Stage B: Groq and Gemini Read-Only Shadow Adapters
Date: October 10, 2026
Status: ADAPTERS READY / ALL CALLS OFF / NO EXTERNAL LLM EVALUATED
Repository: `/home/ubuntu/sports-hulk`
Existing Stage A synthetic bank digest: `c23540369860727d16d35639ff753e037f901c5f4cb98ff17a600abd4145954b`

## User requirement and scope
Continue upgrading the existing Sports Zenith brain with **genuinely $0 AI**, without paying API providers, buying GPUs, reworking the website, touching official predictions or private Survivor/Fantasy data, or claiming a predictive advantage before evidence.

## Deliverables
- `commercial_web/zenith_free_llm_shadow.js`: independent, pure-provider adapter layer for Groq GPT-OSS 120B (`openai/gpt-oss-120b`) and Gemini 2.5 Flash-Lite (`gemini-2.5-flash-lite`). Official REST endpoints with server-only authentication header are hardcoded; model name overrides and paid/unknown providers are rejected.
- Request builder seals the original versioned 18-case synthetic bank through `sealResearchPacket`, sends only required source-evidence identifiers, facts and timestamps; drops grader goldens, private/undeclared fields, future evidence and untrusted-source instructions before request assembly.
- Model prompt explicitly forbids browsing, external tools, wagering actions, invented prices and real-world sports substitutions. It asks for one JSON answer. Groq uses `tool_choice:'none'`, `response_format:{type:'json_object'}`, max 450 output tokens. Gemini uses the JSON content type, max 450 output tokens, no tools/search.
- Optional `runFreeShadow` requires **three independent explicit conditions**: `enabled:true`, an injected transport (there is no global `fetch` used by default), and a fresh user-confirmed account attestation `tier:'FREE_UNBILLED'`, `billingEnabled:false`, `paymentMethodOnFile:false`. It also requires a credential passed only in memory; it never logs provider responses, keys, source text or private fields.
- Results from mocked providers pass through the original `judgeResearchResponse` literal source-evidence validator, which blocks invented claims, fabricated odds, fake source IDs, future timestamps, unauthorized actions and unproven status promotion. The result is metadata-only: case ID, provider, validity, vetted error identifiers, no raw text. No actual model output or result is accepted as a sports pick.
- Fail-closed behavior for missing credentials, non-free account flags, unknown model IDs, no transport, invalid JSON, oversized replies, 429 rate limits and HTTP errors; no retries or pay-as-you-go fallback.
- `commercial_web/zenith_free_llm_shadow_preview.mjs`: a **strictly no-network** readiness CLI; it prints model names, synthetic bank SHA and exact connection blocker; rejects all arguments including `--live` and paid provider names. Adding shell API keys alone can never activate this preview.
- `reports/SPORTS_ZENITH_FREE_LLM_STAGE_B_READINESS_20261010.json`: generated and SHA-checked offline readiness receipt, frozen 18-case digest preserved from Stage A.
- `commercial_web/zenith_free_llm_shadow.test.js`: 17 unit tests with injected mock responses only.

## Verification and evidence
- Red/green observed for missing adapter (15 expected failures initially), then adapter implementation passed 15/15. Separate red/green observed for missing offline preview CLI (2 expected failures), then preview implemented and 17/17 tests passed.
- Full JS regression: **302/302 pass**.
- Vite production frontend build: **PASS** (normal existing non-fatal bundle-size warning).
- Browser regression: **18/18 pass** (existing Home theme, The Ref, Brain Record/navigation).
- Frozen Stage A receipt matches current 18-case bank checksum exactly.
- Real website `https://sportszenith.com/api/health`: 200 at last check. No modification to `commercial_web/server.js`, public The Ref, frozen sports ledgers, private account data, or production game models in Stage B.
- All external LLM requests: **0**. Model benchmarks run against actual Groq/Gemini output: **0**. Provider spend: **$0**. No provider free account or API key was found in checked project environment files. Do not claim either LLM connected to Sports Zenith yet.

## Strict cost interpretation
- The user explicitly requires **$0**, so API calls must never be attempted on a paid account, a billing-enabled cloud project, or with unknown account status. The code requires fresh explicit account confirmation but does not independently query provider billing status; therefore a future real inference step still requires a **separate user-authorized provider setup and billing-free verification**.
- Models are limited to Groq's currently documented Free plan and Gemini's model-specific Free-tier availability. Official docs used for API wire shapes and cost policy:
  - `https://console.groq.com/docs/rate-limits`
  - `https://console.groq.com/docs/billing-faqs`
  - `https://console.groq.com/docs/structured-outputs`
  - `https://ai.google.dev/gemini-api/docs/billing/`
  - `https://ai.google.dev/gemini-api/docs/pricing`
  - `https://ai.google.dev/api/generate-content`
- Gemini Free inputs may be used for provider product improvement; even a user-confirmed free key must be used only for **fictional/synthetic** examples. No private or licensed material should be transmitted.

## Repeatable commands
```bash
cd /home/ubuntu/sports-hulk/commercial_web
node zenith_free_llm_shadow_preview.mjs
node --test zenith_free_llm_shadow.test.js
node --test *.test.js
npm run build
```
This does not authorize live provider calls. A later feature request should implement explicit verified-free connectivity only in a separately reviewed/committed CLI job, with strict request count and daily limit, and without altering the existing prediction engine.

## Next gated step
The only current blocker is legitimate **free-unbilled GroqCloud or Gemini API credentials**, which require the user's explicit account-side action. Never ask for credentials pasted into chat; arrange secret entry directly into the server's protected environment under user authorization, then perform a small trial with the 18 frozen **synthetic** cases, compare unsupported-claim and abstention rates, and only after proven success consider improving public The Ref explanations. The current adapter's manual `accountProof` is not by itself an independent zero-billing guarantee.
