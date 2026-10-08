# MLB verified 100-result batching — live production acceptance

UTC date: 2026-10-08
Source revision: 66299fd
Backup: .deploy_backups/mlb_100_grade_20261008T000519Z
Recovery branch: backup/pre-mlb-batch-100-20261008T000519Z

## What changed
- Increased the default and enforced maximum MLB forward official grade batch size from 50 to 100. Smaller manual batches remain valid. Requests exceeding 100 are rejected, including an invalid bool.
- Retained original pregame source provenance, exact MLB StatsAPI Final official game, MLB gamePk, official numeric player ID/name/team, played box metrics, market/side/line and no prior result contradictions.
- The immutable original ledger is always append-only; the result evidence source is not used to automatically promote a model, infer real bets or claim payouts.

## Verified MLB production rollout
- MLB StatsAPI official game 849833: Cleveland Guardians at Chicago White Sox, October 7, 2026, final score Cleveland 9–Chicago 3.
- Read-only preflight: 147 newly eligible box-scored prop predictions, 98 WIN and 49 LOSS, previous grades independently verified, zero conflicts.
- Validated live production results in exactly TWO batch scans: 100 + 47. Enforced per-batch maximum 100.
- After live grading: 2,498 MLB frozen predictions, 1,467 WIN, 623 LOSS, 408 PENDING. Settled total 2,090.
- Repeated official source scan appended zero duplicates and independently confirmed all 2,090 previously graded MLB outcomes.
- Existing settled predictions, all sports' other forward grades, probabilities and frozen choices preserved. Entire original forward ledger prefix (9,310,571 bytes) retained.
- All newly appended result events have exact official MLB final game and player proof and explicit platform_payout_claimed=false, automatic_model_promotion=false.

## Outstanding cases
- The remaining 408 MLB predictions are not automatically graded WIN or LOSS. At the final settlement scan the other three original provider games were not official Final, and some previously captured cases lack verified played status or original pregame capture. Later official result feeds may reduce those pending totals.
- Brain Performance rebuilt READY, matching embedded/public accountability.
- Brain forward MLB: 2,498 tracked, 1,467 wins, 623 losses, 2,090 settled, 408 pending, 35 pending overdue 12 hours.
- NHL remained 977 WIN, 646 LOSS and 323 PENDING. Automatic model promotion remains disabled.
- Commercial API HTTP 200, Survivor HTTP 200, Brain API HTTP 200.

## Tests
- New 105-result fixture proved the default splits into 100 + 5 + 0 idempotently; input limits reject 101 and larger: 16 identity/batching tests PASS.
- Other regression checks: MLB official 26, rolling 10, frozen source 10, original capture 17, MLB master 14, NHL 23, NFL 11, NBA 43, competition regime 59, forward evidence 22, deployment safety 8 all PASS.
- Commercial Node tests 66 PASS; Vite frontend build and Python syntax PASS.
- Source-only fast-forward deployment after hashed snapshot and recovery branch; all unrelated live market and UI work preserved.
- GitHub main receives CI-only verification; there is no destructive automatic deployment.
