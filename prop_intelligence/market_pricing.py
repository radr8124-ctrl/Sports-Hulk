"""Sports HULK prop-market pricing utilities.

This module deliberately separates three jobs:

1. Market belief: remove vig *inside each sportsbook's own two-sided market*.
2. Consensus: aggregate the per-book fair probabilities for the identical prop line.
3. Execution: keep the best actually available price separate from consensus belief.

Never pair an OVER price from one book with an UNDER price from another book.
Never treat a prop line (for example -3.5) as American odds.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from statistics import median
from typing import Any, Iterable
import math


MIN_AMERICAN_ODDS = 100.0
DEFAULT_MAX_QUOTE_AGE_SECONDS = 300
MIN_REASONABLE_OVERROUND = 0.98
MAX_REASONABLE_OVERROUND = 1.15


def _number(value: Any) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(value) else value


def valid_american_odds(value: Any) -> bool:
    odds = _number(value)
    return odds is not None and abs(odds) >= MIN_AMERICAN_ODDS


def american_to_decimal(value: Any) -> float | None:
    odds = _number(value)
    if odds is None or abs(odds) < MIN_AMERICAN_ODDS:
        return None
    return 1.0 + (odds / 100.0 if odds > 0 else 100.0 / abs(odds))


def american_to_implied(value: Any) -> float | None:
    decimal = american_to_decimal(value)
    return None if decimal is None else 1.0 / decimal


def expected_value(model_probability: float, american_odds: Any) -> float | None:
    """Expected profit per $1 staked at the executable price."""
    decimal = american_to_decimal(american_odds)
    p = _number(model_probability)
    if decimal is None or p is None or not 0.0 <= p <= 1.0:
        return None
    return p * decimal - 1.0


def proportional_no_vig(over_odds: Any, under_odds: Any) -> dict[str, float] | None:
    """Remove vig from one sportsbook's exact two-sided market."""
    over_raw = american_to_implied(over_odds)
    under_raw = american_to_implied(under_odds)
    if over_raw is None or under_raw is None:
        return None

    overround = over_raw + under_raw
    if not MIN_REASONABLE_OVERROUND <= overround <= MAX_REASONABLE_OVERROUND:
        return None

    return {
        "over_raw_probability": over_raw,
        "under_raw_probability": under_raw,
        "overround": overround,
        "hold": overround - 1.0,
        "over_fair_probability": over_raw / overround,
        "under_fair_probability": under_raw / overround,
    }


def _parse_timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def quote_age_seconds(updated_at: Any, now: datetime | None = None) -> float | None:
    dt = _parse_timestamp(updated_at)
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return max(0.0, (now.astimezone(timezone.utc) - dt).total_seconds())


def _median_absolute_deviation(values: list[float]) -> float | None:
    if not values:
        return None
    center = median(values)
    return median(abs(value - center) for value in values)


@dataclass(frozen=True)
class BookFairQuote:
    bookmaker: str
    line: float
    over_price: float
    under_price: float
    over_fair_probability: float
    under_fair_probability: float
    overround: float
    hold: float
    updated_at: str | None
    age_seconds: float | None
    freshness: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def fair_quote_from_row(
    row: dict[str, Any],
    *,
    now: datetime | None = None,
    max_age_seconds: int = DEFAULT_MAX_QUOTE_AGE_SECONDS,
) -> tuple[BookFairQuote | None, str | None]:
    """Validate and de-vig one same-book OVER/UNDER quote."""
    bookmaker = str(row.get("bookmaker") or row.get("book") or "").strip()
    line = _number(row.get("line"))
    over_price = _number(row.get("over_price"))
    under_price = _number(row.get("under_price"))

    if not bookmaker:
        return None, "MISSING_BOOKMAKER"
    if line is None:
        return None, "BAD_LINE"
    if not valid_american_odds(over_price) or not valid_american_odds(under_price):
        return None, "INVALID_TWO_SIDED_PRICE"

    no_vig = proportional_no_vig(over_price, under_price)
    if no_vig is None:
        return None, "SUSPICIOUS_OVERROUND"

    age = quote_age_seconds(row.get("updated_at"), now=now)
    if age is None:
        freshness = "UNKNOWN"
    elif age <= max_age_seconds:
        freshness = "FRESH"
    else:
        freshness = "STALE"

    return BookFairQuote(
        bookmaker=bookmaker,
        line=line,
        over_price=float(over_price),
        under_price=float(under_price),
        over_fair_probability=no_vig["over_fair_probability"],
        under_fair_probability=no_vig["under_fair_probability"],
        overround=no_vig["overround"],
        hold=no_vig["hold"],
        updated_at=None if row.get("updated_at") in (None, "") else str(row.get("updated_at")),
        age_seconds=age,
        freshness=freshness,
    ), None


def _best_price(quotes: Iterable[BookFairQuote], side: str) -> tuple[float | None, str | None]:
    price_field = "over_price" if side == "OVER" else "under_price"
    best: tuple[float, str, float] | None = None
    for quote in quotes:
        price = getattr(quote, price_field)
        decimal = american_to_decimal(price)
        if decimal is None:
            continue
        candidate = (decimal, quote.bookmaker, price)
        if best is None or candidate[0] > best[0]:
            best = candidate
    return (None, None) if best is None else (best[2], best[1])


