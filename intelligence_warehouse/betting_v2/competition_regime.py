from __future__ import annotations

REGIME_SCHEMA_VERSION = "COMPETITION_REGIME_V1"
REGIME_ENFORCED_SPORTS = frozenset({"NBA"})

_NUMERIC_REGIMES = {
    1: "PRESEASON",
    2: "REGULAR",
    3: "POSTSEASON",
}

_TEXT_REGIMES = {
    "preseason": "PRESEASON",
    "pre-season": "PRESEASON",
    "regular": "REGULAR",
    "regular season": "REGULAR",
    "regular-season": "REGULAR",
    "postseason": "POSTSEASON",
    "post-season": "POSTSEASON",
    "playoff": "POSTSEASON",
    "playoffs": "POSTSEASON",
}


def normalize_competition_regime(value, sport=None) -> str:
    if value is None:
        return "UNKNOWN"

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = None
        if numeric is not None and numeric.is_integer():
            return _NUMERIC_REGIMES.get(int(numeric), "UNKNOWN")

    text = str(value).strip().lower()
    if not text:
        return "UNKNOWN"

    try:
        numeric = float(text)
    except ValueError:
        numeric = None
    if numeric is not None and numeric.is_integer():
        return _NUMERIC_REGIMES.get(int(numeric), "UNKNOWN")

    return _TEXT_REGIMES.get(text, "UNKNOWN")


def regime_enforced(sport) -> bool:
    return str(sport or "").strip().upper() in REGIME_ENFORCED_SPORTS


def proof_lane_key(sport, market, regime) -> str:
    sport_key = str(sport or "").strip().upper()
    market_key = str(market or "").strip().upper()
    lane_key = f"{sport_key}_{market_key}"
    if not regime_enforced(sport_key):
        return lane_key
    canonical_regime = normalize_competition_regime(regime, sport_key)
    return f"{lane_key}|{canonical_regime}"


def proof_version(model_version, sport, regime) -> str:
    version = str(model_version or "").strip()
    sport_key = str(sport or "").strip().upper()
    if not regime_enforced(sport_key):
        return version
    canonical_regime = normalize_competition_regime(regime, sport_key)
    return f"{version}|{REGIME_SCHEMA_VERSION}|{canonical_regime}"
