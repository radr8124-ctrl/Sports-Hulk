# Survivor duplicate pool ticket import acceptance

Date: 2026-10-08 UTC

- Original wide CSV parser silently collapsed two separate tickets with the same Entry name into one entry, losing the second row. Original long-format rows with the same name intentionally grouped as a single ticket spanning weeks.
- PDF and wide CSV/XLSX imports now retain repeated-name tickets under unique stable imported entry labels with source name recorded. The first ticket retains its original name; additional identical names carry [ENTRY 2], [ENTRY 3], etc. A preexisting identifier collision is safely avoided.
- Long-format Excel/CSV with an explicit Ticket ID or Entry ID now groups each ticket separately while still consolidating weekly picks for that ticket. Long-format without IDs preserves the existing one-entry-per-name semantics; this remains ambiguous if an actual pool contains repeated names without ticket identifiers.
- The existing Streamlit whole-pool import preview now announces how many repeated-name tickets were kept separately. Already-imported and confirmation banners correctly say pool file rather than PDF when uploading Excel/CSV.
- Current real nine-page Week 4 PDF still parses into exactly 364 entries and 1,811 weekly picks with no regression and zero new duplicate clones.
- Ten new read-only/sandbox tests PASS: wide CSV duplicates, XLSX doubles, long rows as one entry, long rows with distinct Ticket IDs, duplicate lines in PDF, explicit numbered entry names, generated-name collisions, no mutation on preview, legacy XLS validation, and confirmed whole-pool import into TEMPORARY sandbox preserving the previously saved Week 4 Vikings WIN, used teams and pool survival state.
- No live source was imported/replaced during testing. The parser module, Streamlit UI messages and both GitHub CI test gates were updated. GitHub CI requires pypdf alongside already installed numpy/pandas/pyarrow.
- Safety release: back up current importer and user personal Survivor state, merge source-only, run real PDF read-only acceptance, confirm personal Week 4 bytes unchanged and leave imported pool snapshot untouched.
