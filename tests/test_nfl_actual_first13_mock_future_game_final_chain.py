"""Real 13 frozen NFL forecasts → in-memory synthetic independent Final → score.

NEVER save synthetic Week5 outcome to actual NFLverse source/Survivor/bookmaker
ledgers or to original game model predictions. This test proves only the
implementation's *future* source/grade compatibility, not winning predictions.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import MagicMock,patch
import hashlib,json,tempfile,unittest

import pandas as pd

from intelligence_warehouse.historical_recovery.nfl_forward_individual_final_source import collect_cycle
from intelligence_warehouse.historical_recovery.nfl_nine_col_official_scoring import score_cycle

ROOT=Path(__file__).resolve().parents[1]
REAL=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_FIRST_PREKICKOFF_NINE_FEATURE_SCORE_FORM_SHADOW.jsonl'
CURRENT=ROOT/'nfl_live/derived/NFLVERSE_2026_SCHEDULE.csv'
RESULT=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_2026_FIRST_FUTURE_EVENT_ESPN_FINAL_ORIGINAL_SOURCE.jsonl'
SCORED=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_NINE_FEATURE_SAME_BOOK_OFFICIAL_FINAL_SCORES.jsonl'
HISTORY=ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_2026_VERIFIED_PRIOR_FINAL_SCORES.jsonl'

class NFLAuthenticFirstForecastSyntheticFinalEndToEnd(unittest.TestCase):
    def test_real_original_week5_future_source_hash_never_changes_while_mocked_final_scores(self):
        tracked=(REAL,CURRENT,RESULT,SCORED,HISTORY)
        original_sha={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in tracked}
        true_models=[json.loads(line) for line in REAL.read_text().splitlines() if line.strip()]
        self.assertGreaterEqual(len(true_models),13)
        self.assertEqual(hashlib.sha256(''.join(REAL.read_text().splitlines(keepends=True)[:13]).encode()).hexdigest(),
                         'b74351d24c0cf591624a74c8dc2d33f84ea34f1374c65d782219bc5d95b60602')
        original=next(x for x in true_models if x['official_espn_event_id']=='401872982')
        self.assertEqual((original['away_team'],original['home_team']),('CIN','MIA'))
        self.assertEqual(original['source_first_real_future_prediction_frozen_at_utc']<original['official_first_pitch_utc'],True)
        kickoff=pd.Timestamp(original['official_first_pitch_utc'])
        now=(kickoff+pd.Timedelta(hours=9)).to_pydatetime()
        frame=pd.read_csv(CURRENT,low_memory=False)
        selector=frame.espn.eq(401872982)
        self.assertEqual(int(selector.sum()),1)
        self.assertTrue(frame.loc[selector,'home_score'].isna().all())
        future=frame.copy()
        future.loc[selector,'home_score']=27.
        future.loc[selector,'away_score']=20.
        payload={'events':[{
            'id':'401872982',
            'date':original['official_first_pitch_utc'],
            'season':{'year':2026,'type':2},
            'week':{'number':5},
            'status':{'type':{'name':'STATUS_FINAL','completed':True}},
            'competitions':[{'competitors':[
                {'homeAway':'home','team':{'id':'15','abbreviation':'MIA'},'score':'27'},
                {'homeAway':'away','team':{'id':'4','abbreviation':'CIN'},'score':'20'},
            ]}],
        }]}
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            first=base/'AUTHENTIC_EARLIER_SOURCE.jsonl'
            first.write_text(json.dumps(original)+'\n')
            mock_schedule=base/'ONLY_FAKE_FINAL_NUMERIC_SOURCE.csv'
            future.to_csv(mock_schedule,index=False)
            final_ledger=base/'SYNTHETIC_ESPN_EVENT_FINAL.jsonl'
            analysis=base/'SYNTHETIC_MODEL_BRIER.jsonl'
            mock_response=MagicMock()
            mock_response.json.return_value=payload
            with patch('intelligence_warehouse.historical_recovery.nfl_forward_individual_final_source.requests.get',
                       return_value=mock_response) as net:
                stage=collect_cycle(first,mock_schedule,final_ledger,now=now)
                self.assertEqual(net.call_count,1)
            self.assertEqual(stage['verified_new_independent_final_games'],1)
            self.assertEqual(len(final_ledger.read_text().splitlines()),1)
            performance=score_cycle(first,final_ledger,analysis,now=now+timedelta(minutes=1))
            self.assertEqual(performance['newly_scored_final_games'],1)
            self.assertEqual(performance['independent_final_game_blocks'],1)
            self.assertIsNotNone(performance['raw_book_brier'])
            self.assertIsNotNone(performance['market_only_brier'])
            self.assertIsNotNone(performance['score_form_brier'])
            self.assertFalse(performance['market_advantage_statistically_proven'])
            self.assertFalse(performance['live_play_approved'])
            replay=score_cycle(first,final_ledger,analysis,now=now+timedelta(minutes=2))
            self.assertEqual(replay['newly_scored_final_games'],0)
            self.assertEqual(len(analysis.read_text().splitlines()),1)
        after_sha={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in tracked}
        self.assertEqual(original_sha,after_sha)

if __name__=='__main__':unittest.main()
