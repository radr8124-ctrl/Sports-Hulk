"""Only 849809 future NL bracket can be changed after two archived source captures."""
from __future__ import annotations
import copy,hashlib,json,shutil,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path

import pandas as pd
from baseball_vault.mlb_future_bracket_attestation import (
    load_archived_original_responses,verified_nl_placeholder_overrides,
)
from scripts import mlb_attested_future_bracket_reconcile as fix

NOW=datetime(2026,10,9,7,51,tzinfo=timezone.utc)


class FakeResponse:
    def __init__(self,payload):
        self._body=json.dumps(payload).encode()
        self.content=self._body
    def raise_for_status(self):return None
    def json(self):return json.loads(self._body)


class FakeSession:
    def __init__(self,payload):self.body=payload
    def get(self,url,*,params,timeout):return FakeResponse(self.body)


class TestNLFutureAttestation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for path in (
            fix.MASTER_REL,fix.PARQUET_REL,fix.EVIDENCE_REL,
            fix.FROZEN_REL,fix.RAW_ODDS_REL,
        ):
            source=fix.ROOT/path
            dest=self.root/path
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,dest)
        src=fix.ROOT/'intelligence_warehouse/mlb_pregame_capture/official_future_schedule_raw'
        target=self.root/'intelligence_warehouse/mlb_pregame_capture/official_future_schedule_raw'
        shutil.copytree(src,target)
        self.raw_file=next(target.glob('*074614Z.json'))
        self.receipt=next(target.glob('*074614Z_RECEIPT.json'))
        self.payload=json.loads(self.raw_file.read_text())
        self.session=FakeSession(self.payload)

    def run_dry(self,**kwargs):
        return fix.run(root=self.root,session=self.session,now=NOW,dry_run=True,**kwargs)

    def test_verified_public_sources_change_exactly_seven_one_game_fields(self):
        a=self.run_dry()
        self.assertEqual(a['state'],'DRY_RUN_ONLY')
        self.assertEqual(a['gamePk'],849809)
        self.assertEqual(a['original_gamepk_rows_count'],a['new_gamepk_rows_count'])
        self.assertEqual({x['field'] for x in a['changes']},fix.WHITELIST)
        self.assertEqual({x['gamePk'] for x in a['changes']},{'849809'})
        self.assertEqual(a['proof']['independent_original_captures'],2)
        self.assertFalse(a['real_batting_orders_verified'])
        self.assertFalse(a['future_play_or_proven_edge_claim'])

    def test_dry_run_is_original_source_byte_identical(self):
        before={p:(self.root/p).read_bytes() for p in (
            fix.MASTER_REL,fix.PARQUET_REL,fix.EVIDENCE_REL,fix.FROZEN_REL,fix.RAW_ODDS_REL)}
        self.run_dry()
        for path,original in before.items():
            self.assertEqual((self.root/path).read_bytes(),original)
        self.assertFalse((self.root/fix.RECEIPT_REL).exists())

    def test_apply_changes_only_original_future_placeholder_fields(self):
        source_before=(self.root/fix.EVIDENCE_REL).read_bytes()
        model_before=(self.root/fix.FROZEN_REL).read_bytes()
        final_before=(self.root/fix.RAW_ODDS_REL).read_bytes()
        previous=pd.read_csv(self.root/fix.MASTER_REL,dtype=str,low_memory=False).fillna('')
        ret=fix.run(root=self.root,session=self.session,now=NOW,dry_run=False)
        current=pd.read_csv(self.root/fix.MASTER_REL,dtype=str,low_memory=False).fillna('')
        self.assertEqual(ret['state'],'VERIFIED_FUTURE_FIXTURE_MASTER_CORRECTED')
        self.assertEqual(len(previous),len(current))
        self.assertEqual(len(ret['changes']),7)
        diffs=[(current.loc[i,'gamePk'],col) for col in previous
               for i in previous.index[previous[col]!=current[col]]]
        self.assertEqual(set(diffs),{('849809',x) for x in fix.WHITELIST})
        row=current[current.gamePk.eq('849809')].iloc[0]
        self.assertEqual(row['home_team'],'Milwaukee Brewers')
        self.assertEqual(row['away_team'],'Los Angeles Dodgers')
        self.assertEqual(row['venue_id'],'32')
        self.assertEqual(row['gameDate'],'2026-10-12T00:00:00Z')
        self.assertEqual((self.root/fix.FROZEN_REL).read_bytes(),model_before)
        self.assertEqual((self.root/fix.RAW_ODDS_REL).read_bytes(),final_before)
        self.assertEqual((self.root/fix.EVIDENCE_REL).read_bytes(),source_before)
        self.assertTrue((self.root/fix.RECEIPT_REL).exists())
        with self.assertRaisesRegex(ValueError,'ZERO_OR_MULTIPLE'):
            fix.run(root=self.root,session=self.session,now=NOW,dry_run=True)

    def test_wrong_response_hash_refused_no_source_change(self):
        altered=self.raw_file.read_bytes().replace(b'Dodgers',b'Yankees')
        self.raw_file.write_bytes(altered)
        before=(self.root/fix.MASTER_REL).read_bytes()
        with self.assertRaisesRegex(ValueError,'TAMPERED'):
            self.run_dry()
        self.assertEqual((self.root/fix.MASTER_REL).read_bytes(),before)

    def test_wrong_current_team_identity_never_corrects_placeholder(self):
        false=copy.deepcopy(self.payload)
        games=[g for day in false['dates'] for g in day['games'] if g.get('gamePk')==849809]
        self.assertEqual(len(games),1)
        games[0]['teams']['home']['team']['id']=999
        self.session=FakeSession(false)
        before=(self.root/fix.MASTER_REL).read_bytes()
        with self.assertRaisesRegex(ValueError,'ZERO_OR_MULTIPLE'):
            self.run_dry()
        self.assertEqual((self.root/fix.MASTER_REL).read_bytes(),before)

    def test_missing_independent_collector_source_refuses(self):
        p=self.root/fix.EVIDENCE_REL
        rows=[x for x in p.read_text().splitlines() if x.strip() and json.loads(x).get('game_pk')!=849809]
        p.write_text('\n'.join(rows)+'\n')
        with self.assertRaisesRegex(ValueError,'ZERO_OR_MULTIPLE'):
            self.run_dry()

    def test_no_source_resolution_after_placeholder_start(self):
        with self.assertRaisesRegex(ValueError,'ZERO_OR_MULTIPLE'):
            fix.run(root=self.root,session=self.session,
                    now=datetime(2026,10,11,10,tzinfo=timezone.utc),dry_run=True)

    def test_only_literal_allowed_game_id(self):
        with self.assertRaisesRegex(ValueError,'TARGETED_ONE_FIXTURE'):
            self.run_dry(game_pk='849812')

    def test_wrong_old_bracket_venue_cannot_be_rewritten(self):
        path=self.root/fix.MASTER_REL
        f=pd.read_csv(path,dtype=str,low_memory=False)
        f.loc[f.gamePk.eq('849809'),'venue_id']='1234'
        f.to_csv(path,index=False)
        with self.assertRaisesRegex(ValueError,'ZERO_OR_MULTIPLE'):
            self.run_dry()

    def test_archived_raw_filename_path_cannot_escape_original_source_folder(self):
        j=json.loads(self.receipt.read_text())
        j['source_filename']='../../outside.json'
        self.receipt.write_text(json.dumps(j))
        with self.assertRaisesRegex(ValueError,'RAW_FILENAME_MISMATCH'):
            load_archived_original_responses(self.root)


if __name__=='__main__':unittest.main()
