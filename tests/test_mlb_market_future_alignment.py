"""Book/source fixture crosswalk must reject stale times and phantom prop pairs."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
import json
import pandas as pd
import unittest
from intelligence_warehouse.mlb_pregame_capture.audit_upcoming_market_alignment import (
    audit_quotes,source_proof,digest,
)

NOW=datetime(2026,10,9,8,5,tzinfo=timezone.utc)
START="2026-10-11T00:00:00Z"
HOME="Cleveland Guardians"
AWAY="Chicago White Sox"


def fixture():
    return {849831:{
        "pk":849831,"start":datetime(2026,10,11,0,tzinfo=timezone.utc),
        "home":HOME,"away":AWAY,"lineup_confirmed":False,
    }}


def odds(side,*,source_start=START,price=-110,player="player-1",book="thescore",
         capture="2026-10-09T08:02:00+00:00",event="uuid-event",line=.5,kind="PLAYER_TOTAL_HITS"):
    return {
        "provider":"sportwizzard","sportsbook":book,"event_id":event,
        "start":source_start,"away_team":AWAY,"home_team":HOME,
        "market":"PLAYER_TOTAL","market_subtype":kind,
        "selection":"Test Player "+side,
        "side":side,"line":line,"price_american":price,
        "player_id":player,"player":"Test Player",
        "captured_at":capture,
    }


class TestSourceMarketIdentityAudit(unittest.TestCase):
    def test_exact_valid_original_both_sides_are_research_pairs(self):
        data=pd.DataFrame([odds("OVER",price=-115),odds("UNDER",price=-105)])
        out=audit_quotes(data,fixture(),NOW)
        self.assertEqual(out["book_player_exact_same_source_time_pairs_accepted"],1)
        self.assertEqual(out["per_official_game"][0]["source_bookmakers_with_identity_matched_pairs"],["thescore"])
        self.assertFalse(out["per_official_game"][0]["can_freeze_new_full16_prediction_now"])

    def test_two_hour_stale_provider_event_must_not_mix_with_good_source(self):
        old="2026-10-10T21:00:00Z"
        data=pd.DataFrame([
            odds("OVER",source_start=old,price=-110),
            odds("UNDER",source_start=old,price=-112),
            odds("OVER",book="draftkings",price=-110),
            odds("UNDER",book="draftkings",price=-110),
        ])
        out=audit_quotes(data,fixture(),NOW)
        self.assertEqual(out["book_player_exact_same_source_time_pairs_accepted"],1)
        self.assertEqual(out["rejected_source_row_reasons"]["STALE_PROVIDER_FIXTURE_START"],2)

    def test_cross_book_side_mixing_cannot_be_paired(self):
        data=pd.DataFrame([odds("OVER",book="draftkings"),odds("UNDER",book="thescore")])
        out=audit_quotes(data,fixture(),NOW)
        self.assertEqual(out["book_player_exact_same_source_time_pairs_accepted"],0)

    def test_duplicate_same_book_side_fails_pair(self):
        data=pd.DataFrame([odds("OVER"),odds("OVER",price=-105),odds("UNDER")])
        out=audit_quotes(data,fixture(),NOW)
        self.assertEqual(out["book_player_exact_same_source_time_pairs_accepted"],0)
        self.assertEqual(out["rejected_source_row_reasons"]["MISSING_UNIQUE_SAME_BOOK_PAIR"],3)

    def test_milestone_yes_and_nonhalf_line_not_two_sided_hits(self):
        data=pd.DataFrame([odds("YES",kind="PLAYER_HITS",line=None),odds("OVER",line=1.5)])
        out=audit_quotes(data,fixture(),NOW)
        self.assertEqual(out["book_player_exact_same_source_time_pairs_accepted"],0)
        self.assertEqual(out["rejected_source_row_reasons"]["NOT_EXACT_TWO_SIDED_PLAYER_TOTAL_HITS"],1)

    def test_older_aggregator_capture_cannot_claim_new_quote(self):
        data=pd.DataFrame([odds("OVER",capture="2026-10-09T07:00:00+00:00"),
                           odds("UNDER",capture="2026-10-09T07:00:00+00:00")])
        out=audit_quotes(data,fixture(),NOW)
        self.assertEqual(out["book_player_exact_same_source_time_pairs_accepted"],0)
        self.assertEqual(out["rejected_source_row_reasons"]["SOURCE_CAPTURE_NOT_RECENT_PREGAME"],2)

    def test_invalid_american_book_price_rejected(self):
        data=pd.DataFrame([odds("OVER",price=-25),odds("UNDER",price=-110)])
        out=audit_quotes(data,fixture(),NOW)
        self.assertEqual(out["book_player_exact_same_source_time_pairs_accepted"],0)

    def test_source_proof_requires_exact_schedule_master_identity(self):
        schedule={"dates":[{"date":"2026-10-10","games":[{
            "gamePk":849831,"gameDate":START,"status":{"detailedState":"Scheduled"},
            "teams":{
                "home":{"team":{"id":114,"name":HOME}},
                "away":{"team":{"id":145,"name":AWAY}},
            },"venue":{"id":5,"name":"Progressive Field"},
        }]}]}
        raw=json.dumps(schedule,sort_keys=True,separators=(",",":")).encode()
        sha=digest(raw)
        cache={"schedule":schedule,"canonical_payload_sha256":sha,
               "captured_at_utc":"2026-10-09T08:03:00+00:00"}
        readiness={
            "at_utc":"2026-10-09T08:04:00+00:00",
            "official_schedule_source_receipt":{"source_sha256":sha,
                "captured_at_utc":"2026-10-09T08:03:00+00:00"},
            "next_games":[{"game_pk":849831,"status":"EXACT_SOURCE_FIXTURE_MATCH",
                "official_start":"2026-10-11T00:00:00+00:00","official_lineup_verified":False}],
        }
        master=pd.DataFrame([{"gamePk":849831,"gameDate":START,
                "home_team":HOME,"away_team":AWAY,
                "home_team_id":114,"away_team_id":145,"venue_id":5}])
        ok=source_proof(readiness,cache,master,NOW)
        self.assertEqual(list(ok),[849831])
        self.assertFalse(ok[849831]["lineup_confirmed"])
        bad=master.copy();bad.loc[0,"away_team_id"]=999
        self.assertEqual(source_proof(readiness,cache,bad,NOW),{})
        schedule["dates"][0]["games"][0]["startTimeTBD"]=True
        newcanon=json.dumps(schedule,sort_keys=True,separators=(",",":")).encode()
        cache["canonical_payload_sha256"]=digest(newcanon)
        readiness["official_schedule_source_receipt"]["source_sha256"]=digest(newcanon)
        self.assertEqual(source_proof(readiness,cache,master,NOW),{})
        cache["canonical_payload_sha256"]="wrong"
        with self.assertRaisesRegex(ValueError,"HASH_CHANGED"):
            source_proof(readiness,cache,master,NOW)

    def test_back_to_back_playoff_same_opponents_are_distinguished_by_exact_start(self):
        second_start=(datetime(2026,10,12,0,tzinfo=timezone.utc))
        second=dict(pk=849812,start=second_start,
                    home=HOME,away=AWAY,lineup_confirmed=False)
        new_start=second_start.isoformat()
        quotes=pd.DataFrame([
            odds("OVER",event="event-game-one",player="same-athlete",price=-115),
            odds("UNDER",event="event-game-one",player="same-athlete",price=-105),
            odds("OVER",source_start=new_start,event="event-game-two",player="same-athlete",price=-115),
            odds("UNDER",source_start=new_start,event="event-game-two",player="same-athlete",price=-105),
        ])
        result=audit_quotes(quotes,{**fixture(),849812:second},NOW)
        self.assertEqual(result["book_player_exact_same_source_time_pairs_accepted"],2)
        self.assertEqual(set(result["official_game_blocks"]),{849831,849812})

    def test_reused_provider_event_identity_across_two_games_cannot_be_paired(self):
        second_start=datetime(2026,10,12,0,tzinfo=timezone.utc)
        second=dict(pk=849812,start=second_start,
                    home=HOME,away=AWAY,lineup_confirmed=False)
        rows=[
            odds("OVER",event="reused-event",price=-115),
            odds("UNDER",event="reused-event",price=-105),
            odds("OVER",source_start=second_start.isoformat(),event="reused-event",price=-115),
            odds("UNDER",source_start=second_start.isoformat(),event="reused-event",price=-105),
        ]
        result=audit_quotes(pd.DataFrame(rows),{**fixture(),849812:second},NOW)
        self.assertEqual(result["book_player_exact_same_source_time_pairs_accepted"],0)
        self.assertEqual(result["rejected_source_row_reasons"]["PROVIDER_EVENT_ID_MAPPED_TO_MULTIPLE_OFFICIAL_GAMES"],4)

    def test_existing_refresh_runs_market_audit_only_after_official_identity(self):
        from pathlib import Path
        driver=Path("/home/ubuntu/sports-hulk/mlb_live/run_mlb_refresh.sh").read_text()
        name="intelligence_warehouse.mlb_pregame_capture.audit_upcoming_market_alignment"
        self.assertEqual(driver.count(name),1)
        self.assertLess(driver.index("mlb-official-fixture-readiness"),driver.index(name))
        self.assertLess(driver.index("mlb-full16-selective70-future-research"),driver.index(name))
        self.assertIn("SPORTS_MAX_SECONDS=12",driver)
        self.assertIn("original odds, context and games preserved",driver)


if __name__=="__main__":unittest.main()
