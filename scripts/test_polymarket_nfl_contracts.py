import unittest
from copy import deepcopy
from audit_polymarket_nfl_contracts import audit

class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.game = dict(event_id='1', sport='NFL', away='Philadelphia Eagles', home='Jacksonville Jaguars', away_abbr='PHI', home_abbr='JAC', start_time='2026-10-11T13:30Z')
        self.market = dict(id='m1', sportsMarketType='moneyline', gameStartTime='2026-10-11 13:30:00+00', active=True, closed=False, outcomes='["Eagles","Jaguars"]', clobTokenIds='["1","2"]', outcomePrices='["0.4","0.6"]', description='Tie resolves 50-50.')
        self.event = dict(slug='nfl-phi-jax-2026-10-11', markets=[self.market])
    def test_exact_alias_and_outcome_mapping(self):
        rows, rejected = audit([self.event], [self.game, deepcopy(self.game)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['outcome_teams'], [self.game['away'], self.game['home']])
        self.assertFalse(rows[0]['approved_pick'])
        self.assertEqual(rejected, [])
    def test_wrong_date_time_order_and_type_are_rejected(self):
        for field, value in [('slug','nfl-phi-jax-2026-10-12'), ('slug','nfl-jax-phi-2026-10-11'), ('gameStartTime','2026-10-11T17:00Z'), ('sportsMarketType','spread'), ('closed',True)]:
            with self.subTest(field=field):
                event = deepcopy(self.event)
                (event if field == 'slug' else event['markets'][0])[field] = value
                self.assertEqual(audit([event], [self.game])[0], [])
    def test_unknown_outcomes_duplicate_tokens_and_ambiguous_games_rejected(self):
        for field, value in [('outcomes','["Eagles","Bears"]'), ('clobTokenIds','["1","1"]')]:
            event = deepcopy(self.event); event['markets'][0][field] = value
            self.assertEqual(audit([event], [self.game])[0], [])
        other = dict(self.game, event_id='2')
        self.assertEqual(audit([self.event], [self.game, other])[0], [])

if __name__ == '__main__': unittest.main()
