# Sports Zenith — $0 LLM Trial, Stage A: Existing Brain Baseline and Entity Proof Guard
Date: 2026-10-10
Environment: isolated fixture servers on localhost 8535 (retrieval) and 8537 (semantic).
Status: implementation re-tested; live publication must be verified separately.

## Why
Before benchmarking free Groq/Gemini or adding any LLM-powered summary to The Ref, we must establish that the existing deterministic system does not mistake irrelevant sports reporting for an exact player's injury news. A frozen re-run identified an actual mismatch that October 7 historical saved summaries would otherwise have concealed.

## Original failure observed, before patch
- `node run_retrieval_golden_eval.mjs` on fixture localhost8535: FAIL, 4/5. Synthetic unknown player "Nebula Quarterback" wrongly returned `intent=news,status=CURRENT,confidence=REPORTING` with zero verified matching claim-source IDs.
- `node run_semantic_answer_eval.mjs` on fixture localhost8537: FAIL, 4/5, same unknown-player failure. Four positive/known tests each passed, including explicit stale and conflict withholding.
- Debugging the output revealed an irrelevant headline: "Week 5 Quarterback Rankings for Fantasy Football: Weekend Updates". In `server.js`, `newsAnswerV2()` accepted a row if **any** non-stop-word token matched: "quarterback" matched the headline, even though "Nebula" did not. Scoring a generic football position as a player identity is an evidence-integrity failure.
- Last previously published October 7 synthetic golden files read PASS 5/5, but live code had diverged. Fresh replay, not old report, is authoritative.

## Fix
Scoped **one function** in `commercial_web/server.js`:
- For multi-token named injury/status/news/report/practice/return/update inquiries, require all significant subject tokens in an article headline; no generic one-word substitute.
- Existing pure topical questions and single-token matches retain their previous matching contract. Explicit source-backed structured retrieval remains preferred to unstructured news.
- When no matching named subject remains, the pre-existing `INSUFFICIENT_EVIDENCE` response is used, never an invented injury label or gambling recommendation.

## Verification
- Fresh isolated retrieval golden after patch: **PASS 5/5**, including the formerly failing unknown-subject restraint.
- Fresh isolated semantic answer golden after patch: **PASS 5/5**, including current known fact, two-source consensus, stale withholding, conflict withholding and unknown abstention.
- Existing Node tests `node --test *.test.js`: **PASS 270/270**.
- All isolated fixture servers ran with `ASK_TRACE_LEDGER_PATH=/tmp/zenith_free_pilot_*_trace_*.jsonl` and fixture-specific temp evaluation queues. Outputs were written to `/tmp/zenith_free_pilot_*.json`, never overwrote the canonical `reports/ASK_*_CURRENT.json` or private Survivor state.
- Scoped source backup SHA-verified before patch at `.deploy_backups/zenith_named_player_guard_before_20261010/SOURCE_SHA256.txt`.
- No external LLM request, billing, credential creation, model score edits, official pick changes or visitor data transfer performed.

## What this means / not
- **This is a 10-case deterministic synthetic source-handling acceptance test, not 10 independently graded sports predictions and not evidence of betting profits.**
- This specific false-positive named injury claim is corrected in the tested backend code. It does NOT prove the entire Sports Zenith prediction engine is accurate.
- GroqCloud Free / Gemini Free remain *unconnected* until the user supplies/authorizes verified unbilled credentials. Proposed multi-LLM shadow mode remains OFF. Any future request must use sanitized public/synthetic cases only and a hard $0 spending ceiling.
- Production verification after service restart and live anonymous/private tests are separate acceptance steps. If absent, do not claim deployed.

## Next
1. Verify main app tests and live deployment after controlled restart.
2. Extend the initial source-grounded golden matrix with held-out cases and as-of-time rules, without backfilling prediction histories.
3. Compare external free models only after verified free credentials and explicit consent, using deterministic source-quality gates rather than majority-vote guesses.
