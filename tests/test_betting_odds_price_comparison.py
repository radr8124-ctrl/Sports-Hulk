"""Odds-first betting board uses actual same-game, same-book, same-line pairs."""
import unittest
from datetime import datetime,timedelta,timezone

from intelligence_warehouse.betting_v2 import build_betting_odds_board as b

CLOCK=datetime(2026,10,9,22,0,tzinfo=timezone.utc)
GAME=CLOCK+timedelta(hours=34)
OBS=CLOCK-timedelta(minutes=2)


def bookmaker(book='fanduel',side='AWAY',odds='-110',market='MONEYLINE',
              line='',subtype=None,start=None,updated=None,event='uuid-1'):
    return {
        'provider':'sportwizzard','sportsbook':book,'event_id':event,
        'start':(start or GAME).isoformat(),'away_team':'Texas Longhorns',
        'home_team':'Oklahoma Sooners','market':market,
        'market_subtype':subtype or {'MONEYLINE':'MONEYLINE','SPREAD':'SPREAD','TOTAL':'TOTAL_POINTS'}[market],
        'selection':'Texas' if side=='AWAY' else 'Oklahoma','side':side,'line':line,
        'price_american':odds,'captured_at':(updated or OBS).isoformat(),
    }


def pair(book='fanduel',away='-110',home='-110',market='MONEYLINE',
         awayline='',homeline=''):
    return [bookmaker(book,'AWAY' if market!='TOTAL' else 'OVER',away,market,awayline),
            bookmaker(book,'HOME' if market!='TOTAL' else 'UNDER',home,market,homeline)]


def normalized(rows):
    return [b.canonical_source(r,'CFB',CLOCK) for r in rows if b.canonical_source(r,'CFB',CLOCK)]


