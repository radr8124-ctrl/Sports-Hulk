# NHL official box-score forward settlement — acceptance

Date: 2026-10-07 UTC
Source branch: feature/nhl-official-box-forward
Status: isolated acceptance passed; production integration pending

## Source integrity and provenance
- Official data: NHL API-derived NHL_GAME_HISTORY, NHL_GAMES_CURRENT, NHL_PLAYER_GAME_HISTORY, NHL_CURRENT_ROSTERS. No provider sportsbook UUID is interpreted as an official NHL game ID.
- Frozen forward entry is joined by exact NHL game date + away/home teams, then by unique official NHL player ID from the roster and unique NHL box-score event/player row.
- Every eligible prediction must have an original pregame capture, official start within two hours of frozen start, completed official game with numeric scores, matching official season and game type, a playing skater's official team/opponent, positive TOI, supported stat, and exact frozen side/line.
- Supported markets: assists, goals, points, shots on goal. Other markets, date-only matches, DNP, absent final games and duplicate/conflicting player IDs remain unresolved.
- Source CSV content SHA-256 fingerprints are compared before/after reading and again immediately before writing; changed sources stop the batch without appends.
- Existing settled grades are reverified. Any contradictory settled grade is a batch-level integrity hold with zero new writes.
- All output events are append-only and carry official game ID, player ID, league source, official stat and explicit platform_settlement_claimed=false flag.
- These analytical grades are NOT evidence of placed wagers, payouts, or proof of real-money profit. Automatic live model promotion remains disabled.

## Production-data replay on isolated copy
- Pre-replay NHL frozen prop predictions: 1,935 (267 WIN, 185 LOSS, 1,483 PENDING).
- Independently verified 1,171 additional prop results from official game/player boxes: 710 WIN, 461 LOSS.
- Existing 452 settled results all agreed with official boxes; contradictory existing results: 0.
- Post-replay NHL frozen record: 977 WIN, 646 LOSS, 312 PENDING.
- Remaining unresolved: 302 without an official completed game and 10 without a unique official player box in this source snapshot.
- Ledger preserved full original byte prefix; repeated replay appended zero duplicate events and reverified 1,623 settled results.
- Isolated complete prop V2 builder rebuilt READY, preserved predictions and future promotion gates, and generated NHL_OFFICIAL_BOX_FORWARD_RECEIPT.json. Model promotion false and platform payout claim false.

## Tests
- NHL new exact official box and concurrency tests: 23 PASS.
- Regime tests: 59 PASS.
- NBA tests: 43 PASS.
- Other forward evidence: 22 PASS.
- NFL player identity tests: 11 PASS.
- Deployment-safety tests: 8 PASS.
- Commercial Node tests: 66 PASS.
- Frontend Vite production build: PASS.
- Python syntax and GitHub YAML parse: PASS.

## Production integration checklist
- Check active NHL and performance collectors.
- Save complete copies of NHL official source CSVs, frozen forward ledger, PROP_V2_FORWARD_SUMMARY, Brain Record and historical grade outputs.
- Fast-forward verified source-only changes; never touch unrelated uncommitted UI work.
- Run regular prop V2 forward builder on live, check actual verified outcome distribution and append-only prefix, rerun for idempotence.
- Rebuild Brain Performance and validate commercial/Survivor endpoint health.
- Push only to GitHub CI-only workflow; do not activate old destructive auto-deploy.
