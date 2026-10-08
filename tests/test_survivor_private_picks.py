"""Week 5 personal Survivor save always preserves settled pick history."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from commercial_web.survivor_pick_bridge import save_week
from premium_ui import survivor_editor as editor


BEFORE_KICKOFF = datetime(2026, 10, 8, 21, 0, tzinfo=timezone.utc)
AFTER_KICKOFF = datetime(2026, 10, 9, 1, 0, tzinfo=timezone.utc)

SCORES = {
    "games": [],
    "next_games": [
        {"home": "Dallas Cowboys", "away": "Tampa Bay Buccaneers",
         "start_time": "2026-10-09T00:15Z"},
        {"home": "New York Jets", "away": "New England Patriots",
         "start_time": "2026-10-11T17:00Z"},
        {"home": "Minnesota Vikings", "away": "Chicago Bears",
         "start_time": "2026-10-11T17:00Z"},
    ],
}


class SurvivorPersonalPickTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        directory = Path(temp.name)
        self.entries_path = directory / "SURVIVOR_ENTRIES.json"
        self.audit_path = directory / "SURVIVOR_ENTRY_AUDIT.jsonl"
        self.score_path = directory / "nfl_scores.json"
        self.score_path.write_text(json.dumps(SCORES))
        self.existing = {
            "pool_current_week": 5,
            "active": "ANNIE G 01",
            "entries": {
                "ANNIE G 01": {
                    "status": "ALIVE",
                    "current_week": 4,
                    "current_picks": [],
                    "used_teams": ["Minnesota Vikings", "San Francisco 49ers"],
                    "week_4": {
                        "entry_result": "WIN",
                        "picks": [{"team": "Minnesota Vikings", "result": "WIN",
                                   "game_status": "FINAL: Miami Dolphins 10 - Minnesota Vikings 15"}],
                    },
                    "week_5": {
                        "entry_result": "OPEN",
                        "required_picks": None,
                        "rule_status": "AWAITING_OFFICIAL_POOL_SHEET",
                        "picks": [],
                        "submitted": False,
                    },
                },
                "ANNIE G 03": {
                    "status": "ELIMINATED",
                    "current_week": 5,
                    "used_teams": [],
                    "week_5": {"entry_result": "OPEN", "picks": []},
                },
            },
        }
        self.entries_path.write_text(json.dumps(self.existing))
        patcher = patch.multiple(
            editor, ENTRIES_PATH=self.entries_path, AUDIT_PATH=self.audit_path,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def save(self, teams, *, entry="ANNIE G 01", week=5, now=BEFORE_KICKOFF):
        return save_week(
            {"entry_name": entry, "week": week, "teams": teams},
            now=now, scores_path=self.score_path,
        )

    def state(self):
        return json.loads(self.entries_path.read_text())

    def test_new_week5_team_saved_only_in_sports_hulk_not_pool(self):
        result = self.save(["Dallas Cowboys"])
        self.assertEqual(result["status"], "SAVED_NOT_SUBMITTED")
        self.assertFalse(result["pool_submitted"])
        self.assertEqual(result["pick_status"], "RULE_UNCONFIRMED_SAVED")
        entry = self.state()["entries"]["ANNIE G 01"]
        self.assertEqual(entry["current_week"], 5)
        self.assertEqual(entry["current_picks"], ["Dallas Cowboys"])
        self.assertFalse(entry["week_5"]["submitted"])
        self.assertEqual(entry["week_4"], self.existing["entries"]["ANNIE G 01"]["week_4"])
        self.assertTrue(self.audit_path.is_file())

    def test_two_teams_can_be_saved_when_pool_rule_not_yet_confirmed(self):
        result = self.save(["Dallas Cowboys", "New York Jets"])
        self.assertEqual(result["teams"], ["Dallas Cowboys", "New York Jets"])
        self.assertEqual(len(self.state()["entries"]["ANNIE G 01"]["week_5"]["picks"]), 2)

    def test_historical_used_team_is_not_reusable_even_with_uncertain_week5_rule(self):
        before = self.entries_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Used Survivor team"):
            self.save(["Minnesota Vikings"])
        self.assertEqual(before, self.entries_path.read_bytes())

    def test_eliminated_entry_is_blocked_without_recorded_reentry(self):
        before = self.entries_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "eliminated"):
            self.save(["Dallas Cowboys"], entry="ANNIE G 03")
        self.assertEqual(before, self.entries_path.read_bytes())

    def test_wrong_pool_week_never_changes_historical_result(self):
        before = self.entries_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "pool week changed"):
            self.save(["Dallas Cowboys"], week=4)
        self.assertEqual(before, self.entries_path.read_bytes())

    def test_game_is_locked_at_kickoff_and_current_pick_cannot_be_swapped(self):
        before = self.entries_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Kickoff has passed"):
            self.save(["Dallas Cowboys"], now=AFTER_KICKOFF)
        self.assertEqual(before, self.entries_path.read_bytes())
        self.save(["Dallas Cowboys"], now=BEFORE_KICKOFF)
        saved = self.entries_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Kickoff has passed"):
            self.save(["New York Jets"], now=AFTER_KICKOFF)
        self.assertEqual(saved, self.entries_path.read_bytes())

    def test_unknown_score_feed_refuses_save_without_guessing_kickoff(self):
        with self.assertRaisesRegex(ValueError, "Kickoff cannot be verified"):
            self.save(["Philadelphia Eagles"])

    def test_resolved_week_is_locked(self):
        state = self.state()
        state["entries"]["ANNIE G 01"]["week_5"]["entry_result"] = "WIN"
        self.entries_path.write_text(json.dumps(state))
        before = self.entries_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "resolved"):
            self.save(["New York Jets"])
        self.assertEqual(before, self.entries_path.read_bytes())

    def test_invalid_payload_rejected_without_touching_state(self):
        before = self.entries_path.read_bytes()
        for teams in (["Dallas Cowboys", "Dallas Cowboys"], ["BOGUS"], "Dallas Cowboys", [None], ["Dallas Cowboys"] * 5):
            with self.subTest(teams=teams), self.assertRaises(ValueError):
                self.save(teams)
        self.assertEqual(before, self.entries_path.read_bytes())

    def test_does_not_modify_other_survivor_entries(self):
        self.save(["Dallas Cowboys"])
        self.assertEqual(
            self.state()["entries"]["ANNIE G 03"],
            self.existing["entries"]["ANNIE G 03"],
        )


if __name__ == "__main__":
    unittest.main()
