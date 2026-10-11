# Prediction-market execution evidence — 2026-10-11

Added scripts/audit_prediction_execution_evidence.py, a public read-only collector. It captures the current KXNFLGAME series fee metadata, event-specific fee-change responses with bounded pagination for each of 24 events, and depth-100 books for 48 mapped contracts. Results: 48 books captured, 48 valid observed spreads, 48 contracts with complete series/event metadata receipts. Fee metadata completeness is not execution-fee verification. No fee formula, fee-adjusted edge, independent probability, settlement equivalence or fill guarantee is asserted.

Yes asks are derived as 1 minus the highest positive-size No bid, using Decimal arithmetic. Zero-size, nonfinite and invalid levels are excluded; crossed and one-sided books are not marked usable. Books are time-stamped independently of older contract terms. This is an observation, not a confirmed executable price.

Polymarket initially returned HTTP 403 on default public probes. Subsequent normal collector requests succeeded. The completed bounded collection captured order books with matching asset IDs and fee parameters for all 44 outcome tokens across 22 games, with zero HTTP 403 responses in the saved run. The reported base_fee parameter is retained as source evidence; its relationship to Gamma feeSchedule metadata is not assumed. Fee calculation and execution remain unverified.

Full raw successful responses and hashes, endpoint URLs, and failures are preserved in nfl_live/prediction_markets/execution_evidence_latest.json and a timestamped receipt. Only summary counts and sanitized book levels are added to the public evidence file. No orders, account operations, recurring jobs, or wallet actions.

Refresh sequence: python3 scripts/audit_polymarket_nfl_contracts.py followed by python3 scripts/audit_prediction_execution_evidence.py, then build commercial_web. The first script rebuilds the public matched-contract file, so run the execution collector afterward to attach fresh receipts.

Tests: three focused Python tests cover unsorted bids, complements, zero-size levels, malformed/empty/crossed books, incomplete pagination, wrong-event responses and no approval promotion. They failed before implementation and passed afterward. Vite production build passed. Public panel checks at 320/390/430px assert receipt counts, book details, Polymarket token receipt coverage, provider switching, search and no horizontal overflow. All picks remain PASS; execution and execution fees remain false.
