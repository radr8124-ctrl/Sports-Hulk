"""MLB original player ledger must preserve bytes after completed-game backfills."""
import hashlib
import tempfile
import unittest
from pathlib import Path
import csv

from intelligence_warehouse.mlb_player_history.build_mlb_player_game_history import (
    append_official_player_rows_once, LEDGER_COLUMNS
)


def player(game, player, hits):
    return {
        "gamePk": game, "officialDate": "2026-10-08", "season": 2026,
        "player_id": player, "player": "Sample Verified Player", "team": "Sample A",
        "opponent": "Sample B", "home_away": "HOME", "position": "LF",
        "group": "HITTING", "started": True, "plate_appearances": 4.0,
        "ab": 4.0, "runs": 0.0, "hits": float(hits), "doubles": 0.0,
        "triples": 0.0, "home_runs": 0.0, "rbi": 0.0, "walks": 0.0,
        "strikeouts": 1.0, "stolen_bases": 0.0, "singles": float(hits),
        "total_bases": float(hits), "hrr": float(hits)
    }


class TestProtectedMLBSourceAppend(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/"MLB_PLAYER_GAME_LEDGER.csv"

    def tearDown(self):
        self.temp.cleanup()

    def test_existing_original_bytes_survive_new_game(self):
        self.assertEqual(append_official_player_rows_once(self.path,[player(1,100,2)]),1)
        before=self.path.read_bytes()
        self.assertEqual(append_official_player_rows_once(self.path,[player(2,200,0)]),1)
        after=self.path.read_bytes()
        self.assertTrue(after.startswith(before))
        with self.path.open(newline="") as fd:
            rows=list(csv.DictReader(fd))
        self.assertEqual([(r["gamePk"],r["player_id"]) for r in rows],[("1","100"),("2","200")])

    def test_idempotent_same_official_game(self):
        r=player(1,100,2)
        append_official_player_rows_once(self.path,[r])
        before=self.path.read_bytes()
        self.assertEqual(append_official_player_rows_once(self.path,[r]),0)
        self.assertEqual(before,self.path.read_bytes())

    def test_conflicting_official_player_history_never_overwritten(self):
        append_official_player_rows_once(self.path,[player(1,100,2)])
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,"protected official player grade conflict|Protected official player grade conflict"):
            append_official_player_rows_once(self.path,[player(1,100,3)])
        self.assertEqual(before,self.path.read_bytes())

    def test_duplicate_new_game_source_refused_without_mutation(self):
        a=player(1,100,2)
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            append_official_player_rows_once(self.path,[a,a])
        self.assertFalse(self.path.exists())

    def test_unknown_schema_fields_refused(self):
        bad=player(1,100,2);bad["unverified_future_stat"]=12
        with self.assertRaisesRegex(ValueError,"Unexpected new"):
            append_official_player_rows_once(self.path,[bad])
        self.assertFalse(self.path.exists())

    def test_missing_terminal_newline_must_fail_without_touch(self):
        self.path.write_bytes(b"gamePk,player_id,group\n1,100,HITTING")
        original=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,"incomplete"):
            append_official_player_rows_once(self.path,[player(2,200,1)])
        self.assertEqual(original,self.path.read_bytes())

    def test_no_new_rows_does_not_rewrite_protected_source(self):
        self.path.write_bytes(b"gamePk,player_id,group\n1,100,HITTING\n")
        before=hashlib.sha256(self.path.read_bytes()).digest()
        self.assertEqual(append_official_player_rows_once(self.path,[]),0)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).digest(),before)


if __name__=="__main__": unittest.main()
