"""NFL prop settlement only from exact player ID/name, official week, and teams."""
import unittest

import pandas as pd

from nfl_live.decision import grade_nfl_recommendations as nfl


def stats_frame():
    d = pd.DataFrame([
        {"player_id": "00-0012345", "player_display_name": "Sample Receiver",
         "season": 2026, "week": 3, "team": "IND", "opponent_team": "WAS",
         "receiving_yards": 25},
        {"player_id": "00-0012345", "player_display_name": "Sample Receiver",
         "season": 2026, "week": 4, "team": "IND", "opponent_team": "WAS",
         "receiving_yards": 67},
        {"player_id": "00-0098765", "player_display_name": "Other Receiver",
         "season": 2026, "week": 4, "team": "WAS", "opponent_team": "IND",
         "receiving_yards": 41},
    ])
    d["_player_key"] = d["player_display_name"].map(nfl.player_norm)
    d["_team"] = d["team"].map(nfl.team_abbr)
    d["_opp"] = d["opponent_team"].map(nfl.team_abbr)
    return d


def official_game(week=4, away="IND", home="WAS"):
    return {"week": week, "away_team": away, "home_team": home, "final": True}


class NflExactIdentityTests(unittest.TestCase):
    def setUp(self):
        self.stats = stats_frame()

    def test_player_id_with_team_chooses_exact_week(self):
        entry = {"player": "00-0012345|IND", "team": "IND"}
        row = nfl.find_player_result(entry, official_game(), self.stats)
        self.assertIsNotNone(row)
        self.assertEqual(row["week"], 4)
        self.assertEqual(row["receiving_yards"], 67)

    def test_player_name_prizepicks_uses_same_exact_week(self):
        entry = {"player": "Sample Receiver", "team": "IND"}
        row = nfl.find_player_result(entry, official_game(), self.stats)
        self.assertIsNotNone(row)
        self.assertEqual(row["receiving_yards"], 67)

    def test_missing_week_fails_closed(self):
        entry = {"player": "00-0012345|IND", "team": "IND"}
        self.assertIsNone(nfl.find_player_result(entry, official_game(week=5), self.stats))

    def test_name_with_one_old_week_also_fails_closed(self):
        older_only = self.stats[self.stats["week"].eq(3)]
        self.assertIsNone(nfl.find_player_result(
            {"player": "Sample Receiver", "team": "IND"},
            official_game(week=4), older_only,
        ))

    def test_mismatched_encoded_and_ledger_team_rejected(self):
        self.assertIsNone(nfl.find_player_result(
            {"player": "00-0012345|IND", "team": "WAS"},
            official_game(), self.stats,
        ))

    def test_player_team_not_in_matchup_rejected(self):
        self.assertIsNone(nfl.find_player_result(
            {"player": "00-0012345|IND", "team": "IND"},
            official_game(away="ATL", home="WAS"), self.stats,
        ))

    def test_wildcard_opponent_never_falls_back_to_old_result(self):
        self.assertIsNone(nfl.find_player_result(
            {"player": "00-0012345|IND", "team": "IND"},
            official_game(away="IND", home="MIA"), self.stats,
        ))

    def test_missing_player_id_is_not_guessed_from_someones_name(self):
        self.assertIsNone(nfl.find_player_result(
            {"player": "00-0099999|IND", "team": "IND"},
            official_game(), self.stats,
        ))

    def test_duplicate_identical_week_rows_are_not_arbitrarily_selected(self):
        doubled = pd.concat([self.stats, self.stats.iloc[[1]]], ignore_index=True)
        self.assertIsNone(nfl.find_player_result(
            {"player": "00-0012345|IND", "team": "IND"},
            official_game(), doubled,
        ))

    def test_missing_explicit_official_week_never_settles(self):
        self.assertIsNone(nfl.find_player_result(
            {"player": "00-0012345|IND", "team": "IND"},
            official_game(week=None), self.stats,
        ))

    def test_player_id_parser_accepts_only_exact_id_syntax(self):
        self.assertEqual(nfl.official_player_id("00-0038997|IND"), ("00-0038997", "IND"))
        self.assertEqual(nfl.official_player_id("00-0038997"), ("00-0038997", ""))
        self.assertEqual(nfl.official_player_id("a player called 00-0038997"), ("", ""))


if __name__ == "__main__":
    unittest.main()
