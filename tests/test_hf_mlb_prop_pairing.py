"""Historical de-vig data requires exact same event, book, line, and timestamp."""
import unittest
from intelligence_warehouse.betting_v2.hf_mlb_prop_pairing import evaluate_exact_quote_pair


def sample():
    return dict(status='VERIFIED_HISTORICAL',game_id='m~d83f4183',player='riley greene',
                market='player hits',side='under',line=0.5,book='fanatics',
                ts='2026-03-27T02:19:00',official_start='2026-03-28T01:40:00+00:00',
                odds=2.3)


def offers():
    return [dict(game_id='m~d83f4183',player='riley greene',market='player hits',
                line=0.5,book='fanatics',ts='2026-03-27T02:19:00',side=s,odds=o)
            for s,o in [('under',2.3),('over',1.588235294)]]


class ExactOddsPairingTests(unittest.TestCase):
    def test_valid_same_minute_same_book_pair_produces_fair_probability(self):
        r=evaluate_exact_quote_pair(sample(),offers())
        self.assertEqual(r['status'],'VERIFIED_SAME_BOOK_TIME_PAIR')
        self.assertAlmostEqual(r['fair_probability'],0.408472,places=5)
        self.assertAlmostEqual(r['overround'],0.064412,places=5)
        self.assertEqual(r['opposite_decimal_odds'],1.588235294)

    def test_different_book_market_timestamp_or_line_never_combined(self):
        for key,value in [('book','other'),('market','player rbis'),('ts','2026-03-27T02:20:00'),('line',1.5),('game_id','another')]:
            with self.subTest(key=key):
                bad=offers()
                bad[1]={**bad[1],key:value}
                self.assertEqual(evaluate_exact_quote_pair(sample(),bad)['status'],'NO_EXACT_OPPOSITE_SIDE')

    def test_only_same_side_cannot_qualify_a_fair_market_price(self):
        self.assertEqual(evaluate_exact_quote_pair(sample(),offers()[:1])['status'],'NO_EXACT_OPPOSITE_SIDE')

    def test_conflicting_odds_and_wrong_original_price_rejected(self):
        bad=offers()+[{**offers()[0],'odds':2.7}]
        self.assertEqual(evaluate_exact_quote_pair(sample(),bad)['status'],'CONFLICTING_SAME_SIDE_PRICE')
        self.assertEqual(evaluate_exact_quote_pair({**sample(),'odds':2.4},offers())['status'],'ORIGINAL_PRICE_NOT_REPRODUCED')

    def test_official_analytic_grade_can_pair_price_without_claiming_vendor_settlement(self):
        source={**sample(),'status':'OFFICIAL_DERIVED_HISTORICAL','platform_settlement_claim':False}
        paired=evaluate_exact_quote_pair(source,offers())
        self.assertEqual(paired['status'],'VERIFIED_SAME_BOOK_TIME_PAIR')
        self.assertTrue(paired['research_only'])

    def test_nonverified_and_poststart_quote_never_de_vigged(self):
        self.assertEqual(evaluate_exact_quote_pair({**sample(),'status':'RESULT_DISAGREES_WITH_OFFICIAL'},offers())['status'],'SOURCE_NOT_VERIFIED')
        r=evaluate_exact_quote_pair({**sample(),'ts':'2026-03-28T01:40:00'},offers())
        self.assertEqual(r['status'],'QUOTE_NOT_PREGAME')


if __name__=='__main__':unittest.main()
