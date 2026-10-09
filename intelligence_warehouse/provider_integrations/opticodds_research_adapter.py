"""OpticOdds v3 candidate quote provenance. Offline, read-only; never places bets.

This is a verification boundary, NOT a live connected OpticOdds feed.
The caller supplies an independently approved fixture/player crosswalk
and the original as-observed capture time. No implicit team/player matching,
kickoff repair, PrizePicks payouts or goalie-starter inference.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone


class SourceReview(ValueError):
    """Quote is not eligible for exact-time, exact-identity research support."""


def timestamp(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            raise SourceReview("BAD_TIMESTAMP")
        return datetime.fromtimestamp(float(value), timezone.utc)
    if not isinstance(value, str) or not value.strip():
        raise SourceReview("MISSING_TIMESTAMP")
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceReview("BAD_TIMESTAMP") from exc
    if dt.tzinfo is None:
        raise SourceReview("NAIVE_TIMESTAMP")
    return dt.astimezone(timezone.utc)


def need(value, label):
    text = str(value or "").strip()
    if not text:
        raise SourceReview(f"MISSING_{label}")
    return text


def one_competitor(fixture, label):
    values = fixture.get(label)
    if not isinstance(values, list) or len(values) != 1:
        raise SourceReview(f"BAD_{label}")
    row = values[0]
    if not isinstance(row, dict):
        raise SourceReview(f"BAD_{label}")
    return need(row.get("id"), label.upper() + "_ID")


def confirm_quote(fixture, quote, anchor, captured_at, max_quote_age_seconds=300):
    """Verify a prospective odds quote against an *independent* original anchor.

    Required anchor: league_id, provider_fixture_id, home_provider_team_id,
    away_provider_team_id, scheduled_start, market_id, and either
    selection_provider_team_id (moneyline) or provider_player_id, side, line
    (player prop). All provider IDs need verified crosswalks upstream.
    """
    if not all(isinstance(x, dict) for x in (fixture, quote, anchor)):
        raise SourceReview("BAD_RECORD")
    if need(fixture.get("id"), "FIXTURE_ID") != need(anchor.get("provider_fixture_id"), "CROSSWALK_ID"):
        raise SourceReview("FIXTURE_IDENTITY_MISMATCH")
    lg = fixture.get("league")
    league = lg.get("id") if isinstance(lg, dict) else None
    if need(league, "LEAGUE").lower() != need(anchor.get("league_id"), "ANCHOR_LEAGUE").lower():
        raise SourceReview("LEAGUE_MISMATCH")
    if one_competitor(fixture, "home_competitors") != need(anchor.get("home_provider_team_id"), "HOME_ID"):
        raise SourceReview("HOME_IDENTITY_MISMATCH")
    if one_competitor(fixture, "away_competitors") != need(anchor.get("away_provider_team_id"), "AWAY_ID"):
        raise SourceReview("AWAY_IDENTITY_MISMATCH")
    if fixture.get("status") != "unplayed" or fixture.get("is_live") is True:
        raise SourceReview("GAME_ALREADY_STARTED_OR_UNVERIFIED")
    if quote.get("is_locked") is True or quote.get("is_suspended") is True or quote.get("is_live") is True:
        raise SourceReview("LOCKED_OR_LIVE_QUOTE")
    official_start = timestamp(anchor.get("scheduled_start"))
    provider_start = timestamp(fixture.get("start_date"))
    if abs((official_start - provider_start).total_seconds()) > 180:
        raise SourceReview("SOURCE_KICKOFF_MISMATCH")
    observed = timestamp(captured_at)
    last_quote = timestamp(quote.get("timestamp"))
    if not (last_quote <= observed < official_start):
        raise SourceReview("QUOTE_OUTSIDE_PREGAME_ASOF")
    if (observed - last_quote).total_seconds() > max_quote_age_seconds:
        raise SourceReview("STALE_QUOTE")
    if need(quote.get("market_id"), "MARKET") != need(anchor.get("market_id"), "ANCHOR_MARKET"):
        raise SourceReview("MARKET_MISMATCH")
    price = quote.get("price")
    if isinstance(price, bool) or not isinstance(price, (int, float)):
        raise SourceReview("INVALID_PRICE")
    if not math.isfinite(price) or price == 0 or abs(price) < 100 or abs(price) > 10000:
        raise SourceReview("INVALID_PRICE")
    if not need(quote.get("sportsbook"), "SPORTSBOOK"):
        raise SourceReview("MISSING_SPORTSBOOK")
    # A game-moneyline selection needs an exact provider team ID.
    if anchor.get("selection_provider_team_id"):
        selected = need(anchor["selection_provider_team_id"], "SELECTION_TEAM_ID")
        if selected not in {need(anchor["home_provider_team_id"], "HOME_ID"),
                            need(anchor["away_provider_team_id"], "AWAY_ID")}:
            raise SourceReview("INVALID_ANCHOR_SELECTION")
        if quote.get("team_id") != selected or quote.get("player_id"):
            raise SourceReview("MONEYLINE_SELECTION_IDENTITY_MISMATCH")
    # Player props require original provider player identity, side and line.
    elif anchor.get("provider_player_id"):
        if need(quote.get("player_id"), "QUOTE_PLAYER_ID") != need(anchor["provider_player_id"], "PLAYER_ID"):
            raise SourceReview("PLAYER_IDENTITY_MISMATCH")
        if str(quote.get("selection_line") or "").lower() != need(anchor.get("side"), "SIDE").lower():
            raise SourceReview("PROP_SIDE_MISMATCH")
        try:
            orig_line = float(anchor["line"])
            quote_line = float(quote["points"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SourceReview("PROP_LINE_UNVERIFIED") from exc
        if not math.isfinite(orig_line) or quote_line != orig_line:
            raise SourceReview("PROP_LINE_MISMATCH")
    else:
        raise SourceReview("UNVERIFIED_SELECTION_IDENTITY")
    raw_hash = hashlib.sha256(json.dumps(
        {"fixture": fixture, "quote": quote, "anchor": anchor, "captured_at": captured_at},
        sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "status": "VERIFIED_SOURCE_RESEARCH_ONLY",
        "provider": "opticodds_candidate",
        "fixture_id": fixture["id"],
        "source_odds_id": need(quote.get("id"), "QUOTE_ID"),
        "sport_league": str(league),
        "book": quote["sportsbook"],
        "market_id": quote["market_id"],
        "american_price": float(price),
        "event_start": official_start.isoformat(),
        "quote_captured_at": last_quote.isoformat(),
        "observed_at": observed.isoformat(),
        "source_hash": raw_hash,
        "automatic_bet_allowed": False,
        "prizepicks_payout_verified": False,
        "goalie_starter_confirmed": False,
    }
