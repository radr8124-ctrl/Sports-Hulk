"""Attested future MLB schedule correction without inventing lineups or past source time."""
from datetime import datetime,timezone
from pathlib import Path
from copy import deepcopy
import json,tempfile,unittest

import pandas as pd
from baseball_vault import refresh_mlb_master_status as fix
from tests.test_mlb_master_attested_start_repair import old_master,source_event,evidence
from tests.test_mlb_master_freshness import game,FakeSession,payload

OLD="2026-10-10T21:00:00Z"
NEW="2026-10-11T00:00:00Z"
CLOCK=datetime(2026,10,9,7,15,tzinfo=timezone.utc)


def prior():
    x=old_master().copy(deep=True)
    x.loc[0,'gameDate']=OLD
    x.loc[0,'officialDate']="2026-10-10"
    x.loc[0,'status']="Scheduled"
    return x


def official():
    x=game(849834,start=NEW,status="Scheduled",away_score=None,home_score=None)
    x['venue_id']="4"
    x['officialDate']="2026-10-10"
    x['away_team_id']=str(x['away_team_id'])
    x['home_team_id']=str(x['home_team_id'])
    return x


def obs(at,**changes):
    x=source_event(at,start=NEW,source_status="Scheduled",fixture_date="2026-10-10",lineup=False)
    x.update(changes)
    return x


def observations():
    return [obs("2026-10-09T00:07:38Z"),obs("2026-10-09T03:09:28Z")]


def attest(events=None,old=None,new=None,clock=CLOCK):
    return fix.verified_future_schedule_start_overrides(
       old if old is not None else prior(),
       {'849834':new if new is not None else official()},
       observations() if events is None else events,clock=clock)


class TestOfficialFutureKickoffProof(unittest.TestCase):
    def test_two_distinct_early_confirmed_schedule_captures(self):
        att=attest()
        self.assertEqual(list(att),['849834'])
        proof=att['849834']
        self.assertEqual(proof['independent_capture_count'],2)
        self.assertFalse(proof['source_lineups_verifiably_published_after_original_stale_time'])
        self.assertTrue(proof['source_schedule_captures_verified_before_old_start'])
        result,summary=fix.update_frame(prior(),{'849834':official()},
                      verified_start_overrides=att,clock=CLOCK)
        self.assertEqual(result.loc[0,'gameDate'],NEW)
        self.assertEqual(summary['updated_game_ids'],['849834'])
        self.assertEqual(len(result),len(prior()))
        self.assertEqual(result.loc[1,'gameDate'],prior().loc[1,'gameDate'])

    def test_no_silent_master_change_without_source_attestation(self):
        out,s=fix.update_frame(prior(),{'849834':official()},clock=CLOCK)
        self.assertEqual(s['updated_games'],0)
        self.assertEqual(s['held_for_review'][0]['reason'],'KICKOFF_CHANGED_BEYOND_TWO_HOURS')
        self.assertEqual(out.loc[0,'gameDate'],OLD)

    def test_missing_capture_wrong_official_metadata_prevents_repair(self):
        current=observations()
        variants=[
          current[:1],
          [current[0],obs("2026-10-09T00:17:38Z")],
          [current[0],obs("2026-10-09T03:09:28Z",evidence_id=current[0]['evidence_id'])],
          [current[0],obs("2026-10-09T03:09:28Z",first_pitch_utc="2026-10-11T01:00:00Z")],
          [current[0],obs("2026-10-10T21:10:00Z")],
          [current[0],obs("2026-10-09T03:09:28Z",fixture={**current[1]['fixture'],'venue_id':99})],
          [current[0],obs("2026-10-09T03:09:28Z",fixture={**current[1]['fixture'],'home_team_id':999})],
          [current[0],obs("2026-10-09T03:09:28Z",fixture={**current[1]['fixture'],'official_date':'2026-10-11'})],
        ]
        for entry in variants:
            with self.subTest(events=entry):
                self.assertEqual(attest(events=entry),{})

    def test_cannot_reconcile_future_source_after_original_old_start(self):
        self.assertEqual(attest(clock=datetime(2026,10,10,21,20,tzinfo=timezone.utc)),{})

    def test_original_venue_or_team_conflict_source_not_accepted(self):
        new=official()
        for field,value in [('venue_id','999'),('home_team_id','999'),('gameType','L'),('officialDate','2026-10-11')]:
            with self.subTest(field=field):
                x={**new,field:value}
                self.assertEqual(attest(new=x),{})

    def test_future_schedule_attestation_is_not_late_lineup_bypass(self):
        x=attest()['849834']
        for field,value in [('new_start','2026-10-11T01:00:00Z'),
                            ('source_capture_times_utc',["2026-10-11T01:00:00Z","2026-10-11T01:20:00Z"]),
                            ('source_distinct_evidence_ids',['same','same']),
                            ('source_original_line_sha256',['a'*64,'a'*64]),
                            ('source_schedule_captures_verified_before_old_start',False)]:
            with self.subTest(field=field):
                bad={**x,field:value}
                output,result=fix.update_frame(prior(),{'849834':official()},
                   verified_start_overrides={'849834':bad},clock=CLOCK)
                self.assertEqual(result['updated_games'],0)
                self.assertEqual(output.loc[0,'gameDate'],OLD)

    def test_dry_run_preserves_original_source_master_and_parquet(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            master=root/'baseball_vault/derived/MLB_GAME_MASTER.csv'
            master.parent.mkdir(parents=True)
            prior().to_csv(master,index=False)
            pq=master.with_suffix('.parquet');pq.write_bytes(b'IMMUTABLE_TEST_PARQUET')
            p=root/'intelligence_warehouse/mlb_pregame_capture/MLB_PREGAME_SOURCE_EVIDENCE.jsonl'
            p.parent.mkdir(parents=True)
            p.write_text(evidence(observations()))
            original_csv=master.read_bytes()
            original_source=p.read_bytes()
            g=payload(official())
            for row in g['dates'][0]['games']:
                row['officialDate']="2026-10-10"
                row['venue']={'id':4,'name':'Verified Source Venue'}
            report=fix.run(root,FakeSession(g),clock=CLOCK,dry_run=True)
            self.assertEqual(report['status'],'DRY_RUN_READY')
            self.assertEqual(report['updated_game_ids'],['849834'])
            self.assertEqual(report['verified_large_kickoff_corrections'][0]['source_corroboration'],
                 'TWO_EARLY_ORIGINAL_MLB_OFFICIAL_SCHEDULE_CAPTURES_AND_FRESH_SCHEDULE')
            self.assertEqual(master.read_bytes(),original_csv)
            self.assertEqual(p.read_bytes(),original_source)
            self.assertEqual(pq.read_bytes(),b'IMMUTABLE_TEST_PARQUET')


if __name__=='__main__':unittest.main()
