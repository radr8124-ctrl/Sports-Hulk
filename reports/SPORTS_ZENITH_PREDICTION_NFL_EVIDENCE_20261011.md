# NFL prediction-market evidence update — 2026-10-11

Published the existing Prediction Markets panel with a matched NFL view and a separate broad sample view. No orders or wallet operations.

Polymarket discovery uses the NFL series returned by the official Gamma sports endpoint, with bounded pagination and an explicit completeness flag. This run returned 87 active NFL events and matched 22 moneyline markets across 22 saved ESPN games. Matching requires away/home order, local game date using America/New_York, identical UTC kickoff, two distinct outcome teams and two distinct token IDs. Non-moneylines, closed markets, ambiguous games, unknown outcomes and mismatches are rejected. Captured settlement text, hashes and fee metadata remain research evidence, never approval.

Kalshi displays the existing 48 outcome contracts across 24 matched games. Its original capture timestamp is preserved; it was not refreshed or silently promoted. The panel labels evidence older than 15 minutes. Both providers remain PASS. Their postponement terms differ and cross-provider equivalence is not established.

New output: nfl_live/prediction_markets/polymarket_nfl_contract_audit_latest.json and timestamped audit; allowlisted commercial_web/public/prediction_market_nfl_evidence.json. Refresh command: python3 scripts/audit_polymarket_nfl_contracts.py. No recurring job was added. Prices are saved indicative observations.

Validation: matcher tests first failed on the missing exact match, then passed all three tests including wrong date/time/order/type, unknown outcomes, duplicated tokens and ambiguous game IDs. Seven local Chromium checks passed: three prediction panel widths (320/390/430) and four homepage overflow regressions (320/360/390/430). Production Vite build passed. All three public-site prediction checks passed at 320/390/430px after the final build.

Remaining: independent predictive advantage (existing holdout candidate did not beat market baseline), prospective validation, current executable quote/depth, contract-specific fees and independent settlement confirmation. No independent probabilities, approved picks, fee verification or settlement confirmation are invented by this update. No Safari claim is made; phone layout was confirmed by the user before this task.
