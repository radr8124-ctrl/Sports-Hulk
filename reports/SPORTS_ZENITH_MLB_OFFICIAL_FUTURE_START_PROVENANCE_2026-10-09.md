# Zenith — MLB future start-time truth repair (October 9, 2026)

**Status: LIVE SOURCE-CELL ATTESTATION PASS, no model improvement claimed.**

Why the existing Full16 prospective model stalled: MLB official gamePk **849831**, Chicago White Sox at Cleveland Guardians, had a **three-hour scheduled first-pitch mismatch**. The local historical master said 2026-10-10T21:00Z, while MLB's freshly downloaded independent official schedule and three separate original collector observations established 2026-10-11T00:00Z.

The old conservative MLB repair guard requires two source-verified **post-old-kickoff official lineups** for any >2h shift. That is appropriate for potentially already started games but cannot repair a verifiably rescheduled future game before lineups exist.

Added a separate, narrow `verified_future_schedule_start_overrides` for **Scheduled** upcoming games only. It requires a fresh authoritative MLB schedule, exact gamePk, identical officialDate, gameType, original home/away team names and numeric IDs, venue ID, and two uniquely hashed original pre-old-kickoff official schedule captures at least 15 minutes apart, never from after the old kickoff. Only later-than-old shifts between 2 and 6 hours qualify; both starts must still be future, old first pitch >30 minutes away. It does **not** assert any pitcher or lineup is confirmed, nor reuse old market prices. Completed or already-started games remain subject to their original stricter published-lineup guard.

**Verification: 28 focused tests plus all 390 MLB regressions passed**. Direct live StatsAPI DRY RUN proposed **exactly one** correction while leaving master and source bytes unchanged. Only after backing up all original files and verifying the previously recorded byte hash did the ordinary repair apply the single attested start correction.

A full cell-by-cell comparison across all 7,911 master games verified exactly one changed cell: gamePk 849831 `gameDate` changed from 2026-10-10T21:00:00Z to 2026-10-11T00:00:00Z. Original master SHA: `7689c795b81c6c989cbfc158474b0e5cbd39dc4b7fdabeaa9d6645875cf29a6a`; new master SHA: `6ad270f021e85c63a76cddd7b31b3c4dc6724039afa70bec4cf81777832e58ae`. Full cryptographic proof, raw capture timestamps, source hashes and master backup: `reports/MLB_EARLY_FUTURE_OFFICIAL_START_REPAIR_ACCEPTANCE_2026-10-09.json`.

At latest offline official-fixture readiness check, gamePk 849831 moved from `OFFICIAL_START_MISMATCH_REQUIRES_SOURCE_REPAIR` to `EXACT_SOURCE_FIXTURE_MATCH`. The additional three local master games not on the current official schedule remain held. Upcoming unconfirmed LCS bracket placeholders stay unresolved: do not guess which teams or stadium, and never issue bet/PLAY signals from unresolved fixtures.

**No new eligible player freeze yet**: both verified official batting orders and a fresh same-book source quote still must become available prior to actual kickoff. The original 18 completed Full16 research forecasts, training coefficients, original outcomes, player statistics and live bets were not changed.

All original source files were copied with checksum verification to `.deploy_backups/mlb_verified_future_kickoff_repair_PRECHANGE_20261009T071200Z`. Git stores tests and code, not paid/private sportsbook ledgers or original historical masters. **Independent off-VPS backup recovery remains unverified.**
