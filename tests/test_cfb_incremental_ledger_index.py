"""Resumable 8GB CFB ledger index: never drop old evidence for performance."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from cfb_live.decision.cfb_incremental_ledger_index import (
    HEADER, scan, read_latest_complete, parse_line, INDEX,
)


def record(key: str,stamp:str,decision:str="WATCH",side:str="HOME"):
    values=dict.fromkeys(HEADER,"")
    values.update(
        snapshot_at=stamp,bundle_hash="1"*64,lane="GAME",
        recommendation_key=key,source_file="CFB_GAME_DECISIONS.csv",
        game_key="2026-10-10|1|2",schedule_event_id="400000001",
        market="MONEYLINE",selection=side,decision=decision,
        score="60",context_stage="RESEARCH_READY",
        payload_json=json.dumps({"decision":decision,"selection":side}),
    )
    return values


def append(path: Path,items:list[dict], *,header:bool=False):
    with path.open("a",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=HEADER)
        if header:writer.writeheader()
        writer.writerows(items)


class TestCFBResumableIndex(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=Path(self.temp.name)
        self.source=self.base/"preserved.csv"
        self.index=self.base/"index.sqlite3"
        append(self.source,[
            record("a"*64,"2026-10-03T02:00:00+00:00","OLD"),
            record("b"*64,"2026-10-03T03:00:00+00:00","BASE"),
        ],header=True)

    def tearDown(self):self.temp.cleanup()

    def test_complete_index_retains_only_latest_per_key_but_counts_all_original(self):
        append(self.source,[
            record("a"*64,"2026-10-04T02:00:00+00:00","NEW")
        ])
        before=hashlib.sha256(self.source.read_bytes()).hexdigest()
        ret=scan(source=self.source,index=self.index,max_bytes=100000)
        self.assertTrue(ret["full_raw_ledger_scanned"])
        self.assertEqual(ret["total_processed_raw_rows"],3)
        frame,total=read_latest_complete(source=self.source,index=self.index)
        self.assertEqual(total,3)
        self.assertEqual(len(frame),2)
        self.assertEqual(frame.set_index("recommendation_key").loc["a"*64,"decision"],"NEW")
        self.assertEqual(before,hashlib.sha256(self.source.read_bytes()).hexdigest())

    def test_incremental_resumption_including_after_append(self):
        out=scan(source=self.source,index=self.index,max_bytes=220,batch_size=1)
        self.assertFalse(out["full_raw_ledger_scanned"])
        with self.assertRaisesRegex(ValueError,"NOT_FULLY_CAUGHT_UP"):
            read_latest_complete(source=self.source,index=self.index)
        out=scan(source=self.source,index=self.index,max_bytes=100000,batch_size=1)
        self.assertTrue(out["full_raw_ledger_scanned"])
        append(self.source,[record("c"*64,"2026-10-05T01:00:00+00:00","LAST")])
        with self.assertRaisesRegex(ValueError,"NOT_FULLY_CAUGHT_UP"):
            read_latest_complete(source=self.source,index=self.index)
        out=scan(source=self.source,index=self.index,max_bytes=100000,batch_size=1)
        self.assertTrue(out["full_raw_ledger_scanned"])
        frame,count=read_latest_complete(source=self.source,index=self.index)
        self.assertEqual(count,3)
        self.assertEqual(len(frame),3)

    def test_prior_bytes_tampered_detected(self):
        scan(source=self.source,index=self.index,max_bytes=100000)
        raw=self.source.read_bytes()
        self.assertIn(b"BASE",raw)
        self.source.write_bytes(raw.replace(b"BASE",b"FAKE",1))
        with self.assertRaisesRegex(ValueError,"CHANGED"):
            scan(source=self.source,index=self.index,max_bytes=100000)

    def test_source_inode_replacement_rejected_even_same_contents(self):
        scan(source=self.source,index=self.index,max_bytes=100000)
        moved=self.base/"new.csv"
        moved.write_bytes(self.source.read_bytes())
        self.source.unlink()
        moved.rename(self.source)
        with self.assertRaisesRegex(ValueError,"CHANGED"):
            scan(source=self.source,index=self.index,max_bytes=100000)

    def test_truncation_refused(self):
        scan(source=self.source,index=self.index,max_bytes=100000)
        self.source.write_bytes(self.source.read_bytes()[:180])
        with self.assertRaisesRegex(ValueError,"CHANGED|TRUNCATED"):
            scan(source=self.source,index=self.index,max_bytes=100000)

    def test_malformed_key_refused(self):
        row=record("short","2026-10-03T02:00:00+00:00")
        with tempfile.NamedTemporaryFile(mode="w+",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=HEADER)
            writer.writerow(row)
            f.flush()
            with open(f.name,"rb") as src:
                with self.assertRaisesRegex(ValueError,"INVALID_RECOMMENDATION_KEY"):
                    parse_line(src.readline())

    def test_partial_appended_row_not_indexed(self):
        scan(source=self.source,index=self.index,max_bytes=100000)
        with self.source.open("ab") as f:f.write(b"2026-10-05T03:20")
        report=scan(source=self.source,index=self.index,max_bytes=100000)
        self.assertFalse(report["full_raw_ledger_scanned"])
        self.assertEqual(report["new_bytes_indexed"],0)

    def test_index_never_uses_shortcut_to_skip_source_rows(self):
        out=scan(source=self.source,index=self.index,max_bytes=100000)
        self.assertTrue(out["full_raw_ledger_scanned"])
        self.assertEqual(out["total_processed_raw_rows"],2)


if __name__=="__main__":unittest.main()
