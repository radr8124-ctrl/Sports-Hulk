"""The expanded external sample chooses odds without examining who won."""
import unittest
import pandas as pd
from intelligence_warehouse.betting_v2.hf_mlb_prop_expansion import (
    choose_exact_paired_quotes, record_fingerprint,
)


def record(*, side='over', odds=1.85, game_id='m~a', player='José Ramírez', market='player hits',
           book='fanatics', line=0.5, ts='2026-05-11T16:00:00',
           start='2026-05-11T22:00:00', won=True, result=1.0):
    return dict(game_id=game_id,start_time=start,player=player,market=market,
                line=line,side=side,book=book,ts=ts,odds=odds,won=won,result=result)


class SelectHistoricalQuoteTests(unittest.TestCase):
    def test_one_canonical_market_pair_has_two_exact_observed_sides(self):
        rows=[record(side='over',odds=1.85),record(side='under',odds=2.1,won=False)]
        picks=choose_exact_paired_quotes(pd.DataFrame(rows))
        self.assertEqual(len(picks),1)
        row=picks[0]
        self.assertEqual(row['game_id'],'m~a')
        self.assertEqual(set(x['side'] for x in row['paired_offers']),{'over','under'})
        self.assertEqual(row['pair_status'],'PAIRED_AT_SAME_BOOK_AND_TIME')
        self.assertGreaterEqual(row['lead_time_hours'],2)
        self.assertIn(row['odds'],[1.85,2.1])
        self.assertEqual(record_fingerprint(row),record_fingerprint(dict(row)))

    def test_selection_independent_of_outcome_or_price_favorite(self):
        pair=[record(side='over',odds=1.85,won=True,result=1),record(side='under',odds=2.1,won=False,result=1)]
        before=choose_exact_paired_quotes(pd.DataFrame(pair))[0]
        after=choose_exact_paired_quotes(pd.DataFrame([{**p,'won':not p['won'],'result':0} for p in pair]))[0]
        for key in ['game_id','player','market','line','side','book','ts','odds']:
            self.assertEqual(before[key],after[key])

    def test_unpaired_and_post_start_and_overround_out_of_range_rejected(self):
        a=record()
        self.assertEqual(choose_exact_paired_quotes(pd.DataFrame([a])),[])
        late=[record(ts='2026-05-11T21:00:00'),record(side='under',ts='2026-05-11T21:00:00',won=False)]
        self.assertEqual(choose_exact_paired_quotes(pd.DataFrame(late)),[])
        invalid=[record(odds=1.1),record(side='under',odds=1.1,won=False)]
        self.assertEqual(choose_exact_paired_quotes(pd.DataFrame(invalid)),[])

    def test_book_line_or_timestamp_cannot_be_cross_paired(self):
        a=record()
        for kwargs in [{'book':'other'},{'line':1.5},{'ts':'2026-05-11T15:59:00'},{'game_id':'m~b'}]:
            with self.subTest(kwargs=kwargs):
                opp=record(side='under',odds=2.1,won=False,**kwargs)
                self.assertEqual(choose_exact_paired_quotes(pd.DataFrame([a,opp])),[])

    def test_each_game_and_market_is_one_independent_candidate_even_across_books_and_minutes(self):
        pairs=[record(),record(side='under',odds=2.1,won=False)]
        pairs += [record(book='draftkings',ts='2026-05-11T17:00:00'),record(side='under',odds=2.1,book='draftkings',ts='2026-05-11T17:00:00',won=False)]
        pairs += [record(market='player bases'),record(side='under',market='player bases',odds=2.1,won=False)]
        pairs += [record(game_id='m~b'),record(side='under',game_id='m~b',odds=2.1,won=False)]
        picks=choose_exact_paired_quotes(pd.DataFrame(pairs))
        self.assertEqual(len(picks),3)
        self.assertEqual(len({(x['game_id'],x['market']) for x in picks}),3)

    def test_conflicting_prices_same_source_not_invented(self):
        a=record();opp=record(side='under',odds=2.1,won=False)
        conflicted=record(side='over',odds=1.75)
        self.assertEqual(choose_exact_paired_quotes(pd.DataFrame([a,opp,conflicted])),[])

    def test_same_side_missing_result_or_conflicting_grade_fails_closed(self):
        over=record();under=record(side='under',odds=2.1,won=False)
        self.assertEqual(choose_exact_paired_quotes(pd.DataFrame([
            over,under,record(won=None,result=None)])),[])
        self.assertEqual(choose_exact_paired_quotes(pd.DataFrame([
            over,under,record(won=False,result=0.0)])),[])

    def test_ineligible_market_is_excluded_even_with_valid_two_sided_prices(self):
        a=record(market='odd novelty category');b=record(side='under',odds=2.1,won=False,market='odd novelty category')
        self.assertEqual(choose_exact_paired_quotes(pd.DataFrame([a,b])),[])


if __name__=='__main__':unittest.main()
