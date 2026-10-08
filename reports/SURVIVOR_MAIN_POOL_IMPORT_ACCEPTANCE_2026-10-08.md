# Main Survivor tab — manager-only official pool upload acceptance

Source-only acceptance, 2026-10-08 UTC

- Adds a compact manager-only PDF/XLSX/CSV upload with read-only Preview then explicitly confirmed Import. Duplicate-name tickets are separate entries. Preview shows actual entry/pick counts, source week, duplicate ticket count, and sample entries; no automatic import.
- Uses an authenticated Insforge account and server-assigned survivor_pool_manager role or explicit server-only SURVIVOR_POOL_ADMIN_IDS or SURVIVOR_POOL_ADMIN_EMAILS allowlist. User-provided client metadata cannot grant permission; unauthorized requests return 401/403. No manager is currently configured through .env.local, so access remains fail-closed until explicitly provisioned.
- One-time random preview token is bound to the authenticated manager, 15-minute expiration, exact SHA-256 source and prior global snapshot. Confirm re-parses the file, rechecks both prior source and active pool week, and refuses stale older-week imports.
- Python bridge validates file type, encoded content, maximum 5 MB and XLSX uncompressed size. The existing backed-up, atomic whole-pool import is used only on the confirmed route. Personal historical WIN/LOSS picks and used-team state remain preserved by the existing importer's rules.
- Eight new isolated bridge tests PASS, five manager authorization tests PASS, 12 existing duplicate import and 10 Week 5 saver tests PASS; full commercial Node suite 86 PASS and Vite production build PASS with the user's uncommitted PropsV2Panel refactor included.
- Read-only check of real previously imported 9-page Week 4 PDF correctly rejected as older than the current live Week 5 without changing the private Survivor JSON or pool ledger.
- No manager import was executed on live user data during acceptance. Rollback and user UI edits must be preserved at source merge/deploy. One authorized manager account must be provisioned before the upload controls become visible to that person.
