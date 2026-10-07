import unittest

from intelligence_warehouse.betting_v2.competition_regime import (
    normalize_competition_regime,
    proof_lane_key,
    proof_version,
    regime_enforced,
)


class CompetitionRegimeTests(unittest.TestCase):
    def test_numeric_and_string_preseason_variants_normalize(self):
        for value in (1, 1.0, "1", "1.0", "preseason", "pre-season"):
            with self.subTest(value=value):
                self.assertEqual(
                    normalize_competition_regime(value, "NBA"),
                    "PRESEASON",
                )

    def test_numeric_and_string_regular_variants_normalize(self):
        for value in (2, 2.0, "2", "2.0", "regular", "regular season"):
            with self.subTest(value=value):
                self.assertEqual(
                    normalize_competition_regime(value, "NBA"),
                    "REGULAR",
                )

    def test_numeric_and_string_postseason_variants_normalize(self):
        for value in (
            3,
            3.0,
            "3",
            "3.0",
            "postseason",
            "post-season",
            "playoff",
            "playoffs",
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    normalize_competition_regime(value, "NBA"),
                    "POSTSEASON",
                )

    def test_missing_date_week_and_unrecognized_values_stay_unknown(self):
        for value in (None, "", "2026-10-07", "Week 5", 4, "summer league"):
            with self.subTest(value=value):
                self.assertEqual(
                    normalize_competition_regime(value, "NBA"),
                    "UNKNOWN",
                )

    def test_nba_proof_lane_key_is_regime_specific(self):
        self.assertTrue(regime_enforced("NBA"))
        self.assertEqual(
            proof_lane_key("NBA", "TOTAL", "PRESEASON"),
            "NBA_TOTAL|PRESEASON",
        )
        self.assertEqual(
            proof_lane_key("NBA", "TOTAL", "REGULAR"),
            "NBA_TOTAL|REGULAR",
        )

    def test_cfb_proof_lane_key_remains_backward_compatible(self):
        self.assertFalse(regime_enforced("CFB"))
        self.assertEqual(
            proof_lane_key("CFB", "TOTAL", "REGULAR"),
            "CFB_TOTAL",
        )

    def test_nba_proof_version_is_regime_specific_but_cfb_is_legacy(self):
        model_version = "BETTING_V2_ALL_MARKETS_2026_10_05"
        preseason = proof_version(model_version, "NBA", "PRESEASON")
        regular = proof_version(model_version, "NBA", "REGULAR")

        self.assertNotEqual(preseason, regular)
        self.assertNotEqual(preseason, model_version)
        self.assertNotEqual(regular, model_version)
        self.assertEqual(
            proof_version(model_version, "CFB", "REGULAR"),
            model_version,
        )


if __name__ == "__main__":
    unittest.main()
