# Sports Zenith — Multi-LLM Analyst Staff Pilot (Design for Review)
Date: 2026-10-10
Status: DESIGN DRAFT — user explicitly requires $0 spend; awaiting design approval and any verified no-billing free-tier credentials
Repository: /home/ubuntu/sports-hulk
Live app: https://sportszenith.com
Scope: read-only candidate analysis inside the current Sports Zenith system; no new website, no production activation in this document.

## 1. Goal and preserved work
User wants Gemini, Claude, and Microsoft's AI model platform working like a coordinated administrative staff for Sports Zenith: gather verified evidence, independently review difficult sports cases, reconcile disagreements, and let The Ref explain clearly. The success condition is **measurable factual and decision-support improvement**, not apparent agreement between LLMs or more bets.

Reuse rather than replace:
- Existing commercial_web/server.js -> POST /api/ask intent router with deterministic response and validation.
- Existing commercial_web/ask_output_validation.js and ask_trace.js guardrails/trace.
- Existing source files and frozen model/accountability ledgers across NFL, NBA, NHL, MLB, CFB, CBB, props, fantasy, DFS, and Survivor.
- Existing reports/ASK_SPORTS_HULK_AGENT_ARCHITECTURE.md: specialist-agent, evidence-led design already agreed in earlier work.
- Existing commercial_web/evaluate_ask.py (17 legacy cases), reports/ASK_RETRIEVAL_GOLDEN_CURRENT.json (5 synthetic retrieval cases), reports/ASK_SEMANTIC_ANSWER_GOLDEN_CURRENT.json (5 semantic cases).
- Existing bright, retro-premium UI, original The Ref and private authenticated user features.

## 2. Precisely separate two different kinds of agent

### Production sports evidence analysts
| Role | Initial intended provider | Allowed work | Not allowed |
| --- | --- | --- | --- |
| Source analyst | Gemini free-tier API on an unbilled project | Extract bounded injury, player, team, schedule, and news claims from **already-verified source packets**; separate confirmed facts from attributed reporting | Invent injuries, update team availability statuses, fetch unapproved sources |
| Skeptical analyst | GroqCloud Free API, using GPT-OSS or Qwen open models | Challenge reasoning, identify contradictions, risk, unproven assumptions, as-of-time violations, and missing evidence | Rewrite sportsbook odds, claim sure wins or verified independent betting edge |
| Independent reviewer | OpenRouter Free model as capacity-limited challenger, never a paid Foundry deployment | Compare analyst outputs using a genuinely distinct model family when available; flag unresolved claims | Treat a second deployment of the same model as an independent vote; promote picks |
| Deterministic supervisor | Sports Zenith server and existing validation | Require source IDs, source timestamps, eligible sport/season and competition regime, stop on conflicts, count actual receipts | Majority-vote unsupported claims into truth |
| Public explainer | Existing The Ref app | Present grounded plain-English observations, risks, and clearly labeled RESEARCH/UNKNOWN status | Place bets, send Survivor entries, automatically change official picks or model weights |

No consumer Gemini Advanced, Claude web subscription, or Microsoft Copilot subscription is silently treated as a server-side API credential. **No paid Claude API or Microsoft Foundry calls are permitted** under the user's $0 rule. Actual API models will be chosen from a verified free account only; private data is excluded from unpaid third-party services.

### Coding / operational workflow handoff
Baton Pass (Claude Code and Codex) carries repository state and task ownership, **not sports model authority**. Its CLI/skill is not installed on the current VPS as of the initial Oct 10 preflight. Only install vetted packages after review. Use Git commits plus a versioned, minimal docs/ handoff: prior task, exact source/tests, next action, fail state, provenance, known blockers. A Git commit on the same VPS is *not* proof of off-server disaster recovery. Gemini coding CLI support is not assumed from the Baton Pass skill's declared Claude/Codex scope.

## 3. Fail-closed data and permission boundary
- Inputs are structured provider-independent `ResearchPacket` records created server-side from **existing trusted Zenith sources only**.
- One packet contains: `case_id`, `sport`, `competition_regime`, `as_of_utc`, `question`, normalized `facts[]` (claim/source_id/source_name/event_id/observed_at/source_generated_at/proof_status), known `unknowns[]`, and frozen hash of the exact packet.
- No raw secrets, API keys, connected account credentials, user chat histories, other users' information, private Survivor tickets/entries, private fantasy rosters, or paid sportsbook account information leave the system in the pilot.
- No unrestricted web browsing or tools inside LLM requests. Retrieved source text is treated as **untrusted data**, never instructions, with injection-rejection cases in the benchmark.
- Claims without traceable matching evidence IDs are `UNSUPPORTED`. A stale source stays `STALE`; source contradictions stay `CONFLICT`; missing critical facts stay `UNKNOWN`. Never convert LLM confidence or three agreeing answers into source proof.
- Never ask LLMs to supply a fresh sportsbook line absent verified fresh primary sportsbook feed. Market-assisted probability is not an independent model edge.
- Canonical sports/game/source/as-of and competition regime identity must match the original source; no future information when answering a historical as-of question.

