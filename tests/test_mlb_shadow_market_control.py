"""One pregame market-calibration shadow forecast per player, not per sportsbook."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
import json,tempfile,unittest

from intelligence_warehouse.historical_recovery.mlb_shadow_market_control import (
    build_shadow_market_control,append_immutable_shadow_predictions,shadow_cycle,
)

NOW=datetime(2026,10,8,22,0,tzinfo=timezone.utc)
FIRST=NOW+timedelta(hours=2)


def freeze_baseline(*,pid=501,book='draftkings',over=0.6,vig=1.05):
    return {
        'schema':'MLB_V2_PREGAME_SAME_BOOK_FAIR_PRICE_BASELINE_V1',
        'official_game_pk':849832,'mlbam_player_id':pid,
        'player_name_official':f'Official Player {pid}',
        'original_lineup_source_line_sha256':'a'*64,
        'original_frozen_lineup_feature_at_utc':(NOW-timedelta(minutes=45)).isoformat(),
        'original_pregame_evidence_id':'AUTHENTIC_PREQUOTE_LINEUP',
        'sportsbook':book,'provider':'sportwizzard',
        'market_metric':'hits','market_subtype':'PLAYER_TOTAL_HITS','line':0.5,
        'market_fair_probability_over':over,
        'market_fair_probability_under':1-over,
        'price_over_american':-120,'price_under_american':+100,
        'book_overround':vig,
        'source_snapshot_quote_at_utc':(NOW-timedelta(minutes=14)).isoformat(),
        'fixture_scheduled_start_utc':FIRST.isoformat(),
        'source_raw_market_csv_sha256':'b'*64,
        'source_mlbam_fusion_csv_sha256':'c'*64,
        'betting_selection_approved':False,
        'model_prediction_created':False,
    }


def trained_control():
    return {
        'model_version':'MLB_HF_SPORTS_ZENITH_ASOF_MARKET_CONTEXT_SPEED_WALKS_RESEARCH_V1_20261008',
        'training_independent_games':90,
        'training_last_start':'2026-06-16T18:00:00+00:00',
        'training_official_game_pks':list(range(900000,900090)),
        'market_calibration_beta':[0.2,0.85],
        'live_plays_approved':False,
        'train_july_outcomes_used':False,
        'july_outcomes_already_previously_examined_in_other_research':True,
    }


class MLBShadowMarketControlTruthTests(unittest.TestCase):
    def test_unique_independent_game_with_one_first_shadow_over_forecast_per_player(self):
        rows=[freeze_baseline(pid=501,book='draftkings',over=.54,vig=1.04),
              freeze_baseline(pid=501,book='thescore',over=.58,vig=1.09),
              freeze_baseline(pid=502,book='draftkings',over=.48,vig=1.08)]
        result,summary=build_shadow_market_control(rows,trained_control(),now=NOW,
                                                   original_model_sha256='f'*64)
        self.assertEqual(len(result),2)
        self.assertEqual(summary['independent_games'],1)
        self.assertEqual(summary['player_game_forecasts'],2)
        a=next(x for x in result if x['mlbam_player_id']==501)
        self.assertEqual(a['sportsbook_selected'],'draftkings')
        self.assertEqual(a['raw_no_vig_market_probability_over'],.54)
        self.assertGreater(a['calibrated_market_control_probability_over'],0)
        self.assertLess(a['calibrated_market_control_probability_over'],1)
        self.assertFalse(a['proprietary_speed_walks_model_evaluated'])
        self.assertFalse(a['market_edge_proven'])
        self.assertFalse(a['betting_play_authorized'])
        self.assertFalse(a['wager_submitted'])

    def test_stale_future_graded_or_same_game_training_cannot_be_shadow(self):
        model=trained_control()
        model['training_official_game_pks'].append(849832)
        with self.assertRaisesRegex(ValueError,'training'):
            build_shadow_market_control([freeze_baseline()],model,now=NOW,original_model_sha256='f'*64)
        forged=freeze_baseline()
        forged['source_snapshot_quote_at_utc']=(FIRST+timedelta(minutes=1)).isoformat()
        found,_=build_shadow_market_control([forged],trained_control(),now=NOW,original_model_sha256='f'*64)
        self.assertEqual(found,[])
        after,_=build_shadow_market_control([freeze_baseline()],trained_control(),
                                            now=FIRST+timedelta(minutes=1),original_model_sha256='f'*64)
        self.assertEqual(after,[])

    def test_invalid_no_vig_probability_or_forged_betting_writes_rejected(self):
        b=freeze_baseline();b['market_fair_probability_over']=1.5
        with self.assertRaisesRegex(ValueError,'probability'):
            build_shadow_market_control([b],trained_control(),now=NOW,original_model_sha256='f'*64)
        b=freeze_baseline();b['betting_selection_approved']=True
        with self.assertRaisesRegex(ValueError,'research'):
            build_shadow_market_control([b],trained_control(),now=NOW,original_model_sha256='f'*64)

    def test_prior_hits_calibrator_not_unjustifiably_applied_to_walking_or_total_bases(self):
        walks=freeze_baseline()
        walks['market_metric']='walks'
        walks['market_subtype']='PLAYER_TOTAL_BATTER_WALKS'
        total=freeze_baseline()
        total['market_metric']='total_bases'
        total['market_subtype']='PLAYER_TOTAL_TOTAL_BASES'
        expected,summary=build_shadow_market_control(
            [walks,total],trained_control(),now=NOW,original_model_sha256='f'*64,
        )
        self.assertEqual(expected,[])
        self.assertEqual(summary['player_game_forecasts'],0)

    def test_immutable_first_shadow_and_conflicting_fitted_probability_is_not_replaced(self):
        one,_=build_shadow_market_control([freeze_baseline()],trained_control(),
                                           now=NOW,original_model_sha256='f'*64)
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'FROZEN_SHADOW.jsonl'
            self.assertEqual(append_immutable_shadow_predictions(dest,one),1)
            initial=dest.read_bytes()
            self.assertEqual(append_immutable_shadow_predictions(dest,one),0)
            self.assertEqual(dest.read_bytes(),initial)
            updated=[{**one[0],'calibrated_market_control_probability_over':0.07}]
            with self.assertRaisesRegex(ValueError,'conflict'):
                append_immutable_shadow_predictions(dest,updated)
            self.assertEqual(dest.read_bytes(),initial)

    def test_new_best_vig_book_after_first_forecast_never_changes_frozen_prediction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/'PRICE.jsonl'
            model=root/'MODEL.json'
            shadow=root/'SHADOW.jsonl'
            model.write_text(json.dumps(trained_control())+'\n')
            source.write_text(json.dumps(freeze_baseline(vig=1.09))+'\n')
            first=shadow_cycle(source,model,shadow,now=NOW)
            self.assertEqual(first['new_shadow_forecasts'],1)
            frozen_original=shadow.read_bytes()
            with source.open('a') as f:
                f.write(json.dumps(freeze_baseline(book='thescore',over=.88,vig=1.01))+'\n')
            rerun=shadow_cycle(source,model,shadow,now=NOW+timedelta(minutes=1))
            self.assertEqual(rerun['new_shadow_forecasts'],0)
            self.assertEqual(shadow.read_bytes(),frozen_original)
            self.assertEqual(rerun['already_frozen_forecasts_preserved'],1)

    def test_model_coefficients_cannot_be_changed_after_frozen_pre_game_shadow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'PRICE.jsonl';model=root/'MODEL.json';shadow=root/'SHADOW.jsonl'
            source.write_text(json.dumps(freeze_baseline())+'\n')
            model.write_text(json.dumps(trained_control())+'\n')
            shadow_cycle(source,model,shadow,now=NOW)
            original=shadow.read_bytes()
            manipulated=trained_control()
            manipulated['market_calibration_beta']=[.99,.01]
            model.write_text(json.dumps(manipulated)+'\n')
            with self.assertRaisesRegex(ValueError,'model.*SHA'):
                shadow_cycle(source,model,shadow,now=NOW+timedelta(minutes=1))
            self.assertEqual(shadow.read_bytes(),original)

    def test_source_model_replay_contract_and_quote_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            raw=folder/'PAIRED.jsonl';m=folder/'FROZEN_MODEL.json';out=folder/'SHADOW.jsonl'
            raw.write_text(json.dumps(freeze_baseline())+'\n')
            m.write_text(json.dumps(trained_control())+'\n')
            first=shadow_cycle(raw,m,out,now=NOW)
            self.assertEqual(first['new_shadow_forecasts'],1)
            self.assertEqual(first['unique_independent_games'],1)
            self.assertEqual(first['actual_model_uses_sprint_speed_or_bat_speed'],False)
            self.assertFalse(first['paid_play_approved'])
            second=shadow_cycle(raw,m,out,now=NOW+timedelta(minutes=2))
            self.assertEqual(second['new_shadow_forecasts'],0)
            self.assertEqual(second['all_original_shadow_records'],1)

if __name__=='__main__':unittest.main()
