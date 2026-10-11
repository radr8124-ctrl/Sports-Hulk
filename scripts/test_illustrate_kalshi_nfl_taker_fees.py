import importlib.util,pathlib,unittest
p=pathlib.Path('/home/ubuntu/sports-hulk/scripts/illustrate_kalshi_nfl_taker_fees.py')
s=importlib.util.spec_from_file_location('fees',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class FeeTests(unittest.TestCase):
 def test_fee_round_up(self):self.assertEqual(str(m.general_fee('.50',100)),'1.75')
 def test_single_contract_round_up(self):self.assertEqual(str(m.general_fee('.50',1)),'0.02')
 def test_bad_price(self):
  with self.assertRaises(ValueError):m.general_fee(1.2,1)
 def test_no_market_verified_picks(self):
  d={'orderbook_capture_utc':'x','contracts':[{'ticker':'T','scenarios':[{'status':'DEPTH_SUFFICIENT','gross_price_per_contract':.5,'requested_contracts':10,'gross_total_dollars':5}]}]}
  r=m.illustrate(d);self.assertFalse(r['market_fee_verified']);self.assertEqual(r['approved_picks'],0);self.assertEqual(r['rows'][0]['scenarios'][0]['illustrative_total_cost'],5.18)
if __name__=='__main__':unittest.main()