## 4. Contract for one analyst's response
Strict bounded structured output, subject to schema validation:
```json
{
  "case_id": "case-001",
  "provider_role": "source_analyst",
  "status": "SUPPORTED | CONFLICT | STALE | INSUFFICIENT_EVIDENCE | ERROR",
  "supported_claims": [{"claim": "...", "source_ids": ["..."], "as_of_utc": "..."}],
  "unresolved_claims": [{"claim": "...", "reason": "..."}],
  "risk_flags": ["..."],
  "suggested_followup": "...",
  "requested_bet_or_action": false
}
```
Reject extra unexpected fields in strict mode, missing evidence for verified claims, mismatched event IDs/as-of time, invented URLs, numeric prices not in approved source packet, personal data, unsupported model confidence scores, unbounded content, and any attempt to act.
Do not generate a `PLAY` or edit the official / performance ledger. Existing `validateAskOutput` remains an additional validation layer for any later *display* integration.

## 5. Read-only execution stages
Stage A — inspect existing data contracts, verify providers, freeze an initial **no-cost evaluation source sample**, and record baseline from the existing deterministic Ask router. No external LLM calls until an explicitly connected free-tier credential exists.
Stage B — use **GroqCloud Free** for a skeptical LLM analyst (eligible open models include `openai/gpt-oss-120b` and Qwen), and **Gemini Free** for independent evidence interpretation using a currently listed free model such as `gemini-2.5-flash-lite`. Only explicitly connected unbilled projects and public/synthetic source packets qualify; each request must use a model confirmed free for that account. Claude API remains DISABLED where prepaid credits or billing are required. Cap requests/output and stop when free allowance is exhausted. No paid fallback.
Stage C — optionally test an actual different model family from **OpenRouter Free** (25+ free models, 50 requests/day on Free) as a read-only challenger; never pass private records or route requests to a non-`:free` model. Microsoft Foundry remains DISABLED: no paid Azure provisioning or Copilot subscription is required. A paid model must never be selected, even if it has a trial promotional credit.
Stage D — compare all against original no-LLM Ask baseline; keep model outputs outside the public The Ref until review.
Stage E — separately approved canary behind `ZENITH_MULTI_LLM_MODE=off|shadow|canary` (default **off**); restrict canary to evidence explanations, never direct action or model promotion. Existing deterministic route remains fallback.

## 6. Evaluation cases and scoring
Initial benchmark: 100 frozen, as-of-time-aligned cases from the existing source evidence and explicitly synthetic withheld cases (labeled). Proposed coverage:
- 15 source-backed current/historical scores, schedules, and player/team fact retrieval
- 15 injury lifecycle/news report vs. verified status conflicts
- 15 odds/stale price and bookmaker vs model distinction cases
- 15 player props/PrizePicks stale or incomplete line cases
- 15 Survivor ownership/future-value and eliminated/used-team cases, with **no private user tickets shared**
- 15 Fantasy/DFS missing roster/ownership, source stage, or salary proof cases
- 10 adversarial source conflicts, prompt injections, future leakage, and expected abstentions

Each case must carry explicit expected source_ids and allowed/forbidden claims. Score baseline and models separately for source-supported factual precision, citation matching, abstention when proof missing, contradiction recovery, source freshness, exact game/league identity, as-of leakage, answer relevance, latency and **measured billable usage**. Report the numerator/denominator and failures, not only a single passing percentage. No benchmark leakage through reused grading goldens in prompts.

Go/no-go gates for possible public canary: 0 unauthorized actions, 0 fabricated quoted sportsbook prices labeled current, 0 private-user disclosures, 100% correct abstention on red-line adversarial tests, real source citations, and material improvement over the existing deterministic baseline on held-out cases. Independent sports-win prediction improvement must be shown by a separate pre-registered, forward-frozen scoreboard study before claiming predictive advantage.

## 7. Cost and security
- **Hard cost ceiling is $0 by explicit user instruction. Do not initiate or authorize paid requests, billing account registration, credit card collection, paid subscriptions, GPU jobs, paid Foundry deployments, or charge-capable resources.** If a provider requires a payment method or upgrades on quota exhaustion, it is ineligible; requests fail closed instead.
- Keys go in host protected environment/secrets only, never React bundle, Markdown docs, Git, logs, screenshots, local cached test fixtures, or public API response.
- Prefer managed APIs over VPS-local large models for 4 vCPU / 7.6 GiB RAM / no GPU VPS.
- Explicit per-provider, per-case token/output ceilings; allowlisted Free-only model IDs; local request/time budgets, hard zero-billing check, timeout and outage circuit breaker. Verify actual free-tier receipt and quota after calls. Never install a paid-token fallback or silently upgrade to a paid plan.
- Google's unpaid Gemini API tier permits submitted content to be used for product improvement/human review under its terms. **Do not send user accounts, private tickets, personal rosters, unreleased strategy, sensitive information or restricted/paid licensed source text to any free provider**; only sanitized public facts and synthetic cases. Confirm each provider's commercial use, data retention, and free-tier policy before connection.
- Protect commercial source licenses; do not retransmit paid content to external LLM vendors unless rights and processing terms permit.

