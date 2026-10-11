import datetime,importlib.util,json,pathlib,unittest
path=pathlib.Path('/home/ubuntu/sports-hulk/scripts/evaluate_prediction_markets_readonly.py')
spec=importlib.util.spec_from_file_location('eval_markets',path)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class ConservativeGate(unittest.TestCase):
 def setUp(self):
  self.now=datetime.datetime(2026,10,11,14,0,tzinfo=datetime.timezone.utc)
  self.doc={'captured_at_utc':'2026-10-11T13:58:00+00:00','markets':[{'provider':'KALSHI','id':'A','yes_bid':0.40,'yes_ask':0.45,'volume':100},{'provider':'POLYMARKET','id':'B','display_prices':[0.72]}]}
 def test_no_play_when_model_missing(self):
  r=mod.evaluate(self.doc,self.now);self.assertEqual((r['play'],r['pass']),(0,2));self.assertTrue(all(not row['simulation_eligible'] for row in r['records']))
 def test_indicative_prices_rejected(self):
  r=mod.evaluate(self.doc,self.now);self.assertIn('EXECUTABLE_PRICE_UNVERIFIED',r['records'][1]['reason_codes'])
 def test_stale_price_rejected(self):
  self.doc['captured_at_utc']='2026-10-11T13:30:00+00:00'
  r=mod.evaluate(self.doc,self.now);self.assertTrue(all('SOURCE_STALE_OVER_15_MIN' in row['reason_codes'] for row in r['records']))
 def test_invalid_quote_rejected(self):
  self.doc['markets'][0]['yes_bid']=0.88
  r=mod.evaluate(self.doc,self.now);self.assertIn('INVALID_BID_ASK',r['records'][0]['reason_codes'])
if __name__=='__main__':unittest.main()
