# Sports Zenith — NHL & NBA prop/PrizePicks provenance checkpoint

**UTC 2026-10-09.** Source verification and game competition classification only. No wager was placed, no past frozen picks rewritten, no model coefficients promoted, no goalie assigned a fabricated confirmation, and no MLB postseason proof requirements weakened.

## NHL status (live, not inferred from earlier report)

- Original NHL PrizePicks decision board: 290 current research rows. Exactly 80 remain START_TIME_DISAGREEMENT_REVIEW; 206 have NO_EXACT_SPORTSBOOK_SOURCE_MATCH; four have exact same original event/player/market/start sportsbook references. **Zero PrizePicks finalists** and **zero verified actual PrizePicks American prices**. A matched sportsbook reference is not an executable PrizePicks payout.
- The 14 current starting-goalie listings all remain **LISTED_NOT_CONFIRMED**; none was promoted to a confirmed starter.
- Four focused NHL source and roster test modules: **14 tests passed**. Earlier larger test counts documented in the NHL source report must not be confused with this run.

## NBA official competition proof

- The pre-existing ESPN source join verified **830 of 836** NBA game-market rows as REGULAR. Six are UNKNOWN, not guessed from the October calendar.
- Extended `nba_live/decision/enrich_nba_competition_regime.py` to label NBA player-prop and PrizePicks decisions using an official event, two teams, exact game key, explicit `season.type`, and a matching pregame start. If source unavailable or matching ambiguous, the record stays UNKNOWN.
- New production source receipt verified all **114 NBA sportsbook player-prop** decisions and **68 NBA PrizePicks** decisions as REGULAR (all 2026-10-20/21 market research, **not** current preseason). NBA PrizePicks original start disagreements and unpriced status are preserved; no new PLAYs/finalists were promoted.
- `premium_ui/nba_ui.py` now displays a source-verified competition selector for early player-prop and PrizePicks research, so preseason and regular-season records are not mixed.

## Main SportsZenith.com Props V2

- `build_prop_v2.py` now includes source-verified NBA competition label and ESPN event ID in each appropriate V2 record. Unknown NBA season types fail closed; preseason and postseason data cannot inherit regular-season model validation to become SHADOW_MONITOR or SHADOW_PLAY. The underlying V2 probability model version remains unchanged; NBA source-veto version is recorded separately.
- Main React Props/PrizePicks pages display NBA competition type and separate Preseason, Regular Season, Postseason and Unverified controls without changing other sports.
- Successful bounded full V2 rebuild: **736** total current candidates, **0 PLAY**, **0 MONITOR**, **736 PASS**. NBA has **112 sportsbook prop** and **54 PrizePicks V2** records, all labelled REGULAR and all PASS_INSUFFICIENT_HISTORY. NHL 258 prop, MLB 272 prop/PrizePicks, NFL 40 prop/PrizePicks. The prior 712-row count differs after a newer market refresh; this is not evidence of a higher success rate.
- Production JSON copied identically to `commercial_web/public/prop_v2_current.json` and `commercial_web/dist/prop_v2_current.json`, byte comparison PASS. Direct HTTPS read at `sportszenith.com/prop_v2_current.json` returned 166 NBA records all marked REGULAR. Site `/api/health` HTTP 200. Updated React chunk available via live HTTPS.
- Tests: **55 Python tests passed** across NBA official season identity, props V2, original PrizePicks source joins, pretip gates, result integrity, stable-CSV handling. **14 NHL Python tests passed**. React production build passed. **2 Playwright tests passed** for desktop and 390px phone-width competition filters and overflow.

## Recovery and limitations

- Before editing, original scripts and decision CSVs were checksum-copied to `.deploy_backups/nba_regime_player_proof_before_20261009T2031Z/`. Original Props V2 builder, React component and both baseline V2 JSON outputs were checksum-copied to `.deploy_backups/nba_regime_v2_before_20261009T2040Z/`. Both local SHA256 manifests were checked successfully; after initial self-inclusion in the second manifest was corrected, all four original payloads verified.
- Modified source files, reproducible tests and this report should be committed together. Original supplier/source betting data, immutable prediction history, and lineup/Survivor data were not altered by this implementation. The generated current V2 feed refreshes normally as fresh upstream data arrives.
- **Independent off-VPS recovery has not been verified.** VPS-only backups and a local Git commit are not proof of successful off-server disaster recovery. Browser tests verified the new filters on both viewport sizes, not an unrestricted audit of every phone model or every page.
- Proof still missing: independently validated NBA postseason/preseason prop models; verified NHL goalie starts and unconflicted NHL PrizePicks source prices; genuine PrizePicks entry payout data; independent market-beating prospective validation. A larger candidate count or high paper hit rate does not establish a profitable wagering edge.
