# Survivor duplicate-ticket import — live source acceptance

UTC date: 2026-10-08
Source revision: 17cd611
Backup: .deploy_backups/survivor_duplicate_import_20261008T023415Z
Recovery branch: backup/pre-survivor-duplicate-20261008T023415Z

- Existing PDF, XLSX and CSV parsing now preserves multiple pool tickets entered under the exact same participant name in wide-format source rows and PDF entry lines. Long-form week rows remain grouped per ticket; when explicit Ticket ID or Entry ID exists, repeated participant names with different IDs remain separate tickets.
- The Streamlit Import Full Pool preview now labels duplicate-name tickets separately and uses the generic term pool file for PDF, XLSX and CSV.
- Live production source-only git fast-forward merged with zero conflicting dirty source paths and with all other frontend/collector work untouched.
- The original user's Survivor entry JSON and 1,811-row previously imported full-pool ledger remained byte-for-byte identical. This code release did not execute any new user pool import or modify previously settled Vikings outcomes.
- Production read-only parsing of the saved 9-page Week 4 PDF returned 364 original entries and exactly 1,811 weekly pick rows, with zero extraneous duplicates.
- Ten new tests passed, including CSV/XLSX and PDF duplicates and a temp-directory end-to-end import that preserves a saved historical Week 4 Vikings WIN and member used teams.
- Commercial Sports HULK and legacy Streamlit Survivor health HTTP 200.
- The main commercial website still needs the whole-pool upload/confirmation UI, account-owner authorization and member Week 5 pick editor. The legacy Streamlit upload/preview/confirm workflow already exists. Neither a new sheet nor a new personal pick has been accepted as pool-submitted during this pass.
