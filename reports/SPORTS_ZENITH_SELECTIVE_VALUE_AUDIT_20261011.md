# Fixed selective-value audit

The opponent-adjusted EPA model produced zero selections in 1,669 chronological 2019–2024 games and zero in 284 previously inspected 2025 games. ROI is undefined, not 0%; no profitable strategy or exchange edge was validated.

Rule frozen before this calculation: select at most one side per game, using the larger American-moneyline modeled expected return, requiring at least 3% after subtracting a hypothetical cost equal to 2% of stake. Flat one-unit stakes. No threshold sweep or adjustment after results. Historical data and forecasts were previously inspected, so this is a fixed retrospective diagnostic, not pristine preregistration.

American payout uses the compiled raw price, not no-vig odds. Exact game/season/week, outcome and normalized paired-price identity are checked against preserved forecasts. Source hashes link the protocol, prediction receipt and master. Six seasonal summaries and all decisions are saved in nfl_live/prediction_markets/nfl_selective_value_latest.json. Inference is suppressed below 30 selections and 10 selected season-week blocks; these floors do not by themselves validate an edge.

Independent source audit: data_vault/game_master.py obtains schedules from NFLverse nfldata games.csv. The master has no bookmaker, quote time, or opening/closing moneyline identity. README labels spread and total closing; moneyline timing remains unverified. Historical EPA uses retrospectively revised sources. The binary cohort excludes five 2019–2024 ties and one invalid price pair; the 2025 diagnostic excludes one tie. These exclusions prevent interpreting this as complete executable settlement P&L. The 2% cost is a sensitivity assumption, not Kalshi or Polymarket fees.

Independent strategy review confirmed raw-odds payout arithmetic and flagged sparse selection bootstrap risk. Its separate gross-EV calculation found two bets just above 3% before hypothetical costs; neither clears the registered after-cost hurdle. Those observations do not change the rule or establish an edge.

Next validation requirement: retain the existing frozen prospective model and protected ledgers; source paired same-book/same-update quotes after context freeze and before kickoff, then independently check Finals. Exchange-return evidence additionally needs contract identity, observable executable depth, specific fee terms and settlement treatment. No trades, approved picks or production model changes.

Validation: four payout, side-selection, cost, no-bet ROI and source-integrity tests pass. Research results published in the existing model comparison. Mobile production checks performed separately.
