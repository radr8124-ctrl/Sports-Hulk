import importlib.util,pathlib,unittest
p=pathlib.Path('/home/ubuntu/sports-hulk/scripts/audit_nfl_independent_model_validation.py')
spec=importlib.util.spec_from_file_location('gate',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ValidationGate(unittest.TestCase):
 def sample(self,advanced=.2,market=.21,pristine=False):
  return {'evaluations':{'historical_prior_week_score_form_ridge':{'brier':advanced,'log_loss':.5},'raw_compiled_market_home_no_vig':{'brier':market,'log_loss':.6}},'game_count':300,'paired_week_block_95ci_market_minus_advanced_model':[.001,.02],'historical_2025_seen_diagnostic_not_pristine_future':not pristine}
 def test_holdout_not_pristine(self):self.assertFalse(m.evaluate(self.sample())['validated_independent_edge'])
 def test_market_beats_model(self):self.assertFalse(m.evaluate(self.sample(advanced=.22,market=.21,pristine=True))['validated_independent_edge'])
 def test_strict_gate_all_conditions(self):self.assertTrue(m.evaluate(self.sample(pristine=True))['validated_independent_edge'])
 def test_nonpositive_ci_blocks(self):
  e=self.sample(pristine=True);e['paired_week_block_95ci_market_minus_advanced_model']=[-.01,.01]
  self.assertFalse(m.evaluate(e)['validated_independent_edge'])
if __name__=='__main__':unittest.main()
