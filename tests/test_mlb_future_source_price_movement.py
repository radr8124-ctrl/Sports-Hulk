"""Prospective price-movement research: chronology, market identity, and durability."""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
import copy,hashlib,json,shutil,tempfile,unittest
from pathlib import Path

import pandas as pd

from intelligence_warehouse.mlb_pregame_capture import freeze_source_price_movement as m

ROOT=m.ROOT
NOW=datetime(2026,10,9,8,7,tzinfo=timezone.utc)
REGISTERED=datetime(2026,10,9,7,50,tzinfo=timezone.utc)
START=datetime(2026,10,11,0,tzinfo=timezone.utc)


def fixture(start=START):
    return {849831:{"pk":849831,"start":start,
                    "home":"Cleveland Guardians","away":"Chicago White Sox",
                    "lineup_confirmed":False}}


def marketrows(captured,*,book="thescore",event="game-vendor-uuid",
               player="provider-player-uuid",homename="Cleveland Guardians",
               awayname="Chicago White Sox",start=START,over=-110,under=-110):
    return [
        {
            "provider":"sportwizzard","sportsbook":book,
            "event_id":event,"start":start.isoformat(),
            "away_team":awayname,"home_team":homename,
            "market":"PLAYER_TOTAL","market_subtype":"PLAYER_TOTAL_HITS",
            "selection":"Player "+side+" 0.5",
            "side":side,"line":.5,
            "price_american":price,
            "player_id":player,"player":"Player One",
            "captured_at":captured.isoformat(),
        }
        for side,price in (("OVER",over),("UNDER",under))
    ]


