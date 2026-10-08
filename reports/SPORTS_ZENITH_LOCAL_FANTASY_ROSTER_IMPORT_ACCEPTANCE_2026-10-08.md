# Sports Zenith local fantasy roster import — 2026-10-08

## Why

ESPN, Yahoo and CBS authorized provider sync require separate future integration and the user chose to defer Yahoo API application. Fantasy already had a manual Rate My Team editor, but not a safe upload for simple exported player rosters. This feature enables provider-neutral CSV or TXT roster import **without** pretending to sign users into ESPN/Yahoo/CBS.

## Scope and privacy

- Add a compact `Import roster from CSV or TXT` panel within Fantasy > Season-Long > My Teams / Rate My Team. Users choose an existing CSV with `Player`, `Player Name`, `Name` or other standard player-name column heading, a one-column CSV, or a TXT file with one player per line. Excel users can save a spreadsheet as CSV first. Format support is generic, not a guarantee of every provider export schema.
- Parse text locally **in the browser**, not through a server upload. CSV quoted fields, CRLF, UTF-8 BOM, spreadsheet column layout, case-insensitive duplicate detection, and “Last, First” name format conversion (to avoid the existing manual editor splitting commas) are supported. Invalid missing headers, oversized files >256KB, oversized fields, >1,000 rows, >60 distinct players, unsafe formula-style names, unsupported extensions and unfinished quotes fail safely.
- Preview shows all extracted names and skipped/duplicate/reformatted counts. No editor state changes until a user confirms `Use these N players in editor`; **no private roster is saved** until the pre-existing authenticated `Analyze & save my team` operation. No ESPN/Yahoo/CBS password, cookies, tokens or unrelated CSV metadata is collected or sent.
- Existing manually saved leagues, existing user's uncommitted PropsV2Panel refactor and frozen Survivor/betting data remain unchanged; the import is preview-only until explicit user action.

## Acceptance

- 12 pure parser tests PASS covering generic ESPN/Yahoo/CBS-style CSV samples, TXT, BOM, quoted surname-first names, duplicates, row and file limits, invalid inputs, no private metadata leakage and no silent player truncation.
- All 135 existing+new Node tests PASS and isolated Vite production build PASS including exact current live App.jsx and PropsV2Panel.jsx UI source.
- Chromium interactions at 1365x768, 390x844, 320x568 PASS: select a hypothetical Yahoo-style CSV, preview two player names including surname-first conversion, verify editor unchanged before confirmation, apply names to editor explicitly, reject an unsupported XLS, preserve applied local roster, make **zero** calls to authenticated Fantasy write endpoints and show no JS errors or horizontal overflow.
- No real user file uploaded or live roster data modified by test runs.
