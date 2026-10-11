import importlib.util,pathlib,unittest
p=pathlib.Path('/home/ubuntu/sports-hulk/scripts/simulate_kalshi_nfl_entry_costs.py')
s=importlib.util.spec_from_file_location('calc',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class EntryCostTests(unittest.TestCase):
 def test_yes_cost_from_no_bid(self):
  r=m.estimate_yes_buy([{'price_dollars':0.2,'contracts':10}],2)
  self.assertEqual(r['gross_total_dollars'],1.6);self.assertFalse(r['fee_included'])
 def test_best_price_consumed_first(self):
  r=m.estimate_yes_buy([{'price_dollars':0.1,'contracts':10},{'price_dollars':0.2,'contracts':2}],3)
  self.assertAlmostEqual(r['gross_total_dollars'],2.5)
 def test_depth_shortfall_is_not_full_fill(self):
  r=m.estimate_yes_buy([{'price_dollars':0.3,'contracts':1}],10)
  self.assertEqual(r['status'],'INSUFFICIENT_DEPTH');self.assertFalse(r['guaranteed_fill'])
 def test_bad_size(self):
  self.assertEqual(m.estimate_yes_buy([],0)['status'],'INVALID_SIZE')
if __name__=='__main__':unittest.main()