class TestFrozenMLBPriceMovement(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.dir=Path(self.tmp.name)
        self.spec=json.loads(m.SPEC.read_text())
        self.old_at=datetime(2026,10,9,6,0,tzinfo=timezone.utc)
        self.new_at=datetime(2026,10,9,8,0,tzinfo=timezone.utc)

    def make(self,now,snapshot):
        path=self.dir/("MLB_PLAYER_PROP_MARKET_"+now.strftime("%Y%m%dT%H%M%SZ")+".csv")
        pd.DataFrame(snapshot).to_csv(path,index=False)
        return path

    def pair(self,*,old_over=-110,old_under=-110,new_over=-170,new_under=140,
             new_start=START):
        prior=self.make(self.old_at,marketrows(self.old_at,over=old_over,under=old_under,start=new_start))
        current=self.make(self.new_at,marketrows(self.new_at,over=new_over,under=new_under,start=new_start))
        return prior,current

    def study(self,sources,*,now=NOW,registered=REGISTERED,fixtures=None):
        return m.movement_candidates(
            self.dir,self.spec,fixtures if fixtures is not None else fixture(),now,registered,
            scan_files=sources,
        )

    def test_fixed_two_hour_pair_freezes_early_study_with_fair_probability(self):
        before,now=self.pair()
        frozen,rejected,n=self.study([before,now])
        self.assertEqual(n,2)
        self.assertEqual(len(frozen),1)
        x=frozen[0]
        self.assertEqual(x["official_game_pk"],849831)
        self.assertEqual(x["fixed_asof_horizon"],"EARLY_DISCOVERY")
        self.assertAlmostEqual(x["source_2hour_reference_age_minutes"],120)
        self.assertGreater(x["source_2hour_book_fair_over_movement_pp"],5)
        self.assertAlmostEqual(x["registered_fixed_trend_over_probability"],
                               min(.975,x["registered_unadjusted_market_over_probability"]+
                               .5*(x["source_2hour_book_fair_over_movement_pp"]/100)),places=7)
        self.assertFalse(x["independent_MLBAM_player_identity_matched"])
        self.assertFalse(x["production_bet_or_model_promotion"])

    def test_no_original_source_drift_if_only_one_paired_capture(self):
        _,current=self.pair()
        frozen,reasons,_=self.study([current])
        self.assertFalse(frozen)
        self.assertEqual(reasons["MISSING_ORIGINAL_SAME_BOOK_TWO_HOUR_REFERENCE"],1)

    def test_no_source_crossbook_pair(self):
        old,current=self.pair()
        first=marketrows(self.new_at,book="thescore")
        second=marketrows(self.new_at,book="draftkings")
        current.write_text(pd.DataFrame([first[0],second[1]]).to_csv(index=False))
        frozen,_,_=self.study([old,current])
        self.assertFalse(frozen)

    def test_unverified_provider_event_start_rejected_even_if_team_names_match(self):
        old,current=self.pair(new_start=START-timedelta(hours=2))
        frozen,reasons,_=self.study([old,current])
        self.assertFalse(frozen)
        self.assertEqual(reasons["WRONG_ORIGINAL_BOOK_GAME_START"],4)

    def test_same_book_exact_source_quote_side_duplication_is_rejected(self):
        old,current=self.pair()
        values=marketrows(self.new_at)
        current.write_text(pd.DataFrame([*values,values[0]]).to_csv(index=False))
        frozen,reasons,_=self.study([old,current])
        self.assertFalse(frozen)
        self.assertEqual(reasons["SOURCE_NOT_UNIQUE_EXACT_SAME_BOOK_TWO_SIDES"],3)

    def test_only_current_quotes_after_preregistration_can_create_forward_evidence(self):
        old,current=self.pair()
        frozen,_,_=self.study([old,current],registered=self.new_at+timedelta(seconds=10))
        self.assertFalse(frozen)

    def test_prior_gap_outside_fixed_90_150_minutes_not_backfilled(self):
        early=self.make(self.old_at-timedelta(hours=4),marketrows(self.old_at-timedelta(hours=4)))
        current=self.make(self.new_at,marketrows(self.new_at))
        frozen,_,_=self.study([early,current])
        self.assertFalse(frozen)

    def test_source_both_sides_must_have_same_original_capture_timestamp(self):
        old,current=self.pair()
        rows=marketrows(self.new_at)
        rows[1]["captured_at"]=(self.new_at-timedelta(seconds=20)).isoformat()
        current.write_text(pd.DataFrame(rows).to_csv(index=False))
        frozen,reasons,_=self.study([old,current])
        self.assertFalse(frozen)
        self.assertEqual(reasons["OVER_UNDER_ORIGINAL_CAPTURE_TIME_NOT_SAME"],2)

    def test_future_windows_are_fixed_before_game(self):
        now=self.new_at
        self.assertEqual(m.horizon(24.10,self.spec),"H24")
        self.assertEqual(m.horizon(4.10,self.spec),"H4")
        self.assertEqual(m.horizon(1.10,self.spec),"H1")
        self.assertEqual(m.horizon(40,self.spec),"EARLY_DISCOVERY")
        self.assertIsNone(m.horizon(.5,self.spec))
        self.assertIsNone(m.horizon(75,self.spec))

    def test_book_source_priority_fixed_not_hindsight_best_price(self):
        old,current=self.pair()
        first=pd.read_csv(old)
        latest=pd.read_csv(current)
        first=pd.concat([first,pd.DataFrame(marketrows(self.old_at,book="draftkings",over=-110,under=-110))],ignore_index=True)
        latest=pd.concat([latest,pd.DataFrame(marketrows(self.new_at,book="draftkings",over=-300,under=220))],ignore_index=True)
        first.to_csv(old,index=False)
        latest.to_csv(current,index=False)
        frozen,_,_=self.study([old,current])
        self.assertEqual(len(frozen),1)
        self.assertEqual(frozen[0]["source_sportsbook"],"thescore")

    def test_future_after_kickoff_cannot_create_new_evidence(self):
        old,current=self.pair()
        # The original quotes remain pregame, but the process now runs after
        # independently known kickoff: no valid upcoming fixture exists.
        later=START+timedelta(minutes=10)
        frozen,_,_=self.study([old,current],now=later,fixtures={})
        self.assertFalse(frozen)

    def test_saved_source_hash_readback_refuses_tampering(self):
        old,current=self.pair()
        frozen,_,_=self.study([old,current])
        self.assertEqual(len(frozen),1)
        x=frozen[0]
        home=self.dir/"isolated_original"
        folder=home/"mlb_live/markets/history"
        folder.mkdir(parents=True)
        for field in ("original_current_raw_archive","original_prior_raw_archive"):
            fname=Path(x[field]).name
            shutil.copy2(self.dir/fname,folder/fname)
            x[field]="mlb_live/markets/history/"+fname
        verified=m.verify_frozen_archive_lineage([x],root=home,spec=self.spec)
        self.assertEqual(verified["frozen_rows_hash_verified"],1)
        self.assertEqual(verified["distinct_original_market_snapshots_sha256_readback"],2)
        bad=dict(x,original_prior_raw_sha256="1"*64)
        with self.assertRaisesRegex(ValueError,"SHA256_CHANGED"):
            m.verify_frozen_archive_lineage([bad],root=home,spec=self.spec)
        with (folder/Path(x["original_prior_raw_archive"]).name).open("a") as f:f.write("tampered")
        with self.assertRaisesRegex(ValueError,"SHA256_CHANGED"):
            m.verify_frozen_archive_lineage([x],root=home,spec=self.spec)

    def test_append_first_record_is_idempotent_and_never_reprices(self):
        old,current=self.pair()
        frozen,_,_=self.study([old,current])
        ledger=self.dir/"research.jsonl"
        self.assertEqual(m.append_rows(ledger,frozen),1)
        original=ledger.read_bytes()
        changed=[dict(frozen[0],registered_fixed_trend_over_probability=.90)]
        self.assertEqual(m.append_rows(ledger,changed),0)
        self.assertEqual(ledger.read_bytes(),original)
        self.assertEqual(len(m.records(ledger)),1)

    def test_playoff_same_two_teams_next_day_uses_exact_original_start(self):
        old,current=self.pair()
        second={
            "pk":849812,
            "start":START+timedelta(days=1),
            "home":"Cleveland Guardians","away":"Chicago White Sox",
            "lineup_confirmed":False,
        }
        both={**fixture(),849812:second}
        frozen,_,_=self.study([old,current],fixtures=both)
        self.assertEqual(len(frozen),1)
        self.assertEqual(frozen[0]["official_game_pk"],849831)

    def test_reused_provider_event_uuid_across_two_games_fails_closed(self):
        old,current=self.pair()
        older=pd.concat([pd.read_csv(old),
             pd.DataFrame(marketrows(self.old_at,event="game-vendor-uuid",
                                     start=START+timedelta(days=1)))],ignore_index=True)
        newer=pd.concat([pd.read_csv(current),
             pd.DataFrame(marketrows(self.new_at,event="game-vendor-uuid",
                                     start=START+timedelta(days=1)))],ignore_index=True)
        older.to_csv(old,index=False)
        newer.to_csv(current,index=False)
        second={
            "pk":849812,"start":START+timedelta(days=1),
            "home":"Cleveland Guardians","away":"Chicago White Sox",
            "lineup_confirmed":False,
        }
        frozen,reasons,_=self.study([old,current],fixtures={**fixture(),849812:second})
        self.assertEqual(frozen,[])
        self.assertGreaterEqual(reasons.get("PROVIDER_EVENT_UUID_COLLIDES_BETWEEN_GAMES",0),8)

    def test_real_source_never_counts_original_full16_game_as_new(self):
        from hashlib import sha256
        raw=m.FROZEN.read_bytes()
        self.assertEqual(sha256(raw).hexdigest(),
           "0cea5e38c94451cacbc1ff552276c5df7aa1e341296b127fd0cfa6a2d19c66a8")
        self.assertEqual(len(raw.splitlines()),18)
        self.assertEqual({json.loads(x)["official_game_pk"] for x in raw.splitlines()}, {849832})


if __name__=="__main__":unittest.main()
