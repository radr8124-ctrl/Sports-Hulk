"""Only independently corroborated official far-start corrections may update MLB master."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
import tempfile
import json
import unittest

import pandas as pd

from baseball_vault import refresh_mlb_master_status as mod
from tests.test_mlb_master_freshness import (
    baseline,game,FakeSession,payload,schedule_row,
)

OLD='2026-10-05T21:00:00Z'
NEW='2026-10-06T00:00:00Z'
PROOF_TIME='2026-10-05T23:20:00Z'


def old_master():
    frame=baseline()
    frame['venue_id']=[4,100,333]
    return frame


def official():
    g=game(849834,start=NEW,status='Pre-Game',away_score=None,home_score=None)
    g['venue_id']='4'
    g['away_team_id']=str(g['away_team_id'])
    g['home_team_id']=str(g['home_team_id'])
    return g


def source_event(dt,*,venue=4,home=114,away=145,start=NEW,teams=True,lineup=True,
                 source_status='Pre-Game',fixture_date='2026-10-05'):
    block={
        'schema':'MLB_PREGAME_SOURCE_EVIDENCE_V1',
        'evidence_id':f'capture-{dt}',
        'captured_at_utc':dt,
        'first_pitch_utc':start,
        'game_pk':849834,
        'fixture':{
            'home_team_id':home,'home_team':'Cleveland Guardians',
            'away_team_id':away,'away_team':'Chicago White Sox',
            'venue_id':venue,'official_date':fixture_date,
            'official_game_type':'D','official_status_at_capture':source_status,
        },
        'lineups':{'status':'OFFICIAL_BATTING_ORDER_VISIBLE_BEFORE_KICKOFF'},
    }
    if lineup:
        for side,offset in [('home',1000),('away',2000)]:
            block['lineups'][side]={
                'player_ids':list(range(offset+1,offset+10)),
                'player_names':[f'Player {n}' for n in range(offset+1,offset+10)],
                'source':'LIVE_FEED_OFFICIAL_BATTING_ORDER_CAPTURED_PREGAME',
                'confirmed_asof_capture':True,
            }
    return block


def evidence(rows):
    return ''.join(json.dumps(x,sort_keys=True)+'\n' for x in rows)


def verified_rows():
    return [source_event('2026-10-05T22:30:00Z'),
            source_event('2026-10-05T23:20:00Z')]


class StrictOriginalMLBKickoffReconciliationTests(unittest.TestCase):
    def test_original_cached_shift_still_held_without_attestation(self):
        current=old_master()
        c=official()
        approved,meta=mod.update_frame(current,{'849834':c})
        self.assertEqual(meta['updated_games'],0)
        self.assertEqual(meta['held_for_review'][0]['reason'],'KICKOFF_CHANGED_BEYOND_TWO_HOURS')
        self.assertEqual(approved.loc[0,'gameDate'],OLD)

    def test_two_timestamped_both_official_lineups_verify_three_hour_attestation_only(self):
        prior=old_master()
        official_row=official()
        verified=mod.verified_far_start_overrides(
            prior,{'849834':official_row},verified_rows(),clock=datetime(2026,10,5,23,22,tzinfo=timezone.utc))
        self.assertEqual(set(verified),{'849834'})
        receipt=verified['849834']
        self.assertEqual(receipt['old_start'],OLD)
        self.assertEqual(receipt['new_start'],NEW)
        self.assertEqual(receipt['official_venue_id'],4)
        self.assertEqual(receipt['independent_capture_count'],2)
        self.assertEqual(len(receipt['source_original_line_sha256']),2)
        self.assertTrue(receipt['source_lineups_verifiably_published_after_original_stale_time'])
        result,summary=mod.update_frame(prior,{'849834':official_row},verified_start_overrides=verified)
        self.assertEqual(summary['updated_game_ids'],['849834'])
        self.assertEqual(summary['verified_large_kickoff_corrections'][0]['gamePk'],'849834')
        self.assertEqual(result.loc[0,'gameDate'],NEW)
        self.assertEqual(result.loc[0,'status'],'Pre-Game')
        self.assertEqual(len(result),len(prior))
        self.assertEqual(result.loc[2,'gameDate'],prior.loc[2,'gameDate'])

    def test_one_observation_wrong_player_uuid_wrong_venue_wrong_dates_not_whitelisted(self):
        normal=verified_rows()
        variants=[
            normal[:1],
            [source_event('2026-10-05T22:30:00Z',venue=5),normal[1]],
            [source_event('2026-10-05T22:30:00Z',home=888),normal[1]],
            [source_event('2026-10-05T22:30:00Z',start='2026-10-06T01:00:00Z'),normal[1]],
            [source_event('2026-10-05T22:30:00Z',fixture_date='2026-10-04'),normal[1]],
            [source_event('2026-10-05T22:30:00Z',lineup=False),normal[1]],
            [source_event('2026-10-05T20:00:00Z'),source_event('2026-10-05T20:15:00Z')],
            [source_event('2026-10-06T00:30:00Z'),normal[1]],
            [source_event('2026-10-05T22:30:00Z'),
             source_event('2026-10-05T22:32:00Z')],
        ]
        for bad in variants:
            with self.subTest(changes=bad):
                verified=mod.verified_far_start_overrides(
                    old_master(),{'849834':official()},bad,
                    clock=datetime(2026,10,6,0,40,tzinfo=timezone.utc))
                self.assertEqual(verified,{})

    def test_independently_wrong_official_venue_never_accepted(self):
        changed=official()
        changed['venue_id']=14
        verified=mod.verified_far_start_overrides(
            old_master(),{'849834':changed},verified_rows(),
            clock=datetime(2026,10,5,23,22,tzinfo=timezone.utc))
        self.assertEqual(verified,{})

    def test_forged_attestation_with_other_new_start_rejected_in_update(self):
        verified=mod.verified_far_start_overrides(
            old_master(),{'849834':official()},verified_rows(),
            clock=datetime(2026,10,5,23,22,tzinfo=timezone.utc))
        bad={**verified['849834'],'new_start':'2026-10-07T00:00:00Z'}
        result,proof=mod.update_frame(old_master(),{'849834':official()},
                                      verified_start_overrides={'849834':bad})
        self.assertEqual(proof['updated_games'],0)
        self.assertEqual(proof['held_for_review'][0]['reason'],'KICKOFF_CHANGED_BEYOND_TWO_HOURS')

    def test_uncorroborated_second_fixture_remains_held_with_another_verified_game(self):
        f=old_master()
        changed=official()
        other=game(849839,start='2026-10-06T04:00:00Z',
                   away='New York Yankees',home='Tampa Bay Rays',
                   away_id=147,home_id=139,status='Final')
        other['venue_id']='100'
        other['away_team_id']=str(other['away_team_id'])
        other['home_team_id']=str(other['home_team_id'])
        good=mod.verified_far_start_overrides(
            f,{'849834':changed,'849839':other},verified_rows(),
            clock=datetime(2026,10,5,23,22,tzinfo=timezone.utc))
        new,receipt=mod.update_frame(f,{'849834':changed,'849839':other},
                                     verified_start_overrides=good)
        self.assertEqual(receipt['updated_game_ids'],['849834'])
        self.assertEqual(receipt['held_for_review'][0]['gamePk'],'849839')
        self.assertEqual(new.loc[1,'gameDate'],f.loc[1,'gameDate'])

    def test_source_file_dry_run_has_no_byte_mutation_and_replay_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            dest=root/'baseball_vault/derived/MLB_GAME_MASTER.csv'
            dest.parent.mkdir(parents=True,exist_ok=True)
            frame=old_master()
            frame.to_csv(dest,index=False)
            dest.with_suffix('.parquet').write_bytes(b'TEST_NOT_VALID_PARQUET_AND_DRY_RUN_NEVER_TOUCHES')
            pre=root/'intelligence_warehouse/mlb_pregame_capture/MLB_PREGAME_SOURCE_EVIDENCE.jsonl'
            pre.parent.mkdir(parents=True,exist_ok=True)
            pre.write_text(evidence(verified_rows()))
            payload_=payload(official())
            for record in payload_['dates'][0]['games']:
                record['venue']={'id':4,'name':'Rate Field'}
            before=dest.read_bytes()
            oldpq=dest.with_suffix('.parquet').read_bytes()
            receipt=mod.run(
                root,FakeSession(payload_),
                clock=datetime(2026,10,5,23,23,tzinfo=timezone.utc),
                dry_run=True,
            )
            self.assertEqual(receipt['status'],'DRY_RUN_READY')
            self.assertEqual(receipt['verified_large_kickoff_corrections'][0]['gamePk'],'849834')
            self.assertEqual(dest.read_bytes(),before)
            self.assertEqual(dest.with_suffix('.parquet').read_bytes(),oldpq)
            self.assertFalse((dest.parent/'MLB_MASTER_FRESHNESS_RECEIPT.json').exists())

if __name__=='__main__':
    unittest.main()
