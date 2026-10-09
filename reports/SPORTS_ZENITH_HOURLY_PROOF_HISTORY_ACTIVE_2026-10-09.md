# Zenith — actual hourly permanent evidence scorecard accepted
**2026-10-09 UTC. Versioned, source-first research only. No live bets or model promotions.**

## Finished and running
- Original sports-hulk-intelligence-archive.service and its hourly timer are **unchanged**. Its existing archive ran to systemd success, with the additional nonblocking, 12-second guarded ExecStartPost successfully executing the research-only scorecard at 2026-10-09T09:06:26.761996+00:00.
- Versioned service drop-in under `deploy/systemd/system/sports-hulk-intelligence-archive.service.d/forward-proof-research.conf` **exactly matches** installed root systemd drop-in.
- Scorecard builder `intelligence_warehouse/brain_performance/build_forward_proof_history.py` reads eight existing source receipts, validates counts and prices, writes versioned append-only private `FORWARD_PROOF_TREND_APPEND_ONLY.jsonl`, and atomically updates private `FORWARD_PROOF_CURRENT.json`.
- Current evidence chain contains **3 source-version checkpoints**, all valid with SHA-256 previous-entry linking, SHA-256 receipt for each of eight source files, and current-view hash readback. Current immutable chain tip `2e67858672a21e83b14307a83d517553793d6d7dbe9499ebfe75f3f034631a37`. Unchanged source digest causes no duplicate history append. A missing current-view file can be reconstructed only from verified original history; a missing, truncated, tampered, or silently overwritten original source chain fails closed.
- The live scheduled 09:06 UTC archive and scorecard completed with exit status 0. Source files are only read; no old/losing result is deleted, and no retrospective re-grading is performed.
- Combined forward scorecard tests: **19 passed**, including loss-deletion guard, incorrect simulation ROI, modified cache, source disappearance, CFB aggregate consistency, NFL abstention integrity, missing/truncated chain and service wiring. No ongoing user session is needed for normal hourly systemd runs.

## Latest source-model accuracy and economic reality
| Cohort | Result | Paper-priced ROI | Market Brier vs model Brier | Proof |
|---|---|---|---|---|
| Game-lines forward | 115–71 (61.8%) | 4.98% | 0.23609 / 0.23609 | NOT_PROVEN |
| Props / pick'em forward | 1763–1080 (62.0%) | -1.79% | 0.19664 / 0.20062 | NOT_PROVEN |

Game lines' model probability Brier is **equal to sportsbook Brier at reported precision** despite positive *simulated* 4.98% priced return; that does NOT prove market outperformance. Props Brier is 0.20062 vs original sportsbook 0.19664 (worse); props 62% win rate with -1.79% paper ROI makes prices critical.

- Full16 MLB first real pregame frozen model beat the raw source Brier by around 0.001787, but only **one independent completed game**, with 18 correlated player lines. No generalizable or profitable proven edge.
- Future MLB two-hour provider-quote movement: **29** frozen source observations in **two upcoming games**, zero independently verified player-ID+official-Final grades; none is a current betting recommendation.
- NFL 13 original source-pre-kickoff shadow predictions remain frozen and their strict 70%-plus-priced-value research screen abstained on all 13. No official outcomes yet.
- CFB recovered historical index currently lists **21003** distinct recommendations and **12267** analytically settled history labels. This is not a count of winning or placed bets.

## Durability and outstanding limits
- Data history and current view are private files excluded from Git; code, systemd configuration, tests and this machine acceptance are versioned.
- The initial/current history is checksum-verified **on the VPS**, not from independent offsite storage. **Off-VPS restoration is NOT verified**; local Git alone does not ensure disaster recovery. Do not claim otherwise.
- Existing large `commercial_web/public/brain_performance.json` dashboard bundle was intentionally **not overwritten** by this sidecar. The new hourly analytics are presently a separate internal evidence feed, not a redesigned website panel.
- This preserves actual results and source provenance; it does **not** improve sports-betting accuracy or establish a guaranteed 70% win rate.
