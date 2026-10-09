# Sports Zenith — MLB postseason recovery and Fantasy hourly refresh repair

**Date:** October 9, 2026. **Status:** MLB postseason prop and PrizePicks research feed restored to live site. No real wagers, proven betting selections or lowered minimum-history rules.

## What was actually wrong

The MLB official StatsAPI `byDateRange` 14-day form window contained just **1–3** recent games per eligible postseason player, while the untouched V2 research gate required **at least four batting games or two pitching games**. For 812 market-fusion entries (734 regular sportsbook player props; 78 PrizePicks entries), all **812 were automatically `INSUFFICIENT_RECENT_CONTEXT`**. A pre-registered, read-only source check demonstrated that a 28-day StatsAPI range passed the unchanged minimum for all 812, including the late regular season and playoff context.

**Fix:** the MLB fusion builder now looks for official schedule `gameType` W/D/L/F within 14 days of the source date. During postseason only, it uses **28 days**, labels that the window can include late regular-season statistics, and reports the window and original thresholds in the fusion receipt. During normal regular season, incomplete schedule evidence or dates far from playoffs it retains **14 days**. It never changes the minimum four batting/two pitching games, model weights or bet rules.

## Verified before deploying

Source preregistration commit **`96a9256`** and staged acceptance report are preserved. The complete MLB fusion builder ran **with all output paths redirected into a private staging directory**, produced 734 sportsbook prop decisions: 132 HIGH_JUICE, 111 QUALIFIED_RESEARCH, 491 WATCH, and 78 PrizePicks decisions: 20 QUALIFIED_RESEARCH and 58 WATCH. None remained blocked solely by the recent-game sample. Later normal scheduled refresh changed the counts slightly (still zero recent-context failures), confirming the fixed branch operates live.

The combined V2 publisher was run in a fully isolated output directory using the **existing production historical validation and market-reference rules**, and confirmed **zero shadow plays and zero shadow monitors**. Production MLB sportsbook props use market-reference-only probabilities and have no demonstrated independent edge; PrizePicks retains uncertain historical modeling with pricing-quality vetoes.

A coherent nine-file exact-checksum backup of the previous V2 warehouse/public/compiled feeds was made and restored in the updated filesystem before deployment; the new staged model, validation and current research feeds were verified byte-for-byte and published without changing trained model coefficients. **Live, after release:** 226 MLB_PROP and 21 MLB_PRIZEPICKS paper-research rows (aggregate V2 feeds include NFL, NBA and NHL too). Both paths return valid HTTPS; an actual phone-sized and desktop browser opened the MLB filters with no JavaScript errors, no private-account writes and no page overflow.

**Not claimed:** These are *research candidates*, not validated value bets. The named bookmaker's executable odds, postseason lineup/starting pitcher and game-day active status still need verification. Player prop market-only forecasts are not predictive edge. PrizePicks sportsbook odds and actual PrizePicks payout structure are not interchangeable. The 28-day sample crosses the regular season/postseason regime.

## A separate hourly refresh blocker

The hour-long Sports HULK performance service was **failing** in `intelligence_warehouse/fantasy_accountability/build_fantasy_v2.py`, during `settle()`, because four lookup paths used `pd.Series or pd.Series`. This implicitly evaluates a pandas Series as a Boolean, raising *ValueError: The truth value of a Series is ambiguous* and ending the hourly job before its final accountability/Brain Report refresh.

The repair adds a strict `source_stat_row` helper that checks **`is None`** rather than truth value, preserving matched or fallback player statistics for WEEKLY, FAAB, IR_STASH and IDP. Five isolated tests passed; a sandbox run of the actual existing fantasy ledger verified the formerly failing `settle()` path, one official result would be recorded, and the production ledger SHA remained unchanged during the sandbox trial.

## Safety, QA, recovery

- Original source and receipts were backed up on the **same VPS**, under `.deploy_backups/zenith_mlb_postseason_recent_context_20261009T1925Z/`; originals and all nine published feed paths have SHA-matched replay records. This is **not off-VPS disaster recovery**.
- 30 targeted MLB+Fantasy+prop-stability tests and 16 frozen NFL tests passed following repair.
- NFL original frozen nine-feature and first 26 unique player-line futures remain unchanged. The existing betting rules, the standalone Survivor app, and the working website are not redesigned or restarted.
- For future changes, check the hour-long service result and recheck `prop_v2_current.json`, `forward_proof_current.json`, final Fantasy and Brain Record timestamps. A successful sandbox settlement does not alone prove that every subsequent step of the full hourly service will succeed.

## Still needed across sports

1. NFL: **13 original game model predictions + 26 future props across 11 independent game blocks** are frozen, with separate sportsbook and PrizePicks comparisons. Run future official-result grading and paired market Brier/ROI before promoting any PLAY. Verified sportsbook quote movement is still required.
2. MLB: Repeat official event/gamePk and player-identity checks and source-price verification in postseason, then grade only after final. Keep 28-day mixed-regime batting sample labeled honestly.
3. NHL: The earlier independently adjusted core player model was *worse* than its market baseline; keep calibrated-market control until the newer challenger proves itself in future unseen games. Verify starting goalies and injury status.
4. NBA: **Preseason is not 2026–27 regular season.** Public props currently point to later NBA regular-season games. The preseason totals and spread source-quality audits found correlated alternate lines and caution flags; separate game blocks and never turn those into proven bets.

**Bottom line:** The source gap and stale combined publisher have been repaired/verified for MLB now. Better research coverage is real, but winning-pick proof still requires fresh prices and independent forward results.
