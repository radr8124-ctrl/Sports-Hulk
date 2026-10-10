"""Strict source/frozen original and scheduler readback contracts: no wagers/picks."""
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path('/home/ubuntu/sports-hulk')
TARGET = ROOT/'scripts/zenith_nfl_final_observer.py'


def load():
    spec=importlib.util.spec_from_file_location('observer',TARGET)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FinalObserverTests(unittest.TestCase):
    def test_original_prefix_and_survivor_proof_are_not_rewritten(self):
        m=load()
        expected=m.ORIGINAL_FIRST_13_SHA256
        orig=(ROOT/'intelligence_warehouse/nfl_advanced_pregame/NFL_FIRST_PREKICKOFF_NINE_FEATURE_SCORE_FORM_SHADOW.jsonl').read_bytes()
        self.assertEqual(m.first_n_lines_hash(orig,13),expected)
        self.assertEqual(m.first_n_lines_hash(orig+b'future-extra-row\n',13),expected)
        self.assertNotEqual(m.first_n_lines_hash(orig.replace(b'research_only',b'research_ONLY',1),13),expected)
        self.assertEqual(m.first_n_lines_hash((ROOT/'intelligence_warehouse/survivor_accountability/SURVIVOR_V2_FORWARD_LEDGER.jsonl').read_bytes(),1),m.ORIGINAL_SURVIVOR_LEDGER_FIRST_SHA256)

    def test_semantic_private_state_detects_pick_mutation_without_leaking_names(self):
        m=load()
        state={'pool_current_week':5,'entries':{'PRIVATE MEMBER 01':{'status':'ALIVE','used_teams':['A'],
            'current_picks':[],'week_5':{'submitted':False}}}}
        a=m.private_pick_fingerprint(state)
        self.assertRegex(a,r'^[a-f0-9]{64}$')
        state['entries']['PRIVATE MEMBER 01']['current_picks']=['B']
        self.assertNotEqual(m.private_pick_fingerprint(state),a)

    def test_verify_only_does_not_mutate_sources_or_call_a_network_collector(self):
        m=load()
        before=m.snapshot_immutable_state()
        process=subprocess.run([sys.executable,str(TARGET),'--verify-only'],cwd=ROOT,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=18)
        self.assertEqual(process.returncode,0,process.stdout+'\n'+process.stderr)
        receipt=json.loads(process.stdout.strip().splitlines()[-1])
        self.assertIn(receipt.get('status'),('AWAITING_INDEPENDENT_FINALS','TINY_FORWARD_SAMPLE_NOT_MARKET_EDGE',
            'OFFICIAL_FINAL_AWAITING_VALIDATED_GRADE','DIAGNOSTIC_REVIEW_ONLY_NOT_PROVEN_EDGE'))
        self.assertEqual(receipt.get('research_only'),True)
        self.assertEqual(receipt.get('automatic_betting'),False)
        self.assertEqual(receipt.get('network_requests'),0)
        self.assertEqual(m.snapshot_immutable_state(),before)

    def test_timer_only_runs_explicit_read_only_runner(self):
        service=(ROOT/'deploy/systemd/user/sports-zenith-nfl-final-observer.service').read_text()
        timer=(ROOT/'deploy/systemd/user/sports-zenith-nfl-final-observer.timer').read_text()
        self.assertIn('zenith_nfl_final_observer.py --run',service)
        self.assertIn('Type=oneshot',service)
        self.assertIn('/usr/bin/flock -n',service)
        self.assertIn('Persistent=true',timer)
        self.assertIn('OnCalendar=',timer)
        self.assertNotIn('survivor/save-picks',service+timer)
        self.assertNotIn('approved_bet=true',service+timer)


if __name__=='__main__':
    unittest.main()
