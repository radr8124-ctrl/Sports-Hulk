"""Prior-source 16-col MLB model only with a NEW quote after full context frozen."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
from copy import deepcopy
import json
import tempfile
import unittest

from intelligence_warehouse.historical_recovery.mlb_full_context_true_forward_shadow import (
    eligible_same_quote_full_context_shadow,
    append_first_full_context_prediction,
    MODEL_POSITIONAL_MAPPING,
    SHADOW_SCHEMA,
)

NOW=datetime(2026,10,8,23,30,tzinfo=timezone.utc)
START=datetime(2026,10,9,0,0,tzinfo=timezone.utc)
PRE=datetime(2026,10,8,23,23,22,tzinfo=timezone.utc)
QUOTE=datetime(2026,10,8,23,27,18,tzinfo=timezone.utc)
SHA='a'*64

def v4(player=501,ctx=PRE):
    return {
      'schema':'MLB_V4_TRUE_PREGAME_BEFORE_FUTURE_QUOTE_16TERM_CONTEXT_INPUTS_V1',
      'game_pk':849832,'player_id':player,
      'original_prequote_hitter_source_sha256':SHA,
      'full_team_context_first_frozen_at_utc':ctx.isoformat(),
      'verified_probable_park_source_first_frozen_at_utc':'2026-10-08T23:16:17Z',
      'original_game_first_pitch_utc':START.isoformat(),
      'historical_training_16_feature_model_schema':'MLB_HF_SPORTS_ZENITH_ASOF_MARKET_CONTEXT_SPEED_WALKS_RESEARCH_V1_20261008',
      'sixteen_model_components_except_market':[0.2,-0.3,-.1,-.22,-.14,1.,.1,.5,.34,1.,.3,1.,0.1,1.],
      'sixteen_model_component_names_except_market':[a for a,b in MODEL_POSITIONAL_MAPPING],
      'source_model_probability_or_bet_created':False,
      'needs_new_sportsbook_quote_after_context_freeze':True,
      'live_play_approved':False,
    }

def pair(book='draftkings',player=501,captured=QUOTE,p=.58,overround=1.05):
    provider='opaque-unique-'+str(player)
    over_probability=p*overround
    under_probability=(1-p)*overround
    assert .01<over_probability<.99 and .01<under_probability<.99
    to_american=lambda prob: (-100*prob/(1-prob) if prob>=.5 else 100*(1-prob)/prob)
    over_american=to_american(over_probability)
    under_american=to_american(under_probability)
    side=lambda which:{
      'provider':'sportwizzard','sportsbook':book,
      'event_id':'MLB_PROVIDER_EVENT_ID', 'player_id':provider,
      'player':'Official Player '+str(player),
      'line':.5,'market_subtype':'PLAYER_TOTAL_HITS',
      'captured_at':captured.isoformat(),'side':which,
      'price_american':over_american if which=='OVER' else under_american,
    }
    return {
      'schema':'MLB_V2_PREGAME_SAME_BOOK_FAIR_PRICE_BASELINE_V1',
      'official_game_pk':849832,'mlbam_player_id':player,
      'player_name_official':'Official Player '+str(player),
      'original_lineup_source_line_sha256':SHA,
      'original_frozen_lineup_feature_at_utc':'2026-10-08T20:49:50Z',
      'fixture_scheduled_start_utc':START.isoformat(),
      'source_snapshot_quote_at_utc':captured.isoformat(),
      'sportsbook':book,'provider':'sportwizzard',
      'provider_event_id':'MLB_PROVIDER_EVENT_ID',
      'provider_player_id':provider,
      'market_metric':'hits','market_subtype':'PLAYER_TOTAL_HITS','line':.5,
      'book_overround':overround,
      'market_fair_probability_over':p,
      'market_fair_probability_under':1-p,
      'price_over_american':over_american,'price_under_american':under_american,
      'source_raw_market_csv_sha256':'b'*64,
      'source_mlbam_fusion_csv_sha256':'c'*64,
      'provider_player_id':provider,
      'over_provider_source_row':side('OVER'),
      'under_provider_source_row':side('UNDER'),
      'model_prediction_created':False,
      'betting_selection_approved':False,
    }

def model():
    names=['intercept','market_fair_logit']+[b for a,b in MODEL_POSITIONAL_MAPPING]
    return {
      'model_version':'MLB_HF_SPORTS_ZENITH_ASOF_MARKET_CONTEXT_SPEED_WALKS_RESEARCH_V1_20261008',
      'feature_names':names,
      'with_speed_walks_beta':[0.1,.9]+[.1]*14,
      'market_calibration_beta':[0.2,.88],
      'training_independent_games':90,
      'training_official_game_pks':list(range(900000,900090)),
      'training_last_start':'2026-06-18T22:00:00Z',
      'train_july_outcomes_used':False,
      'live_plays_approved':False,
    }

class MLBProspectiveFullContextTests(unittest.TestCase):
    def test_same_eligible_quote_pays_off_market_and_16feature_probabilities(self):
        rows,s=eligible_same_quote_full_context_shadow(
            [v4()], [pair()], model(),now=NOW,
            original_model_sha256='d'*64,
            source_fusion_sha256='e'*64,
            source_market_snapshot_sha256='f'*64,
        )
        self.assertEqual(len(rows),1)
        r=rows[0]
        self.assertEqual(len(r['model_16_features']),16)
        self.assertEqual(r['market_fair_prob_at_exact_new_quote'],.58)
        self.assertEqual(r['official_game_pk'],849832)
        self.assertTrue(0<r['market_only_calibrated_prob_at_same_new_quote']<1)
        self.assertTrue(0<r['sixteen_feature_context_shadow_prob']<1)
        self.assertFalse(r['probable_pitcher_confirmed_starter_model_input'])
        self.assertFalse(r['betting_play_approved'])
        self.assertFalse(r['model_market_edge_proven'])
        self.assertFalse(r['wager_executed'])
        self.assertEqual(s['independent_games'],1)

    def test_earlier_quotes_cannot_steal_later_captured_pitcher_park_context(self):
        original=pair(captured=PRE-timedelta(minutes=1))
        res,_=eligible_same_quote_full_context_shadow([v4()],[original],model(),now=NOW,
            original_model_sha256='d'*64,source_fusion_sha256='e'*64,source_market_snapshot_sha256='f'*64)
        self.assertEqual(res,[])
        future=pair(captured=START+timedelta(minutes=1))
        res,_=eligible_same_quote_full_context_shadow([v4()],[future],model(),now=NOW,
            original_model_sha256='d'*64,source_fusion_sha256='e'*64,source_market_snapshot_sha256='f'*64)
        self.assertEqual(res,[])

    def test_no_snapshot_if_model_executed_after_kickoff(self):
        res,_=eligible_same_quote_full_context_shadow([v4()],[pair()],model(),
            now=START+timedelta(seconds=3),
            original_model_sha256='d'*64,source_fusion_sha256='e'*64,
            source_market_snapshot_sha256='f'*64)
        self.assertEqual(res,[])

    def test_wrong_original_source_player_hash_or_wrong_game_not_forecast(self):
        bad=v4()
        bad['original_prequote_hitter_source_sha256']='9'*64
        with self.assertRaisesRegex(ValueError,'source|SHA'):
            eligible_same_quote_full_context_shadow([bad],[pair()],model(),now=NOW,
               original_model_sha256='d'*64,source_fusion_sha256='e'*64,source_market_snapshot_sha256='f'*64)
        bad=v4(player=999)
        with self.assertRaisesRegex(ValueError,'identity'):
            eligible_same_quote_full_context_shadow([bad],[pair()],model(),now=NOW,
               original_model_sha256='d'*64,source_fusion_sha256='e'*64,source_market_snapshot_sha256='f'*64)

    def test_different_book_or_player_uuid_over_under_never_calibrated(self):
        mismatched=pair()
        mismatched['under_provider_source_row']['sportsbook']='differentbook'
        with self.assertRaisesRegex(ValueError,'same.book|pair'):
            eligible_same_quote_full_context_shadow([v4()],[mismatched],model(),now=NOW,
                original_model_sha256='d'*64,source_fusion_sha256='e'*64,source_market_snapshot_sha256='f'*64)

    def test_quote_book_choice_is_deterministic_min_vig_not_after_the_results(self):
        raw=[pair(book='fanduel',p=.56,overround=1.08),
             pair(book='draftkings',p=.60,overround=1.03)]
        pred,summary=eligible_same_quote_full_context_shadow([v4()],raw,model(),now=NOW,
            original_model_sha256='d'*64,source_fusion_sha256='e'*64,source_market_snapshot_sha256='f'*64)
        self.assertEqual(len(pred),1)
        self.assertEqual(pred[0]['selected_sportsbook'],'draftkings')
        self.assertEqual(pred[0]['market_fair_prob_at_exact_new_quote'],.60)
        self.assertFalse(summary['profitability_proven'])

    def test_duplicate_v4_player_game_refused_and_16_col_unknown_coefficient_refused(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):
            eligible_same_quote_full_context_shadow([v4(),v4()],[pair()],model(),now=NOW,
                 original_model_sha256='d'*64,source_fusion_sha256='e'*64,source_market_snapshot_sha256='f'*64)
        bad=model();bad['with_speed_walks_beta']=[0.1,0.9]
        with self.assertRaisesRegex(ValueError,'coefficient|16'):
            eligible_same_quote_full_context_shadow([v4()],[pair()],bad,now=NOW,
                 original_model_sha256='d'*64,source_fusion_sha256='e'*64,source_market_snapshot_sha256='f'*64)

    def test_immutable_forward_probability_and_first_frozen_original_quote(self):
        res,_=eligible_same_quote_full_context_shadow([v4()],[pair()],model(),now=NOW,
             original_model_sha256='d'*64,source_fusion_sha256='e'*64,source_market_snapshot_sha256='f'*64)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'FORECAST.jsonl'
            self.assertEqual(append_first_full_context_prediction(p,res),1)
            content=p.read_bytes()
            self.assertEqual(append_first_full_context_prediction(p,res),0)
            self.assertEqual(content,p.read_bytes())
            changed=deepcopy(res)
            changed[0]['sixteen_feature_context_shadow_prob']=.0002
            with self.assertRaisesRegex(ValueError,'conflict'):
                append_first_full_context_prediction(p,changed)
            self.assertEqual(content,p.read_bytes())

if __name__=='__main__':unittest.main()
