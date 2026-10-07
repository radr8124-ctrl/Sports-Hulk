"""Official NHL frozen-prediction forward settlement must fail closed."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import csv
import json
import tempfile
import unittest
from unittest.mock import patch

from intelligence_warehouse.betting_v2 import nhl_official_box_forward as nhl
from intelligence_warehouse.betting_v2 import build_prop_v2_forward as props


GAME = {
    "event_id": "2026020040",
    "season": "20262027", "game_type": "2",
    "game_date": "2026-10-05", "start": "2026-10-05T23:00:00Z",
    "away_team": "PHI", "home_team": "TBL",
    "away_score": "3", "home_score": "2",
    "game_state": "OFF", "completed": "True",
}
ROSTER = {
    "team": "PHI", "player_id": "8482142", "player": "Jamie Drysdale",
}
BOX = {
    "event_id": "2026020040", "player_id": "8482142",
    "season": "20262027", "game_type": "2",
    "team": "PHI", "opponent": "TBL",
    "role": "SKATER", "toi_minutes": "18.5",
    "goals": "1", "assists": "2", "points": "3", "shots_on_goal": "4",
}
ENTRY = {
    "event_type": "ENTRY",
    "forward_key": "frozen-nhl-prop-1",
    "sport": "NHL", "lane": "PROP",
    "event_id": "provider-uuid-not-nhl-game-id",
    "game_key": "2026-10-05|PHI|TBL",
    "event_start": "2026-10-05 23:05:00+00:00",
    "captured_at": "2026-10-05T19:00:00Z",
    "player_key": "jamiedrysdale",
    "market": "PLAYER_TOTAL_ASSISTS", "side": "OVER",
    "line": 1.5, "grade": "PENDING",
    "model_version": "PROP_V2_TEST",
}


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [dict(x) for x in rows]
    fields = list(rows[0]) if rows else list(GAME)
    with path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


class NhlBoxForwardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.game = dict(GAME)
        self.roster = dict(ROSTER)
        self.box = dict(BOX)
        self.entry = dict(ENTRY)
        self.save_files()

    def save_files(self, games=None, current=None, boxes=None, rosters=None):
        games = [self.game] if games is None else games
        current = [self.game] if current is None else current
        boxes = [self.box] if boxes is None else boxes
        rosters = [self.roster] if rosters is None else rosters
        for rel, records in zip(nhl.SOURCES, (games, current, boxes, rosters)):
            if not records:
                # Empty but valid provider CSV with meaningful schema.
                template = self.game if "GAME" in rel else self.box if "PLAYER_GAME" in rel else self.roster
                path = self.root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(",".join(template) + "\n")
            else:
                write_csv(self.root / rel, records)

    def plan(self, entries=None):
        return nhl.plan_nhl_settlement(self.root, {
            row["forward_key"]: row for row in (
                [self.entry] if entries is None else entries
            )
        })

    def test_correct_goals_assists_points_and_shots_grade(self):
        stats = {
            "PLAYER_TOTAL_GOALS": ("goals", 1, "LOSS"),
            "PLAYER_TOTAL_ASSISTS": ("assists", 2, "WIN"),
            "PLAYER_TOTAL_POINTS": ("points", 3, "WIN"),
            "PLAYER_TOTAL_SHOTS": ("shots_on_goal", 4, "WIN"),
        }
        for market, (col, actual, grade) in stats.items():
            with self.subTest(market=market):
                self.entry.update(market=market, line=1.5)
                receipt, events = self.plan()
                self.assertEqual(receipt["status"], "READY")
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]["grade"], grade)
                self.assertEqual(events[0]["actual_value"], actual)
                self.assertEqual(events[0]["stat_column"], col)
                self.assertEqual(events[0]["result_event_id"], "2026020040")
                self.assertEqual(events[0]["official_player_id"], "8482142")
                self.assertFalse(events[0]["platform_settlement_claimed"])

    def test_push_is_not_fabricated_loss(self):
        self.entry["line"] = 2
        _, events = self.plan()
        self.assertEqual(events[0]["grade"], "PUSH")

    def test_under_and_over_are_opposites(self):
        self.entry.update(side="UNDER", line=2.5)
        _, events = self.plan()
        self.assertEqual(events[0]["grade"], "WIN")
        self.entry["side"] = "OVER"
        _, events = self.plan()
        self.assertEqual(events[0]["grade"], "LOSS")

    def test_read_only_plan_never_modifies_source_or_ledger(self):
        paths = [self.root / x for x in nhl.SOURCES]
        before = [p.read_bytes() for p in paths]
        self.plan()
        self.assertEqual(before, [p.read_bytes() for p in paths])
        self.assertFalse((self.root / "intelligence_warehouse/betting_v2/PROP_V2_FORWARD_LEDGER.jsonl").exists())

    def test_both_exported_game_records_must_agree(self):
        bad = dict(self.game, home_score="5")
        self.save_files(current=[bad])
        receipt, events = self.plan()
        self.assertEqual(events, [])
        self.assertEqual(receipt["new_verified"], 0)
        self.assertEqual(receipt["review_reasons"].get("NO_COMPLETED_OFFICIAL_GAME"), 1)

    def test_double_game_key_must_not_guess_event(self):
        other = dict(self.game, event_id="2026020041")
        self.save_files(games=[self.game, other], current=[self.game])
        receipt, events = self.plan()
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"].get("AMBIGUOUS_OFFICIAL_GAME"), 1)

    def test_mismatched_teams_and_player_opponent_are_rejected(self):
        wrong = dict(self.box, opponent="BOS")
        self.save_files(boxes=[wrong])
        receipt, events = self.plan()
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"]["PLAYER_GAME_TEAM_CONFLICT"], 1)

    def test_roster_team_disagreement_is_rejected(self):
        self.save_files(rosters=[dict(self.roster, team="BOS")])
        _, events = self.plan()
        self.assertEqual(events, [])

    def test_duplicate_or_missing_roster_identity_is_rejected(self):
        for roster in (
            [self.roster, dict(self.roster, player_id="8482143")],
            [dict(self.roster, player="Other Skater")],
        ):
            with self.subTest(roster=roster):
                self.save_files(rosters=roster)
                receipt, events = self.plan()
                self.assertEqual(events, [])
                self.assertEqual(receipt["review_reasons"]["AMBIGUOUS_OR_MISSING_ROSTER_ID"], 1)

    def test_unicode_roster_name_normalized_only_exactly(self):
        self.roster["player"] = "Jámie Drÿsdale"
        self.save_files()
        receipt, events = self.plan()
        self.assertEqual(receipt["status"], "READY")
        self.assertEqual(len(events), 1)
        self.roster["player"] = "Tim Other"
        self.save_files()
        _, events = self.plan()
        self.assertEqual(events, [])

    def test_duplicate_boxscore_or_missing_player_is_rejected(self):
        self.save_files(boxes=[self.box, dict(self.box)])
        receipt, events = self.plan()
        self.assertEqual(events, [])
        self.assertEqual(receipt["review_reasons"]["MISSING_OR_DUPLICATE_PLAYER_BOX"], 1)

    def test_unplayed_or_goalie_stats_never_become_realized_prop_win(self):
        for change in (
            {"role": "GOALIE"},
            {"toi_minutes": "0.0"},
            {"toi_minutes": ""},
        ):
            with self.subTest(change=change):
                self.save_files(boxes=[dict(self.box, **change)])
                receipt, events = self.plan()
                self.assertEqual(events, [])
                self.assertEqual(receipt["new_verified"], 0)

    def test_official_season_and_game_type_must_match(self):
        for change in (
            {"season": "20252026"},
            {"game_type": "1"},
        ):
            with self.subTest(change=change):
                self.save_files(boxes=[dict(self.box, **change)])
                receipt, events = self.plan()
                self.assertEqual(events, [])
                self.assertEqual(receipt["review_reasons"]["COMPETITION_REGIME_CONFLICT"], 1)

    def test_not_final_missing_score_and_future_never_settle(self):
        for change in (
            {"completed": "False"},
            {"game_state": "PRE"},
            {"away_score": ""},
        ):
            with self.subTest(change=change):
                self.save_files(games=[dict(self.game, **change)],
                                current=[dict(self.game, **change)])
                _, events = self.plan()
                self.assertEqual(events, [])

    def test_game_key_and_clock_must_match_official_sources(self):
        for change, reason in (
            ({"game_key": "2026-10-05|PHI|BOS"}, "NO_COMPLETED_OFFICIAL_GAME"),
            ({"event_start": "2026-10-06T04:00:00Z"}, "EVENT_START_MISMATCH"),
            ({"captured_at": "2026-10-06T01:00:00Z"}, "NOT_FROZEN_PREGAME"),
            ({"captured_at": ""}, "NO_FROZEN_PREGAME_TIMESTAMPS"),
        ):
            with self.subTest(change=change):
                entry = dict(self.entry, **change)
                report, events = self.plan([entry])
                self.assertEqual(events, [])
                self.assertEqual(report["review_reasons"][reason], 1)

    def test_invalid_market_stat_side_line_never_settles(self):
        for change, reason in (
            ({"market": "PLAYER_LONGEST_ASSIST"}, "UNSUPPORTED_FROZEN_MARKET"),
            ({"side": "YES"}, "NO_VALID_FROZEN_LINE_SIDE"),
            ({"line": -1}, "NO_VALID_FROZEN_LINE_SIDE"),
        ):
            with self.subTest(change=change):
                receipt, events = self.plan([dict(self.entry, **change)])
                self.assertEqual(events, [])
                self.assertEqual(receipt["review_reasons"][reason], 1)

    def test_existing_agreed_grade_preserved_not_rewritten(self):
        record = dict(self.entry, grade="WIN")
        receipt, events = self.plan([record])
        self.assertEqual(receipt["existing_verified"], 1)
        self.assertEqual(events, [])

    def test_existing_contradictory_grade_freezes_entire_batch(self):
        settled = dict(self.entry, grade="LOSS", forward_key="already-settled")
        receipt, events = self.plan([self.entry, settled])
        self.assertEqual(receipt["status"], "INTEGRITY_HOLD_CONTRADICTORY_SETTLEMENT")
        self.assertEqual(receipt["conflicting_previous_grades_count"], 1)
        self.assertEqual(events, [])

    def test_source_changed_during_read_blocks_entire_replay(self):
        original = nhl.file_digests(self.root)
        mismatched = dict(original)
        mismatched[nhl.SOURCES[2]] = "another-verified-hash"
        with patch.object(nhl, "file_digests", side_effect=[original, mismatched]):
            receipt, events = self.plan()
        self.assertEqual(receipt["status"], "SOURCE_CHANGED_DURING_READ")
        self.assertEqual(events, [])

    def test_source_changed_after_plan_but_before_writing_blocks_append(self):
        ledger_dir = self.root / "intelligence_warehouse/betting_v2"
        ledger_dir.mkdir(parents=True)
        ledger = ledger_dir / "PROP_V2_FORWARD_LEDGER.jsonl"
        ledger.write_text(json.dumps(self.entry) + "\n")
        frozen = ledger.read_bytes()
        receipt_path = ledger_dir / "NHL_OFFICIAL_BOX_FORWARD_RECEIPT.json"
        fingerprint = nhl.file_digests(self.root)
        stale = dict(fingerprint)
        stale[nhl.SOURCES[1]] = "changed-while-verifying"
        with patch.object(props, "ROOT", self.root), \
             patch.object(props, "LEDGER", ledger), \
             patch.object(props, "NHL_BOX_RECEIPT", receipt_path), \
             patch.object(nhl, "file_digests", side_effect=[fingerprint, fingerprint, stale]):
            result = props.settle_nhl_official_box()
        self.assertEqual(result["status"], "SOURCE_CHANGED_BEFORE_SETTLEMENT")
        self.assertEqual(ledger.read_bytes(), frozen)
        self.assertEqual(result["settled_now"], 0)

    def test_no_game_or_player_source_never_backfills(self):
        (self.root / nhl.SOURCES[2]).unlink()
        receipt, events = self.plan()
        self.assertEqual(receipt["status"], "SOURCE_UNAVAILABLE")
        self.assertEqual(events, [])

    def test_settlement_wrapper_is_idempotent_and_append_only(self):
        self.entry["forward_key"] = "forward-one"
        ledger_dir = self.root / "intelligence_warehouse/betting_v2"
        ledger_dir.mkdir(parents=True)
        ledger = ledger_dir / "PROP_V2_FORWARD_LEDGER.jsonl"
        ledger.write_text(json.dumps(self.entry) + "\n")
        receipt_path = ledger_dir / "NHL_OFFICIAL_BOX_FORWARD_RECEIPT.json"

        # The production helper must not take the test's W/repo paths.
        with patch.object(props, "ROOT", self.root), \
             patch.object(props, "LEDGER", ledger), \
             patch.object(props, "NHL_BOX_RECEIPT", receipt_path):
            before = ledger.read_bytes()
            first = props.settle_nhl_official_box()
            self.assertEqual(first["settled_now"], 1)
            self.assertTrue(ledger.read_bytes().startswith(before))
            frozen = props.canonical()["forward-one"]
            self.assertEqual(frozen["grade"], "WIN")
            self.assertEqual(frozen["actual_value"], 2)
            self.assertEqual(frozen["market"], "PLAYER_TOTAL_ASSISTS")
            self.assertEqual(frozen["line"], 1.5)
            second = props.settle_nhl_official_box()
            self.assertEqual(second["settled_now"], 0)
            self.assertEqual(second["existing_verified"], 1)
            self.assertEqual(len(ledger.read_text().splitlines()), 2)

    def test_conflicting_result_blocks_all_writes_in_wrapper(self):
        original = dict(self.entry, forward_key="already", grade="LOSS")
        new = dict(self.entry, forward_key="pending")
        ledger_dir = self.root / "intelligence_warehouse/betting_v2"
        ledger_dir.mkdir(parents=True)
        ledger = ledger_dir / "PROP_V2_FORWARD_LEDGER.jsonl"
        ledger.write_text(json.dumps(original) + "\n" + json.dumps(new) + "\n")
        before = ledger.read_bytes()
        receipt_path = ledger_dir / "NHL_OFFICIAL_BOX_FORWARD_RECEIPT.json"
        with patch.object(props, "ROOT", self.root), \
             patch.object(props, "LEDGER", ledger), \
             patch.object(props, "NHL_BOX_RECEIPT", receipt_path):
            with self.assertRaises(RuntimeError):
                props.settle_nhl_official_box()
        self.assertEqual(ledger.read_bytes(), before)
        self.assertEqual(json.loads(receipt_path.read_text())["status"],
                         "INTEGRITY_HOLD_CONTRADICTORY_SETTLEMENT")


if __name__ == "__main__":
    unittest.main()
