import pathlib,importlib.util,unittest
p=pathlib.Path('/home/ubuntu/sports-hulk/scripts/review_kalshi_nfl_settlement_terms.py')
spec=importlib.util.spec_from_file_location('rule_audit',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class RuleTests(unittest.TestCase):
 def test_missing_rules_block(self):
  r=m.review({'ticker':'T-JAC','yes_team_abbr':'JAC'});self.assertFalse(r['literal_rule_check_passed']);self.assertFalse(r['approved_pick'])
 def test_wrong_team_block(self):
  r=m.review({'ticker':'T-PHI','yes_team_abbr':'JAC'});self.assertFalse(r['rule_checks']['contract_team_in_event'])
if __name__=='__main__':unittest.main()
