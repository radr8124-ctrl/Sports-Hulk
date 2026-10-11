import unittest
from audit_prediction_execution_evidence import book_summary, fee_summary

class EvidenceTests(unittest.TestCase):
    def test_unsorted_bid_book_complements_and_zero_size(self):
        data={'orderbook_fp':{'yes_dollars':[['0.2','10'],['0.7','0'],['0.4','8']], 'no_dollars':[['0.3','4'],['0.5','12']]}}
        result=book_summary(data)
        self.assertEqual(result['yes_bid'],0.4)
        self.assertEqual(result['yes_ask'],0.5)
        self.assertEqual(result['ask_contracts'],12)
        self.assertFalse(result['execution_verified'])
    def test_bad_empty_and_crossed_books_not_promoted(self):
        for value in [{}, {'orderbook_fp':{'yes_dollars':[['NaN','2']], 'no_dollars':[]}}, {'orderbook_fp':{'yes_dollars':[['0.8','2']], 'no_dollars':[['0.7','2']]}}]:
            self.assertFalse(book_summary(value)['usable_observed_spread'])
    def test_fee_provenance_requires_complete_matching_response(self):
        base={'ticker':'KXNFLGAME','fee_type':'quadratic_with_maker_fees','fee_multiplier':1}
        for changes,complete in [([],False),([{'event_ticker':'OTHER'}],True)]:
            self.assertFalse(fee_summary(base,changes,'EVENT',complete)['metadata_complete'])
        result=fee_summary(base,[],'EVENT',True)
        self.assertTrue(result['metadata_complete'])
        self.assertFalse(result['execution_fees_verified'])
if __name__=='__main__':unittest.main()
