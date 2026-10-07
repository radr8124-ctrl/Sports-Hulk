# Sports HULK GitHub release safety — 2026-10-07

## Why the change was needed
The previous GitHub Actions deploy was triggered after a nearly-empty CI job. It ran rsync with a destructive --delete flag into the live Sports HULK directory and restarted the system-level 8501 service. The active commercial site, however, is the user-level sports-hulk-commercial.service on port 8510. Uncommitted commercial UI changes and critical untracked decision/ledger data exist on the production VPS.

## New release policy
- A push to main or feature branches runs code checks ONLY (Python betting proof, Node commercial tests, frontend build).
- There is no GitHub-to-production automatic deployment.
- The former deployment workflow is a MANUAL read-only release validation gate; it cannot deploy even when manually run.
- Thirteen outdated write-enabled/manual cutover workflows were retained verbatim under docs/archived-workflows/2026-10-07 so they cannot be accidentally invoked from GitHub Actions.
- Read-only diagnostic/render trace and the emergency recovery workflow remain available.
- The read-only local preflight at scripts/sports_deploy_preflight.py checks that a proposed origin/main revision is forward-only, does not delete tracked files, does not collide with local changes, and does not publish stale frontend assets over uncommitted commercial work.
- The local preflight does NOT fetch, reset, copy, build, restart, or change production. A manual deployment still requires explicit review, backup, tests, controlled release and live health validation.

## Test gates
- python3 -m unittest discover -s tests -p test_sports_workflow_safety.py
- .venv/bin/python -m unittest discover -s tests -p 'test_*regime*.py'
- cd commercial_web && node --test ./*.test.js
- cd commercial_web && npm run build

## Commercial app
Correct commercial unit: systemctl --user restart sports-hulk-commercial.service (with the Ubuntu user session bus).
Live API: http://127.0.0.1:8510/api/health
Survivor service on 8502 remains independent and should not be disturbed.

## Recovery / change control
Existing backup and previous code checkpoint: .deploy_backups/betting_regime_20261007T201003Z and branch backup/pre-regime-20261007T201003Z.
Preserve uncommitted commercial_web/src/App.jsx and all runtime data/ledgers.
Never use rsync --delete against the live repository, and never reset Git history to force a deployment.
