# Sports Zenith — OddsJam Independent Product Reference
**Observed:** October 9, 2026 (America/New_York)
**Source:** OddsJam official public feature pages, published sports API documentation and iOS App Store listing, cross-checked with public sports-betting user reports. OddsJam's primary website challenged headless browser access (HTTP 403), so paid member/dashboard behavior was NOT directly tested.

## Evidence sources
- https://oddsjam.com/betting-tools/positive-ev
- https://oddsjam.com/odds-api
- https://oddsjam.com/betting-tools/sharp-money
- https://oddsjam.com/getting-started-guide/7
- https://oddsjam.com/lp/ads/arbfather-platinum
- https://apps.apple.com/us/app/oddsjam-sharp-sports-betting/id6448072108
- Reddit user feedback: https://www.reddit.com/r/PositiveEVbetting/comments/1lhf02o/latest_oddsjam_review/ ; https://www.reddit.com/r/sportsbetting/comments/1vb0a0v/is_oddsjam_any_good_or_legit_anyone_tried_it_or/

## Verified marketing features, not independent results
- OddsJam markets a Positive EV (+EV) screen: pairs available bookmaker prices for the exact bet with a fair-value reference to estimate potential EV; advises exact sportsbook and wager, tracked separately from actual bettor execution. Positive expected value is not guaranteed profit.
- 100+ sportsbook coverage claimed, including real-time player props, alternate lines and futures; proprietary enterprise API separately available for licensed odds/line history, odds-change push feed, closing/opening lines, results and injury status. The public developer offering is contact-for-pricing; a normal consumer subscription is NOT equivalent to developer API rights.
- OddsJam shows sharp-money/market-reference information, odds comparison, line movement history, market screens, stake/arb calculator and automatic bet tracking incl. ROI and Closing Line Value (CLV).
- The iOS App Store listing advertises Trends $19.99/month, Fantasy $59.99/month, Sharp Money $199.99/month and Platinum $499.99/month (prices/features subject to change and entitlement; verify current checkout before any spending). No need to buy to study product workflow.
- User anecdotes on Reddit report both usefulness and stale/unavailable high-EV quotes or disputed billing. These are unverified anecdotes, not measured performance, and reinforce executable-quote and billing-provenance guardrails. Official promotional language such as 'risk-free' or guaranteed profit is NOT verified.

## Important method distinction
- Comparing the best quote with an average/median **peer bookmaker** price can identify a better *offered price*, but does NOT prove a positive-EV bet. Independent fair win-probability evidence and exact timestamp + line + accessible sportsbook are separately required.
- For decimal net payout b and estimated win probability p, estimated EV per $1 stake is p*b-(1-p). For American odds A, b = A/100 if A>0 or 100/|A| if A<0. Without p with defensible independent origin, a correct EV% cannot be claimed.
- A sharp-book reference may be stronger than peer median, but must be same event, outcome, line, sport phase, market type, and as-of snapshot. Multiple devig methods and leave-one-book-out sharp consensus should be *tested*, not automatically treated as truth. Calibration and last quote age must be visible.
- For arbitrage, verify two independently executable opposite positions, the same grading rules, true limits, hold, and execution ordering; quotes alone do not establish a risk-free return.

## Three external references — distinct roles, not copied software
1. **PolyPredictr** — clean cards: market probability, plain-language verdict, clear risk/catalyst explanation, deeper Signal Lab and public history. Its paid AI confidence was not independently proven.
2. **Stat Sniper** — branded conversational analyst ("Chad AI"), cross-page bet/prop questions, named sources, quick takes, interactive replies; Zenith's proposed referee-inspired avatar must be distinctive, not a clone.
3. **OddsJam** — serious line-shopping and EV scanner, sharp bookmaker reference, exact market matching, quote-freshness/line movements, +EV/arb/prop workflow and automatic actual bet/CLV performance logging.

## Suggested Sports Zenith roadmap (implementation NOT authorized by this research report)
**Priority A, not a redesign:** "Odds / Price / Zenith" on the current Best Bets and Props screens. Show exact side/team, bookmaker, market subtype, line, odds, quote capture time/age, typical peer book price, sharp no-vig reference (if genuinely available), independent Zenith probability (if calibrated), hypothetical ROI/EV only when inputs qualify, confidence *of the evidence*, and a one-tap 'Why'. Keep three separate statuses: more attractive relative book price, potentially positive EV pending proof, validated recommendation. No invented wins.
**Priority B:** quote history by exact event/line with opening -> current -> real close snapshots, record which book moved first, append-only CLV / market beating vs outcome evaluation, and bookmaker-availability audit. This is the critical infrastructure gap.
**Priority C:** player props/PrizePicks tailored research: real paired book prop prices, 5/10/20 game historical trends (actual as-of only), injury lineup verification, then entry payout+correlated-leg calculations and frozen prospective validation.
**Priority D:** tie the above to the distinctive referee-style Zenith Ask bot, not just a generic chat bubble: "Official review: selected side, current quote, model vs market, why, risk, source freshness, and specific next check." A model can explicitly declare insufficient evidence without repeating PASS on every card.

## Current live Sports Zenith evidence (checked October 9, ~8 PM ET)
- Odds board source JSON currently contains **102** priced upcoming research games; exact number varies each refresh.
- BETTING_V2_CLV.json currently tracks 98 observations, 49 labeled closed; entry-price CLV EV mean -2.3203% (research metric, not confirmed actual bettor P/L). Different close source clocks and earlier quotes are NOT accepted as guaranteed true final market close.
- Separate spread/total line CLV report currently shows **zero** independently qualifying closed spread/total comparisons, despite 114 tracked entries. This means claimed OddsJam-style closing-line proof is NOT yet available for these markets.
- Current prop V2 defaults to market-only probabilities when trained independent edge has not been proven. Do not call these model forecasts. Existing uncalibrated four-game NFL form histories remain research, not real +EV bets.
- No OddsJam API entitlement or subscription was verified; do NOT imply a data integration exists or that premium functionality is free.

## Storage, IP and integration constraints
No UI or proprietary code was copied, no OddsJam account was created, no payment made, no site/ledger/model modified, and no third-party data feed was scraped or connected. This is a versioned research reference, not an approval to lower Sports Zenith's quality gates. Confirm provider licensing, allowed display/redistribution and cost before any commercial sportsbook feed connection. Off-server disaster recovery remains separately unverified.
