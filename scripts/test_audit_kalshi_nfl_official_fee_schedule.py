import pathlib,importlib.util,unittest
p=pathlib.Path('/home/ubuntu/sports-hulk/scripts/audit_kalshi_nfl_official_fee_schedule.py')
spec=importlib.util.spec_from_file_location('fees',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class FeeSchedule(unittest.TestCase):
 def test_nfl_series_only(self):
  rows=m.assess([{'ticker':'KXNFLGAME-26OCT11PHIJAC-JAC','status':'active'}]);self.assertTrue(rows[0]['published_series_fee_schedule_verified']);self.assertFalse(rows[0]['fee_execution_quote_verified'])
 def test_other_series_not_silently_approved(self):
  r=m.assess([{'ticker':'KXNHLGAME-TEST','status':'active'}])[0];self.assertFalse(r['published_series_fee_schedule_verified'])
 def test_inactive_not_ready(self):
  r=m.assess([{'ticker':'KXNFLGAME-TEST','status':'closed'}])[0];self.assertFalse(r['published_series_fee_schedule_verified'])
if __name__=='__main__':unittest.main()
