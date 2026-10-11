import importlib.util,pathlib,unittest
p=pathlib.Path('/home/ubuntu/sports-hulk/scripts/collect_kalshi_nfl_orderbooks_readonly.py')
spec=importlib.util.spec_from_file_location('depth',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class DepthSafety(unittest.TestCase):
 def test_valid_bid_levels(self):
  r=m.transform({'orderbook_fp':{'yes_dollars':[['0.7','5'],['0.8','2']],'no_dollars':[['0.2','10']]}})
  self.assertTrue(r['levels_present']);self.assertEqual(r['top_yes_bid'],0.8)
 def test_missing_side_is_not_two_sided(self):
  self.assertFalse(m.transform({'orderbook_fp':{'yes_dollars':[['0.8','1']]}})['levels_present'])
 def test_invalid_levels_filtered(self):
  self.assertEqual(m.sanitize_side([['2.0','1'],['0.2','-1'],['0.5','3']]),[{'price_dollars':0.5,'contracts':3.0}])
if __name__=='__main__':unittest.main()
