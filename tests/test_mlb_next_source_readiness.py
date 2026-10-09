"""Verified MLB fixture readiness must not infer odds or rewrite game start."""
import unittest
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

from intelligence_warehouse.mlb_pregame_capture.build_forward_readiness import audit, verified_lineup, official_fixtures

NOW=datetime(2026,10,9,5,30,tzinfo=timezone.utc)
START="2026-10-10T23:30:00Z"
def official(pk=849900, start=START, h="Cleveland Guardians", a="Chicago White Sox"):
    return {"dates":[{"date":"2026-10-10","games":[{
        "gamePk":pk,"gameDate":start,"gameType":"D","status":{"detailedState":"Scheduled"},
        "teams":{"home":{"team":{"id":114,"name":h}},"away":{"team":{"id":145,"name":a}}},
    }]}]}

def master(pk=849900,start=START, home="Cleveland Guardians",away="Chicago White Sox"):
    return pd.DataFrame([{"gamePk":pk,"gameDate":start,"status":"Scheduled",
        "home_team":home,"away_team":away,"home_team_id":114,"away_team_id":145}])

def evidence(pk=849900, scheduled=START):
    ids=list(range(101,110))
    return {"game_pk":pk, "captured_at_utc":"2026-10-09T05:00:00Z",
        "first_pitch_utc":scheduled,
        "lineups":{"status":"OFFICIAL_BATTING_ORDER_VISIBLE_BEFORE_KICKOFF",
                   "home":{"player_ids":ids,"confirmed_asof_capture":True},
                   "away":{"player_ids":list(range(201,210)),"confirmed_asof_capture":True}}}

def check(official_schedule=None,master_data=None,evidence_records=None,v2=None,v3=None,v4=None,forecast=None,graded=None):
    return audit(official_schedule or official(),master_data if master_data is not None else master(),
                 evidence_records if evidence_records is not None else [],
                 v2 or [], v3 or [], v4 or [], forecast or [],graded or [],now=NOW)


class TestForwardMLBOfficialReadiness(unittest.TestCase):
    def test_exact_official_fixture_and_verified_full_lineup(self):
        x=check(evidence_records=[evidence()])
        game=x["next_games"][0]
        self.assertEqual(game["status"],"EXACT_SOURCE_FIXTURE_MATCH")
        self.assertTrue(game["source_eligible_for_new_model_research"])
        self.assertEqual(x["official_scheduled_game_count"],1)

    def test_three_hour_stale_master_not_model_ready(self):
        x=check(master_data=master(start="2026-10-10T20:30:00Z"),evidence_records=[evidence()])
        self.assertEqual(x["next_games"][0]["status"],"OFFICIAL_START_MISMATCH_REQUIRES_SOURCE_REPAIR")
        self.assertFalse(x["next_games"][0]["source_eligible_for_new_model_research"])

    def test_conditional_master_game_absent_in_official_quarantined(self):
        stale=pd.concat([master(),master(pk=849901)],ignore_index=True)
        x=check(master_data=stale)
        self.assertEqual(x["fixture_status_counts"]["MASTER_GAME_NOT_ON_CURRENT_OFFICIAL_SCHEDULE"],1)

    def test_placeholder_participants_quarantined(self):
        x=check(master_data=master(home="AL Higher Seed",away="AL Lower Seed"))
        self.assertEqual(x["next_games"][0]["status"],"PARTICIPANTS_NOT_RESOLVED")

    def test_missing_lineup_never_promoted(self):
        x=check()
        self.assertFalse(x["next_games"][0]["official_lineup_verified"])
        self.assertFalse(x["next_games"][0]["source_eligible_for_new_model_research"])

    def test_source_lineup_fake_confirmed_fails(self):
        s=evidence()
        s["lineups"]["home"]["player_ids"]=[101]*9
        self.assertFalse(verified_lineup(s,datetime(2026,10,10,23,30,tzinfo=timezone.utc)))

    def test_source_lineup_wrong_clock_is_not_confirmation(self):
        s=evidence(scheduled="2026-10-11T02:30:00Z")
        self.assertFalse(verified_lineup(s,datetime(2026,10,10,23,30,tzinfo=timezone.utc)))

    def test_only_official_new_game_not_already_in_master(self):
        x=check(master_data=master(pk=849901))
        self.assertEqual(x["fixture_status_counts"]["OFFICIAL_GAME_MISSING_FROM_MASTER_WINDOW"],1)

    def test_source_position_complete_is_not_starter_or_model(self):
        x=check(evidence_records=[evidence()],v2=[{"game_pk":849900,"player_id":101}])
        self.assertEqual(x["next_games"][0]["v2_players_frozen"],1)
        self.assertEqual(x["next_games"][0]["v4_model_forecasts_frozen"],0)
        self.assertFalse(x["paid_bets_or_model_changes"])

    def test_same_book_starter_is_not_inferred_by_source(self):
        s=evidence()
        del s["lineups"]["away"]
        self.assertFalse(verified_lineup(s,datetime(2026,10,10,23,30,tzinfo=timezone.utc)))

    def test_official_repeated_pk_disallowed(self):
        x=official()
        x["dates"][0]["games"].append(dict(x["dates"][0]["games"][0]))
        with self.assertRaisesRegex(ValueError,"DUPLICATE_OFFICIAL_GAME_PK"):
            official_fixtures(x)

    def test_operational_ten_minute_refresh_has_isolated_readiness_check(self):
        driver=Path('/home/ubuntu/sports-hulk/mlb_live/run_mlb_refresh.sh').read_text()
        self.assertEqual(driver.count('intelligence_warehouse.mlb_pregame_capture.build_forward_readiness'),1)
        self.assertLess(driver.find('run_mlb_learning_postrefresh.sh'),driver.find('mlb-official-fixture-readiness'))
        self.assertLess(driver.find('mlb-official-fixture-readiness'),driver.find('MLB REFRESH COMPLETE'))
        self.assertIn('SPORTS_MAX_SECONDS=16',driver)
        self.assertIn('original master, source and forecasts preserved',driver)


if __name__=="__main__":unittest.main()
