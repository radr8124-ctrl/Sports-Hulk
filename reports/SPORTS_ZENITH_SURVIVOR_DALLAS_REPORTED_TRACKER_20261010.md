# Sports Zenith — Week 5 Dallas Thursday Report Tracker

Date: 2026-10-10 (ET). Existing production Sports Zenith only; source-honest private Survivor work resumed after the user reported the prior session stalled.

## Truth boundaries and source
- User conversational summary reports 147 separate numbered Survivor tickets chose Dallas in Week 5; Dallas lost to Tampa Bay 24–16. Reported reconciliation summary: 146 prior-week matches, one possible name mismatch. The actual source list of 147 numbered rows is **not available** in live server, Project/Library file search or earlier context retrieval. Do **NOT** present the 147 as imported or certified.
- Latest official imported Week 4 PDF metadata is 364 rows, 360 active/unconfirmed and four eliminated. It is **not** a confirmed Week 5 roster; no Week 5 official remaining-field count may be inferred.
- The actual Week 4 CSV contains the extraction-distorted `DAWN & MIKE BUCK 01YCHARGERS`. Previewing a synthetic single `DAWN & MIKE BUCK 01 COWBOYS` line against the real Week 4 source reports `EXTRACTION_NAME_MISMATCH_REVIEW`, not an exact match. Names are not auto-merged.
- ANNIE G 01 remains ALIVE in Week 5 with Chargers, 49ers, Chiefs, Bills, Vikings already used. `current_picks=[]` and `week_5.submitted=false` at deployment acceptance. User explicitly said they are not choosing yet. No personal pick saved, and no pool-submission attempt made.

## What this release actually built
- New compact, private, authenticated `Dallas elimination tracker` appears on the current Survivor page only when signed in and authorized. Reported 147 is labeled as a user-reported count; saved reported rows show 0 until source upload. Official remaining count displays dash, not `360 - 147`.
- Manager-only expandable report form accepts plain pasted numbered ticket lines, source name and explicit per-list Dallas attestation. First PREVIEW is authenticated, rate-limited and bound to that manager's session; reports per-row matches and name ambiguities only back to that manager. Second CONFIRM requires separate attestation that this is **reported evidence**, not official standings; preview tokens expire and cannot be reused. Entry identifiers are never returned in the aggregate summary endpoint.
- New dedicated reconciliation algorithm compares to the exact official Week 4 CSV and its metadata. Exact row counts and source filename are checked. It distinguishes exact active previous-week names, previous eliminated names, unknown names, token-extraction mismatches and ambiguous/repeated printed names. Every repeated reported line stays a distinct ticket, but cannot count as a confirmed exact match without review.
- New private sidecar at `/home/ubuntu/sports-zenith-private/survivor_thursday/week5_dallas_report.json`. Source text and SHA256 are preserved only after the manager actually imports. Writes use fresh temporary-file verification, atomic rename, previous-version SHA-verified archive copies and readback verification. The original full-pool importer, personal Survivor state, forward predictions and selection submission paths are not altered by confirmation. **No 147-row import occurred in this release.**
- GET summary requires an authenticated linked pool entry or an authorized manager. Both preview and confirm require manager privilege from server-side roles/allowlists. Anonymous requests all return HTTP 401. Non-manager summaries receive no source name or participant rows.

## Verification
- Test-first approach: new Thursday API browser checks initially failed HTTP 404/405, then passed after implementation. New parser/storage unit cases passed 10/10, including a real 364-row roster readback check run separately.
- Full Node test suite **331/331 PASS**; Vite build **PASS** (pre-existing nonfatal large-chunk warning).
- Combined Playwright production/staging regression **34/34 PASS**: Survivor, Props, PrizePicks, Best Bets, markets, Home, and dedicated Thursday privacy checks.
- After real `sports-hulk-commercial.service` restart, actual HTTPS health **200**, anonymous Thursday summary/preview/confirm **401**, 7/7 production targeted browser checks PASS, and `ANNIE G 01` semantic state unchanged.
- Frozen Survivor forward prediction ledger SHA256 unchanged throughout this batch: `3778bcff7ec9f87f29df739acf1f41dc75c4c7ddfc740c867b9078a51f426f55`.
- Pre-edits stored as matched source copies under `.deploy_backups/zenith_survivor_thursday_before_20261010/` (same VPS; not independently restored offsite). Code is committed below; note an on-VPS Git commit is not proof of off-server raw-data recovery.

## Unresolved
- Actual 147-row Dallas reported source must be supplied through the manager form; source was NOT fabricated or imported.
- The organizer's official Week 5 full pool sheet must be imported separately by the existing verified pool-manager workflow before updated certified field totals can be shown.
- Authenticated owner/manager real-browser navigation has **not** been exercised with a genuine private account. Production anonymous browser/privacy checks were executed. No wager or external pool pick was placed.
- Off-VPS private raw-data restore is NOT independently verified.

## File scope
New: `commercial_web/survivor_thursday_tracker.js`, `survivor_thursday_tracker.test.js`, `survivor_thursday_store.js`, `survivor_thursday_store.test.js`, `src/SurvivorThursdayTracker.jsx`, `survivor-thursday-api.e2e.spec.js`. Modified only for this build: `commercial_web/server.js`, `src/App.jsx`, `survivor_pool_leverage.js` (export original CSV parser without changing logic), plus this report. All unrelated dirty work left untouched.
