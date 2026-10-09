"""Research archive integration cannot count a grade without exact source odds."""
import unittest
import pandas as pd
from intelligence_warehouse.betting_v2.hf_mlb_prop_expanded_analysis import analyze_expanded_samples


def history():
    rows=[]
    for i in range(7):
        day=f'2026-05-{i+1:02d}'
        rows.append(dict(game_pk=100+i,player='Eugenio Suárez',player_id=1,game_date=f'{day}T22:00:00Z',official_date=day,
          game_type='R',status='Final',group='HITTING',team='Arizona Diamondbacks',opponent='San Francisco Giants',
          hits=float(i%2),total_bases=float(i%3),rbi=0.,home_runs=0.,walks=0.,strikeouts=0.,plate_appearances=4.,outs=None))
    rows.append(dict(game_pk=500,player='Eugenio Suárez',player_id=1,game_date='2026-05-08T22:00:00Z',official_date='2026-05-08',
          game_type='R',status='Final',group='HITTING',team='Arizona Diamondbacks',opponent='San Francisco Giants',
          hits=2.,total_bases=3.,rbi=0.,home_runs=0.,walks=0.,strikeouts=0.,plate_appearances=4.,outs=None))
    return pd.DataFrame(rows)


def offer(*,book='fanduel'):
    row=dict(sample_index=0,pair_status='PAIRED_AT_SAME_BOOK_AND_TIME',game_id='m~q',start_time='2026-05-08T22:01:00',
        player='eugenio suarez',market='player hits',line=1.5,side='over',book=book,ts='2026-05-08T16:00:00',
        odds=1.8,result=2.,won=True)
    row['paired_offers']=[{k:row[k] for k in ('game_id','player','market','line','book','ts')}|{'side':s,'odds':o} for s,o in [('over',1.8),('under',2.1)]]
    return row


class ExpandedHistoricalAuditTests(unittest.TestCase):
    def test_valid_pair_audit_and_strict_prior_games_become_research_not_forward_history(self):
        result=analyze_expanded_samples([offer()],history())
        self.assertEqual(result['summary']['verified_grade_and_pair_games'],1)
        self.assertEqual(result['summary']['asof_feature_games'],1)
        row=result['asof'][0]
        self.assertEqual(row['status'],'VERIFIED_HISTORICAL')
        self.assertEqual(row['pair_status'],'VERIFIED_SAME_BOOK_TIME_PAIR')
        self.assertGreater(row['market_fair_probability'],0)
        self.assertEqual(row['prior_latest_date'],'2026-05-07')
        self.assertNotIn('shadow_decision',row)
        self.assertEqual(result['fair_lane']['player hits']['live_play_approved'],False)

    def test_missing_opposite_side_cannot_count_as_fair_market(self):
        src=offer();src['paired_offers']=src['paired_offers'][:1]
        result=analyze_expanded_samples([src],history())
        self.assertEqual(result['summary']['verified_official_game_count'],1)
        self.assertEqual(result['summary']['verified_grade_and_pair_games'],0)
        self.assertEqual(result['asof'][0]['pair_status'],'NO_EXACT_OPPOSITE_SIDE')

    def test_opt_in_official_analytic_outcome_is_separate_from_absent_vendor_grade(self):
        source=offer();source['won']=None;source['result']=None
        result=analyze_expanded_samples([source],history(),allow_official_derivation=True,run_model_comparisons=False)
        self.assertEqual(result['audit'][0]['status'],'OFFICIAL_DERIVED_HISTORICAL')
        self.assertEqual(result['audit'][0]['pair_status'],'VERIFIED_SAME_BOOK_TIME_PAIR')
        self.assertEqual(result['asof'][0]['asof_status'],'PREGAME_FEATURE_VERIFIED')
        self.assertFalse(result['audit'][0]['platform_settlement_claim'])

    def test_holdout_audit_can_skip_all_model_refits(self):
        result=analyze_expanded_samples([offer()],history(),run_model_comparisons=False)
        self.assertEqual(result['fair_lane'],{})
        self.assertEqual(result['summary']['asof_feature_games'],1)

    def test_conflicting_official_stat_rejected(self):
        src=offer();src['result']=0.;src['won']=False
        result=analyze_expanded_samples([src],history())
        self.assertEqual(result['summary']['verified_grade_and_pair_games'],0)
        self.assertEqual(result['audit'][0]['status'],'RESULT_DISAGREES_WITH_OFFICIAL')


if __name__=='__main__':unittest.main()
