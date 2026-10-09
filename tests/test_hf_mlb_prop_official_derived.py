"""Research-grade boxscore outcomes may fill absent vendor grades; never overwrite conflicts."""
import unittest
import pandas as pd
from intelligence_warehouse.betting_v2.hf_mlb_prop_official_derived import derive_missing_vendor_outcomes


def official(**kw):
    base=dict(game_pk=823077,player='Alec Burleson',game_date='2026-03-31T23:45:00Z',
       group='HITTING',plate_appearances=4.,outs=None,hits=2.,total_bases=3.,rbi=1.,home_runs=0.,walks=0.,strikeouts=1.)
    base.update(kw);return base


def record(**kw):
    base=dict(status='MISSING_VENDOR_OUTCOME',official_game_pk=823077,official_group='HITTING',
      player='alec burleson',market='player hits',side='over',line=1.5,odds=1.8,
      result=None,won=None,timestamp_before_official_start=True)
    base.update(kw);return base


class OfficialDerivedHistoricalTests(unittest.TestCase):
    def test_derive_hit_grade_strictly_from_unique_official_stat_and_player_participation(self):
        rows=derive_missing_vendor_outcomes([record()],pd.DataFrame([official()]))
        self.assertEqual(rows[0]['status'],'OFFICIAL_DERIVED_HISTORICAL')
        self.assertTrue(rows[0]['verified_win'])
        self.assertEqual(rows[0]['official_stat'],2.0)
        self.assertEqual(rows[0]['provider_grade_state'],'UNAVAILABLE_NOT_SETTLED_BY_VENDOR')
        self.assertFalse(rows[0]['platform_settlement_claim'])
        self.assertEqual(rows[0]['source_graded'],False)

    def test_vendor_conflicts_and_ambiguous_fixtures_never_rescued(self):
        for value in ['RESULT_DISAGREES_WITH_OFFICIAL','CONFLICTING_PROVIDER_GAME_ID','NO_UNIQUE_PLAYER_GAME_MATCH']:
            with self.subTest(value=value):
                r=derive_missing_vendor_outcomes([record(status=value)],pd.DataFrame([official()]))[0]
                self.assertEqual(r['status'],value)

    def test_unplayed_player_never_fabricated_as_over_under(self):
        r=derive_missing_vendor_outcomes([record()],pd.DataFrame([official(plate_appearances=0)]))[0]
        self.assertNotEqual(r['status'],'OFFICIAL_DERIVED_HISTORICAL')

    def test_no_duplicate_official_person_records_may_be_merged(self):
        x=pd.DataFrame([official(),official(player='Alec Burleson',hits=1.)])
        r=derive_missing_vendor_outcomes([record()],x)[0]
        self.assertNotEqual(r['status'],'OFFICIAL_DERIVED_HISTORICAL')

    def test_market_push_and_half_missing_vendor_result_not_accepted(self):
        a=derive_missing_vendor_outcomes([record(line=2.)],pd.DataFrame([official()]))[0]
        self.assertNotEqual(a['status'],'OFFICIAL_DERIVED_HISTORICAL')
        b=derive_missing_vendor_outcomes([record(result=2.,won=None)],pd.DataFrame([official()]))[0]
        self.assertNotEqual(b['status'],'OFFICIAL_DERIVED_HISTORICAL')

    def test_pitcher_k_only_if_pitcher_actually_recorded_outs(self):
        h=official(player='Dylan Cease',group='PITCHING',plate_appearances=None,outs=14.,strikeouts=8.)
        r=record(player='dylan cease',official_group='PITCHING',market='player strikeouts',line=7.5)
        x=derive_missing_vendor_outcomes([r],pd.DataFrame([h]))[0]
        self.assertEqual(x['status'],'OFFICIAL_DERIVED_HISTORICAL')
        self.assertTrue(x['verified_win'])
        y=derive_missing_vendor_outcomes([r],pd.DataFrame([official(**{**h,'outs':0.})]))[0]
        self.assertNotEqual(y['status'],'OFFICIAL_DERIVED_HISTORICAL')

if __name__=='__main__':unittest.main()
