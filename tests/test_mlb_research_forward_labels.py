"""Official outcome observations join frozen MLB research features without rewrites."""
from __future__ import annotations
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
import pandas as pd

from intelligence_warehouse.historical_recovery.mlb_research_forward_labels import (
    select_verified_final_labels,append_unique_official_labels,grade_cycle,
    verify_original_pregame_source,
)

OBS=datetime(2026,10,9,9,0,tzinfo=timezone.utc)
START=datetime(2026,10,9,0,0,tzinfo=timezone.utc)


def frozen(pid=501,game=849832,*,start=START,asof=None):
    if asof is None:asof=start-timedelta(hours=4)
    return {
        'schema':'MLB_TRUE_PREGAME_RESEARCH_FEATURE_FREEZE_V2',
        'game_pk':game,'player_id':pid,
        'team_side_at_capture':'home',
        'source_evidence_id':'official-prematch-lineup-event',
        'source_capture_at_utc':(asof-timedelta(minutes=5)).isoformat(),
        'feature_frozen_at_utc':asof.isoformat(),
        'scheduled_first_pitch_utc':start.isoformat(),
        'source_history_revision':'OFFICIAL_FINAL_REGULAR_AND_POSTSEASON_V2',
        'live_play_approved':False,'betting_prediction_written':False,
        'original_append_only_line_sha256':'a'*64,
        'source_history_verified_completed_through_date':'2026-10-07',
    }


def original_source_line(records:tuple[int,...]=tuple(range(501,510))):
    source={
        'schema':'MLB_PREGAME_SOURCE_EVIDENCE_V1',
        'evidence_id':'official-prematch-lineup-event',
        'game_pk':849832,
        'fixture':{'official_status_at_capture':'Pre-Game'},
        'captured_at_utc':(START-timedelta(hours=4,minutes=5)).isoformat(),
        'first_pitch_utc':START.isoformat(),
        'lineups':{
            'status':'ONLY_ONE_TEAM_LINEUP_VISIBLE_PREGAME',
            'home':{
                'player_ids':list(records),
                'source':'LIVE_FEED_OFFICIAL_BATTING_ORDER_CAPTURED_PREGAME',
                'confirmed_asof_capture':True,
            }
        },
    }
    raw=json.dumps(source)+'\n'
    return raw,source


def frozen_from_actual_bytes(record,raw):
    import hashlib
    out=dict(record)
    out['original_append_only_line_sha256']=hashlib.sha256(raw.encode()).hexdigest()
    return out


def master(status='Final',game=849832,date='2026-10-08'):
    return pd.DataFrame([{
        'gamePk':game,'officialDate':date,
        'gameDate':START.isoformat(),
        'gameType':'D','status':status,
        'home_score':4,'away_score':2,
    }])


def box(game=849832,*,hits=2.,walks=1.,players=(501,)):
    return pd.DataFrame([{
        'gamePk':game,'officialDate':'2026-10-08','player_id':pid,
        'group':'HITTING','hits':hits,'walks':walks,'strikeouts':1.,
        'total_bases':3.,'stolen_bases':0.,'plate_appearances':4.,
    } for pid in players])


class OriginalPregameSourceReceiptIdentityTests(unittest.TestCase):
    def test_original_lineup_pre_game_bytes_prove_hash_player_and_game_id(self):
        raw,_=original_source_line()
        with tempfile.TemporaryDirectory() as folder:
            sidecar=Path(folder)/'ORIGINAL_PREGAME.jsonl'
            sidecar.write_text(raw)
            frozen_row=frozen_from_actual_bytes(frozen(),raw)
            status=verify_original_pregame_source([frozen_row],sidecar)
            self.assertEqual(status['verified_original_frozen_player_ids'],1)
            self.assertEqual(status['missing_original_source_rows'],0)

    def test_tampered_source_or_wrong_player_cannot_become_official_label(self):
        raw,_=original_source_line()
        with tempfile.TemporaryDirectory() as folder:
            sidecar=Path(folder)/'ORIGINAL_PREGAME.jsonl'
            sidecar.write_text(raw)
            valid=frozen_from_actual_bytes(frozen(),raw)
            wrong=frozen_from_actual_bytes(frozen(999),raw)
            with self.assertRaisesRegex(ValueError,'[Oo]riginal.*player'):
                verify_original_pregame_source([wrong],sidecar)
            sidecar.write_text(raw.replace('501','1999'))
            with self.assertRaisesRegex(ValueError,'[Oo]riginal.*sha'):
                verify_original_pregame_source([valid],sidecar)

    def test_unavailable_original_ledger_fails_closed_without_fabricated_proof(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'original.*source'):
                verify_original_pregame_source([frozen()],Path(folder)/'MISSING.jsonl')


