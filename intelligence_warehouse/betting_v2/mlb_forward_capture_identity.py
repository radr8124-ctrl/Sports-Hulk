"""Freeze MLB player/game identity present in the original decision feed.

Capture-time numeric IDs are evidence, not proof that the player appeared
or that a wager was placed. Settlement still requires a unique official
gamePk, final box, exact player ID/team/name and original market/line.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
import unicodedata

IDENTITY_PROVENANCE = "MLB_DECISION_EXPLICIT_PLAYER_ID_TEAM"


def player_key(value):
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]", "", ascii_name)


def explicit_id(value):
    if value is None:
        return ""
    raw = str(value).strip()
    # Pandas CSV readers may represent all-numeric IDs as 700250.0.
    if re.fullmatch(r"[0-9]{4,12}(?:\.0)?", raw):
        return raw[:-2] if raw.endswith(".0") else raw
    return ""


def utc_start(value):
    try:
        when = datetime.fromisoformat(str(value or "").strip().replace("Z", "+00:00"))
        return when.astimezone(timezone.utc) if when.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def pick(source, *names):
    for name in names:
        value = source.get(name)
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() not in {"nan", "none", "null"}:
            return text
    return ""


def frozen_mlb_identity(source) -> dict:
    """Return trustworthy *capture identity* only if every field agrees.

    Accept original MLB decision records and their identical Prop V2 picks.
    Reject inconsistent player-key, team matchup, source time or provenance.
    Does not contact any API or infer identity from a player name.
    """
    id_value = pick(source, "mlb_source_player_id", "player_id")
    id_value = explicit_id(id_value)
    name = pick(source, "mlb_source_player_name", "player")
    key = pick(source, "player_key")
    team = pick(source, "mlb_source_player_team", "team")
    away = pick(source, "mlb_source_away_team", "away_team")
    home = pick(source, "mlb_source_home_team", "home_team")
    event = pick(source, "event_id")
    event_start = pick(source, "event_start", "start")
    source_start = pick(source, "mlb_source_original_start", "start", "event_start")
    provided_provenance = pick(source, "mlb_source_identity_provenance")
    nteam, naway, nhome = player_key(team), player_key(away), player_key(home)
    stamp = utc_start(event_start)
    original = utc_start(source_start)
    if not all((id_value, name, key, nteam, naway, nhome, event, stamp, original)):
        return {}
    if (
        (provided_provenance and provided_provenance != IDENTITY_PROVENANCE)
        or player_key(name) != player_key(key)
        or naway == nhome
        or nteam not in {naway, nhome}
        or stamp != original
    ):
        return {}
    return {
        "mlb_source_player_id": id_value,
        "mlb_source_player_name": name,
        "mlb_source_player_team": team,
        "mlb_source_away_team": away,
        "mlb_source_home_team": home,
        "mlb_source_original_start": original.isoformat(),
        "mlb_source_identity_provenance": IDENTITY_PROVENANCE,
        "mlb_source_box_verified_at_capture": False,
        "mlb_source_platform_payout_claimed": False,
    }
