# NHL official box-score forward settlement — production release

Date: 2026-10-07 UTC
Production source revision: fe7d0b9
Environment: /home/ubuntu/sports-hulk
Recovery branch: backup/pre-nhl-official-20261007T215111Z
Production backup: .deploy_backups/nhl_official_forward_20261007T215111Z

## Delivered
- Source-only fast-forward merged NHL official-box result verification and integrated it into scheduled Prop V2 forward refreshes.
- Recorded independent source evidence from NHL API-derived completed game history, current games, official skater boxscores and current NHL roster.
- Every new grade required a unique official game (date, away and home teams, official ID), unique roster player ID, one official player boxscore, actual played minutes, official season/game type, exact frozen side/line, supported stat and pregame capture.
- Official source content hashes must remain unchanged throughout the read/verification/write cycle. Source changes stop settlement.
- No sportsbook UUID used as an NHL game ID. No interpolation from a game date, similar player name, book odds or another frozen line.
- Any disagreement with an already-settled official-box result stops the entire new NHL batch.
- Output is analytic forward-tracking evidence. It does not claim NHL betting platform payouts or real-money wagers.

## Verified live ledger outcomes
- Previous forward NHL prop state: 1,935 tracked, 267 WIN, 185 LOSS, 1,483 PENDING.
- Exact NHL official-box verified new settlements: 1,171 = 710 WIN + 461 LOSS; existing official-box-verified settled results: 452.
- Final frozen NHL forward state: 1,935 tracked, 977 WIN, 646 LOSS, 312 PENDING.
- Unresolved cases from current source snapshot: 302 without completed NHL game result, 10 without a uniquely resolved player boxscore. They remain PENDING.
- Existing result contradictions: 0.
- Original prop ledger bytes preserved as exact prefix of updated append-only ledger: 7,279,767 -> 8,119,763 bytes.
- Live rerun added 0 duplicated settlement events and reconfirmed 1,623 official NHL result matches.
- No existing settled grade, market price, model probability, frozen selection or unrelated sport outcome was changed.
- Automatic model promotion remains disabled. Sample-specific sports records remain separate from real-world wager ROI.

## Site and Brain Record
- Brain Performance rebuild: PASS/READY; forward NHL proof correctly visible.
- Public/embedded forward accountability: NHL 1,623 SETTLED, 312 PENDING, 10 overdue more than 12 hours.
- Across all four tracked forward families: 7,458 records and 3,208 recorded settlements; overlapping families are not independent wagers. Overdue 12+ hours across families: 1,751.
- Commercial API HTTP 200; Brain Record API HTTP 200; Survivor health HTTP 200. No service restart required.
- Existing unrelated dirty commercial App.jsx and NBA market collector changes were preserved.

## Validation
- New NHL safety and race-condition tests: 23 PASS.
- Betting competition-regime tests: 59 PASS.
- NBA historical and official feed tests: 43 PASS.
- Forward provenance tests: 22 PASS.
- NFL official player-ID tests: 11 PASS.
- GitHub deployment-safety tests: 8 PASS.
- Commercial Node tests: 66 PASS.
- Production Vite build on isolated branch: PASS. Live web tests: PASS.
- All four official source files included in local hashed snapshot backup (SHA256SUMS.txt).

## Forward plan
- Automatic hourly Prop V2 forward collection reruns official NHL evidence matching and remains idempotent; pending games will grade only after official NHL results and player boxes become available.
- Next lane: MLB source identity crosswalk from frozen provider event to official gamePk, player ID, specific metric, market side and line; no same-date-only backfill.
- Existing GitHub workflow remains read-only CI; no automatic destructive production deploy.
