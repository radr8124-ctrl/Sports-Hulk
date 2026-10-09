# Sports Zenith: Odds-First Betting Intelligence — 2026-10-09

## User-facing problem and actual fix

The Best Bets page showed model abstentions more prominently than sportsbook prices, even though Zenith already had tens of thousands of source-market observations. The existing site now puts an odds-first, searchable, sortable price-comparison board above the original audit/ledger section. This is a functional improvement, not a website rebrand and not a relaxing of betting-proof requirements.

## Source-proven current game odds

Implemented read-only builder: intelligence_warehouse/betting_v2/build_betting_odds_board.py. Input: preserved original NFL bookmaker CSV with independently verified ESPN matchup/time and source archive SHA; existing CFB, CBB, MLB, NBA and NHL game-market CSVs. No new vendor or API calls. The builder matches same-event, same-book, two-sided moneyline/spread/total quotes for the SAME market and exact spread/total, rejecting missing sides, mismatched spread signs or totals, unsupported subtypes, conflicting duplicate prices, bad American odds, changed source bytes, inconsistent within-book start clocks, overly inconsistent provider kickoff (greater than 15 minutes), and unsuitable overround. Every displayed representative market must have at least two verified book pairs.

The sample published Oct 9 around 22:55 UTC had 98 upcoming priced matchups: NFL 13, CFB 50, NHL 18, NBA 16, MLB 1, CBB 0. There were 95 source-priced moneyline markets, 96 spreads and 92 totals. For each side the odds board shows the best observed American odds and sportsbook, the typical same-line competing sportsbook price, the book-consensus no-vig fair probability and the precise difference in break-even implied probability. The notable book-to-book price distinction requires a 2.0 percentage-point break-even improvement and at least three full paired books for that exact line; 38 games contained at least one such difference at the observed snapshot. This rating is PRICE SHOPPING, not independent winning edge or guaranteed executable odds.

The live Best Bets page now offers all existing sport and market filters, sort by upcoming games vs better observed prices, dated quote capture labels, automatic browser revalidation of stale capture time, and incremental Show 12 more access to every qualified game. Original research/proof cards remain beneath the priced board.

## What Zenith predicts

For exactly matched NFL events, the board reads the original public frozen nine-feature forecasts through the previously implemented source-proof validator (nfl_frozen_forecast_presentation.js), then joins by verified ESPN event ID and kickoff. Displays the predicted winning team and experimental winner probability, alongside original pinned Pinnacle no-vig market probability and signed model-minus-book difference. The model was market-assisted and its historical 2025 holdout did NOT demonstrate market superiority. This remains explicitly experimental, with no official betting recommendation. No other sport model projections have been fabricated.

The Props and PrizePicks tabs now show sportsbook reference odds/market probabilities or true pick-em lines prominently, with player search, existing NBA season-type and sport filters, upcoming-only default, optional past research and Show 12 more pagination, instead of trapping users at the first twelve of many research records. PrizePicks has no claimed direct bookmaker price, entry payout or joint EV without corresponding proof.

## Read-only recurring update

Added and read-back verified crontab marker SPORTSZENITH_GAME_ODDS_READONLY_BOARD_V1, scheduled every ten minutes at minute 3, 13, 23, 33, 43, and 53; existing user/project crontab entries were unchanged. One genuine scheduled run was observed at 22:53 UTC with a successful published JSON readback. Source refresh is local-data-only and makes no new paid bookmaker calls. Public and dist versions of betting_odds_board.json are byte-identical.

## Acceptance and safeguards

11 focused Python unit checks passed for odds identity/math/source; 31 regression Python checks passed for original odds and independent-game protection prior to the final additional timing test. All 193 existing website Node tests passed. 19 browser end-to-end checks passed, including 8 new odds/price/matched-model/props/PrizePicks tests and 11 existing NFL/Survivor/mobile checks. React production build passed; the public HTTPS JSON and website health endpoints returned HTTP 200. Existing Survivor saves, betting forward ledgers, model coefficients and original historical data were untouched. Before-change UI files and crontab text are stored with SHA256 proof under .deploy_backups/odds_first_bets_before_20261009T2240Z on the VPS.

## Honest limitations

The platform does not currently establish any proven positive-EV bet or real money profit. Exact accessible/current executable sportsbook offers have not been verified; every price is a dated observation and may move. Non-NFL bookmaker event IDs are provider-verified only, not independently joined to official league game IDs. NBA pricing dates are not equivalent to preseason market coverage. CBB currently has zero source game lines; no lines are invented. Independent off-VPS raw-data disaster recovery remains unverified. The goal of this delivery is letting users evaluate real source-priced options and see exactly what model evidence exists without hiding everything behind a PASS message.