## 8. Durability and acceptance
- Every new code change when approved must be TDD red/green, tested on frozen fixtures in an isolated worktree; no edits to existing model/odds/Survivor or mixed dirty worktree. Publish a static evidence report only after source readback verified.
- Versioned experiment manifest, prompts, model IDs/versions, provider responses (only sanitized aggregate research), packet hash, errors, per-provider caps, results and rollback instruction.
- Before any future deployment: full existing Node and Playwright regressions, independent private route tests, production build, and deliberate gate off check. Any non-green test remains a blocker.
- Run a separate off-VPS recovery exercise for handoff/results; do not imply that a same-VPS Git commit proves it.

## 9. Preflight evidence / truthful current status
- Existing Oct 10 commercial_web/server.js `POST /api/ask` is deterministic `routeAsk`, with optional specialized private context and output validation. There is no live general-purpose Gemini/Claude/Microsoft model inference route.
- VPS: 4 CPUs, 7.6 GiB RAM, no GPU driver detected.
- Checked server config: only InsForge public/anonymous authentication integration variables; **no named Gemini, Claude, Microsoft Foundry, Azure OpenAI or OpenRouter API key** available in checked env files/shell. This check does not prove there are no credentials elsewhere, but none is authorized for this pilot.
- `baton-pass`, `claude`, `codex`, `gemini` CLIs are absent from PATH; none installed.
- Existing synthetic goldens are just 5 retrieval + 5 answer cases, reported PASS on October 7. Legacy `evaluate_ask.py` has 17 cases and is not a multi-LLM comparison.
- Existing repo has unrelated uncommitted model and Survivor work: do not reset, clean, stash, or stage any such files in this plan.

## 10. Approval decisions needed before implementation plan
1. Approve this read-only/shadow design, separate from the site's original predictor/picks and private account data.
2. **RESOLVED: $0 total budget**. The user explicitly declined paid API usage. No billing account, payment method, credits, subscription, paid GPU, or usage-based API services may be enabled.
3. Only after the user explicitly connects an eligible **free, unbilled** provider, store its API credential securely on the VPS. No keys pasted into chat. No Claude prepay or Azure billing.
4. Approve whether only anonymous public/synthetic sports packets are allowed during the pilot (recommended YES).

After the written design is approved, write the implementation plan with individual TDD boundaries and no-billing connector-onboarding. No external model is connected or benchmarked without a real, verified **free-tier** inference receipt. If no free credential exists, leave external calls OFF and continue the existing deterministic Sports Zenith evidence pipeline.

## 11. Verified no-charge API routes (October 10, 2026 provider documentation)
- **GroqCloud Free:** `https://console.groq.com/docs/rate-limits` confirms free-plan rate limits for open-source/open-weight models such as `openai/gpt-oss-120b`: 30 requests/min, 1,000 requests/day, 8,000 tokens/min, 200,000 tokens/day at the documentation snapshot. The billing FAQ `https://console.groq.com/docs/billing-faqs` says a payment method is needed to **upgrade** from Free to Developer. *Verify the user's actual new account is Free and unbilled before using a key.*
- **Google Gemini Developer API Free:** `https://ai.google.dev/gemini-api/docs/billing` distinguishes unbilled Free and linked-billing paid tiers; `https://ai.google.dev/gemini-api/docs/pricing` lists selected models including `gemini-2.5-flash-lite` with free text input/output allowances, quota-dependent. `https://ai.google.dev/gemini-api/terms` permits free-tier input/output use for training/product improvement and review. Restrict to sanitized public/synthetic packets.
- **OpenRouter Free:** `https://openrouter.ai/pricing` confirms API access to 25+ free models and 50 free requests/day, with no payment options on the Free plan. Model IDs must explicitly be currently priced $0/free in the user's account, and the route must never auto-escalate to pay-as-you-go.
- **Cloudflare Workers AI Free optional backup:** `https://developers.cloudflare.com/workers-ai/platform/pricing/` lists a 10,000-neuron daily allowance on Workers Free with above-quota operations failing until reset, and identifies some models requiring a paid billing method. Use only eligible Free models without upgrading or purchasing credits.
- A no-charge consumer chat session is **not** an authorized API key. Any actual provider connection requires the user to establish/connect an unbilled account via the provider and the server secret store; never post API keys in chat. No endpoint changes, predictions, or live outputs are claimed in this design.
