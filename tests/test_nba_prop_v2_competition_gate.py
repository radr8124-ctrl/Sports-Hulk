"""NBA Props V2 cannot borrow proven regular-season model status for preseason."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from intelligence_warehouse.betting_v2 import build_prop_v2 as builder

class NbaCompetitionV2Gate(unittest.TestCase):
    def base(self, **kwargs):
        row = {
            'event_id':'original-provider-event-id',
            'game_key':'2099-10-20|PHI|NYK',
            'start_dt':'2099-10-20T23:00:00+00:00',
            'player_key':'testperson', 'player':'Test Player',
            'market_subtype':'PLAYER_TOTAL_POINTS', 'side':'OVER', 'line':20.5,
            'decision':'EARLY_MARKET_WATCH', 'evidence_score':82,
            'median_price_american':-110, 'book_count':3,
            'sample_games':40, 'meaningful_games':35,
            'competition_regime':'REGULAR', 'season_type':'2',
            'competition_regime_source':'ESPN_SITE_SCOREBOARD_EXACT_GAME',
            'espn_event_id':'401909089',
        }
        row.update(kwargs)
        return row

    def test_official_source_and_explicit_type_required(self):
        cfg={'sport':'NBA'}
        good=builder.nba_competition_proof(pd.Series(self.base()),cfg)
        self.assertEqual(good['competition_regime'],'REGULAR')
        self.assertEqual(good['espn_event_id'],'401909089')
        for wrong in (
            {'season_type':'1'},
            {'competition_regime_source':'SCHEDULE_GUESSED'},
            {'espn_event_id':''},
            {'competition_regime':'UNKNOWN'},
        ):
            with self.subTest(wrong=wrong):
                self.assertEqual(builder.nba_competition_proof(pd.Series(self.base(**wrong)),cfg)['competition_regime'],'UNKNOWN')
        self.assertEqual(builder.nba_competition_proof(pd.Series(self.base()),{'sport':'NHL'}),{})

    def test_veto_cannot_promote_unverified_preseason_postseason(self):
        for regime, expected in (
            ('UNKNOWN','PASS_NBA_COMPETITION_UNVERIFIED'),
            ('PRESEASON','PASS_NBA_PRESEASON_MODEL_UNVALIDATED'),
            ('POSTSEASON','PASS_NBA_POSTSEASON_MODEL_UNVALIDATED'),
        ):
            with self.subTest(regime=regime):
                self.assertEqual(builder.nba_competition_veto('SHADOW_PLAY',{'competition_regime':regime}),expected)
        self.assertEqual(builder.nba_competition_veto('SHADOW_PLAY',{'competition_regime':'REGULAR'}),'SHADOW_PLAY')
        self.assertEqual(builder.nba_competition_veto('PASS_NO_EDGE',{}),'PASS_NO_EDGE')

    def test_actual_v2_builder_adds_metadata_and_regime_gate(self):
        cases=(
            (self.base(), 'REGULAR', 'PASS_INSUFFICIENT_HISTORY'),
            (self.base(season_type='1',competition_regime='PRESEASON'),
             'PRESEASON','PASS_NBA_PRESEASON_MODEL_UNVALIDATED'),
            (self.base(competition_regime_source=''),
             'UNKNOWN','PASS_NBA_COMPETITION_UNVERIFIED'),
        )
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/'nba.csv'
            cfg=dict(builder.LANES['NBA_PROP'],current=file)
            for record, regime, expected in cases:
                pd.DataFrame([record]).to_csv(file,index=False)
                with patch.object(builder,'devig_data',return_value={}), \
                     patch.object(builder,'segment_data',return_value={}):
                    rows=builder.build_current_lane('NBA_PROP',cfg,{'status':'INSUFFICIENT_HISTORY'})
                self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]['competition_regime'],regime)
                self.assertEqual(rows[0]['shadow_decision'],expected)
                self.assertFalse(rows[0]['live_pick_changed'])

if __name__=='__main__': unittest.main()
