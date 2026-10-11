# Narrowed NFL validation run

Scope is now one existing frozen model, NFL full-game winners, and one observation ledger. No new feature search, training or threshold sweep. The 14 original pre-kickoff forecasts remain the model cohort. Five games had not started during the 2026-10-11T17:16 source capture; games already underway are excluded from new observations.

Fresh execution evidence produced 14 usable outcome asks across five future games: eight Kalshi observations and six Polymarket observations. This is incomplete provider coverage, not every possible outcome on both venues. Quote observations are required to occur after the original forecast freeze, within 15 minutes, and before kickoff. Exact event and outcome team identity must match. Alias normalization distinguishes Rams LA/LAR from Chargers LAC. Unsorted Polymarket asks use minimum valid price and aggregate size at that price.

The raw conditional-model probability minus ask is saved for research. Five observations had positive raw gaps, but these are not verified EV or picks. The model lacks a proven advantage; tie/cancellation-adjusted value and actual fee confirmation remain unavailable. No paper-trade profit, fill or trade approval is invented. Ask depth is an observation, not guaranteed execution. Fee-adjusted expected value remains null.

Protocol: NFL_NARROW_FORWARD_PROTOCOL_20261011.json. Timestamped observation snapshots and latest receipt: nfl_live/prediction_markets/nfl_narrow_forward_quotes_*.json. The receipt binds protocol, original forecasts and raw execution capture via SHA256; the raw execution receipt retains public source URLs, data and hashes. No original forecasts were rewritten.

Verification: three timing, alias/side and orderbook-price tests pass. Scope remains a single future-game cohort; independent Finals will assess prediction accuracy and any proposed fee/settlement-adjusted strategy requires its own frozen rule before profit grading.
