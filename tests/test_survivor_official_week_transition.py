"""Rollover must never certify an external Survivor ticket from a live scoreboard.

All tests are on synthetic isolated copies. Original private member ledger is
never written, graded or used as a fixture for authorized pick changes.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from nfl_live import update_survivor_current_week as rollover

WEEK_4={'required_picks':1,'official_pool_sheet_confirmed':True,
        'rule_status':'CONFIRMED_FROM_IMPORTED_POOL_HEADER','entry_result':'WIN',
        'picks':[{'team':'Minnesota Vikings','result':'WIN'}]}
WEEK_5={'required_picks':None,'rule_status':'AWAITING_OFFICIAL_POOL_SHEET',
        'official_pool_sheet_confirmed':False,'submitted':False,
        'picks':[],'entry_result':'OPEN'}

def owner(**updates):
    base={'status':'ALIVE','current_week':5,'current_picks':[],
          'current_pick_status':'OPEN','used_teams':['Minnesota Vikings'],
          'history':[{'week':4,'team':'Minnesota Vikings','result':'SURVIVED'}],
          'week_4':copy.deepcopy(WEEK_4),'week_5':copy.deepcopy(WEEK_5)}
    base.update(updates)
    return base

def official(owner_record=None):
    e=copy.deepcopy(owner_record or owner())
    e['week_5']={'required_picks':1,'official_pool_sheet_confirmed':True,
     'rule_status':'CONFIRMED_FROM_IMPORTED_POOL_HEADER','entry_result':'WIN',
     'picks':[{'team':'Jacksonville Jaguars','result':'WIN'}]}
    return e

class SafeSurvivorRollover(unittest.TestCase):
    def test_private_empty_week5_does_not_open_week6_without_official_ticket(self):
        e=owner()
        before=copy.deepcopy(e)
        rollover.open_current_week(e,6,'2026-10-13T12:00:00+00:00')
        self.assertEqual(e,before)
        self.assertFalse(rollover.can_advance(entry=e,from_week=5,to_week=6))

    def test_even_synthetic_zenith_only_winning_selection_cannot_substitute_official_confirmation(self):
        e=owner()
        e['week_5']={'required_picks':1,'official_pool_sheet_confirmed':False,
             'rule_status':'CONFIRMED_FROM_2026_ORIGINAL_RULES','submitted':False,
             'entry_result':'WIN','picks':[{'team':'Jacksonville Jaguars','result':'WIN'}]}
        before=copy.deepcopy(e)
        rollover.open_current_week(e,6,'2026-10-13T12:00:00+00:00')
        self.assertEqual(e,before)

    def test_original_imported_week5_and_full_official_winner_can_open_week6_with_two_pick_rule(self):
        e=official()
        rollover.open_current_week(e,6,'2026-10-13T12:00:00+00:00')
        self.assertEqual(e['current_week'],6)
        self.assertEqual(e['week_5']['entry_result'],'WIN')
        self.assertEqual(e['week_6']['entry_result'],'OPEN')
        self.assertEqual(e['week_6']['picks'],[])
        self.assertEqual(e['status'],'ALIVE')
        self.assertTrue(rollover.can_advance(entry=official(),from_week=5,to_week=6))

    def test_week3_original_double_pick_requirement_must_have_both_wins(self):
        e=owner(current_week=3,week_3={'required_picks':2,'official_pool_sheet_confirmed':True,
          'entry_result':'WIN','picks':[{'team':'Buffalo Bills','result':'WIN'}]})
        self.assertFalse(rollover.can_advance(entry=e,from_week=3,to_week=4))
        e['week_3']['picks'].append({'team':'Kansas City Chiefs','result':'WIN'})
        self.assertTrue(rollover.can_advance(entry=e,from_week=3,to_week=4))

    def test_missing_sheet_tie_loss_duplicate_inactive_and_week_jump_never_advance(self):
        for kind in ['no_sheet','open','one_leg_pending','lost','duplicate','eliminated','jump']:
            e=official()
            to=6
            if kind=='no_sheet':e['week_5']['official_pool_sheet_confirmed']=False
            if kind=='open':e['week_5']['entry_result']='OPEN'
            if kind=='one_leg_pending':e['week_5']['picks'][0]['result']='PENDING'
            if kind=='lost':e['week_5']['picks'][0]['result']='LOSS'
            if kind=='duplicate':e['week_5']['picks'].append(copy.deepcopy(e['week_5']['picks'][0]))
            if kind=='eliminated':e['status']='ELIMINATED'
            if kind=='jump':to=7
            previous=copy.deepcopy(e)
            rollover.open_current_week(e,to,'2026-10-13T12:00:00+00:00')
            self.assertEqual(e,previous,kind)

    def test_no_private_write_if_unconfirmed_entry_and_collector_moves_global_week(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            entries=root/'SURVIVOR_ENTRIES.json'
            sched=root/'SCHEDULE.csv'
            strategy=root/'STRATEGY.csv'
            state={'pool_current_week':5,'entries':{'SYNTHETIC MEMBER 01':owner()}}
            entries.write_text(json.dumps(state,indent=2))
            schedule=pd.DataFrame([
                {'season':2026,'game_type':'REG','week':5,'away_team':'JAX','home_team':'PHI','away_score':20,'home_score':13},
                {'season':2026,'game_type':'REG','week':6,'away_team':'NE','home_team':'BUF','away_score':None,'home_score':None},
            ])
            schedule.to_csv(sched,index=False)
            pd.DataFrame([{'current_week':6}]).to_csv(strategy,index=False)
            before=entries.read_bytes()
            with patch.object(rollover,'ENTRIES',entries),patch.object(rollover,'SCHEDULE',sched),patch.object(rollover,'STRATEGY',strategy):
                rollover.main()
            self.assertEqual(entries.read_bytes(),before)

    def test_global_transition_denied_when_any_active_member_would_be_advanced_unverified(self):
        s={'pool_current_week':5,'entries':{
            'SYNTHETIC ACTIVE 01':official(),
            'SYNTHETIC ACTIVE 02':owner(),
            'SYNTHETIC ELIMINATED':owner(status='ELIMINATED'),
        }}
        assert not rollover.can_advance_pool(s,6)
        s['entries']['SYNTHETIC ACTIVE 02']=official()
        self.assertTrue(rollover.can_advance_pool(s,6))
        self.assertFalse(rollover.can_advance_pool(s,7))
        self.assertFalse(rollover.can_advance_pool(s,4))

    def test_direct_invocation_import_only_is_safe_from_any_directory(self):
        # Use runpy with a non-main name: verifies the actual scheduled script
        # import path without executing the main that edits private state.
        import subprocess
        import sys
        script=Path(rollover.__file__).resolve()
        result=subprocess.run([sys.executable,'-c',
              'import runpy; r=runpy.run_path('+repr(str(script))+',run_name="__survivor_import_only__"); assert callable(r["can_advance_pool"])'],
            cwd='/tmp',capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr[:600])

    def test_active_entry_stays_on_same_week_without_resetting_current_pick_after_refresh(self):
        e=owner(current_picks=['Jacksonville Jaguars'],current_pick_status='SAVED_NOT_SUBMITTED')
        rollover.open_current_week(e,5,'2026-10-10T21:00:00+00:00')
        self.assertEqual(e['current_picks'],['Jacksonville Jaguars'])
        self.assertEqual(e['current_pick_status'],'SAVED_NOT_SUBMITTED')

if __name__=='__main__':
    unittest.main()
