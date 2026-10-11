import unittest
from benchmark_nfl_compact_challenger import chronological_split, advantage_gate
class ChallengerTests(unittest.TestCase):
 def test_train_is_strictly_before_test_and_ids_do_not_overlap(self):
  rows=[dict(game_id=str(y),season=y) for y in [2016,2018,2019,2020,2025]]
  train,test=chronological_split(rows,2019)
  self.assertEqual([r['season'] for r in train],[2016,2018])
  self.assertEqual([r['season'] for r in test],[2019])
  rows.append(dict(game_id='2016',season=2019))
  with self.assertRaises(ValueError):chronological_split(rows,2019)
 def test_no_edge_from_mean_only_or_missing_forward_proof(self):
  self.assertFalse(advantage_gate(.001,.001,[-.001,.003],True))
  self.assertFalse(advantage_gate(.001,.001,[.0001,.003],False))
  self.assertFalse(advantage_gate(-.001,.001,[.0001,.003],True))
  self.assertTrue(advantage_gate(.001,.001,[.0001,.003],True))
if __name__=='__main__':unittest.main()
