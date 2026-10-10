"""Official MLB postseason source archive must fail closed, never overwrite."""
from __future__ import annotations
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from intelligence_warehouse.sport_cohorts.update_mlb_postseason_schedule import (
    archive_once,verify_response,SERIES_TYPES,ROOT
)

CAPTURE=ROOT/"intelligence_warehouse/sport_cohorts/sources/MLB_STATSAPI_POSTSEASON_SCHEDULE_20261010.raw.json"

class FakeResponse:
    def __init__(self,content):self.content=content
    def raise_for_status(self):pass
class FakeSession:
    def __init__(self,content):self.content=content;self.calls=0
    def get(self,*args,**kwargs):self.calls+=1;return FakeResponse(self.content)


class ImmutableMLBPostseasonScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=CAPTURE.read_bytes()
        cls.sha=hashlib.sha256(cls.raw).hexdigest()

    @classmethod
    def tearDownClass(cls):
        assert hashlib.sha256(CAPTURE.read_bytes()).hexdigest()==cls.sha

    def test_original_snapshot_has_explicit_division_and_championship_codes(self):
        meta=verify_response(self.raw)
        self.assertGreaterEqual(meta["unique_game_ids"],16)
        self.assertIn("D",meta["source_game_types"])
        self.assertIn("L",meta["source_game_types"])
        self.assertTrue(set(meta["source_game_types"]).issubset(SERIES_TYPES))

    def test_incomplete_wrong_game_type_and_duplicate_id_get_quarantined(self):
        sample=json.loads(self.raw)
        for defect in ["unknown_type","duplicate","no_team","missing_all_dates"]:
            bad=copy.deepcopy(sample)
            if defect=="unknown_type":bad["dates"][0]["games"][0]["gameType"]="R"
            elif defect=="duplicate":bad["dates"][0]["games"].append(copy.deepcopy(bad["dates"][0]["games"][0]))
            elif defect=="no_team":bad["dates"][0]["games"][0]["teams"].pop("home")
            else:bad["dates"]=[]
            with self.subTest(defect=defect):
                with self.assertRaises(ValueError):
                    verify_response(json.dumps(bad).encode("utf-8"))

    def test_existing_capture_reused_without_network(self):
        session=FakeSession(b"unsafe")
        out=archive_once(root=ROOT,now=datetime(2026,10,10,16,tzinfo=timezone.utc),session=session)
        self.assertEqual(out["status"],"EXISTING_SOURCE_UNCHANGED")
        self.assertEqual(out["sha256"],self.sha)
        self.assertEqual(session.calls,0)

    def test_daily_original_capture_files_do_not_overwrite_one_another(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            session=FakeSession(self.raw)
            oct10=datetime(2026,10,10,17,tzinfo=timezone.utc)
            oct11=datetime(2026,10,11,17,tzinfo=timezone.utc)
            first=archive_once(root=root,now=oct10,session=session)
            second=archive_once(root=root,now=oct11,session=session)
            older=root/first["path"]
            before=older.read_bytes()
            repeat=archive_once(root=root,now=oct10,session=session)
            self.assertEqual(session.calls,2)
            self.assertEqual(first["status"],"NEW_ORIGINAL_SOURCE_ARCHIVED")
            self.assertEqual(repeat["status"],"EXISTING_SOURCE_UNCHANGED")
            self.assertNotEqual(first["path"],second["path"])
            self.assertEqual(older.read_bytes(),before)
            self.assertEqual(hashlib.sha256(older.read_bytes()).hexdigest(),first["sha256"])

    def test_bad_network_payload_does_not_publish_a_new_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            session=FakeSession(b"not valid")
            with self.assertRaises(ValueError):
                archive_once(root=root,now=datetime(2026,10,12,tzinfo=timezone.utc),session=session)
            self.assertFalse(list(root.rglob("*.raw.json")))

if __name__=="__main__":
    unittest.main()
