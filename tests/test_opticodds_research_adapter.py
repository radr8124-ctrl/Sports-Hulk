"""Offline contract tests for a possible paid OpticOdds v3 research connection."""
import copy
import unittest

from intelligence_warehouse.provider_integrations.opticodds_research_adapter import (
    SourceReview, confirm_quote,
)

STAMP = 1791741600  # 2026-10-11 18:00:00 UTC


def sample():
    fixture = {
        "id": "OD-FIXTURE-1",
        "start_date": "2026-10-11T19:00:00Z",
        "home_competitors": [{"id": "TEAM-A", "abbreviation": "AAA"}],
        "away_competitors": [{"id": "TEAM-B", "abbreviation": "BBB"}],
        "status": "unplayed",
        "is_live": False,
        "league": {"id": "nhl"},
    }
    quote = {
        "id": "QUOTE-1",
        "sportsbook": "DraftKings",
        "market_id": "moneyline",
        "price": -125,
        "timestamp": STAMP,
        "team_id": "TEAM-A",
        "player_id": None,
    }
    anchor = {
        "league_id": "nhl",
        "provider_fixture_id": "OD-FIXTURE-1",
        "home_provider_team_id": "TEAM-A",
        "away_provider_team_id": "TEAM-B",
        "scheduled_start": "2026-10-11T19:00:00Z",
        "market_id": "moneyline",
        "selection_provider_team_id": "TEAM-A",
    }
    return fixture, quote, anchor, "2026-10-11T18:01:00Z"


class CandidateSourceVerification(unittest.TestCase):
    def case(self):
        f, q, a, t = sample()
        return copy.deepcopy(f), copy.deepcopy(q), copy.deepcopy(a), t

    def rejected(self, expected, f, q, a, t):
        with self.assertRaises(SourceReview) as context:
            confirm_quote(f, q, a, t)
        self.assertIn(expected, str(context.exception))

    def test_exact_moneyline_price_is_research_only(self):
        result = confirm_quote(*self.case())
        self.assertEqual(result["status"], "VERIFIED_SOURCE_RESEARCH_ONLY")
        self.assertFalse(result["automatic_bet_allowed"])
        self.assertFalse(result["prizepicks_payout_verified"])
        self.assertFalse(result["goalie_starter_confirmed"])

    def test_eight_minute_start_time_disagreement_is_blocked(self):
        f, q, a, t = self.case()
        f["start_date"] = "2026-10-11T19:08:00Z"
        self.rejected("SOURCE_KICKOFF_MISMATCH", f, q, a, t)

    def test_exact_provider_fixture_identity_required(self):
        f, q, a, t = self.case()
        f["id"] = "different-game"
        self.rejected("FIXTURE_IDENTITY_MISMATCH", f, q, a, t)

    def test_wrong_opponent_or_home_id_blocked(self):
        f, q, a, t = self.case()
        f["away_competitors"][0]["id"] = "TEAM-C"
        self.rejected("AWAY_IDENTITY_MISMATCH", f, q, a, t)

    def test_wrong_selection_id_blocked(self):
        f, q, a, t = self.case()
        q["team_id"] = "TEAM-B"
        self.rejected("MONEYLINE_SELECTION_IDENTITY_MISMATCH", f, q, a, t)

    def test_wrong_league_blocked(self):
        f, q, a, t = self.case()
        f["league"]["id"] = "nba"
        self.rejected("LEAGUE_MISMATCH", f, q, a, t)

    def test_betting_started_is_blocked(self):
        f, q, a, t = self.case()
        f["status"] = "live"
        self.rejected("GAME_ALREADY_STARTED", f, q, a, t)

    def test_suspended_price_is_blocked(self):
        f, q, a, t = self.case()
        q["is_locked"] = True
        self.rejected("LOCKED_OR_LIVE_QUOTE", f, q, a, t)

    def test_stale_odds_are_blocked(self):
        f, q, a, t = self.case()
        q["timestamp"] -= 900
        self.rejected("STALE_QUOTE", f, q, a, t)

    def test_future_observation_is_blocked(self):
        f, q, a, t = self.case()
        q["timestamp"] += 90
        self.rejected("QUOTE_OUTSIDE_PREGAME_ASOF", f, q, a, t)

    def test_unverified_price_blocked(self):
        f, q, a, t = self.case()
        q["price"] = -95
        self.rejected("INVALID_PRICE", f, q, a, t)

    def test_prop_uses_exact_athlete_side_line(self):
        f, q, a, t = self.case()
        a.pop("selection_provider_team_id")
        a.update(market_id="player_shots_on_goal", provider_player_id="P007",
                 side="over", line=2.5)
        q.update(market_id="player_shots_on_goal", team_id=None,
                 player_id="P007", selection_line="over", points=2.5)
        result = confirm_quote(f, q, a, t)
        self.assertEqual(result["american_price"], -125.0)
        q["player_id"] = "P008"
        self.rejected("PLAYER_IDENTITY_MISMATCH", f, q, a, t)
        q["player_id"] = "P007"
        q["points"] = 3.5
        self.rejected("PROP_LINE_MISMATCH", f, q, a, t)

    def test_unresolved_player_or_team_cannot_pass(self):
        f, q, a, t = self.case()
        a.pop("selection_provider_team_id")
        self.rejected("UNVERIFIED_SELECTION_IDENTITY", f, q, a, t)


if __name__ == "__main__":
    unittest.main()
