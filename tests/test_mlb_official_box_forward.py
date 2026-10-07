"""MLB forward results require exact historical player IDs and official finals."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from intelligence_warehouse.betting_v2 import mlb_official_box_forward as mlb
from intelligence_warehouse.betting_v2 import build_prop_v2_forward as props

EVENT = "77937117-5d59-43ce-85a3-11931bb451d8"
SCHEDULE = {
    "dates": [{
        "date": "2026-10-05",
        "games": [{
            "gamePk": 849834, "gameDate": "2026-10-05T21:00:00Z",
            "gameNumber": 1, "gameType": "D",
            "status": {"detailedState": "Final"},
            "teams": {
                "away": {"team": {"id": 145, "name": "Chicago White Sox"}},
                "home": {"team": {"id": 114, "name": "Cleveland Guardians"}},
            },
        }],
    }],
}
BOX = {
    "gameData": {
        "status": {"abstractGameState": "Final", "detailedState": "Final"},
        "game": {"pk": 849834, "type": "D", "season": "2026"},
        "datetime": {"dateTime": "2026-10-05T21:00:00Z"},
        "teams": {
            "away": {"id": 145, "name": "Chicago White Sox"},
            "home": {"id": 114, "name": "Cleveland Guardians"},
        },
    },
    "liveData": {
        "linescore": {
            "teams": {"away": {"runs": 4}, "home": {"runs": 3}},
        },
        "boxscore": {
            "teams": {
                "away": {
                    "batters": [643217], "pitchers": [],
                    "players": {"ID643217": {
                        "person": {"id": 643217, "fullName": "Andrew Benintendi"},
                        "stats": {"batting": {
                            "hits": 2, "runs": 1, "rbi": 1, "doubles": 1,
                            "triples": 0, "homeRuns": 0, "baseOnBalls": 0,
                            "stolenBases": 1, "totalBases": 3,
                        }, "pitching": {}},
                    }},
                },
                "home": {"batters": [], "pitchers": [], "players": {}},
            },
        },
    },
}
SOURCE_ROW = {
    "event_id": EVENT,
    "start": "2026-10-05 21:00:00+00:00",
    "away_team": "Chicago White Sox",
    "home_team": "Cleveland Guardians",
    "player_id": "643217", "player": "Andrew Benintendi",
    "player_key": "andrewbenintendi", "team": "Chicago White Sox",
}
ENTRY = {
    "event_type": "ENTRY", "forward_key": "frozen-mlb-one",
    "sport": "MLB", "lane": "PROP", "model_version": "TEST_FORWARD_1",
    "event_id": EVENT, "game_key": "",
    "event_start": "2026-10-05 21:00:00+00:00",
    "captured_at": "2026-10-05T18:00:00+00:00",
    "player_key": "andrewbenintendi",
    "market": "PLAYER_TOTAL_HITS", "side": "OVER",
    "line": 1.5, "grade": "PENDING",
}


def csvfile(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class Reply:
    def __init__(self, value, status=200):
        self.value, self.status = value, status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError("OFFICIAL_HTTP_ERROR")

    def json(self):
        return self.value


class FakeSession:
    def __init__(self, schedule=None, boxes=None):
        self.schedule = json.loads(json.dumps(SCHEDULE)) if schedule is None else schedule
        self.boxes = {"849834": json.loads(json.dumps(BOX))} if boxes is None else boxes
        self.calls = []

    def get(self, url, *, params=None, timeout):
        self.calls.append((url, params, timeout))
        if url == mlb.SCHEDULE_URL:
            return Reply(self.schedule)
        key = url.split("/")[-3] if url.endswith("/feed/live") else ""
        if key in self.boxes:
            return Reply(self.boxes[key])
        raise TimeoutError("NO_OFFICIAL_GAME_FEED")


class MlbOfficialBoxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.archive = self.root / "mlb_live/decision/history/snapshots/20261005T180000Z_a/MLB_PROP_CANDIDATES.csv"
        csvfile(self.archive, [dict(SOURCE_ROW)])
        self.entry = dict(ENTRY)
        self.s = FakeSession()

    def plan(self, rows=None, session=None):
        entries = [self.entry] if rows is None else rows
        return mlb.plan_mlb_settlement(
            self.root, {x["forward_key"]: x for x in entries},
            session or self.s,
        )

    def test_frozen_pick_requires_matching_gamepk_and_playerid(self):
        receipt, events = self.plan()
        self.assertEqual(receipt["status"], "READY")
        self.assertEqual(receipt["mapped_official_events"], 1)
        self.assertEqual(receipt["official_final_games"], 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["official_game_pk"], "849834")
        self.assertEqual(events[0]["official_player_id"], "643217")
        self.assertEqual(events[0]["settlement_match_type"], "MLB_OFFICIAL_GAME_AND_PLAYER_ID")
        self.assertEqual(events[0]["grade"], "WIN")
        self.assertEqual(events[0]["actual_value"], 2)
        self.assertFalse(events[0]["platform_payout_claimed"])
        self.assertFalse(events[0]["automatic_model_promotion"])

    def test_all_relevant_hitter_metrics(self):
        expected = {
            "PLAYER_TOTAL_HITS": 2,
            "PLAYER_TOTAL_RUNS": 1,
            "PLAYER_TOTAL_RBIS": 1,
            "PLAYER_TOTAL_DOUBLES": 1,
            "PLAYER_TOTAL_HOME_RUNS": 0,
            "PLAYER_TOTAL_STOLEN_BASES": 1,
            "PLAYER_TOTAL_BATTER_WALKS": 0,
            "PLAYER_TOTAL_TOTAL_BASES": 3,
            "PLAYER_TOTAL_SINGLES": 1,
            "PLAYER_TOTAL_HITS_+_RUNS_+_RBIS": 4,
        }
        for market, actual in expected.items():
            with self.subTest(market=market):
                self.entry["market"] = market
                _, events = self.plan()
                self.assertEqual(events[0]["actual_value"], actual)

    def test_pitcher_outs_uses_base_three(self):
        row = {"pitching_played": True, "pitching": {
            "inningsPitched": "5.2", "strikeOuts": 8, "earnedRuns": 2,
            "baseOnBalls": 1, "hits": 4,
        }}
        self.assertEqual(mlb.stat_actual(row, "PLAYER_TOTAL_PITCHING_OUTS"), (17, "VERIFIED"))
        self.assertEqual(mlb.stat_actual(row, "PLAYER_TOTAL_PITCHER_STRIKEOUTS"), (8, "VERIFIED"))
        self.assertEqual(mlb.stat_actual(row, "PLAYER_TOTAL_EARNED_RUNS_ALLOWED"), (2, "VERIFIED"))
        self.assertEqual(mlb.stat_actual(row, "PLAYER_TOTAL_WALKS_ALLOWED"), (1, "VERIFIED"))
        self.assertEqual(mlb.stat_actual(row, "PLAYER_TOTAL_HITS_ALLOWED"), (4, "VERIFIED"))
        row["pitching"]["inningsPitched"] = "5.9"
        self.assertIsNone(mlb.stat_actual(row, "PLAYER_TOTAL_PITCHING_OUTS")[0])

    def test_over_under_and_push(self):
        self.entry["line"] = 2
        _, events = self.plan()
        self.assertEqual(events[0]["grade"], "PUSH")
        self.entry.update(side="UNDER", line=2.5)
        _, events = self.plan()
        self.assertEqual(events[0]["grade"], "WIN")
        self.entry["side"] = "OVER"
        _, events = self.plan()
        self.assertEqual(events[0]["grade"], "LOSS")

    def test_no_inprogress_or_future_settlement(self):
        for status in ("In Progress", "Pre-Game"):
            with self.subTest(status=status):
                fake = FakeSession()
                fake.schedule["dates"][0]["games"][0]["status"]["detailedState"] = status
                receipt, events = self.plan(session=fake)
                self.assertEqual(receipt["status"], "READY")
                self.assertEqual(events, [])
                self.assertEqual(receipt["review_reasons"]["NO_OFFICIAL_FINAL_BOX"], 1)
                self.assertEqual(len(fake.calls), 1)

    def test_conflicting_schedule_doubleheader_is_ambiguous(self):
        fake = FakeSession()
        copy = dict(fake.schedule["dates"][0]["games"][0])
        copy["gamePk"] = 849835
        fake.schedule["dates"][0]["games"].append(copy)
        receipt, events = self.plan(session=fake)
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"]["NO_UNIQUE_OFFICIAL_GAME_MAPPING"], 1)

    def test_game_date_and_both_teams_must_match_provider_archive(self):
        for change in (
            {"home_team": "New York Yankees"},
            {"start": "2026-10-05 23:15:00+00:00"},
        ):
            with self.subTest(change=change):
                csvfile(self.archive, [dict(SOURCE_ROW, **change)])
                receipt, events = self.plan()
                self.assertEqual(events, [])
                self.assertEqual(receipt["review_reasons"]["NO_UNIQUE_OFFICIAL_GAME_MAPPING"], 1)

    def test_invalid_or_missing_original_player_id_blocks_settlement(self):
        for change in (
            {"player_id": ""},
            {"player_id": "a-uuid-not-an-mlb-id"},
            {"player_id": "999999"},
        ):
            with self.subTest(change=change):
                csvfile(self.archive, [dict(SOURCE_ROW, **change)])
                receipt, events = self.plan()
                self.assertEqual(events, [])

    def test_archive_conflicting_player_ids_blocks_match(self):
        csvfile(self.archive, [dict(SOURCE_ROW), dict(SOURCE_ROW, player_id="999999")])
        receipt, events = self.plan()
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"]["NO_UNIQUE_ARCHIVED_OFFICIAL_PLAYER_ID"], 1)

    def test_source_player_team_and_name_must_agree_with_official_box(self):
        for change in (
            {"team": "New York Yankees"},
            {"player": "Another Player"},
        ):
            with self.subTest(change=change):
                csvfile(self.archive, [dict(SOURCE_ROW, **change)])
                receipt, events = self.plan()
                self.assertEqual(events, [])
                self.assertEqual(receipt["review_reasons"]["OFFICIAL_PLAYER_ID_TEAM_NAME_CONFLICT"], 1)

    def test_provider_uuid_does_not_replace_official_gamepk(self):
        receipt, events = self.plan([dict(self.entry, event_id="not-in-archive")])
        self.assertEqual(events, [])
        self.assertEqual(receipt["status"], "NO_ARCHIVED_EVENT_IDENTITIES")

    def test_absent_stats_or_dnp_never_becomes_an_under_win(self):
        for change in (
            {"batters": []},
            {"batters": [643217], "players": {}},
        ):
            with self.subTest(change=change):
                fake = FakeSession()
                fake.boxes["849834"]["liveData"]["boxscore"]["teams"]["away"].update(change)
                receipt, events = self.plan(session=fake)
                self.assertEqual(events, [])

    def test_missing_explicit_stat_is_not_assumed_zero(self):
        fake = FakeSession()
        del fake.boxes["849834"]["liveData"]["boxscore"]["teams"]["away"]["players"]["ID643217"]["stats"]["batting"]["hits"]
        receipt, events = self.plan(session=fake)
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"]["OFFICIAL_METRIC_UNAVAILABLE"], 1)

    def test_invalid_market_side_line_capture_remain_pending(self):
        for change in (
            {"market": "NOT_A_REAL_MARKET"},
            {"line": -1},
            {"side": "YES"},
            {"captured_at": "2026-10-05T21:30:00Z"},
            {"event_start": "2026-10-05T23:30:00Z"},
        ):
            with self.subTest(change=change):
                _, events = self.plan([dict(self.entry, **change)])
                self.assertEqual(events, [])

    def test_schedule_final_but_feed_live_does_not_grade(self):
        fake = FakeSession()
        fake.boxes["849834"]["gameData"]["status"]["abstractGameState"] = "Live"
        receipt, events = self.plan(session=fake)
        self.assertEqual(events, [])
        self.assertEqual(receipt["status"], "INVALID_OFFICIAL_FINAL_BOX")

    def test_official_team_gamepk_game_type_mismatch_quarantines(self):
        for change in (
            ("game", "pk", 849835),
            ("game", "type", "R"),
        ):
            with self.subTest(change=change):
                fake = FakeSession()
                fake.boxes["849834"]["gameData"][change[0]][change[1]] = change[2]
                receipt, events = self.plan(session=fake)
                self.assertEqual(events, [])
                self.assertEqual(receipt["status"], "INVALID_OFFICIAL_FINAL_BOX")

    def test_prior_matching_settled_grade_is_preserved(self):
        prior = dict(self.entry, grade="WIN")
        receipt, events = self.plan([prior])
        self.assertEqual(events, [])
        self.assertEqual(receipt["existing_verified"], 1)

    def test_contradictory_prior_grade_blocks_entire_batch(self):
        prior = dict(self.entry, grade="LOSS", forward_key="pre-existing")
        receipt, events = self.plan([prior, self.entry])
        self.assertEqual(receipt["status"], "INTEGRITY_HOLD_PREVIOUS_GRADE_CONFLICT")
        self.assertEqual(receipt["conflicting_previous_grades_count"], 1)
        self.assertEqual(events, [])

    def test_no_archive_means_no_any_outcomes(self):
        self.archive.unlink()
        receipt, events = self.plan()
        self.assertEqual(events, [])
        self.assertEqual(receipt["status"], "SOURCE_UNAVAILABLE")

    def test_sources_only_ever_read(self):
        source = self.archive.read_bytes()
        receipt, events = self.plan()
        self.assertEqual(self.archive.read_bytes(), source)
        self.assertEqual(len(events), 1)
        self.assertFalse((self.root / "intelligence_warehouse/betting_v2/PROP_V2_FORWARD_LEDGER.jsonl").exists())

    def test_wrapper_append_only_and_idempotent(self):
        out = self.root / "intelligence_warehouse/betting_v2"
        out.mkdir(parents=True)
        ledger = out / "PROP_V2_FORWARD_LEDGER.jsonl"
        ledger.write_text(json.dumps(self.entry) + "\n")
        receipt = out / "MLB_OFFICIAL_BOX_FORWARD_RECEIPT.json"
        with patch.object(props, "ROOT", self.root), \
             patch.object(props, "LEDGER", ledger), \
             patch.object(props, "MLB_BOX_RECEIPT", receipt):
            frozen = ledger.read_bytes()
            first = props.settle_mlb_official_box(session=FakeSession())
            self.assertEqual(first["settled_now"], 1)
            self.assertTrue(ledger.read_bytes().startswith(frozen))
            self.assertEqual(props.canonical()["frozen-mlb-one"]["grade"], "WIN")
            second = props.settle_mlb_official_box(session=FakeSession())
            self.assertEqual(second["settled_now"], 0)
            self.assertEqual(second["existing_verified"], 1)
            self.assertEqual(len(ledger.read_text().splitlines()), 2)
            self.assertFalse(json.loads(receipt.read_text())["automatic_model_promotion"])

    def test_archive_changed_before_write_blocks_and_does_not_append(self):
        out = self.root / "intelligence_warehouse/betting_v2"
        out.mkdir(parents=True)
        ledger = out / "PROP_V2_FORWARD_LEDGER.jsonl"
        ledger.write_text(json.dumps(self.entry) + "\n")
        initial = ledger.read_bytes()
        receipt = out / "MLB_OFFICIAL_BOX_FORWARD_RECEIPT.json"
        sha = mlb.archive_fingerprint(self.root)
        stale = dict(sha, sha256="different")
        with patch.object(props, "ROOT", self.root), \
             patch.object(props, "LEDGER", ledger), \
             patch.object(props, "MLB_BOX_RECEIPT", receipt), \
             patch.object(mlb, "archive_fingerprint", side_effect=[sha, sha, stale]):
            result = props.settle_mlb_official_box(session=FakeSession())
        self.assertEqual(result["status"], "ARCHIVE_CHANGED_BEFORE_APPEND")
        self.assertEqual(result["settled_now"], 0)
        self.assertEqual(ledger.read_bytes(), initial)

    def test_official_api_failure_never_sets_unverified_results(self):
        fake = FakeSession(boxes={})
        receipt, events = self.plan(session=fake)
        self.assertEqual(events, [])
        self.assertEqual(receipt["status"], "OFFICIAL_API_UNAVAILABLE")

    def test_archive_changed_during_research_freezes_entire_plan(self):
        first = mlb.archive_fingerprint(self.root)
        newer = dict(first, sha256="changed-source")
        with patch.object(mlb, "archive_fingerprint", side_effect=[first, newer]):
            receipt, events = self.plan()
        self.assertEqual(receipt["status"], "ARCHIVE_CHANGED_DURING_RESEARCH")
        self.assertEqual(events, [])

    def test_ledger_changed_before_append_blocks_all_writes(self):
        folder = self.root / "intelligence_warehouse/betting_v2"
        folder.mkdir(parents=True)
        ledger = folder / "PROP_V2_FORWARD_LEDGER.jsonl"
        ledger.write_text(json.dumps(self.entry) + "\n")
        receipt_path = folder / "MLB_OFFICIAL_BOX_FORWARD_RECEIPT.json"
        fake = FakeSession()
        original_get = fake.get
        def concurrent_writer(url, **kwargs):
            result = original_get(url, **kwargs)
            if url.endswith("/feed/live"):
                with ledger.open("a") as output:
                    output.write(json.dumps({"event_type":"MONITOR_TRIGGER", "forward_key":"frozen-mlb-one"})+"\n")
            return result
        fake.get = concurrent_writer
        with patch.object(props, "ROOT", self.root), \
             patch.object(props, "LEDGER", ledger), \
             patch.object(props, "MLB_BOX_RECEIPT", receipt_path):
            receipt = props.settle_mlb_official_box(session=fake)
        self.assertEqual(receipt["status"], "LEDGER_CHANGED_BEFORE_APPEND")
        self.assertEqual(receipt["settled_now"], 0)
        self.assertEqual(len(ledger.read_text().splitlines()), 2)

    def test_conflict_wrapper_never_writes_new_outcomes(self):
        out = self.root / "intelligence_warehouse/betting_v2"
        out.mkdir(parents=True)
        ledger = out / "PROP_V2_FORWARD_LEDGER.jsonl"
        settled = dict(self.entry, forward_key="settled-previous", grade="LOSS")
        ledger.write_text(json.dumps(settled)+"\n"+json.dumps(self.entry)+"\n")
        before = ledger.read_bytes()
        receipt = out / "MLB_OFFICIAL_BOX_FORWARD_RECEIPT.json"
        with patch.object(props, "ROOT", self.root), \
             patch.object(props, "LEDGER", ledger), \
             patch.object(props, "MLB_BOX_RECEIPT", receipt):
            with self.assertRaises(RuntimeError):
                props.settle_mlb_official_box(session=FakeSession())
        self.assertEqual(ledger.read_bytes(), before)
        self.assertEqual(json.loads(receipt.read_text())["status"],
                         "INTEGRITY_HOLD_PREVIOUS_GRADE_CONFLICT")


if __name__ == "__main__":
    unittest.main()
