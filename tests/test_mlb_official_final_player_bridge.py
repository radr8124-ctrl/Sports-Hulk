"""Only official Final MLB game/player boxscore feeds can enter the research ledger.

Tests exercise the gap between game-master results and official player
boxscore history, no fabricated zero hits or postgame prequote claims.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
import copy,hashlib,json,tempfile,unittest

import pandas as pd

from intelligence_warehouse.historical_recovery.mlb_official_final_player_bridge import (
    discover_due_game_pks,
    verified_final_boxscore_player_rows,
    append_verified_final_game_once,
    bridge_cycle,
)

NOW=datetime(2026,10,9,5,30,tzinfo=timezone.utc)
FIRST=datetime(2026,10,9,0,0,tzinfo=timezone.utc)
GAME=849832
SHA='a'*64

def frozen(pid=501):
    return {
      'schema':'MLB_TRUE_PREGAME_RESEARCH_FEATURE_FREEZE_V2',
      'game_pk':GAME,'player_id':pid,'team_side_at_capture':'away',
      'source_evidence_id':'real_pregame_source',
      'source_capture_at_utc':(FIRST-timedelta(hours=3)).isoformat(),
      'feature_frozen_at_utc':(FIRST-timedelta(hours=2)).isoformat(),
      'scheduled_first_pitch_utc':FIRST.isoformat(),
      'original_append_only_line_sha256':SHA,
      'source_history_revision':'OFFICIAL_FINAL_REGULAR_AND_POSTSEASON_V2',
      'live_play_approved':False,'betting_prediction_written':False,
    }

def master(status='Final',start=FIRST):
    return pd.DataFrame([{
      'gamePk':GAME,'officialDate':'2026-10-08','gameDate':start.isoformat(),
      'gameType':'D','status':status,
      'home_team_id':145,'away_team_id':114,
      'home_team':'Chicago White Sox','away_team':'Cleveland Guardians',
    }])

def actual_feed(status='Final'):
    return {
      'gameData':{
        'game':{'pk':GAME},
        'status':{'detailedState':status},
        'datetime':{'dateTime':FIRST.isoformat(),'officialDate':'2026-10-08'},
      }
    }

def batter(pid=501,pa=4,hits=2):
    return {
      'person':{'id':pid,'fullName':'Real Athlete 501'},
      'stats':{'batting':{
        'plateAppearances':pa,'atBats':3,'hits':hits,'baseOnBalls':1,
        'strikeOuts':1,'stolenBases':0,'doubles':0,'triples':0,
        'homeRuns':0,'rbi':1,'runs':0,
      }},
      'allPositions':[{'abbreviation':'CF'}],
      'position':{'abbreviation':'CF'},
    }

def box(pid=501,*,include_player=True):
    return {
       'teams':{
         'home':{'team':{'id':145,'name':'Chicago White Sox'},'battingOrder':[],
                 'players':{}},
         'away':{'team':{'id':114,'name':'Cleveland Guardians'},
                 'battingOrder':[pid] if include_player else [],
                 'players':{f'ID{pid}':batter(pid)} if include_player else {},
                },
       }
    }

def actual_original():
    p=[501]+list(range(510,518))
    source={
       'schema':'MLB_PREGAME_SOURCE_EVIDENCE_V1',
       'evidence_id':'real_pregame_source',
       'game_pk':GAME,
       'captured_at_utc':(FIRST-timedelta(hours=3)).isoformat(),
       'first_pitch_utc':FIRST.isoformat(),
       'fixture':{'official_status_at_capture':'Pre-Game'},
       'lineups':{'status':'ONLY_ONE_TEAM_LINEUP_VISIBLE_PREGAME','away':{
          'player_ids':p,'player_names':[f'Player {n}' for n in p],
          'source':'LIVE_FEED_OFFICIAL_BATTING_ORDER_CAPTURED_PREGAME',
          'confirmed_asof_capture':True}},
    }
    text=json.dumps(source,sort_keys=True)+'\n'
    return source,text

def with_real_sha():
    orig,line=actual_original()
    r=frozen()
    r['original_append_only_line_sha256']=hashlib.sha256(line.encode()).hexdigest()
    return r,line

class StrictMLBFinalBoxscoreBridgeTests(unittest.TestCase):
    def test_final_fixture_due_but_never_live_or_pregame(self):
        a,d=discover_due_game_pks([frozen()],master(),pd.DataFrame(),now=NOW)
        self.assertEqual(a,[GAME])
        self.assertEqual(d['final_games_pending_boxscores'],1)
        for status in ('Scheduled','Warmup','In Progress','Game Over'):
            due,_=discover_due_game_pks([frozen()],master(status=status),pd.DataFrame(),now=NOW)
            self.assertEqual(due,[])
        due,_=discover_due_game_pks([frozen()],master(),pd.DataFrame(),now=FIRST-timedelta(minutes=1))
        self.assertEqual(due,[])

    def test_original_start_must_match_final_master_before_external_fetch(self):
        with self.assertRaisesRegex(ValueError,'start|first.pitch'):
            discover_due_game_pks([frozen()],master(start=FIRST+timedelta(minutes=10)),
                                  pd.DataFrame(),now=NOW)

    def test_fresh_final_verified_stats_parsed_without_turning_missing_player_into_loss(self):
        rows,audit=verified_final_boxscore_player_rows(
            GAME,master().iloc[0].to_dict(),actual_feed(),box(),[frozen()],now=NOW)
        self.assertGreaterEqual(len(rows),1)
        hits=rows[(rows.player_id==501)&(rows.group=='HITTING')]
        self.assertEqual(len(hits),1)
        self.assertEqual(hits.iloc[0]['hits'],2.)
        self.assertEqual(hits.iloc[0]['walks'],1.)
        self.assertEqual(hits.iloc[0]['plate_appearances'],4.)
        self.assertEqual(audit['official_final_status'],'Final')
        self.assertEqual(audit['source_frozen_lineup_players_present_in_hitting_stats'],1)
        self.assertEqual(audit['missing_frozen_hitter_boxscore_records'],0)

    def test_nonfinal_feed_or_wrong_game_pk_refused_even_if_stale_master_is_final(self):
        with self.assertRaisesRegex(ValueError,'Final'):
            verified_final_boxscore_player_rows(GAME,master().iloc[0].to_dict(),
                                               actual_feed(status='Live'),box(),[frozen()],now=NOW)
        forged=actual_feed()
        forged['gameData']['game']['pk']=800001
        with self.assertRaisesRegex(ValueError,'gamePk|game.*identity'):
            verified_final_boxscore_player_rows(GAME,master().iloc[0].to_dict(),
                                               forged,box(),[frozen()],now=NOW)

    def test_missing_stat_field_and_wrong_team_id_never_fabricate_clean_final(self):
        original=box()
        del original['teams']['away']['players']['ID501']['stats']['batting']['hits']
        with self.assertRaisesRegex(ValueError,'missing.*stat|incomplete'):
            verified_final_boxscore_player_rows(GAME,master().iloc[0].to_dict(),actual_feed(),
                                               original,[frozen()],now=NOW)
        bad=box();bad['teams']['away']['team']['id']=191
        with self.assertRaisesRegex(ValueError,'team'):
            verified_final_boxscore_player_rows(GAME,master().iloc[0].to_dict(),actual_feed(),
                                               bad,[frozen()],now=NOW)

    def test_player_scratched_without_boxscore_is_pending_never_zero(self):
        actual=box()
        actual['teams']['away']['battingOrder']=[]
        actual['teams']['away']['players']={}
        # An entirely blank final game boxscore must wait for completeness.
        with self.assertRaisesRegex(ValueError,'incomplete|empty'):
            verified_final_boxscore_player_rows(GAME,master().iloc[0].to_dict(),actual_feed(),
                                               actual,[frozen()],now=NOW)
        # One participant can score while another frozen source participant
        # stays PENDING, never inferred "0 hits" from missing records.
        source=[frozen(),frozen(pid=517)]
        rows,audit=verified_final_boxscore_player_rows(GAME,master().iloc[0].to_dict(),
                                                actual_feed(),box(),source,now=NOW)
        self.assertEqual(audit['missing_frozen_hitter_boxscore_records'],1)
        self.assertEqual(audit['source_frozen_lineup_players_present_in_hitting_stats'],1)
        self.assertNotIn(517,set(rows.player_id))

    def test_append_provenance_and_output_idempotent_with_conflicting_grade_blocked(self):
        candidate,_=verified_final_boxscore_player_rows(GAME,master().iloc[0].to_dict(),
                                                actual_feed(),box(),[frozen()],now=NOW)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'LEDGER.csv'
            count,audit=append_verified_final_game_once(path,candidate)
            self.assertEqual(count,len(candidate))
            initial=path.read_bytes()
            self.assertEqual(append_verified_final_game_once(path,candidate)[0],0)
            self.assertEqual(initial,path.read_bytes())
            corrupted=candidate.copy()
            corrupted.loc[corrupted.group.eq('HITTING'),'hits']=15
            with self.assertRaisesRegex(ValueError,'conflict'):
                append_verified_final_game_once(path,corrupted)
            self.assertEqual(initial,path.read_bytes())

    def test_cycle_before_final_never_fetches_or_writes_a_boxscore(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            r,line=with_real_sha()
            src=root/'FROZEN.jsonl';src.write_text(json.dumps(r)+'\n')
            original=root/'ORIGINAL.jsonl';original.write_text(line)
            m=root/'MASTER.csv';master(status='Warmup').to_csv(m,index=False)
            ledger=root/'LEDGER.csv'
            with patch('intelligence_warehouse.historical_recovery.mlb_official_final_player_bridge.requests.get',
                       side_effect=AssertionError('NO NETWORK while not official Final')):
                out=bridge_cycle(src,m,ledger,root/'RECEIPTS.jsonl',
                                 original_source_file=original,now=FIRST-timedelta(minutes=1))
            self.assertEqual(out['new_official_final_player_rows_added'],0)
            self.assertEqual(out['official_final_games_with_new_hitter_results'],0)
            self.assertFalse(ledger.exists())

if __name__=='__main__':unittest.main()

class VerifiedFinalBridgeEndToEndMockTests(unittest.TestCase):
    def test_real_cycle_retrieves_two_original_official_final_sources_then_idempotent(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            r,line=with_real_sha()
            frozen_file=root/'FROZEN.jsonl';frozen_file.write_text(json.dumps(r)+'\n')
            orig=root/'ORIGINAL.jsonl';orig.write_text(line)
            master_file=root/'MASTER.csv';master().to_csv(master_file,index=False)
            ledger=root/'PLAYER_LEDGER.csv'
            receipts=root/'FINAL_EVIDENCE.jsonl'
            feed=actual_feed();boxscore=box()
            def final_request(url,**_):
                resp=MagicMock()
                resp.json.return_value=feed if '/feed/live' in url else boxscore
                return resp
            with patch('intelligence_warehouse.historical_recovery.mlb_official_final_player_bridge.requests.get',
                       side_effect=final_request) as call:
                initial=bridge_cycle(frozen_file,master_file,ledger,receipts,
                                     now=NOW,original_source_file=orig)
                self.assertEqual(call.call_count,2)
            self.assertEqual(initial['official_final_games_with_new_hitter_results'],1)
            self.assertEqual(initial['new_official_final_player_rows_added'],1)
            self.assertEqual(len(pd.read_csv(ledger)),1)
            stored=[json.loads(x) for x in receipts.read_text().splitlines() if x.strip()]
            self.assertEqual(len(stored),1)
            self.assertEqual(stored[0]['source_original_final_boxscore_full_payload'],boxscore)
            self.assertEqual(stored[0]['source_frozen_lineup_players_present_in_hitting_stats'],1)
            ledger_before=ledger.read_bytes()
            receipt_before=receipts.read_bytes()
            with patch('intelligence_warehouse.historical_recovery.mlb_official_final_player_bridge.requests.get',
                       side_effect=AssertionError('Never refetch once original final captured')):
                second=bridge_cycle(frozen_file,master_file,ledger,receipts,
                                    now=NOW+timedelta(minutes=10),original_source_file=orig)
            self.assertEqual(second['new_official_final_player_rows_added'],0)
            self.assertEqual(second['network_requests_to_official_mlb_only'],0)
            self.assertEqual(ledger.read_bytes(),ledger_before)
            self.assertEqual(receipts.read_bytes(),receipt_before)

    def test_existing_player_history_earlier_unrelated_game_bytes_not_reformatted(self):
        candidate,_=verified_final_boxscore_player_rows(GAME,master().iloc[0].to_dict(),
                                                actual_feed(),box(),[frozen()],now=NOW)
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'LEDGER.csv'
            older=candidate.copy()
            older.loc[:,'gamePk']=GAME-1
            older.loc[:,'officialDate']='2026-10-07'
            older.to_csv(src,index=False)
            initial=src.read_bytes()
            appended,audit=append_verified_final_game_once(src,candidate)
            self.assertEqual(appended,1)
            self.assertTrue(src.read_bytes().startswith(initial))
            self.assertEqual(len(pd.read_csv(src)),2)

class CrashBetweenOriginalPlayerAppendAndBoxscoreReceiptRecovery(unittest.TestCase):
    def test_prior_final_player_rows_without_receipt_are_revalidated_and_receipted(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            frozen_row,line=with_real_sha()
            f=root/'FROZEN.jsonl';f.write_text(json.dumps(frozen_row)+'\n')
            pre=root/'ORIGINAL.jsonl';pre.write_text(line)
            m=root/'MASTER.csv';master().to_csv(m,index=False)
            ledger=root/'LEDGER.csv'
            receipts=root/'RECEIPTS.jsonl'
            done,_=verified_final_boxscore_player_rows(
                GAME,master().iloc[0].to_dict(),actual_feed(),box(),[frozen_row],now=NOW)
            done.to_csv(ledger,index=False)
            original_bytes=ledger.read_bytes()
            def source(url,**_):
                response=MagicMock()
                response.json.return_value=actual_feed() if '/feed/live' in url else box()
                return response
            with patch('intelligence_warehouse.historical_recovery.mlb_official_final_player_bridge.requests.get',
                       side_effect=source) as provider:
                result=bridge_cycle(f,m,ledger,receipts,now=NOW,original_source_file=pre)
                self.assertEqual(provider.call_count,2)
            self.assertEqual(result['official_final_games_with_new_hitter_results'],1)
            self.assertEqual(result['new_official_final_player_rows_added'],0)
            self.assertEqual(ledger.read_bytes(),original_bytes)
            self.assertEqual(len(receipts.read_text().splitlines()),1)
            with patch('intelligence_warehouse.historical_recovery.mlb_official_final_player_bridge.requests.get',
                       side_effect=AssertionError('Already sourced and receipted player/game must never refetch')):
                replay=bridge_cycle(f,m,ledger,receipts,now=NOW+timedelta(minutes=12),original_source_file=pre)
            self.assertEqual(replay['network_requests_to_official_mlb_only'],0)

    def test_prior_final_player_result_changed_by_provider_blocks_receipt_recovery(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            original,line=with_real_sha()
            frozen_path=root/'FROZEN.jsonl';frozen_path.write_text(json.dumps(original)+'\n')
            original_file=root/'ORIGINAL.jsonl';original_file.write_text(line)
            m=root/'MASTER.csv';master().to_csv(m,index=False)
            dest=root/'LEDGER.csv';receipt=root/'RECEIPTS.jsonl'
            before_provider=box()
            before_provider['teams']['away']['players']['ID501']['stats']['batting']['hits']=1
            prior,_=verified_final_boxscore_player_rows(
                GAME,master().iloc[0].to_dict(),actual_feed(),before_provider,[original],now=NOW)
            prior.to_csv(dest,index=False)
            before=dest.read_bytes()
            def provider(url,**_):
                response=MagicMock()
                response.json.return_value=actual_feed() if '/feed/live' in url else box()
                return response
            with patch('intelligence_warehouse.historical_recovery.mlb_official_final_player_bridge.requests.get',
                       side_effect=provider):
                with self.assertRaisesRegex(ValueError,'conflict'):
                    bridge_cycle(frozen_path,m,dest,receipt,now=NOW,original_source_file=original_file)
            self.assertEqual(before,dest.read_bytes())
            self.assertFalse(receipt.exists())
