"""NBA result grading: source conflicts and competition regimes fail closed."""
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from nba_live.decision import grade_nba_recommendations as grader
from nba_live.decision.nba_result_reconciliation import (
    explicit_type, reconcile_games,
)


def game(event_id="401902644", season_type="1", *, score=(129, 105),
         away="MIA", home="TOR", start="2026-10-03T23:00Z",
         completed=True, source=1):
    return {
        "event_id": event_id, "season_type": season_type,
        "start": start, "away_team": away, "home_team": home,
        "away_score": score[0], "home_score": score[1],
        "completed": completed, "_source_order": source,
    }


def game_frame(*rows):
    frame = pd.DataFrame(rows)
    frame["away_team_norm"] = frame["away_team"].map(grader.team)
    frame["home_team_norm"] = frame["home_team"].map(grader.team)
    frame["start_dt"] = pd.to_datetime(frame["start"], utc=True, format="mixed")
    frame["date_key"] = frame["start_dt"].dt.strftime("%Y-%m-%d")
    return frame


def choice(frame, *, market="TOTAL", selection="OVER", line=227):
    return grader.grade_game({
        "game_key": "2026-10-03|MIA|TOR",
        "market": market, "selection": selection, "line": line,
    }, frame)


class ReconciliationTests(unittest.TestCase):
    def test_explicit_type_variants(self):
        for input_value in ("1", "1.0", 1, 1.0, "preseason"):
            self.assertEqual(explicit_type(input_value), "1")
        for input_value in (None, float("nan"), "", "Week 1", "October", "regular-ish"):
            self.assertEqual(explicit_type(input_value), "")

    def test_prefer_rich_final_metadata_even_when_legacy_row_is_last(self):
        history = game(source=1, season_type="1")
        legacy = game(source=2, season_type=None)
        for rows in ([history, legacy], [legacy, history]):
            with self.subTest(order=[v["_source_order"] for v in rows]):
                resolved = reconcile_games(game_frame(*rows))
                self.assertEqual(len(resolved), 1)
                self.assertEqual(resolved.iloc[0]["season_type"], "1")
                self.assertEqual(resolved.iloc[0]["_result_conflict"], "")
                result = choice(resolved)
                self.assertEqual(result["grade"], "WIN")
                self.assertEqual(result["season_type"], "1")
                self.assertEqual(result["context_status"], "FINAL_SCORE_VERIFIED")

    def test_incomplete_final_cannot_override_complete_verified_score(self):
        resolved = reconcile_games(game_frame(
            game(score=(129, 105), season_type="1", source=1),
            game(score=(float("nan"), 105), season_type=None, source=2),
        ))
        self.assertEqual(resolved.iloc[0]["season_type"], "1")
        self.assertEqual(choice(resolved)["actual_value"], 234)

    def test_final_score_conflict_quarantines_grade(self):
        resolved = reconcile_games(game_frame(
            game(score=(129, 105), source=1),
            game(score=(120, 105), source=2),
        ))
        self.assertIn("FINAL_SCORE_CONFLICT", resolved.iloc[0]["_result_conflict"])
        result = choice(resolved)
        self.assertEqual(result["grade"], "REVIEW_SOURCE_CONFLICT")
        self.assertEqual(result["season_type"], "")
        player = grader.grade_player({"game_key": "2026-10-03|MIA|TOR"}, resolved, pd.DataFrame())
        self.assertEqual(player["grade"], "REVIEW_SOURCE_CONFLICT")

    def test_final_team_conflict_quarantines_grade(self):
        resolved = reconcile_games(game_frame(
            game(home="TOR", source=1), game(home="BKN", source=2),
        ))
        self.assertIn("FINAL_TEAM_CONFLICT", resolved.iloc[0]["_result_conflict"])
        self.assertEqual(choice(resolved)["grade"], "REVIEW_SOURCE_CONFLICT")

    def test_final_season_type_conflict_quarantines_grade(self):
        resolved = reconcile_games(game_frame(
            game(season_type="1", source=1), game(season_type="2", source=2),
        ))
        self.assertIn("FINAL_SEASON_TYPE_CONFLICT", resolved.iloc[0]["_result_conflict"])
        self.assertEqual(choice(resolved)["grade"], "REVIEW_SOURCE_CONFLICT")

    def test_final_day_conflict_quarantines_grade(self):
        resolved = reconcile_games(game_frame(
            game(source=1), game(start="2026-10-04T23:00Z", source=2),
        ))
        self.assertIn("FINAL_DATE_CONFLICT", resolved.iloc[0]["_result_conflict"])
        self.assertEqual(choice(resolved)["grade"], "REVIEW_SOURCE_CONFLICT")

    def test_not_final_cannot_override_verified_final(self):
        resolved = reconcile_games(game_frame(
            game(season_type="1", completed=True, source=1),
            game(season_type="2", completed=False, source=0),
        ))
        self.assertEqual(choice(resolved)["season_type"], "1")
        self.assertEqual(choice(resolved)["grade"], "WIN")

    def test_two_different_event_ids_same_game_are_ambiguous(self):
        frames = game_frame(game(event_id="111"), game(event_id="222"))
        result = grader.game_from_key("2026-10-03|MIA|TOR", frames)
        self.assertEqual(result["_result_conflict"], "AMBIGUOUS_GAME_MATCH")
        self.assertEqual(choice(frames)["grade"], "REVIEW_SOURCE_CONFLICT")

    def test_source_without_season_type_does_not_infer_from_date(self):
        resolved = reconcile_games(game_frame(game(season_type=None)))
        self.assertFalse(resolved.iloc[0]["season_type"])
        self.assertEqual(choice(resolved)["grade"], "WIN")
        self.assertFalse(choice(resolved)["season_type"])


class SourceLoadingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.paths = [self.d / x for x in ["current.csv", "history.csv", "legacy.csv"]]
        self.saved = (grader.CURRENT_GAMES, grader.GAME_HISTORY, grader.RESULT_HISTORY)

    def tearDown(self):
        grader.CURRENT_GAMES, grader.GAME_HISTORY, grader.RESULT_HISTORY = self.saved

    def write(self, slot, rows):
        with self.paths[slot].open("w", newline="") as f:
            out = csv.DictWriter(f, fieldnames=list(game()))
            out.writeheader()
            out.writerows(rows)

    def load(self):
        grader.CURRENT_GAMES, grader.GAME_HISTORY, grader.RESULT_HISTORY = self.paths
        return grader.load_games()

    def test_real_duplicate_event_preserves_explicit_source_type(self):
        self.write(1, [game()])
        self.write(2, [game(season_type=None, source=2)])
        result = choice(self.load())
        self.assertEqual(result["grade"], "WIN")
        self.assertEqual(result["season_type"], "1")

    def test_float_event_id_and_integer_id_dedupe(self):
        self.write(0, [game(event_id="401902644.0", source=0)])
        self.write(1, [game(event_id="401902644", source=1)])
        rows = self.load()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.iloc[0]["event_id"], "401902644")

    def test_missing_event_id_cannot_earn_win(self):
        self.write(0, [game(event_id="")])
        rows = self.load()
        self.assertEqual(choice(rows)["grade"], "REVIEW_SOURCE_CONFLICT")

    def test_different_unidentified_results_do_not_merge(self):
        self.write(0, [game(event_id="", source=0)])
        self.write(1, [game(event_id="", source=1)])
        rows = self.load()
        self.assertEqual(len(rows), 2)
        self.assertEqual(choice(rows)["grade"], "REVIEW_SOURCE_CONFLICT")


if __name__ == "__main__":
    unittest.main()