class OddsBoardTruthTests(unittest.TestCase):
    def test_two_sided_same_book_winner_odds_and_comparison(self):
        raw=pair('fanduel','-120','+105')+pair('draftkings','-115','+102')+pair('caesars','-130','+113')
        event=b.build_event(normalized(raw),CLOCK)
        self.assertIsNotNone(event)
        ml=event['markets']['MONEYLINE']
        away=ml['sides']['AWAY']
        home=ml['sides']['HOME']
        self.assertEqual(away['best_american_odds'],-115)
        self.assertEqual(away['best_sportsbook'],'draftkings')
        self.assertEqual(home['best_american_odds'],113)
        self.assertEqual(home['best_sportsbook'],'caesars')
        self.assertEqual(ml['paired_book_count'],3)
        self.assertFalse(away['proven_positive_expected_value'])
        self.assertFalse(home['book_accessibility_or_executability_verified'])
        self.assertIsNone(home['independent_zenith_model_probability_pct'])

    def test_no_two_sided_book_cannot_create_price_market(self):
        raw=[bookmaker('fanduel','AWAY','-120'),bookmaker('draftkings','HOME','+104')]
        self.assertIsNone(b.build_event(normalized(raw),CLOCK))

    def test_book_opposing_prices_need_same_original_source_start_time(self):
        raw=pair('fanduel','-120','+105')+pair('draftkings','-115','+102')
        raw[1]['start']=(GAME+timedelta(minutes=8)).isoformat()
        self.assertIsNone(b.build_event(normalized(raw),CLOCK))

    def test_spread_opposing_sign_and_line_required(self):
        raw=pair('fanduel','-110','-110','SPREAD','-4.5','+4.5')+pair('draftkings','-105','-115','SPREAD','-4.5','+4.5')
        raw+=pair('caesars','-110','-110','SPREAD','-3.5','+3.5')
        result=b.build_event(normalized(raw),CLOCK)
        self.assertEqual(result['markets']['SPREAD']['line'],-4.5)
        self.assertEqual(result['markets']['SPREAD']['paired_book_count'],2)
        self.assertNotIn('MONEYLINE',result['markets'])
        unmatched=pair('fanduel','-110','-110','SPREAD','-4.5','-4.5')
        self.assertIsNone(b.build_event(normalized(unmatched),CLOCK))

    def test_total_subtype_mismatch_never_becomes_game_total(self):
        raw=pair('fanduel','-110','-110','TOTAL','42.5','42.5')+pair('draftkings','-115','-105','TOTAL','42.5','42.5')
        game=b.build_event(normalized(raw),CLOCK)
        self.assertEqual(game['markets']['TOTAL']['line'],42.5)
        for r in raw:r['market_subtype']='TOTAL_TOUCHDOWNS'
        self.assertEqual(normalized(raw),[])

    def test_duplicate_conflicting_book_cannot_be_cherrypicked(self):
        raw=pair('fanduel','-120','+105')+pair('draftkings','-115','+102')
        raw.append(dict(raw[0],price_american='-105'))
        self.assertIsNone(b.build_event(normalized(raw),CLOCK))
        raw+=pair('caesars','-123','+107')
        result=b.build_event(normalized(raw),CLOCK)
        self.assertIsNotNone(result)
        self.assertEqual(result['markets']['MONEYLINE']['paired_book_count'],2)
        self.assertNotEqual(result['markets']['MONEYLINE']['sides']['AWAY']['best_sportsbook'],'fanduel')

    def test_price_increase_reduces_breakeven_without_claiming_edge(self):
        quotes=b.paired_quotes(normalized(
            pair('fanduel','+110','-130')+
            pair('draftkings','+115','-135')+
            pair('caesars','+112','-132')
        ))
        option=b.research_side('MONEYLINE','AWAY',quotes[('MONEYLINE','')])
        self.assertEqual(option['best_american_odds'],115)
        self.assertGreater(option['price_improvement_pct_points'],0)
        self.assertFalse(option['proven_positive_expected_value'])
        self.assertTrue(0<option['market_consensus_no_vig_probability_pct']<100)

    def test_no_fake_prices_from_started_game_or_future_capture(self):
        a=bookmaker(start=CLOCK-timedelta(minutes=1))
        self.assertIsNone(b.canonical_source(a,'CFB',CLOCK))
        a=bookmaker(updated=CLOCK+timedelta(minutes=1))
        self.assertIsNone(b.canonical_source(a,'CFB',CLOCK))
        a=bookmaker(odds='-90')
        self.assertIsNone(b.canonical_source(a,'CFB',CLOCK))

    def test_clock_drift_under_15min_allowed_not_cross_event_starts(self):
        raw=pair('fanduel','-120','+105')+pair('draftkings','-115','+102')
        raw[2]['start']=(GAME+timedelta(minutes=10)).isoformat()
        raw[3]['start']=(GAME+timedelta(minutes=10)).isoformat()
        result=b.build_event(normalized(raw),CLOCK)
        self.assertIsNotNone(result)
        self.assertEqual(result['provider_source_clock_spread_minutes'],10)
        self.assertEqual(result['start'],GAME.isoformat())
        raw[2]['start']=(GAME+timedelta(hours=2)).isoformat()
        raw[3]['start']=(GAME+timedelta(hours=2)).isoformat()
        self.assertIsNone(b.build_event(normalized(raw),CLOCK))

    def test_no_price_promotion_from_unsupported_provider_or_book(self):
        bad=bookmaker(book='unknown_unlicensed_book')
        self.assertIsNone(b.canonical_source(bad,'CFB',CLOCK))
        bad=bookmaker(subtype='DRAW_NO_BET')
        self.assertIsNone(b.canonical_source(bad,'CFB',CLOCK))

    def test_stale_archived_source_stays_stale_research_not_live(self):
        rows=normalized(pair('fanduel','-120','+105')+pair('draftkings','-115','+102'))
        self.assertEqual(b.quality(rows,GAME,CLOCK),'RECENT_CAPTURE')
        later=CLOCK+timedelta(hours=26)
        # Advance the observation clock but not the sportsbook capture time.
        self.assertEqual(b.quality(rows,GAME,later),'STALE_RECHECK_REQUIRED')


if __name__=='__main__':
    unittest.main()