class MLBTrueForwardResearchGradeTests(unittest.TestCase):
    def test_final_boxscore_per_player_is_separate_research_grade_not_bet_settlement(self):
        proposed,receipt=select_verified_final_labels([frozen()],master(),box(),now=OBS)
        self.assertEqual(len(proposed),1)
        r=proposed[0]
        self.assertEqual(r['player_id'],501)
        self.assertEqual(r['official_hits'],2.)
        self.assertEqual(r['official_walks'],1.)
        self.assertEqual(r['official_plate_appearances'],4.)
        self.assertEqual(r['official_game_pk'],849832)
        self.assertTrue(r['pregame_frozen_before_official_game_start'])
        self.assertFalse(r['sportsbook_bet_settled'])
        self.assertFalse(r['model_win_or_probability_qualified'])
        self.assertFalse(r['live_play_approved'])
        self.assertEqual(receipt['official_grade_ready_games'],1)

    def test_scheduled_game_or_clock_before_first_pitch_never_settled(self):
        samples=[frozen()]
        for status in ('Scheduled','Live','In Progress','Cancelled'):
            proposed,r=select_verified_final_labels(samples,master(status=status),box(),now=OBS)
            self.assertEqual(proposed,[])
            self.assertEqual(r['official_grade_ready_games'],0)
        before=START-timedelta(minutes=10)
        proposed,_=select_verified_final_labels(samples,master(),box(),now=before)
        self.assertEqual(proposed,[])

    def test_unrecognized_player_not_mislabeled_zero_hits_or_false_loss(self):
        rows=[frozen(501),frozen(502)]
        proposed,receipt=select_verified_final_labels(rows,master(),box(players=(501,)),now=OBS)
        self.assertEqual(len(proposed),1)
        self.assertEqual(receipt['missing_frozen_player_boxscore_rows'],1)
        self.assertNotIn(502,{r['player_id'] for r in proposed})

    def test_official_mismatch_or_duplicates_fail_closed_without_partial_grade(self):
        with self.assertRaisesRegex(ValueError,'date mismatch'):
            select_verified_final_labels([frozen()],master(date='2026-10-07'),box(),now=OBS)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            select_verified_final_labels([frozen()],master(),pd.concat([box(),box()]),now=OBS)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            select_verified_final_labels([frozen(),frozen()],master(),box(),now=OBS)

    def test_forged_postgame_frozen_feature_never_becomes_forward_proof(self):
        after=frozen(asof=START+timedelta(minutes=2))
        with self.assertRaisesRegex(ValueError,'pregame'):
            select_verified_final_labels([after],master(),box(),now=OBS)
        switched=frozen()
        switched['betting_prediction_written']=True
        with self.assertRaisesRegex(ValueError,'research-only'):
            select_verified_final_labels([switched],master(),box(),now=OBS)

    def test_append_only_grade_deduplicates_and_conflicting_provider_changes_block(self):
        with tempfile.TemporaryDirectory() as dir:
            dest=Path(dir)/'OFFICIAL_LABELS.jsonl'
            result,_=select_verified_final_labels([frozen()],master(),box(),now=OBS)
            self.assertEqual(append_unique_official_labels(dest,result),1)
            content=dest.read_bytes()
            self.assertEqual(append_unique_official_labels(dest,result),0)
            self.assertEqual(dest.read_bytes(),content)
            changed,_=select_verified_final_labels([frozen()],master(),box(hits=3.),now=OBS)
            with self.assertRaisesRegex(ValueError,'conflicting'):
                append_unique_official_labels(dest,changed)
            self.assertEqual(dest.read_bytes(),content)

    def test_real_cycle_non_final_does_not_require_present_boxscore_rows(self):
        with tempfile.TemporaryDirectory() as dir:
            folder=Path(dir)
            live=folder/'FROZEN.jsonl'
            graded=folder/'GRADED.jsonl'
            game=folder/'GAMES.csv'
            player=folder/'PLAYER.csv'
            raw,_=original_source_line()
            original=folder/'ORIGINAL.jsonl'
            original.write_text(raw)
            live.write_text(json.dumps(frozen_from_actual_bytes(frozen(),raw))+'\n')
            master(status='Scheduled').to_csv(game,index=False)
            result=grade_cycle(live,graded,game,player,now=START-timedelta(minutes=30),original_source_file=original)
            self.assertEqual(result['labels_appended'],0)
            self.assertFalse(graded.exists())
            self.assertEqual(result['non_final_games_deferred'],1)

    def test_real_cycle_final_writes_only_official_status_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as dir:
            folder=Path(dir)
            live=folder/'FROZEN.jsonl'
            graded=folder/'GRADED.jsonl'
            game=folder/'GAMES.csv'
            player=folder/'PLAYER.csv'
            raw,_=original_source_line()
            original=folder/'ORIGINAL.jsonl'
            original.write_text(raw)
            live.write_text(json.dumps(frozen_from_actual_bytes(frozen(),raw))+'\n')
            master().to_csv(game,index=False)
            box().to_csv(player,index=False)
            first=grade_cycle(live,graded,game,player,now=OBS,original_source_file=original)
            second=grade_cycle(live,graded,game,player,now=OBS+timedelta(minutes=5),original_source_file=original)
            self.assertEqual(first['labels_appended'],1)
            self.assertEqual(second['labels_appended'],0)
            self.assertEqual(second['independent_games_with_official_labels'],1)
            self.assertEqual(len(graded.read_text().splitlines()),1)
            self.assertFalse(first['sportsbook_predictions_scored_or_promoted'])

