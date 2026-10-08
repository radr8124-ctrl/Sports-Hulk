# Week 5 private Survivor save — production release

UTC date: 2026-10-08
Code revision: f0b1334
Rollback: .deploy_backups/survivor_week5_editor_20261008T034640Z

- Main Survivor tab now renders a compact private linked-entry Week 5 pick editor above My Pick Score. Team reuse is blocked, and attempted changes after verified kickoff or to eliminated/resolved entries fail closed.
- New linked-member-only POST /api/survivor/save-picks route uses authenticated Insforge bearer, explicit linked entry ownership, rate limits and the existing atomic personal Survivor editor. It stores only Sports HULK local picks; nothing is submitted to the external pool.
- 10 Python sandbox cases passed and all 81 commercial UI/API tests passed. Hybrid production build included the user's uncommitted Props panel refactor unchanged.
- Existing personal Survivor entry state, prior Vikings WIN, Week 3 history and all unrelated App.jsx modifications remained byte-for-byte identical. Live authenticated save was not exercised against a user account to avoid creating a selection without user instruction.
- Staged frontend and controlled Node server restart succeeded; 200 for web, API, private score-card component, public NFL scores and legacy Survivor site. Unauthenticated save returns HTTP 401.
- Main commercial whole-pool PDF/XLSX/CSV upload remains to be connected with explicit manager-only authorization. The legacy Streamlit import remains operational.
