"""Survivor pool import must treat duplicate tickets as separate entries."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest
import zipfile

from nfl_live import survivor_pool_upload as upload


def workbook_bytes():
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    pkg = "http://schemas.openxmlformats.org/package/2006/relationships"
    book = (f'<workbook xmlns="{main}" xmlns:r="{rel}">'
            '<sheets><sheet name="Pool" sheetId="1" r:id="rId1"/></sheets></workbook>')
    links = (f'<Relationships xmlns="{pkg}">'
             '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
    data = [
        ["Entry", "Week 1", "Week 2"],
        ["Alex Smith", "KC", "BUF"],
        ["Alex Smith", "SF", "NE"],
    ]
    xml = f'<worksheet xmlns="{main}"><sheetData>'
    for r_index, values in enumerate(data, start=1):
        xml += f'<row r="{r_index}">'
        for col, val in zip("ABC", values):
            xml += (f'<c r="{col}{r_index}" t="inlineStr"><is><t>'
                    f'{val}</t></is></c>')
        xml += '</row>'
    xml += '</sheetData></worksheet>'
    stream = BytesIO()
    with zipfile.ZipFile(stream, mode="w") as out:
        out.writestr("xl/workbook.xml", book)
        out.writestr("xl/_rels/workbook.xml.rels", links)
        out.writestr("xl/worksheets/sheet1.xml", xml)
    return stream.getvalue()


class DuplicateSurvivorTicketsTests(unittest.TestCase):
    def test_import_paths_follow_current_checkout_not_fixed_vps_location(self):
        from nfl_live import survivor_pool_import as old_importer
        expected_root = Path(upload.__file__).resolve().parents[1]
        self.assertEqual(upload.ROOT, expected_root)
        self.assertEqual(old_importer.ROOT, expected_root)
        self.assertEqual(upload.DERIVED, expected_root / "nfl_live/survivor_pool/derived")
        self.assertEqual(old_importer.RAW, upload.RAW)

    def test_import_module_does_not_create_pool_directories(self):
        # This was the GitHub CI failure: import had tried to make a directory
        # under /home/ubuntu instead of running from the GitHub checkout.
        import subprocess
        import sys
        root = Path(upload.__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as home:
            before = (root / "nfl_live/survivor_pool").exists()
            completed = subprocess.run(
                [sys.executable, "-c",
                 "from nfl_live import survivor_pool_import, survivor_pool_upload"],
                cwd=root, env={"PYTHONPATH": str(root), "HOME": home},
                capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual((root / "nfl_live/survivor_pool").exists(), before)

    def test_wide_csv_same_name_represents_two_tickets(self):
        raw = b"Entry,Week 1,Week 2\nAlex Smith,KC,BUF\nAlex Smith,SF,NE\n"
        output = upload.parse_upload(raw, "pool.csv")
        self.assertEqual(output["entry_count"], 2)
        self.assertEqual(output["duplicate_ticket_instances"], 1)
        self.assertEqual(output["pick_rows"], 4)
        self.assertEqual([v["entry_name"] for v in output["entries"]],
                         ["Alex Smith", "Alex Smith [ENTRY 2]"])
        self.assertEqual(output["entries"][1]["source_entry_name"], "Alex Smith")
        self.assertEqual(output["entries"][1]["participant"], "Alex Smith")

    def test_wide_xlsx_same_name_represents_two_tickets(self):
        output = upload.parse_upload(workbook_bytes(), "pool.xlsx")
        self.assertEqual(output["entry_count"], 2)
        self.assertEqual(output["duplicate_ticket_instances"], 1)
        self.assertEqual(output["pick_rows"], 4)
        self.assertEqual(output["meta"]["format"], "XLSX")
        self.assertEqual(output["entries"][1]["entry_name"], "Alex Smith [ENTRY 2]")

    def test_long_csv_multiple_week_rows_group_into_one_ticket(self):
        raw = b"Entry,Week,Team\nAlex Smith,1,KC\nAlex Smith,2,BUF\n"
        output = upload.parse_upload(raw, "week_rows.csv")
        self.assertEqual(output["entry_count"], 1)
        self.assertEqual(output["pick_rows"], 2)
        self.assertEqual(output["duplicate_ticket_instances"], 0)

    def test_long_csv_ticket_ids_keep_same_name_distinct(self):
        raw = (b"Entry,Ticket ID,Week,Team\nAlex Smith,001,1,KC\n"
               b"Alex Smith,002,1,SF\nAlex Smith,001,2,BUF\nAlex Smith,002,2,NE\n")
        output = upload.parse_upload(raw, "week_rows.csv")
        self.assertEqual(output["entry_count"], 2)
        self.assertEqual(output["pick_rows"], 4)
        self.assertEqual(output["duplicate_ticket_instances"], 1)
        self.assertEqual([len(e["picks"]) for e in output["entries"]], [2, 2])

    def test_pdf_duplicate_lines_are_distinct_tickets(self):
        class Page:
            def extract_text(self):
                return "WEEK #1\nAlex Smith KC\nAlex Smith SF"
        def parse(line, page_no):
            if line.endswith(" KC"):
                team = "Kansas City Chiefs"
            elif line.endswith(" SF"):
                team = "San Francisco 49ers"
            else:
                return None
            return {
                "entry_name": "Alex Smith", "participant": "Alex Smith",
                "entry_suffix": None, "page": page_no,
                "raw_line": line,
                "picks": [{
                    "week_position": 1,
                    "week_pick_number": 1,
                    "team": team,
                    "marker": None,
                    "raw_token": line,
                }],
            }
        with patch.object(upload, "PdfReader",
                          return_value=SimpleNamespace(pages=[Page()])), \
             patch.object(upload, "parse_entry_line", side_effect=parse):
            entries, meta = upload.parse_pdf_bytes(b"%PDF-mock")
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[1]["entry_name"], "Alex Smith [ENTRY 2]")
        self.assertEqual(meta["current_week"], 1)
        self.assertEqual(meta["current_week_required_picks"], 1)

    def test_explicit_numeric_suffixes_are_not_collapsed(self):
        raw = b"Entry,Week 1\nANNIE G 01,KC\nANNIE G 02,SF\n"
        output = upload.parse_upload(raw, "pool.csv")
        self.assertEqual(output["entry_count"], 2)
        self.assertEqual(output["duplicate_ticket_instances"], 0)
        self.assertEqual([e["entry_name"] for e in output["entries"]],
                         ["ANNIE G 01", "ANNIE G 02"])

    def test_suffixed_duplicate_name_collision_is_avoided(self):
        rows = [
            {"entry_name": "Alex Smith", "picks": []},
            {"entry_name": "Alex Smith [ENTRY 2]", "picks": []},
            {"entry_name": "Alex Smith", "picks": []},
        ]
        output = upload._preserve_duplicate_tickets(rows)
        self.assertEqual(len(output), 3)
        self.assertEqual(len({r["entry_name"] for r in output}), 3)
        self.assertEqual(output[2]["entry_name"], "Alex Smith [ENTRY 3]")

    def test_parse_only_has_no_live_state_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            snapshot = Path(folder) / "personal.json"
            snapshot.write_bytes(b'{"picks":["Minnesota Vikings"]}')
            before = snapshot.read_bytes()
            result = upload.parse_upload(
                b"Entry,Week 1\nANNIE G 01,KC\nANNIE G 01,SF\n",
                "new.csv",
            )
            self.assertEqual(result["entry_count"], 2)
            self.assertEqual(snapshot.read_bytes(), before)

    def test_confirm_import_preserves_historical_resolved_vikings_in_isolation(self):
        # All write targets are patched into a temporary sandbox. The live
        # personal Survivor state and imported pool are NEVER modified.
        import json
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            base = root / "nfl_live/survivor_pool"
            raw, derived, snapshots = (
                base / "raw", base / "derived", base / "snapshots"
            )
            for d in (raw, derived, snapshots):
                d.mkdir(parents=True, exist_ok=True)
            personal_file = root / "nfl_live/derived/SURVIVOR_ENTRIES.json"
            personal_file.parent.mkdir(parents=True, exist_ok=True)
            saved = {
                "active": "ANNIE G 01",
                "pool_current_week": 5,
                "entries": {
                    "ANNIE G 01": {
                        "status": "ALIVE",
                        "current_week": 5,
                        "used_teams": ["Minnesota Vikings"],
                        "week_4": {
                            "entry_result": "WIN",
                            "picks": [{
                                "team": "Minnesota Vikings", "result": "WIN",
                                "game_status": "FINAL: Miami Dolphins 10 - Minnesota Vikings 15",
                            }],
                        },
                        "week_5": {
                            "entry_result": "OPEN", "picks": [],
                        },
                    },
                },
            }
            personal_file.write_text(json.dumps(saved))
            preview = upload.parse_upload(
                b"Entry,Week 5\nAlex Smith,KC\nAlex Smith,SF\n",
                "week5.csv",
            )
            with patch.multiple(
                upload, ROOT=root, BASE=base,
                RAW=raw, DERIVED=derived, SNAPSHOTS=snapshots,
            ):
                result = upload.commit_preview(
                    preview, b"Entry,Week 5\nAlex Smith,KC\nAlex Smith,SF\n"
                )
            after = json.loads(personal_file.read_text())
            self.assertEqual(result["entries"], 2)
            self.assertEqual(result["ledger_rows"], 2)
            self.assertEqual(after["entries"]["ANNIE G 01"]["week_4"],
                             saved["entries"]["ANNIE G 01"]["week_4"])
            self.assertEqual(after["entries"]["ANNIE G 01"]["used_teams"],
                             ["Minnesota Vikings"])
            self.assertEqual(after["entries"]["ANNIE G 01"]["status"], "ALIVE")
            self.assertEqual(after["entries"]["ANNIE G 01"]["week_5"]["picks"], [])
            import pandas as pd
            rows = pd.read_csv(derived / "SURVIVOR_POOL_LEDGER.csv")
            self.assertEqual(len(rows), 2)
            self.assertEqual(len(set(rows.entry_name)), 2)

    def test_unsupported_legacy_xls_reports_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Save the workbook as .xlsx"):
            upload.parse_upload(b"not-xls", "old.xls")


if __name__ == "__main__":
    unittest.main()
