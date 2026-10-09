"""Actual original 18 MLB model predictions -> FAKE final ONLY IN MEMORY/TEMP.

One unit acceptance simulates future API "Final" and full boxscore for the
actual original 18 frozen player IDs, runs the NEW Final player bridge, the
original official grade source and 16-column model Brier scorer end-to-end.
It is NOT evidence actual game Finished or that any model beat the book.
Every real source, official ledger, frozen prediction and outcome file must
have exactly the same SHA256 before and after test.
"""
from __future__ import annotations

from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import tempfile
import unittest

import pandas as pd

from intelligence_warehouse.historical_recovery.mlb_official_final_player_bridge import bridge_cycle
from intelligence_warehouse.historical_recovery.mlb_research_forward_labels import grade_cycle
from intelligence_warehouse.historical_recovery.mlb_full16_forward_official_scoring import score_cycle

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'intelligence_warehouse/mlb_pregame_capture'
GAME=849832
FIRST='2026-10-09T00:00:00Z'
SIMULATION=datetime(2026,10,9,5,30,tzinfo=timezone.utc)

class Original18RealMLBForecastersSyntheticFinalFullPipeline(unittest.TestCase):
    def test_actual_full16_and_original_player_ids_fake_only_when_mocked_final(self):
        files=[
          ROOT/'baseball_vault/derived/MLB_GAME_MASTER.csv',
          ROOT/'intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_LEDGER.csv',
          BASE/'MLB_PREGAME_SOURCE_EVIDENCE.jsonl',
          BASE/'MLB_RESEARCH_ASOF_FEATURE_FREEZE_V2.jsonl',
          BASE/'MLB_V4_SIXTEEN_FEATURE_ACTUAL_FORWARD_SHADOW.jsonl',
          BASE/'MLB_FINAL_PLAYER_BOX_SOURCE_RECEIPTS.jsonl',
          BASE/'MLB_V2_OFFICIAL_FORWARD_RESEARCH_LABELS.jsonl',
          BASE/'MLB_V4_FULL16_SAME_NEW_QUOTE_OFFICIAL_THREEWAY_SCORES.jsonl',
        ]
        before={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
        original=[json.loads(s) for s in files[3].read_text().splitlines() if s.strip()]
        shadows=[json.loads(s) for s in files[4].read_text().splitlines() if s.strip()]
        game_orig=[x for x in original if x['game_pk']==GAME]
        model_orig=[x for x in shadows if x['official_game_pk']==GAME]
        self.assertEqual(len(game_orig),18)
        self.assertEqual(len(model_orig),18)
        g=pd.read_csv(files[0],low_memory=False)
        fixture=g[g.gamePk.eq(GAME)].iloc[0]
        self.assertEqual(fixture.gameDate,FIRST)
        batters={}
        for side in ('home','away'):
            members=sorted([r for r in game_orig if r['team_side_at_capture']==side],
                           key=lambda r:r['player_id'])
            self.assertEqual(len(members),9)
            players={}
            for index,original_r in enumerate(members):
                pid=int(original_r['player_id'])
                hits=float(index%3)
                players[f'ID{pid}']={
                  'person':{'id':pid,'fullName':f'TEST ONLY ATHLETE {pid}'},
                  'allPositions':[{'abbreviation':'CF'}],
                  'position':{'abbreviation':'CF'},
                  'stats':{'batting':{
                    'plateAppearances':4,'atBats':4,'hits':hits,
                    'baseOnBalls':0,'strikeOuts':1,'stolenBases':0,
                    'doubles':0,'triples':0,'homeRuns':0,
                    'rbi':0,'runs':0,
                  }}
                }
            batters[side]={
                'team':{'id':int(fixture[f'{side}_team_id']),
                        'name':str(fixture[f'{side}_team'])},
                'battingOrder':[int(r['player_id']) for r in members],
                'players':players,
            }
        simulated_box={'teams':batters}
        synthetic_feed={
            'gameData':{
                'game':{'pk':GAME},
                'datetime':{'dateTime':FIRST,'officialDate':'2026-10-08'},
                'status':{'detailedState':'Final'},
            }
        }
        with tempfile.TemporaryDirectory() as folder:
            tmp=Path(folder)
            simulated_master=g.copy()
            simulated_master.loc[simulated_master.gamePk.eq(GAME),'status']='Final'
            master_path=tmp/'MASTER_SIMULATED_FINAL.csv'
            simulated_master.to_csv(master_path,index=False)
            pregame_path=tmp/'TRUE_ORIGINAL_PREGAME.jsonl'
            pregame_path.write_bytes(files[3].read_bytes())
            official_player_ledger=tmp/'SIMULATED_OFFICIAL_FINAL_PLAYERS.csv'
            original_final_receipts=tmp/'ORIGINAL_MLB_RESULT_PROOF_FROM_SIMULATION.jsonl'
            class FakeResponse:
                def __init__(self,body):self.body=body
                def json(self):return self.body
                def raise_for_status(self):return None
            def mock_official_api(url,**kwargs):
                if url.endswith('/feed/live'):
                    return FakeResponse(synthetic_feed)
                if url.endswith('/boxscore'):
                    return FakeResponse(simulated_box)
                raise AssertionError('Unrecognized official source endpoint')
            with patch('intelligence_warehouse.historical_recovery.mlb_official_final_player_bridge.requests.get',
                       side_effect=mock_official_api) as official_api:
                ingested=bridge_cycle(
                    frozen_file=pregame_path,
                    master_file=master_path,
                    ledger_file=official_player_ledger,
                    receipt_file=original_final_receipts,
                    now=SIMULATION,
                    original_source_file=files[2],
                )
            self.assertEqual(official_api.call_count,2)
            self.assertEqual(ingested['official_final_games_with_new_hitter_results'],1)
            self.assertEqual(ingested['new_official_final_player_rows_added'],18)
            receipt=[json.loads(x) for x in original_final_receipts.read_text().splitlines()]
            self.assertEqual(len(receipt),1)
            self.assertEqual(receipt[0]['source_frozen_lineup_players_present_in_hitting_stats'],18)
            labelfile=tmp/'SIMULATED_HITTER_GRADES.jsonl'
            grade=grade_cycle(
                pregame_path,labelfile,master_path,official_player_ledger,
                now=SIMULATION,original_source_file=files[2],
            )
            self.assertEqual(grade['labels_appended'],18)
            self.assertEqual(grade['independent_games_with_official_labels'],1)
            scoring=score_cycle(
                forecasts_file=files[4],
                official_file=labelfile,
                output=tmp/'SYNTHETIC_THREEWAY_SCORES.jsonl',
                now=SIMULATION+timedelta(minutes=1),
            )
            self.assertEqual(scoring['newly_official_player_results_compared'],18)
            self.assertEqual(scoring['independent_official_game_blocks'],1)
            self.assertIsNotNone(scoring['book_raw_brier'])
            self.assertIsNotNone(scoring['market_only_brier'])
            self.assertIsNotNone(scoring['full16_brier'])
            self.assertFalse(scoring['profitable_market_edge_qualified'])
            self.assertFalse(scoring['play_authorized'])
        after={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
        self.assertEqual(before,after)

if __name__=='__main__':
    unittest.main()
