"""REAL pregame evidence + corrected official master, SYNTHETIC Final in memory ONLY.

Never save mock postgame outcomes. This proves identity/provenance chain from
true pregame 18 hitters to future official Final player boxscore grading and
full 16-column same-new-quote model-vs-market three-way scoring. It asserts
on-disk official result and betting ledgers are never modified by the test.
"""
from __future__ import annotations

from datetime import datetime,timezone,timedelta
import hashlib
import json
from pathlib import Path
import unittest

import pandas as pd

from intelligence_warehouse.historical_recovery.mlb_research_forward_labels import (
    select_verified_final_labels,verify_original_pregame_source,
)
from intelligence_warehouse.historical_recovery.mlb_full16_forward_official_scoring import (
    score_after_original_final,
)

ROOT=Path(__file__).resolve().parents[1]
SOURCES=ROOT/'intelligence_warehouse/mlb_pregame_capture'
GAME_PK=849832
SYNTHETIC_GRADE_CLOCK=datetime(2026,10,9,1,0,tzinfo=timezone.utc)

class ExistingOfficialSourceIdentityForwardFinalRehearsal(unittest.TestCase):
    def test_full_real_source_identity_reaches_synthetic_inmemory_final_score_only(self):
        inputs=[
            ROOT/'baseball_vault/derived/MLB_GAME_MASTER.csv',
            SOURCES/'MLB_PREGAME_SOURCE_EVIDENCE.jsonl',
            SOURCES/'MLB_RESEARCH_ASOF_FEATURE_FREEZE_V2.jsonl',
            SOURCES/'MLB_V4_SIXTEEN_FEATURE_ACTUAL_FORWARD_SHADOW.jsonl',
            SOURCES/'MLB_V2_OFFICIAL_FORWARD_RESEARCH_LABELS.jsonl',
            SOURCES/'MLB_V4_FULL16_SAME_NEW_QUOTE_OFFICIAL_THREEWAY_SCORES.jsonl',
        ]
        before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
        original=[json.loads(line) for line in inputs[2].read_text().splitlines() if line.strip()]
        original=[r for r in original if r['game_pk']==GAME_PK]
        new_model=[json.loads(line) for line in inputs[3].read_text().splitlines() if line.strip()]
        new_model=[r for r in new_model if r['official_game_pk']==GAME_PK]
        self.assertEqual(len(original),18)
        self.assertEqual(len(new_model),18)
        self.assertEqual(
            verify_original_pregame_source(original,inputs[1])['verified_original_frozen_player_ids'],18
        )
        persisted=pd.read_csv(inputs[0],usecols=['gamePk','officialDate','gameDate','gameType','status'],low_memory=False)
        actual_row=persisted.loc[persisted.gamePk.eq(GAME_PK)].iloc[0]
        self.assertEqual(actual_row.gameDate,'2026-10-09T00:00:00Z')
        self.assertEqual(actual_row.officialDate,'2026-10-08')
        self.assertEqual(actual_row.gameType,'D')
        # Only the COPY is set Final. Never write this hypothetical result
        # to the real official game master, prediction, grade or bankroll.
        fake_master=persisted.copy()
        fake_master.loc[fake_master.gamePk.eq(GAME_PK),'status']='Final'
        mock_box=pd.DataFrame([
            {
                'gamePk':GAME_PK,
                'officialDate':'2026-10-08',
                'player_id':int(row['player_id']),
                'group':'HITTING',
                'hits':float(i%3),
                'walks':float(i%2),
                'strikeouts':1.,
                'total_bases':float(i%3),
                'stolen_bases':0.,
                'plate_appearances':4.,
            }
            for i,row in enumerate(original)
        ])
        pending_labels,audit=select_verified_final_labels(
            original,fake_master,mock_box,now=SYNTHETIC_GRADE_CLOCK
        )
        self.assertEqual(len(pending_labels),18)
        self.assertEqual(audit['official_grade_ready_games'],1)
        result,score=score_after_original_final(
            new_model,pending_labels,now=SYNTHETIC_GRADE_CLOCK+timedelta(minutes=1)
        )
        self.assertEqual(len(result),18)
        self.assertEqual(score['independent_official_game_blocks'],1)
        self.assertEqual(score['source_player_comparisons'],18)
        self.assertFalse(score['profitable_market_edge_qualified'])
        self.assertFalse(score['play_authorized'])
        self.assertTrue(all(x['original_official_pregame_source_sha256'] for x in result))
        self.assertTrue(all(x['original_forward_model_was_full16_pregame_context'] for x in result))
        # Synthetic mock data are discarded at end of method: ALL original
        # on-server private records and source timestamps unchanged.
        after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
        self.assertEqual(before,after)

if __name__=='__main__':unittest.main()
