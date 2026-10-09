"""CFB grade path must use fully indexed original history, never 8GB pandas."""
from contextlib import ExitStack
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import pandas as pd

from cfb_live.decision import cfb_incremental_ledger_index as idx
from cfb_live.decision import grade_cfb_recommendations as grader

ROOT=Path(__file__).resolve().parents[1]


def original_rows():
    src=ROOT/"cfb_live/decision/history/CFB_RECOMMENDATION_EPISODES.csv"
    with src.open(newline="") as f:
        reader=csv.DictReader(f)
        return reader.fieldnames, next(reader)


def write_fixture(path, header, rows, mode="w"):
    with path.open(mode,newline="") as f:
        writer=csv.DictWriter(f,fieldnames=header)
        if mode=="w":writer.writeheader()
        writer.writerows(rows)


class TestCFBIndexedGrader(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=Path(self.temp.name)
        self.src=self.base/"original_source.csv"
        self.index=self.base/"CFB_RECOMMENDATION_LATEST_INDEX.sqlite3"
        self.cols,self.row=original_rows()
        write_fixture(self.src,self.cols,[self.row])

    def tearDown(self):self.temp.cleanup()

    def scoped(self):
        stack=ExitStack()
        for name,path in {
            "LEDGER":self.src,"INDEX":self.index,
            "EPISODES":self.base/"episodes.csv",
            "GRADED":self.base/"graded.csv",
            "SIGNALS":self.base/"signals.csv",
            "OUTCOMES":self.base/"outcomes.csv",
            "SUMMARY":self.base/"summary.json",
        }.items():
            stack.enter_context(mock.patch.object(grader,name,path))
        stack.enter_context(mock.patch.object(grader,"load_games",return_value=pd.DataFrame()))
        return stack

    def test_same_key_updated_but_all_original_rows_retained(self):
        changed={**self.row,"snapshot_at":"2026-10-09T02:00:00+00:00","decision":"NEW_PENDING"}
        write_fixture(self.src,self.cols,[changed],mode="a")
        indexed=idx.scan(source=self.src,index=self.index,max_bytes=100000)
        self.assertEqual(indexed["total_processed_raw_rows"],2)
        with self.scoped():
            grader.main()
        j=json.loads((self.base/"summary.json").read_text())
        f=pd.read_csv(self.base/"episodes.csv")
        self.assertEqual(j["ledger_rows"],2)
        self.assertEqual(j["unique_recommendations"],1)
        self.assertEqual(f.loc[0,"decision"],"NEW_PENDING")
        self.assertFalse(j["automatic_model_adjustment"])

    def test_stale_index_cannot_rewrite_existing_output(self):
        idx.scan(source=self.src,index=self.index,max_bytes=100000)
        (self.base/"summary.json").write_text("PRESERVED_ORIGINAL_REPORT")
        changed={**self.row,"snapshot_at":"2026-10-09T02:00:00+00:00"}
        write_fixture(self.src,self.cols,[changed],mode="a")
        with self.scoped():
            with self.assertRaisesRegex(ValueError,"NOT_FULLY_CAUGHT_UP"):
                grader.main()
        self.assertEqual((self.base/"summary.json").read_text(),"PRESERVED_ORIGINAL_REPORT")
        self.assertFalse((self.base/"episodes.csv").exists())

    def test_learning_timer_guards_and_indexes_before_grading(self):
        script=(ROOT/"cfb_live/decision/run_cfb_learning_postrefresh.sh").read_text()
        self.assertIn("cfb_incremental_ledger_index --max-megabytes 128",script)
        self.assertLess(script.index("archive_cfb_decisions.py"),script.index("cfb_incremental_ledger_index"))
        self.assertLess(script.index("cfb_incremental_ledger_index"),script.index("grade_cfb_recommendations"))
        self.assertIn("CFB LEARNING INCOMPLETE",script)
        self.assertIn("INDEX RC:",script)
        self.assertNotIn("536870912",script)

    def test_grader_never_reads_full_ledger_with_pandas(self):
        code=(ROOT/"cfb_live/decision/grade_cfb_recommendations.py").read_text()
        self.assertIn("read_latest_complete(source=LEDGER,index=INDEX)",code)
        self.assertNotIn("ledger = read_csv(",code)


if __name__=="__main__":
    unittest.main()