if __name__=='__main__':
    unittest.main()

class MLBResearchGradeAdditionalSourceIntegrity(unittest.TestCase):
    def test_grade_rejects_official_start_time_mismatch_and_missing_grade_value(self):
        g=master()
        g.loc[0,'gameDate']=(START+timedelta(minutes=25)).isoformat()
        with self.assertRaisesRegex(ValueError,'first-pitch.*mismatch'):
            select_verified_final_labels([frozen()],g,box(),now=OBS)
        b=box()
        b.loc[0,'hits']=None
        with self.assertRaisesRegex(ValueError,'Invalid official'):
            select_verified_final_labels([frozen()],master(),b,now=OBS)

    def test_no_source_row_or_missing_box_is_pending_without_fabricated_zero(self):
        with tempfile.TemporaryDirectory() as dir:
            base=Path(dir)
            src=base/'FROZEN.jsonl'
            out=base/'RESEARCH_LABELS.jsonl'
            fixture=base/'MLB_GAMES.csv'
            raw,_=original_source_line()
            original=base/'ORIGINAL.jsonl'
            original.write_text(raw)
            src.write_text(json.dumps(frozen_from_actual_bytes(frozen(),raw))+'\n')
            master().to_csv(fixture,index=False)
            result=grade_cycle(src,out,fixture,base/'MISSING_BOX.csv',now=OBS,original_source_file=original)
            self.assertEqual(result['labels_appended'],0)
            self.assertEqual(result['missing_official_player_results'],1)
            self.assertFalse(out.exists())
            self.assertTrue(result['official_boxscore_source_read'])
