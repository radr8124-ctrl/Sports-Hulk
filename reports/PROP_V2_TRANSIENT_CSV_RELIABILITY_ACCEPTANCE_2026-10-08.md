# Prop V2 temporary CSV read failure — acceptance

- October 8, 2026: the 01:31 UTC hourly performance refresh failed at 01:35 UTC in build_prop_v2.py with pandas EmptyDataError (No columns to parse from file), while multiple sport/market source CSV collectors were rebuilding. The prior Brain Report was left stale even though the live app remained healthy.
- The MLB source identified 106 new official Dodgers–Braves finals and settled them separately in exactly two official 100+6 grade batches: 73 WIN, 33 LOSS, zero conflicts; previously recorded grades stayed unchanged.
- This source-only fix retries a transient empty or concurrently changed current-decision CSV up to 20 times with a 0.5 second interval before failing closed with an explicit source validation error. Malformed/non-transient parser errors still propagate; no missing market/pick is fabricated.
- The fix applies only to reads of current Prop V2 lane CSVs, not historical archive evidence, betting outcomes, model calibrations, bankroll, real wagers or forward grades.
- All eight current sport/Prop/PrizePicks CSVs loaded with their real headers and entries; 6 new transient/empty/partial/error tests PASS and 17 MLB capture, 7 automatic batching, 26 official MLB, 16 player ID crosswalk, 22 forward evidence, 8 workflow safety regressions PASS.
- The normal hourly forward workflow is retained, with up to four strictly source-verified 100-result MLB batches. The new read logic never upgrades an unverified pending outcome.
- Release: back up previous source and frozen ledger, commit only source/tests/CI/docs, merge fast-forward while source writers are idle, rerun full Prop V2 builder on the live original decision inputs, confirm Brain is healthy and next scheduled hourly job can resume.
