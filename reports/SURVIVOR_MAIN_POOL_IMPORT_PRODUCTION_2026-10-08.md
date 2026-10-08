# Main Survivor PDF/XLSX/CSV pool upload — safe production release

Date: 2026-10-08 UTC
Source revision: 9f98c93
Recovery directory: .deploy_backups/survivor_pool_admin_ui_20261008T035558Z

- Manager-only two-stage upload is deployed on the main Survivor tab. Preview is read-only, and confirms require a bound one-time ticket plus identical SHA-256 source, unchanged prior pool snapshot and nonregressed active pool week. Only authenticated accounts with explicit server-assigned survivor_pool_manager role or server allowlist may access pool-wide imports.
- Server has no SURVIVOR_POOL_ADMIN_IDS/EMAILS configured in local .env.local, so the UI remains hidden until a manager account is provisioned. This is intentional; no ordinary user may change global pool ownership or all entries.
- Upload bridge restricts to max 5 MB PDF/XLSX/CSV, validates PDF signatures and XLSX zip bounds, and reuses the backed-up existing importer. All repeated-name tickets remain distinct and historical personal picks are preserved.
- The actual previously accepted nine-page Week 4 PDF was tested read-only against active Week 5 and explicitly rejected. No historical file or user entry state was overwritten by any live import.
- Python import bridge 8/8, duplicate ticket 12/12, private pick saver 10/10, commercial Node 86/86 passed; current user Props V2 refactor included in tested hybrid Vite build. Previous live static frontend and all personal pool data backed up prior to swapping published assets.
- Production HTTP 200 commercial API, root, NFL scores, Survivor current and lazy upload component; legacy Streamlit Survivor HTTP 200. All unauthenticated manager/proxy endpoints return 401. Before/after byte equality confirmed for personal Survivor state and 1,811-pick existing global pool ledger.
- No manager-linked-account end-to-end preview/confirm has yet run on production, because no manager identity has been assigned; only sandbox confirms were tested. Do not claim this last step complete until an authorized manager signs in.
