# Sports Zenith — Anonymous PostHog Ask Monitoring (October 10, 2026)
Status: **Service deployed and enabled**; collection is forward-only and intentionally has no historical backfill.

## Why
Measure whether the **existing deterministic Ask/The Ref brain** is getting more reliable, without giving an external analytics company user text or touching the public website. This does **not** connect any third-party LLM or establish a sports betting advantage.

## Technical integration
- Installed `scripts/zenith_posthog_monitor.py` as a separate read-only watcher of existing `intelligence_warehouse/experiment_registry/ASK_TRACE_LEDGER.jsonl` (mode 0600).
- `scripts/systemd/sports-zenith-anonymous-observer.service` and `.timer` are installed into the Ubuntu user's systemd service directory; timer scheduled every 10 minutes, with no restart to the live Sports Zenith server.
- The local cursor is stored at `/home/ubuntu/.local/state/sports-zenith/posthog-cursor.json` (mode 0600), initialized at the **existing file end**. No historical questions, trace IDs or source rows were exported.
- Protected environment at `commercial_web/.env.posthog_monitor` (mode 0600, ignored by git), with only the PostHog public project token and approved US ingestion host. No credentials in source or Git.
- Organization: Sports zenith, active project: Default project. PostHog HTTP capture at `https://us.i.posthog.com/i/v0/e/`.
- PostHog's `zenith_observer_probe` test used a **synthetic, anonymous event** and received **HTTP 200**, without touching Ask evaluation or user traffic.
- Observer's `zenith_ask_review` events follow only future generic Ask trace rows. **Not** PostHog AI-generation events, because no external LLM inference was wired into The Ref yet.

## Deliberate privacy restrictions
- Only `route_lane = GENERIC` records are eligible; `PERSONAL_SURVIVOR` and `PERSONAL_FANTASY` and unknown route lanes always skip.
- No user ID, email, user-specific session, private ticket/roster, private pick, raw question, question hash, full answer, trace UUID, page, prompt, tool payload, sportsbook credentials, or free-text error message leaves the server.
- Sent event fields: constant anonymous server ID; `$process_person_profile: false`; bounded, allowlisted intent/status bucket; integer latency; source count; claim-source count; validation flag/error count; server error bool; one deduplication hash.
- **No browser SDK or autocapture, no cookies, no user tracking, no session replay.**
- Browser's Ask output contract and private authentication remain unchanged. No wagers, official results, model weights, user preferences, Survivor submissions or player data modified.

## Firm $0 design
- PostHog's documented [Product Analytics pricing](https://posthog.com/docs/product-analytics/pricing) includes 1,000,000 events/month at $0 and no credit card required to start.
- Hard code limit: **50 outgoing eligible events/day** (at most 1,550/month), 12 per process run. The timer does not purchase credits or change a subscription. Any excess event backlog is dropped.
- Host locked to PostHog US/EU cloud ingestion; no provider fallback or third-party billed inference.
- The connected PostHog plugin is missing `billing:read`; account billing/payment state cannot be independently audited from chat. No paid billing product was enabled or requested, and this observer does not use AI-generated PostHog evaluations.

## Verification
- TDD red verified before creating observer, then **9/9 Python unit tests PASS**, including field-exfiltration sentinels, private-lane exclusion, no historical export, no incomplete line forwarding, no after-cap paid overage, and retriable delivery failures.
- Explicit first-run result was `INITIALIZED`, `sent=0`, and its 0600 cursor equaled the trace ledger EOF.
- Separate user systemd timer showed `ActiveState=active`, `SubState=waiting`; manual oneshot service run `Result=success`.
- Synthetic PostHog capture returned HTTP 200. PostHog's schema listing initially did not show the probe; independent indexing/readback is separately checked. Do not claim a browser event when none exists.
- Existing server files remain unchanged (checksums verified separately). Test homepage and Survivor anonymous privacy endpoints after deployment.
- Strict recovery: same-host Git restores versioned code, but no off-VPS disaster-recovery test is implied.

## Disable / rollback
```bash
export XDG_RUNTIME_DIR=/run/user/1000
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
systemctl --user disable --now sports-zenith-anonymous-observer.timer
# Optional: change ZENITH_POSTHOG_ENABLED to 0 in protected local env.
```
To revert source, restore the isolated versioned files from the relevant observer commit; do **not** reset unrelated Sports Zenith research/pick/data changes.
