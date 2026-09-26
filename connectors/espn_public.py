from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional

import requests

BASE = "https://site.api.espn.com/apis/site/v2/sports"


class ESPNPublicClient:
    """Best-effort, no-key ESPN public JSON reader.

    ESPN does not publish this as a supported developer API. Treat it as a
    backup/context source: cache responses, keep provenance, and never assume
    fields are present.
    """

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def _get(self, path: str, params: Optional[dict] = None) -> Dict[str, Any]:
        r = requests.get(
            BASE.rstrip("/") + "/" + path.lstrip("/"),
            params=params or {},
            timeout=self.timeout,
            headers={"User-Agent": "Sports-Hulk/1.0"},
        )
        r.raise_for_status()
        return r.json()

    def scoreboard(self, sport: str, league: str, dates: Optional[str] = None):
        params = {}
        if dates:
            params["dates"] = dates
        return self._get(f"{sport}/{league}/scoreboard", params=params)

    def nfl_scoreboard(self, dates=None):
        return self.scoreboard("football", "nfl", dates)

    def cfb_scoreboard(self, dates=None):
        return self.scoreboard("football", "college-football", dates)

    def mlb_scoreboard(self, dates=None):
        return self.scoreboard("baseball", "mlb", dates)


def _number(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower().replace("o", "").replace("u", "")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else None


def _team(comp: Dict[str, Any], side: str) -> Dict[str, Any]:
    for item in comp.get("competitors", []) or []:
        if item.get("homeAway") == side:
            return item
    return {}


def _close_value(container: Dict[str, Any], key: str):
    if not isinstance(container, dict):
        return None
    close = container.get("close") or {}
    if isinstance(close, dict) and close.get(key) is not None:
        return _number(close.get(key))
    return _number(container.get(key))


def _moneyline(odds: Dict[str, Any], side: str):
    ml = odds.get("moneyline") or {}
    branch = ml.get(side) if isinstance(ml, dict) else None
    value = _close_value(branch or {}, "odds")
    if value is not None:
        return value
    legacy = odds.get(f"{side}TeamOdds") or {}
    for key in ("moneyLine", "moneyline", "moneyLineClose"):
        if legacy.get(key) is not None:
            return _number(legacy.get(key))
    return None


def _spread(odds: Dict[str, Any], side: str):
    ps = odds.get("pointSpread") or {}
    branch = ps.get(side) if isinstance(ps, dict) else None
    value = _close_value(branch or {}, "line")
    if value is not None:
        return value
    home_spread = _number(odds.get("spread"))
    if home_spread is None:
        return None
    return home_spread if side == "home" else -home_spread


def _total(odds: Dict[str, Any]):
    value = _number(odds.get("overUnder"))
    if value is not None:
        return value
    total = odds.get("total") or {}
    over = total.get("over") if isinstance(total, dict) else None
    return _close_value(over or {}, "line")


def _provider_name(odds: Dict[str, Any]) -> str:
    provider = odds.get("provider") or {}
    return str(provider.get("name") or provider.get("id") or "ESPN")


def scoreboard_to_market_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    collected = datetime.now(timezone.utc).isoformat()
    rows = []
    for event in payload.get("events", []) or []:
        comps = event.get("competitions", []) or []
        if not comps:
            continue
        comp = comps[0]
        home = _team(comp, "home")
        away = _team(comp, "away")
        home_name = ((home.get("team") or {}).get("displayName"))
        away_name = ((away.get("team") or {}).get("displayName"))
        if not home_name or not away_name:
            continue

        odds_list = comp.get("odds", []) or []
        odds = odds_list[0] if odds_list else {}
        provider = _provider_name(odds) if odds else "ESPN"

        rows.append({
            "event_id": str(event.get("id") or comp.get("id") or ""),
            "start": event.get("date") or comp.get("date"),
            "away_team": away_name,
            "home_team": home_name,
            "away_moneyline": _moneyline(odds, "away") if odds else None,
            "home_moneyline": _moneyline(odds, "home") if odds else None,
            "away_spread": _spread(odds, "away") if odds else None,
            "home_spread": _spread(odds, "home") if odds else None,
            "total": _total(odds) if odds else None,
            "sportsbooks": 1 if odds else 0,
            "books_list": provider if odds else "",
            "collected_at": collected,
            "source_provider": "espn_public",
            "source_status": "LIVE_BACKUP",
        })
    return rows


def scoreboard_to_odds_api_events(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert ESPN scoreboard odds into the subset consumed by odds_merge.py."""
    out = []
    for row in scoreboard_to_market_rows(payload):
        home = row["home_team"]
        away = row["away_team"]
        markets = []

        h2h = []
        if row["home_moneyline"] is not None:
            h2h.append({"name": home, "price": row["home_moneyline"]})
        if row["away_moneyline"] is not None:
            h2h.append({"name": away, "price": row["away_moneyline"]})
        if h2h:
            markets.append({"key": "h2h", "outcomes": h2h})

        spreads = []
        if row["home_spread"] is not None:
            spreads.append({"name": home, "point": row["home_spread"]})
        if row["away_spread"] is not None:
            spreads.append({"name": away, "point": row["away_spread"]})
        if spreads:
            markets.append({"key": "spreads", "outcomes": spreads})

        if row["total"] is not None:
            markets.append({
                "key": "totals",
                "outcomes": [
                    {"name": "Over", "point": row["total"]},
                    {"name": "Under", "point": row["total"]},
                ],
            })

        out.append({
            "id": row["event_id"],
            "commence_time": row["start"],
            "home_team": home,
            "away_team": away,
            "bookmakers": [{
                "title": row["books_list"] or "ESPN",
                "markets": markets,
            }] if markets else [],
            "source_provider": "espn_public",
        })
    return out
