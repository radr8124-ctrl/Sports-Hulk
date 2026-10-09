# Zenith CFB archive — suppress derived clock-only repeats, preserve every source fact

**October 9, 2026 UTC.** This is an append-only growth optimization for the newly recovered CFB grader, not an odds/model/payout change. **Do not delete or rewrite the original 8.4GB raw ledger or old snapshots.**

## Why growth occurs

Compared two consecutive original CFB archive snapshots:
- Previous: 2026-10-09T05:52:32.086756+00:00, 7,640 recommendation keys.
- Next: 2026-10-09T06:02:37.076790+00:00, 7,640 identical keys.
- **7,580** rows changed only in the automatically derived `hours_to_start` field. **30** others changed market `median_price_american` and/or derived `raw_market_support`; **30** were fully identical. No new unique recommendation keys appeared across those two snapshots.
- Original archiver appended all 7,640 rows (~14 MB) merely because at least one substantive source value changed in the bundle. The 8.4GB raw CSV also grew by 7,640 entries in the latest 06:01 automated CFB run.

## Exact clock-only delta rule

`cfb_live/decision/archive_cfb_decisions.py` now loads latest old source rows from the verified complete SQLite index **before** appending anything. It compares the complete source metadata (excluding new snapshot clock/bundle hash) and every original full `payload_json` field except the one trivially derived `hours_to_start` countdown.

Only records identical under that rule may be **omitted from future repeated append batches**. Changed source price, sportsbook count/provider, player/selection, final context, model score, decision, line or any other actual source field MUST still append normally. Existing old source bytes, original snapshots, training decisions and grader outcomes are never trimmed or edited.

The original per-bundle source copies and `manifest.json` remain preserved. Manifest now records `source_index_verification`, `original_recommendation_rows_appended`, `derived_clock_only_rows_not_repeated`, and `old_raw_source_history_rewritten_or_truncated=false`. Original observation time and source copies therefore remain in the snapshot manifest even when a redundantly derived hours-countdown row is not reappended.

If index cannot be proven caught up or is unavailable, fallback **appends every row**, preserving prior semantics with no missing source events. Any unexpected source fingerprint/replacement/corruption raises a failure rather than accepting a tampered source.

## Verification

- Unit and temp-directory integration tests: **17 passed** across original incremental scanner, indexed grader and new clock-only archive tests.
- The full temp source test appended exactly two first-proven game recommendations, then simulated a new snapshot where one record changed only hours and the other changed actual price. It appended **only one** new market observation, preserving a byte-identical original CSV prefix and both snapshot manifests.
- Source-verified latest-row readback works and refuses an index stale behind source append. Bad/malformed prior price payload fails closed (append real observation, do not suppress).
- Live production acceptance of this new optimization from the next 10-minute scheduled CFB refresh is still required. **No verified reduction should be claimed until that actual timer report.**
- Original 06:01 CFB automatic index+grader previously finished with `INDEX RC:0`, `GRADE RC:0`, `CFB LEARNING COMPLETE` and `Result=success` while preserving all 10,629 previously settled legacy grades exactly.

## Private-data Git safety

The active Git worktree has other in-progress `.gitignore` edits that were not part of this batch and should not be staged. Instead, a local-only `.git/info/exclude` guard was added for `cfb_live/decision/history/` and generated CFB decision CSV/JSON files. That prevents accidental inclusion of the original private 8.4GB recommendation data and local SQLite index in ordinary local Git staging. The private excluded raw data remains on this VPS and is not thereby backed up to another machine. Independent off-VPS restoration is still **unverified**.
