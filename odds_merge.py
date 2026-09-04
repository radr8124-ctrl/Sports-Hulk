from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple
import re
import statistics


ALIASES = {
    "miami fl": "miami",
    "miami hurricanes": "miami",
    "southern california": "usc",
    "usc trojans": "usc",
    "uconn": "connecticut",
    "connecticut huskies": "connecticut",
    "ole miss": "mississippi",
    "mississippi rebels": "mississippi",
    "utsa": "texas san antonio",
    "utep": "texas el paso",
    "ucf": "central florida",
    "smu": "southern methodist",
    "lsu": "louisiana state",
    "byu": "brigham young",
}

# Common mascot words that often appear in sportsbook team names but not CFBD names.
MASCOT_WORDS = {
    "horned","frogs","tar","heels","tigers","bulldogs","wildcats","bears","eagles",
    "hawks","falcons","cardinals","cougars","panthers","huskies","trojans","bruins",
    "aggies","longhorns","razorbacks","gators","seminoles","volunteers","commodores",
    "rebels","cowboys","mountaineers","cyclones","jayhawks","sooners","buckeyes",
    "wolverines","spartans","hoosiers","terrapins","terps","boilermakers","badgers",
    "hawkeyes","gophers","cornhuskers","nittany","lions","ducks","beavers","utes",
    "buffaloes","sun","devils","bearcats","knights","mustangs","owls","wave","green",
    "orange","demon","deacons","yellow","jackets","cavaliers","hokies","wolfpack",
    "blue","devils","gamecocks","crimson","tide"
}


def normalize_team(name: Optional[str]) -> str:
    if not name:
        return ""
    x = str(name).lower().strip()
    x = x.replace("&", " and ")
    x = re.sub(r"\([^)]*\)", " ", x)
    x = re.sub(r"[^a-z0-9 ]+", " ", x)
    x = re.sub(r"\b(university|college)\b", " ", x)
    x = re.sub(r"\s+", " ", x).strip()
    return ALIASES.get(x, x)


def _core_tokens(name: str):
    return [t for t in normalize_team(name).split() if t not in MASCOT_WORDS]


def _similar(a: str, b: str) -> float:
    a = normalize_team(a)
    b = normalize_team(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        shorter = min(len(a), len(b))
        longer = max(len(a), len(b))
        if shorter >= 3:
            return max(0.92, shorter / longer)

    at = set(_core_tokens(a))
    bt = set(_core_tokens(b))
    if at and bt:
        overlap = len(at & bt) / max(1, min(len(at), len(bt)))
        if overlap == 1.0:
            return 0.96
        if overlap >= 0.67:
            return max(0.86, overlap)

    return SequenceMatcher(None, a, b).ratio()


def _market(bookmaker: Dict[str, Any], key: str):
    for market in bookmaker.get("markets", []) or []:
        if market.get("key") == key:
            return market
    return None


def _median(values):
    vals = [v for v in values if isinstance(v, (int, float))]
    return statistics.median(vals) if vals else None


def consensus_summary(game: Dict[str, Any]) -> Dict[str, Any]:
    home = game.get("home_team")
    away = game.get("away_team")
    home_ml, away_ml, home_spreads, totals = [], [], [], []

    for book in game.get("bookmakers", []) or []:
        h2h = _market(book, "h2h")
        if h2h:
            for outcome in h2h.get("outcomes", []) or []:
                if outcome.get("name") == home:
                    home_ml.append(outcome.get("price"))
                elif outcome.get("name") == away:
                    away_ml.append(outcome.get("price"))

        spreads = _market(book, "spreads")
        if spreads:
            for outcome in spreads.get("outcomes", []) or []:
                if outcome.get("name") == home:
                    home_spreads.append(outcome.get("point"))

        total = _market(book, "totals")
        if total:
            over_points = [
                o.get("point") for o in total.get("outcomes", []) or []
                if o.get("name") == "Over"
            ]
            if over_points:
                totals.extend(over_points)
            else:
                totals.extend(o.get("point") for o in total.get("outcomes", []) or [])

    return {
        "Odds_books": len(game.get("bookmakers", []) or []),
        "Home_moneyline": _median(home_ml),
        "Away_moneyline": _median(away_ml),
        "Home_spread": _median(home_spreads),
        "Total": _median(totals),
        "Odds_event_id": game.get("id"),
        "Odds_start": game.get("commence_time"),
    }


def find_match(home: str, away: str, odds_games: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], float]:
    best = None
    best_score = 0.0

    for game in odds_games:
        direct = (_similar(home, game.get("home_team","")) + _similar(away, game.get("away_team",""))) / 2
        swapped = (_similar(home, game.get("away_team","")) + _similar(away, game.get("home_team",""))) / 2 - 0.10
        score = max(direct, swapped)
        if score > best_score:
            best = game
            best_score = score

    if best_score < 0.72:
        return None, best_score
    return best, best_score


def merge_college_rows(rows: List[Dict[str, Any]], odds_games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = []
    for row in rows:
        out = dict(row)
        home = row.get("home") or row.get("homeTeam") or row.get("Home")
        away = row.get("away") or row.get("awayTeam") or row.get("Away")
        match, score = find_match(str(home or ""), str(away or ""), odds_games)

        out["Odds_matched"] = bool(match)
        out["Odds_match_score"] = round(score, 3) if score else 0.0
        if match:
            out.update(consensus_summary(match))
        else:
            out.update({
                "Odds_books": None,
                "Home_moneyline": None,
                "Away_moneyline": None,
                "Home_spread": None,
                "Total": None,
                "Odds_event_id": None,
                "Odds_start": None,
            })
        merged.append(out)
    return merged
