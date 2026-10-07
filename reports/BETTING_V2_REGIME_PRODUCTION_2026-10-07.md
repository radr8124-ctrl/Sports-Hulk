# Betting V2 Regime Isolation — Production Integration

Date: 2026-10-07 UTC
Environment: /home/ubuntu/sports-hulk (production source)
Change: feature/betting-v2-regime-isolation -> main (fast-forward)
Previous main: 9550ed2
Merged main: 739e838
Prior production-state backup: .deploy_backups/betting_regime_20261007T201003Z
Recovery branch: backup/pre-regime-20261007T201003Z

## Post-merge gates
- Python regime checks: 42/42 passed
- Commercial web Node checks: 66/66 passed
- Production Vite build: passed
- Backend server node --check and Python builder py_compile: passed
- Updated all-markets current, all-markets forward, CLV, and Brain Performance builders: all returned zero
- All-markets forward ledger prefix preserved: 604,806 -> 620,111 bytes
- All-markets price ledger prefix preserved: 1,039,560 -> 1,047,483 bytes

## Deployment
- Restarted the **user-level** systemd unit sports-hulk-commercial.service, not the system-level service
- Unit active, port 8510
- GET /api/health: 200, status ok
- GET /brain_performance.json: 200, status READY
- GET /: 200
- POST /api/ask for NBA best bet: 200, intent best_bet, status WAITING, trace_id present; no current qualified NBA market candidate
- Independent Survivor service on 8502: health 200

## Proof and data observations
- Brain current proof lanes: 18, with NBA UNKNOWN keys for MONEYLINE, SPREAD, TOTAL
- Live NBA current candidate count: 0; current live decision feed contains CFB, MLB and NHL picks
- Brain forward proof lanes: 1 (CFB moneyline); no active NBA forward cohort at integration time
- Do not infer NBA competition regime from date or week; wait for upstream explicit evidence
- No model promotion or live play based on unknown-regime proof
- Unrelated uncommitted application edits and local runtime artifacts preserved

## Follow-up
Audit NBA upstream competition-regime coverage once there are current NBA candidate rows and continue forward validation. See BETTING_V2_REGIME_ISOLATION_ACCEPTANCE_2026-10-07.md for the full test and isolation specification.
