import importlib.util,pathlib,unittest
p=pathlib.Path('/home/ubuntu/sports-hulk/scripts/audit_kalshi_nfl_contracts.py')
spec=importlib.util.spec_from_file_location('contract',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ContractSafety(unittest.TestCase):
 def setUp(self):
  self.c={'event_ticker':'KXNFLGAME-26OCT11PHIJAC','espn_event_id':'401','away_abbr':'PHI','home_abbr':'JAC'}
  self.market={'ticker':'KXNFLGAME-26OCT11PHIJAC-JAC','title':'Jacksonville wins','rules_primary':'If Jacksonville wins the game, then the market resolves to Yes.','rules_secondary':'If the game ends in a tie, resolve 0.50.','yes_bid_dollars':'0.4','yes_ask_dollars':'0.5'}
  self.data={'event':{'event_ticker':self.c['event_ticker'],'markets':[self.market]}}
 def test_capture_real_rules(self):
  rows,status=m.extract(self.c,self.data);self.assertEqual((len(rows),status),(1,'CAPTURED'));self.assertFalse(rows[0]['approved_pick'])
 def test_reject_wrong_event(self):
  self.data['event']['event_ticker']='OTHER';self.assertEqual(m.extract(self.c,self.data)[1],'EVENT_ID_MISMATCH')
 def test_reject_no_tie_rules(self):
  self.market['rules_secondary']='';self.assertEqual(m.extract(self.c,self.data)[0],[])
 def test_reject_wrong_team(self):
  self.market['ticker']='KXNFLGAME-26OCT11PHIJAC-NYG';self.assertEqual(m.extract(self.c,self.data)[0],[])
if __name__=='__main__':unittest.main()
