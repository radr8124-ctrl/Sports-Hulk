# Sports Zenith — CFB 8GB source-preserving streaming learning recovery

**UTC October 9, 2026.** Goal: restore previously deferred college-football historical recommendation grading with bounded memory. No original raw data, bet/probability selection rules, official grades, site pages, or customer bets altered. Source history index results are research recommendation records, **not verified real wagers or profitability**.

## Failure recovered

The 10-minute CFB refresh had continued archiving, but since October 6 its grader attempted a full pandas read of an **8.46GB append-only source CSV**, resulting in out-of-memory kills. A temporary 512MB safety guard therefore deferred every new CFB grade despite the rest of the CFB system working. The protected original evidence was never cleared or truncated.

## Actual full-original-ledger index and new CFB grading

- Original source: `cfb_live/decision/history/CFB_RECOMMENDATION_LEDGER.csv`, 8,462,861,184 bytes at the 05:52Z snapshot. Original CSV rows are permanently retained; no bulk pandas read and no source trimming.
- Created `cfb_live/decision/cfb_incremental_ledger_index.py`, a bounded, resumable SQLite latest-per-recommendation index, protected by single-writer lock and with original file inode, header/prefix hash, source cursor, processed-row count and last scanned boundary hash. Source may only grow by complete CSV lines. Atomic SQLite transactions checkpoint rows and cursor together. Unexpected source replacement, truncation, rewritten boundary, malformed identity and partial CSV row all fail closed.
- **Initial one-time scan:** 4,585,385 original rows to the start-state size 8,448,778,922 bytes, **311.59 seconds**, 56,448 KB peak resident process memory; then a separate **14,082,262-byte** catch-up processed 7,640 new rows in **0.70 seconds** at 55,424 KB peak.
- **Completed source-as-of-05:52Z state**: **4,593,025 original recommendation snapshot records** indexed, **20,995 latest unique recommendation identities** (20,698 game-lane, 297 parlay-lane). Original raw source was not modified. This is substantially more complete than old October 6 episode file (16,948 unique records).
- Changed `cfb_live/decision/grade_cfb_recommendations.py` to require a verified *fully caught-up* index, then read only 20,995 latest per-key records with the same original pandas field parsing, instead of ingesting 8.46GB. Old report files were independently backed up before the test under `.deploy_backups/cfb_incremental_grader_pregraft_20261009T055700Z/`.
- Actual full indexed grader ran **exit code 0**, in **58.29 seconds**, **475,508 KB peak RSS**. Its original grading output now contains **20,995 records**, including **6,128 WIN, 6,041 LOSS, 98 PUSH, 8,728 PENDING**. Exactly **12,267** are technically settled *research recommendations*; they are not guaranteed available/executable prices or proof of a betting edge. Automatic model adjustment remains **false**; no spreads/totals model qualification claimed.
- Independent acceptance: all **20,995** source recommendation keys matched the reproduced latest SQLite entries and **all 20,995 original payload_json values** matched. Every one of **10,629 earlier settled legacy CFB grades** matched its new grade with **zero retroactive reversals**.
- `cfb_live/decision/run_cfb_learning_postrefresh.sh` now archives current evidence, runs bounded source-index catch-up (128 MB maximum per cycle), and grades **only when the original source is fully indexed**. An incomplete/changed original source returns exit 85 as a truthful incomplete-learning status, rather than declaring successful learning or OOM-killing sports refresh. Grader errors also cannot become a false successful message.
- Regression: 8 source-index tests and 4 indexed-grader/wiring tests passed, and Python syntax, shell syntax and Git whitespace tests passed.

## Current limitations and next work

1. **Recurring systemd timer validation** is still required AFTER first restored grading pass; confirm the next ordinary CFB refresh appends fresh original rows, resumes the index, grades, and ends with status SUCCESS without accidentally changing settled grades.
2. **Unbounded archive writer remains**: source currently grows ~14MB every 10 minutes when the bundle hash changes, even for repeated unchanged game recommendations. The new grader fixes OOM and repeated huge reads but does NOT yet reduce that future raw-ledger disk growth. Next separate, versioned, source-provenance-preserving task should suppress unchanged per-key source snapshots or otherwise preserve old raw evidence while reducing redundant append growth. Do **not** delete, truncate or rewrite the original 8.46GB file.
3. Source index verifies original header/prefix and recently processed boundary; it does not cryptographically attest every one of 8GB original bytes at every refresh. Original content-addressed archival backups and independent offsite restores remain separate requirements.
4. Despite restoring actual ongoing learning, no statistically established market probability/ROI advantage or 70% selective profitable win-rate evidence has emerged from this maintenance alone.
5. SQLite index contains private data and stays excluded from Git. Only code, tests, summaries and acceptance report belong in source control, not the original 8GB sportsbook-source record.

## Reproducible commands

```bash
cd /home/ubuntu/sports-hulk
.venv/bin/python -m unittest tests.test_cfb_incremental_ledger_index tests.test_cfb_indexed_grader -q
.venv/bin/python -m cfb_live.decision.cfb_incremental_ledger_index --max-megabytes 128
.venv/bin/python -m cfb_live.decision.grade_cfb_recommendations
```

Manual first-restore private log: `reports/cfb_incremental_recovery_20261009/CFB_INDEXED_GRADE_EXECUTION_PRIVATE.log`. Historical comparator source backup and readback manifest: `.deploy_backups/cfb_incremental_grader_pregraft_20261009T055700Z/SHA256_BEFORE.txt`. A true off-VPS raw-data restore remains **NOT VERIFIED**.