def consensus_for_exact_line(
    rows: Iterable[dict[str, Any]],
    *,
    target_line: float | None = None,
    now: datetime | None = None,
    max_age_seconds: int = DEFAULT_MAX_QUOTE_AGE_SECONDS,
    allow_unknown_freshness: bool = True,
) -> dict[str, Any]:
    """Build consensus from per-book no-vig probabilities for one exact prop line.

    The function never mixes different lines. If target_line is omitted, it uses
    the modal valid line and reports how many other-line quotes were excluded.
    """
    rows = list(rows)
    valid: list[BookFairQuote] = []
    rejected: list[dict[str, Any]] = []

    for row in rows:
        quote, reason = fair_quote_from_row(
            row, now=now, max_age_seconds=max_age_seconds
        )
        if quote is None:
            rejected.append({
                "bookmaker": row.get("bookmaker") or row.get("book"),
                "line": row.get("line"),
                "reason": reason,
            })
            continue
        valid.append(quote)

    if not valid:
        return {
            "status": "NO_VALID_TWO_SIDED_MARKET",
            "paired_book_count": 0,
            "rejected": rejected,
        }

    if target_line is None:
        line_counts: dict[float, int] = {}
        for quote in valid:
            line_counts[quote.line] = line_counts.get(quote.line, 0) + 1
        target_line = max(line_counts, key=lambda line: (line_counts[line], -abs(line)))

    exact = [quote for quote in valid if quote.line == float(target_line)]
    line_mismatch_count = len(valid) - len(exact)

    usable = [
        quote for quote in exact
        if quote.freshness == "FRESH"
        or (allow_unknown_freshness and quote.freshness == "UNKNOWN")
    ]
    stale_count = sum(quote.freshness == "STALE" for quote in exact)
    unknown_count = sum(quote.freshness == "UNKNOWN" for quote in exact)

    if not usable:
        return {
            "status": "NO_FRESH_TWO_SIDED_MARKET",
            "target_line": float(target_line),
            "paired_book_count": len(exact),
            "stale_count": stale_count,
            "unknown_freshness_count": unknown_count,
            "line_mismatch_count": line_mismatch_count,
            "rejected": rejected,
        }

    over_probs = [quote.over_fair_probability for quote in usable]
    under_probs = [quote.under_fair_probability for quote in usable]
    holds = [quote.hold for quote in usable]
    fresh_count = sum(quote.freshness == "FRESH" for quote in usable)

    over_consensus = float(median(over_probs))
    under_consensus = 1.0 - over_consensus
    dispersion = _median_absolute_deviation(over_probs)
    best_over_price, best_over_book = _best_price(usable, "OVER")
    best_under_price, best_under_book = _best_price(usable, "UNDER")

    count = len(usable)
    fresh_ratio = fresh_count / count if count else 0.0
    dispersion = 0.0 if dispersion is None else float(dispersion)

    if count >= 5 and fresh_ratio >= 0.80 and dispersion <= 0.025:
        quality = "A"
    elif count >= 3 and fresh_ratio >= 0.50 and dispersion <= 0.04:
        quality = "B"
    elif count >= 2 and dispersion <= 0.06:
        quality = "C"
    else:
        quality = "D"

    warnings: list[str] = []
    if line_mismatch_count:
        warnings.append("CONFLICTING_LINES_EXCLUDED")
    if stale_count:
        warnings.append("STALE_QUOTES_EXCLUDED")
    if unknown_count:
        warnings.append("UNKNOWN_QUOTE_FRESHNESS")
    if count < 3:
        warnings.append("LOW_PAIRED_BOOK_COUNT")
    if dispersion > 0.04:
        warnings.append("HIGH_BOOK_DISAGREEMENT")

    return {
        "status": "READY",
        "target_line": float(target_line),
        "paired_book_count": count,
        "fresh_book_count": fresh_count,
        "stale_count": stale_count,
        "unknown_freshness_count": unknown_count,
        "line_mismatch_count": line_mismatch_count,
        "over_fair_probability": over_consensus,
        "under_fair_probability": under_consensus,
        "over_fair_probability_mad": dispersion,
        "median_hold": float(median(holds)),
        "best_over_price": best_over_price,
        "best_over_book": best_over_book,
        "best_under_price": best_under_price,
        "best_under_book": best_under_book,
        "data_quality_grade": quality,
        "warnings": warnings,
        "books": [quote.to_dict() for quote in usable],
        "rejected": rejected,
    }


def side_market_probability(consensus: dict[str, Any], side: str) -> float | None:
    side = str(side or "").upper()
    if consensus.get("status") != "READY":
        return None
    if side == "OVER":
        return _number(consensus.get("over_fair_probability"))
    if side == "UNDER":
        return _number(consensus.get("under_fair_probability"))
    return None


def side_best_price(consensus: dict[str, Any], side: str) -> float | None:
    side = str(side or "").upper()
    if side == "OVER":
        return _number(consensus.get("best_over_price"))
    if side == "UNDER":
        return _number(consensus.get("best_under_price"))
    return None
