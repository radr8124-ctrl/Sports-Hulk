"""NHL completed-game starter status must be based on explicit source truth."""
import unittest

from nhl_live.build_nhl_data import player_rows_from_boxscore
from scripts.nhl_starter_source_truth_reconcile import canonical_nhl_player_id


def make_game():
    return {
        "event_id": "test-only-2026",
        "game_date": "2026-10-08",
        "start": "2026-10-08T23:00:00Z",
        "season": "20262027",
        "game_type": 2,
        "away_team": "AAA",
        "home_team": "BBB",
        "away_score": 2,
        "home_score": 3,
    }


def team_rows(goalies_away, goalies_home):
    box = {
        "playerByGameStats": {
            "awayTeam": {"goalies": goalies_away},
            "homeTeam": {"goalies": goalies_home},
        }
    }
    _, _, teams = player_rows_from_boxscore(make_game(), box)
    return {str(row["team"]): row for _, row in teams.iterrows()}


def goalie(player_id, starter, toi):
    return {
        "playerId": player_id,
        "name": f"Goalie {player_id}",
        "starter": starter,
        "toi": toi,
        "shotsAgainst": 24,
        "saves": 22,
    }


class TestOfficialNhlStarterFlag(unittest.TestCase):
    def test_source_integer_and_pandas_float_serialization_same_player(self):
        self.assertEqual(canonical_nhl_player_id("8481519"), "8481519")
        self.assertEqual(canonical_nhl_player_id("8481519.0"), "8481519")
        self.assertEqual(canonical_nhl_player_id("8481519.1"), "")
        self.assertNotEqual(canonical_nhl_player_id("8481519.0"), canonical_nhl_player_id("8481518"))

    def test_unflagged_maximum_toi_is_not_confirmed_starter(self):
        rows = team_rows([goalie(101, False, "60:00")], [])
        self.assertTrue(rows["AAA"]["starting_goalie"] in ("", None))
        self.assertTrue(rows["AAA"]["starting_goalie_id"] in ("", None))
        self.assertIsNone(rows["AAA"]["starting_goalie_save_pct"])

    def test_explicit_true_is_used_even_with_shorter_ice_time(self):
        rows = team_rows(
            [goalie(111, True, "12:00"), goalie(112, False, "48:00")], []
        )
        self.assertEqual(rows["AAA"]["starting_goalie_id"], 111)
        self.assertEqual(rows["AAA"]["starting_goalie"], "Goalie 111")

    def test_string_starter_flag_is_not_a_verified_boolean(self):
        rows = team_rows(
            [goalie(121, "false", "60:00")],
            [goalie(122, "true", "59:00")],
        )
        for team in ("AAA", "BBB"):
            self.assertTrue(rows[team]["starting_goalie_id"] in ("", None))


if __name__ == "__main__":
    unittest.main()
