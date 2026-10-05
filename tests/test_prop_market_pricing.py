from datetime import datetime, timedelta, timezone

from prop_intelligence.market_pricing import (
    american_to_implied,
    consensus_for_exact_line,
    expected_value,
    proportional_no_vig,
    valid_american_odds,
)


NOW = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)


def quote(book, line, over, under, age_seconds=30):
    return {
        "bookmaker": book,
        "line": line,
        "over_price": over,
        "under_price": under,
        "updated_at": (NOW - timedelta(seconds=age_seconds)).isoformat(),
    }


def test_prop_line_is_never_american_odds():
    assert not valid_american_odds(-3.5)
    assert american_to_implied(-3.5) is None
    assert expected_value(0.60, -3.5) is None


def test_same_book_no_vig_normalizes_to_one():
    fair = proportional_no_vig(-115, -105)
    assert fair is not None
    assert abs(
        fair["over_fair_probability"] + fair["under_fair_probability"] - 1.0
    ) < 1e-12
    assert fair["overround"] > 1.0


def test_consensus_uses_per_book_fair_probabilities_not_median_prices():
    rows = [
        quote("Book A", 5.5, -130, +105),
        quote("Book B", 5.5, -105, -115),
        quote("Book C", 5.5, -120, +100),
    ]
    result = consensus_for_exact_line(rows, target_line=5.5, now=NOW)
    assert result["status"] == "READY"
    assert result["paired_book_count"] == 3

    expected = []
    for row in rows:
        fair = proportional_no_vig(row["over_price"], row["under_price"])
        expected.append(fair["over_fair_probability"])

    assert result["over_fair_probability"] == sorted(expected)[1]
    assert result["best_over_book"] == "Book B"
    assert result["best_over_price"] == -105
    assert result["best_under_book"] == "Book C"
    assert result["best_under_price"] == 100


def test_mismatched_lines_are_excluded_not_blended():
    rows = [
        quote("Book A", 5.5, -110, -110),
        quote("Book B", 5.5, -115, -105),
        quote("Book C", 6.5, +105, -125),
    ]
    result = consensus_for_exact_line(rows, target_line=5.5, now=NOW)
    assert result["status"] == "READY"
    assert result["paired_book_count"] == 2
    assert result["line_mismatch_count"] == 1
    assert "CONFLICTING_LINES_EXCLUDED" in result["warnings"]


def test_stale_quotes_do_not_drive_consensus():
    rows = [
        quote("Fresh A", 2.5, -115, -105, age_seconds=60),
        quote("Fresh B", 2.5, -110, -110, age_seconds=90),
        quote("Stale C", 2.5, +160, -210, age_seconds=900),
    ]
    result = consensus_for_exact_line(
        rows, target_line=2.5, now=NOW, max_age_seconds=300
    )
    assert result["status"] == "READY"
    assert result["paired_book_count"] == 2
    assert result["stale_count"] == 1
    assert "STALE_QUOTES_EXCLUDED" in result["warnings"]


def test_suspicious_or_invalid_two_sided_market_is_rejected():
    rows = [
        quote("Broken", 4.5, -3.5, -110),
    ]
    result = consensus_for_exact_line(rows, target_line=4.5, now=NOW)
    assert result["status"] == "NO_VALID_TWO_SIDED_MARKET"
    assert result["paired_book_count"] == 0


def test_expected_value_uses_executable_price_not_probability_edge():
    # -110 is decimal 1.90909; at 55% model probability EV is +5%.
    ev = expected_value(0.55, -110)
    assert ev is not None
    assert abs(ev - 0.05) < 1e-9
