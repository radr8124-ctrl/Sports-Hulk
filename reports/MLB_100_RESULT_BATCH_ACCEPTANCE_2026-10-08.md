# MLB verified result batch size upgrade — October 8, 2026 UTC

## Decision
- The official MLB frozen-prop settlement limit is increased from 50 to 100 per default hourly run, with an enforced maximum of 100.
- The batch is computed only after checking official MLB StatsAPI Final game state, exact original provider-event-to-gamePk identity, unique player ID and team, played box stats and frozen pregame market/side/line.
- The next run resumes only still-pending verified results, and all prior appended ledger bytes, original market/model probabilities and existing grades are immutable.
- Automated model promotion stays disabled. The record does not claim platform wagers, payouts, or real money profit.

## Production-data isolated acceptance
- MLB provider final game 849833 (Cleveland at Chicago) was confirmed Final by current StatsAPI schedule and exact official player boxes.
- New grades qualified: 147 = 98 WIN + 49 LOSS, zero contradictions with 1,943 previously graded MLB outcomes.
- Two default-sized batches on copied 9,310,571-byte forward ledger: 100 then 47.
- Replayed MLB: 2,498 tracked; 1,467 WIN, 623 LOSS, 408 PENDING.
- Frozen entries across sports identical, settled grades from other sports unchanged. Original ledger byte prefix preserved.
- Third rerun appended 0 duplicates and reconfirmed 2,090 settled MLB outcomes.
- The 408 remaining are not automatically losses or wins. Await official finals, verified participation or preserve invalid pregame capture holds.

## Tests
- Crosswalk suite: 16 PASS, including 105 synthetic valid results automatically batched 100 + 5 + 0 and invalid 101-sized/manual requests blocked.
- Official MLB 26 PASS; rolling official 10, frozen original event 10, MLB capture 17, Game Master 14 PASS.
- NHL 23, NFL 11, NBA 43, competition regime 59, forward provenance 22, deployment safety 8 PASS.
- Commercial Node 66 PASS; production frontend Vite build and Python syntax PASS.

## Production checklist
- Snapshot immutable forward ledger, official-source CSVs and receipts, Brain Record and existing unrelated work before fast-forward.
- Deploy source-only change, run batches with limit 100 and stop immediately on any source/previous-grade conflict.
- Rebuild Brain Performance and confirm public result freshness, API health and Survivor.
- Push GitHub main for CI-only proof. Never stage or reset unrelated live changes.
