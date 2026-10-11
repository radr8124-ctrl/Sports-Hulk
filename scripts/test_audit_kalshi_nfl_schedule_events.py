import importlib.util,pathlib,unittest
path=pathlib.Path('/home/ubuntu/sports-hulk/scripts/audit_kalshi_nfl_schedule_events.py')
spec=importlib.util.spec_from_file_location('nflmatch',path)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class EventAuditTest(unittest.TestCase):
 def setUp(self):
  self.games=[{'start_time':'2026-10-11T13:30:00Z','away_abbr':'PHI','home_abbr':'JAC','event_id':'espn1'}]
 def test_matching_date_and_both_abbreviations(self):
  matches,rejected=mod.audit([{'event_ticker':'KXNFLGAME-26OCT11PHIJAC'}],self.games)
  self.assertEqual(len(matches),1);self.assertEqual(len(rejected),0)
  self.assertEqual(matches[0]['status'],'SCHEDULE_MATCH_ONLY_NO_CONTRACT_VERIFICATION')
 def test_reversed_teams_not_accepted(self):
  m,r=mod.audit([{'event_ticker':'KXNFLGAME-26OCT11JACPHI'}],self.games)
  self.assertFalse(m);self.assertEqual(len(r),1)
 def test_wrong_date_not_accepted(self):
  m,r=mod.audit([{'event_ticker':'KXNFLGAME-26OCT12PHIJAC'}],self.games)
  self.assertFalse(m);self.assertEqual(len(r),1)
if __name__=='__main__':unittest.main()
