"""CFB archive keeps every real data/odds change, not derived-clock duplicates."""
import csv
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from cfb_live.decision import archive_cfb_decisions as archive
from cfb_live.decision.cfb_incremental_ledger_index import scan,latest_source_rows_if_complete


def row(game,selection,price,hours):
    return {
        "game_key":game,
        "schedule_event_id":"400000000",
        "market_canonical":"MONEYLINE",
        "selection_canonical":selection,
        "line":"",
        "sportsbook_count":"5",
        "provider_count":"2",
        "median_price_american":str(price),
        "evidence_score":"76.2",
        "context_stage":"RESEARCH_READY",
        "decision":"QUALIFIED_RESEARCH",
        "hours_to_start":str(hours),
    }


def create_source(path,items):
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(items[0]))
        w.writeheader()
        w.writerows(items)


def load_ledger(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


class TestClockOnlySourceChangePreservation(unittest.TestCase):
    def test_clock_only_changes_skipped_when_previous_verified(self):
        prev={
            k:"" for k in archive.FIELDS
        }
        prev.update({
            "lane":"GAME","recommendation_key":"f"*64,"game_key":"G","market":"MONEYLINE",
            "selection":"AAA","decision":"WATCH",
            "payload_json":json.dumps({"hours_to_start":"18","median_price_american":"-110","decision":"WATCH"}),
        })
        nextrow={**prev,"snapshot_at":"later","bundle_hash":"another",
                 "payload_json":json.dumps({"hours_to_start":"17.8","median_price_american":"-110","decision":"WATCH"})}
        self.assertTrue(archive.redundant_clock_only_observation(prev,nextrow))

    def test_price_and_decision_change_never_discarded(self):
        prev=dict.fromkeys(archive.FIELDS,"")
        prev.update({"lane":"GAME","payload_json":json.dumps({"hours_to_start":"12","median_price_american":"-115"})})
        current={**prev,"payload_json":json.dumps({"hours_to_start":"11.8","median_price_american":"-120"})}
        self.assertFalse(archive.redundant_clock_only_observation(prev,current))
        current={**prev,"decision":"PROMOTED"}
        self.assertFalse(archive.redundant_clock_only_observation(prev,current))
        self.assertFalse(archive.redundant_clock_only_observation(None,prev))

    def test_invalid_old_payload_must_not_be_skipped(self):
        a=dict.fromkeys(archive.FIELDS,"")
        b=dict(a)
        a["payload_json"]="{broken-json"
        b["payload_json"]=json.dumps({"hours_to_start":"17"})
        self.assertFalse(archive.redundant_clock_only_observation(a,b))

    def test_full_archive_preserves_old_raw_prefix_and_only_appends_real_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            decisions=root/"CFB_GAME_DECISIONS.csv"
            ledger=root/"original_history.csv"
            latest=root/"latest.json"
            snaps=root/"snapshots"
            create_source(decisions,[
                row("2026-10-10|1|2","AAA",-110,12),
                row("2026-10-10|3|4","BBB",-125,12),
            ])
            substitutions={
                "ROOT":root,"DEC":root,"HIST":root,"SNAPS":snaps,
                "LEDGER":ledger,"LATEST":latest,
                "SOURCES":{"GAME":decisions},
            }
            with ExitStack() as stack:
                for name,value in substitutions.items():
                    stack.enter_context(mock.patch.object(archive,name,value))
                stack.enter_context(mock.patch.object(
                    archive,"latest_source_rows_if_complete",
                    side_effect=ValueError("CFB_COMPLETE_SOURCE_INDEX_MISSING"),
                ))
                archive.main()
            original=ledger.read_bytes()
            prior=load_ledger(ledger)
            self.assertEqual(len(prior),2)
            previous={v["recommendation_key"]:v for v in prior}
            create_source(decisions,[
                row("2026-10-10|1|2","AAA",-110,11.8),
                row("2026-10-10|3|4","BBB",-130,11.8),
            ])
            with ExitStack() as stack:
                for name,value in substitutions.items():
                    stack.enter_context(mock.patch.object(archive,name,value))
                stack.enter_context(mock.patch.object(
                    archive,"latest_source_rows_if_complete",
                    return_value=previous,
                ))
                archive.main()
            final=load_ledger(ledger)
            self.assertEqual(len(final),3)
            self.assertTrue(ledger.read_bytes().startswith(original))
            meta=json.loads(latest.read_text())
            self.assertEqual(meta["derived_clock_only_rows_not_repeated"],1)
            self.assertEqual(meta["original_recommendation_rows_appended"],1)
            self.assertFalse(meta["old_raw_source_history_rewritten_or_truncated"])
            self.assertEqual(meta["source_index_verification"],"VERIFIED_COMPLETE_SOURCE_INDEX_CLOCK_ONLY_DELTA_GUARD")
            self.assertEqual(len(list(snaps.iterdir())),2)

    def test_source_if_index_caught_up_returns_unmodified_original(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source=root/"original.csv";idx=root/"index.sqlite3"
            with source.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=archive.FIELDS)
                w.writeheader()
                rowdata=dict.fromkeys(archive.FIELDS,"")
                rowdata.update(snapshot_at="2026-10-09T04:00:00+00:00",
                               recommendation_key="e"*64,lane="GAME",
                               payload_json=json.dumps({"hours_to_start":"12"}))
                w.writerow(rowdata)
            before=source.read_bytes()
            scan(source=source,index=idx,max_bytes=100000)
            x=latest_source_rows_if_complete(source=source,index=idx)
            self.assertEqual(len(x),1)
            self.assertEqual(source.read_bytes(),before)
            with source.open("a") as f:f.write("unindexed additional source bytes")
            with self.assertRaisesRegex(ValueError,"NOT_FULLY_CAUGHT_UP"):
                latest_source_rows_if_complete(source=source,index=idx)


if __name__=="__main__":unittest.main()
