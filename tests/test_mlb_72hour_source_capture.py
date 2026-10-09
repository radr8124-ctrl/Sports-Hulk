"""Longer public official schedule lookahead cannot imply resolved playoff teams."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import unittest
from intelligence_warehouse.mlb_pregame_capture.capture_evidence import parse_schedule
from tests.test_mlb_pregame_evidence_capture import fixture_game,fixture_schedule

ROOT=Path(__file__).resolve().parents[1]
NOW=datetime(2026,10,9,7,15,tzinfo=timezone.utc)

def future(at,pk=849809):
    g=fixture_game(game_pk=pk,start=at.isoformat().replace("+00:00","Z"))
    g["gameType"]="L"
    g["officialDate"]="2026-10-11"
    g["venue"]={"id":32,"name":"American Family Field"}
    g["teams"]["home"]["team"]={"id":158,"name":"Milwaukee Brewers"}
    g["teams"]["away"]["team"]={"id":119,"name":"Los Angeles Dodgers"}
    return g

class TestMLB72HourFutureSourceWindow(unittest.TestCase):
    def test_publicly_resolved_65_hour_future_fixture_is_retained(self):
        game=future(NOW+timedelta(hours=65))
        self.assertFalse(parse_schedule(fixture_schedule(game),NOW,lookahead_hours=48))
        found=parse_schedule(fixture_schedule(game),NOW,lookahead_hours=72)
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]["game_pk"],849809)
        self.assertEqual(found[0]["home_team_id"],158)
        self.assertEqual(found[0]["away_team_id"],119)
        self.assertEqual(found[0]["probable_status"],"OFFICIAL_SCHEDULE_PROBABLE_NOT_CONFIRMED")

    def test_distant_fixture_and_unresolved_bracket_placeholders_rejected(self):
        game=future(NOW+timedelta(hours=73))
        self.assertEqual(parse_schedule(fixture_schedule(game),NOW,lookahead_hours=72),[])
        game=future(NOW+timedelta(hours=65))
        game["teams"]["home"]["team"]={"id":5517,"name":"NL Higher Seed"}
        self.assertEqual(parse_schedule(fixture_schedule(game),NOW,lookahead_hours=72),[])
        game=future(NOW+timedelta(hours=65))
        game["teams"]["away"]["team"]={"id":5525,"name":"NL Lower Seed"}
        self.assertEqual(parse_schedule(fixture_schedule(game),NOW,lookahead_hours=72),[])

    def test_no_extra_quotas_or_after_kickoff_status_claims(self):
        text=(ROOT/"mlb_live/run_mlb_refresh.sh").read_text()
        self.assertIn("--lookahead-hours 72 --feed-max-games 4 --weather-max-games 2",text)
        self.assertEqual(text.count("intelligence_warehouse.mlb_pregame_capture.capture_evidence"),1)
        self.assertLess(text.index("capture_evidence"),text.index("mlb_live_research_feature_freeze_v2"))
        self.assertLess(text.index("capture_evidence"),text.index("mlb_full_context_true_forward_shadow"))
        started=future(NOW+timedelta(hours=1))
        started["status"]={"detailedState":"In Progress","abstractGameState":"Live"}
        self.assertFalse(parse_schedule(fixture_schedule(started),NOW,lookahead_hours=72))


if __name__=="__main__":unittest.main()
