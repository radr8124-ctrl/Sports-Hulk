# Sports Zenith — GroqCloud Free Credential Handoff and Single Synthetic Trial

Date: October 10, 2026
Project: Sports Zenith
Status: **Free-account setup prepared; NO key installed and NO Groq inference has occurred.**

## User's current checkpoint
The user is signed in to GroqCloud. The previous accepted budget is **strictly $0** with no payment method, billing upgrade, paid API or GPU. Groq's official docs confirm Free->Developer paid upgrades require a payment method: https://console.groq.com/docs/billing-faqs . The API key page is https://console.groq.com/keys .

## Approved secure setup
In the authorized OVH Ubuntu VPS terminal, not ChatGPT, run:

```bash
cd /home/ubuntu/sports-hulk
python3 scripts/zenith_groq_secure_setup.py
```

The setup script REQUIRES a real interactive terminal (TTY). It asks the human to verify their GroqCloud account is Free **with no payment method** and type the literal word `FREE`. It then uses Python's `getpass` to read the newly created `gsk_...` API key with **no terminal echo**. Never paste the key into chat, ordinary shell commands, screenshots, tool transcripts, or Git. The protected credential file `commercial_web/.env.groq_shadow` is created exactly once, with owner-only mode 0600. Existing keys/symlinks are never overwritten, the path is gitignored, and this setup makes **zero** API calls. Its timestamp records a *user confirmation*, not an independently verified provider billing query.

When setup reports success, the user should write only `Groq key saved securely` in the chat (no key or token details).

## Single synthetic Free plan test, after explicit user go-ahead
The future model test is intentionally a separate explicit CLI action:

```bash
cd /home/ubuntu/sports-hulk/commercial_web
node zenith_groq_free_onecase_cli.mjs --one-synthetic-free-call
```

- Do NOT schedule this CLI. Only run after the user confirms the key is securely saved and the Groq account has no payment method/paid plan.
- `zenith_groq_free_onecase.js` reads **only** the protected credential file and the frozen 18-case public synthetic bank, checksum `c23540369860727d16d35639ff753e037f901c5f4cb98ff17a600abd4145954b`.
- It sends precisely **one lifetime request** for the first fictional test case (`SYN-NFL-INJURY-01`); a protected mode-0600 state file is reserved before any network call. A second call, even after 429 or failure, is blocked; there are no retries or any paid fallback.
- The model is hard-locked to `openai/gpt-oss-120b`, REST host `https://api.groq.com/openai/v1/chat/completions`, JSON object output, `reasoning_format:'hidden'`, no tools, no web search and strict output token caps. See https://console.groq.com/docs/reasoning and https://console.groq.com/docs/api-reference .
- The result is passed through the existing `judgeResearchResponse` source/evidence validator. Only sanitized receipt metadata is printed (pass/fail, case ID, status, issue codes, provider_calls). No raw prompt, user account, provider token or full model response is logged.
- A model API HTTP 200 does **not** independently certify a $0 bill. The test receipt deliberately reports `billing_dollars:null` after a request because this integration has no provider billing-read permission. Zero charge is protected by the user-verified Free/no-payment account requirement, not falsely inferred from tokens.
- No real sports data, account messages, licensed reporting, source credentials, private Survivor/Fantasy state, or current production betting predictions are sent.
- The existing live The Ref and Sports Zenith prediction models are unchanged. The test cannot publish a sports bet/pick or alter an official ledger.

## TDD and acceptance
- Secure setup unit tests written before installer; expected red `FileNotFoundError`, then **6/6** pass.
- One-case request tests written before module; expected red `ERR_MODULE_NOT_FOUND`, then **6/6** pass. Added CLI gate red/green for implicit invocation, now **7/7** pass.
- Groq JSON mode compatibility test written before patch; expected failure until `reasoning_format:'hidden'` was inserted. Existing shadow adapter checks **17/17** pass after fix.
- Fresh full JavaScript regression: **309/309 tests passed** (Node test runner exit 0). The frontend production Vite build also passed (exit 0; pre-existing nonfatal large-bundle warning).
- The protected key file has **not yet been created**; actual Free-tier request has not occurred. The active public site health endpoint remains separately verifiable and this release does not modify the live Ask backend or scores.
- No API key has been collected in this chat, server secret path did not exist at the initial check, and the first real Groq inference is **pending user action**.
- Git snapshots/same-server readbacks do not equal independently restored off-VPS backups.
