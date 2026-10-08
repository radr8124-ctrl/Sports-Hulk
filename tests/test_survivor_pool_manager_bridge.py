"""Pool preview/confirm is fail-closed and preserves existing personal picks."""
from __future__ import annotations

import base64
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from commercial_web import survivor_pool_bridge as bridge
from nfl_live import survivor_pool_upload as upload


def payload(raw: bytes, name: str, action="preview", **extra):
    return {
        "action": action,
        "filename": name,
        "base64": base64.b64encode(raw).decode(),
        **extra,
    }


class PoolManagerImportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.base = self.root / "nfl_live/survivor_pool"
        self.raw = self.base / "raw"
        self.derived = self.base / "derived"
        self.snapshots = self.base / "snapshots"
        self.personal = self.root / "nfl_live/derived/SURVIVOR_ENTRIES.json"
        self.personal.parent.mkdir(parents=True)
        self.initial = {
            "active": "ANNIE G 01",
            "pool_current_week": 5,
            "entries": {
                "ANNIE G 01": {
                    "status": "ALIVE",
                    "current_week": 5,
                    "used_teams": ["Minnesota Vikings"],
                    "week_4": {
                        "entry_result": "WIN",
                        "picks": [{"team": "Minnesota Vikings", "result": "WIN"}],
                    },
                    "week_5": {"entry_result": "OPEN", "picks": [], "submitted": False},
                },
            },
        }
        self.personal.write_text(json.dumps(self.initial))
        up = patch.multiple(
            upload, ROOT=self.root, BASE=self.base, RAW=self.raw,
            DERIVED=self.derived, SNAPSHOTS=self.snapshots,
        )
        br = patch.object(bridge, "ROOT", self.root)
        up.start()
        br.start()
        self.addCleanup(up.stop)
        self.addCleanup(br.stop)

    def test_read_only_csv_preview_does_not_create_pool_state(self):
        sample = b"Entry,Week 5\nAlex Smith,KC\nAlex Smith,SF\n"
        previous = self.personal.read_bytes()
        preview = bridge.process(payload(sample, "week5.csv"))
        self.assertEqual(preview["status"], "PREVIEW_READY")
        self.assertEqual(preview["entry_count"], 2)
        self.assertEqual(preview["pick_rows"], 2)
        self.assertEqual(preview["duplicate_ticket_instances"], 1)
        self.assertEqual(preview["pool_week_before"], 5)
        self.assertFalse(self.base.exists())
        self.assertEqual(self.personal.read_bytes(), previous)

    def test_explicit_confirm_accepts_exact_file_without_overwriting_week4_win(self):
        raw = b"Entry,Week 5\nAlex Smith,KC\nAlex Smith,SF\n"
        prev = bridge.process(payload(raw, "week5.csv"))
        imported = bridge.process(payload(
            raw, "week5.csv", action="confirm",
            expected_sha256=prev["sha256"],
            pool_week_before=prev["pool_week_before"],
            official_source_before_sha256=prev["official_source_before_sha256"],
        ))
        self.assertEqual(imported["status"], "IMPORTED")
        self.assertEqual(imported["entry_count"], 2)
        self.assertEqual(imported["weekly_pick_rows"], 2)
        after = json.loads(self.personal.read_text())
        self.assertEqual(
            after["entries"]["ANNIE G 01"]["week_4"],
            self.initial["entries"]["ANNIE G 01"]["week_4"],
        )
        self.assertEqual(
            after["entries"]["ANNIE G 01"]["used_teams"],
            ["Minnesota Vikings"],
        )
        self.assertEqual(after["entries"]["ANNIE G 01"]["week_5"]["picks"], [])
        self.assertTrue((self.derived / "SURVIVOR_POOL_LEDGER.csv").exists())
        second = bridge.process(payload(
            raw, "week5.csv", action="confirm",
            expected_sha256=prev["sha256"], pool_week_before=5,
            official_source_before_sha256=sha256(
                (self.derived/"LATEST_OFFICIAL_POOL.json").read_bytes()
            ).hexdigest(),
        ))
        self.assertEqual(second["status"], "ALREADY_IMPORTED")

    def test_week4_old_sheet_rejected_against_active_week5(self):
        old = b"Entry,Week 4\nAlex Smith,KC\n"
        prior = self.personal.read_bytes()
        with self.assertRaisesRegex(ValueError, "cannot replace the active Week 5"):
            bridge.process(payload(old, "week4.csv"))
        self.assertEqual(prior, self.personal.read_bytes())
        self.assertFalse(self.derived.exists())

    def test_mismatched_file_after_preview_rejected_without_import(self):
        before = b"Entry,Week 5\nAlex Smith,KC\n"
        after = b"Entry,Week 5\nAlex Smith,SF\n"
        prev = bridge.process(payload(before, "week5.csv"))
        with self.assertRaisesRegex(ValueError, "file changed"):
            bridge.process(payload(
                after, "week5.csv", action="confirm",
                expected_sha256=prev["sha256"],
                pool_week_before=5,
                official_source_before_sha256=prev["official_source_before_sha256"],
            ))
        self.assertFalse(self.derived.exists())

    def test_confirm_fails_when_current_pool_fingerprint_changed(self):
        raw = b"Entry,Week 5\nAlex Smith,KC\n"
        prev = bridge.process(payload(raw, "week5.csv"))
        self.derived.mkdir(parents=True)
        (self.derived / "LATEST_OFFICIAL_POOL.json").write_text('{"updated":true}')
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            bridge.process(payload(
                raw, "week5.csv", action="confirm",
                expected_sha256=prev["sha256"],
                pool_week_before=5,
                official_source_before_sha256=prev["official_source_before_sha256"],
            ))

    def test_preview_cannot_be_confirmed_without_expected_sha(self):
        raw = b"Entry,Week 5\nAlex Smith,KC\n"
        with self.assertRaisesRegex(ValueError, "Preview the pool sheet"):
            bridge.process(payload(raw, "week5.csv", action="confirm"))

    def test_disallowed_files_and_path_traversal_are_rejected(self):
        for filename in ("../week5.csv", "week5.xls", ".hidden.csv", "week5.exe"):
            with self.subTest(filename=filename):
                with self.assertRaises(ValueError):
                    bridge.decode_pool_file(payload(b"whatever", filename))
        with self.assertRaisesRegex(ValueError, "valid PDF"):
            bridge.decode_pool_file(payload(b"garbage", "sample.pdf"))
        with self.assertRaisesRegex(ValueError, "valid XLSX"):
            bridge.decode_pool_file(payload(b"garbage", "sample.xlsx"))

    def test_no_pool_update_on_invalid_base64_or_abusive_size(self):
        with self.assertRaisesRegex(ValueError, "encoding"):
            bridge.decode_pool_file({
                "filename": "week5.csv", "base64": "bad!notbase64"
            })
        with self.assertRaisesRegex(ValueError, "too large"):
            bridge.decode_pool_file({
                "filename": "week5.csv", "base64": "A" * 8_000_000
            })


if __name__ == "__main__":
    unittest.main()
