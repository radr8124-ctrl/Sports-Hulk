"""A frozen retrospectively trained MLB model must not learn from new holdout rows."""
import copy,unittest
from datetime import datetime,timedelta,timezone
from intelligence_warehouse.betting_v2.hf_mlb_prop_locked_holdout import freeze_historical_hits_model,evaluate_new_shard_holdout


def data(n=50,start=datetime(2026,3,25,tzinfo=timezone.utc),first_game=1):
 return [dict(status='VERIFIED_HISTORICAL',pair_status='VERIFIED_SAME_BOOK_TIME_PAIR',asof_status='PREGAME_FEATURE_VERIFIED',
              market='player hits',official_game_pk=i+first_game,
              official_start=(start+timedelta(days=i)).isoformat(),
              market_fair_probability=0.44+(i%4)*0.035,
              pregame_context_signal=(i%5-2)*0.15,
              verified_win=bool(i%3==0)) for i in range(n)]


class LockedModelTests(unittest.TestCase):
 def test_freeze_excludes_external_later_games_and_has_stable_coefficients(self):
  model=freeze_historical_hits_model(data(40))
  self.assertEqual(model['train_independent_games'],40)
  self.assertEqual(model['market'],'player hits')
  self.assertEqual(len(model['market_only_beta']),2)
  self.assertEqual(len(model['market_plus_pregame_beta']),3)
  self.assertEqual(model['deployment'],'RESEARCH_ONLY_NO_LIVE_MODEL_ACCESS')

 def test_new_later_holdout_evaluated_without_refitting(self):
  train=data(40);model=freeze_historical_hits_model(train)
  frozen=copy.deepcopy(model)
  test=data(30,start=datetime(2026,7,1,tzinfo=timezone.utc),first_game=500)
  result=evaluate_new_shard_holdout(model,test)
  self.assertEqual(result['status'],'EXTERNAL_LOCKED_HOLDOUT_EVALUATED')
  self.assertEqual(result['holdout_independent_games'],30)
  self.assertEqual(result['training_independent_games'],40)
  self.assertIn('fair_market_brier',result)
  self.assertIn('frozen_market_plus_pregame_brier',result)
  self.assertEqual(result['production_play_approved'],False)
  self.assertEqual(model,frozen)

 def test_official_stat_derived_later_analytical_grades_are_allowed_but_not_called_platform_settlements(self):
  frozen=freeze_historical_hits_model(data(40))
  later=data(30,start=datetime(2026,7,1,tzinfo=timezone.utc),first_game=500)
  for row in later:
   row['status']='OFFICIAL_DERIVED_HISTORICAL'
   row['platform_settlement_claim']=False
  res=evaluate_new_shard_holdout(frozen,later)
  self.assertEqual(res['holdout_independent_games'],30)
  self.assertFalse(res['production_play_approved'])

 def test_contemporaneous_overlap_is_not_valid_holdout(self):
  model=freeze_historical_hits_model(data(40))
  r=evaluate_new_shard_holdout(model,data(15))
  self.assertEqual(r['status'],'NO_NEW_CHRONOLOGICALLY_LATER_GAMES')

 def test_mixed_market_or_weak_source_cannot_sneak_into_holdout(self):
  model=freeze_historical_hits_model(data(40))
  future=data(30,start=datetime(2026,7,1,tzinfo=timezone.utc),first_game=500)
  future[0]['pair_status']='NO_EXACT_OPPOSITE_SIDE'
  future[1]['market']='player rbis'
  result=evaluate_new_shard_holdout(model,future)
  self.assertEqual(result['holdout_independent_games'],28)

if __name__=='__main__':unittest.main()
