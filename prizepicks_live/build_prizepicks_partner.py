from pathlib import Path
from datetime import datetime, timezone
import json
import requests
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "prizepicks_live" / "derived"
HISTORY = ROOT / "prizepicks_live" / "history"

OUT.mkdir(parents=True, exist_ok=True)
HISTORY.mkdir(parents=True, exist_ok=True)

URL = "https://partner-api.prizepicks.com/projections"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "SportsHulk/1.0",
}

print("=" * 80)
print("SPORTS HULK — PRIZEPICKS PARTNER COLLECTOR")
print("=" * 80)

r = requests.get(
    URL,
    headers=HEADERS,
    params={"per_page": 1000},
    timeout=45,
)

print("HTTP:", r.status_code)

if r.status_code != 200:
    print(r.text[:2000])
    raise SystemExit("RESULT: FAIL")

payload = r.json()

stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

raw_file = HISTORY / f"prizepicks_raw_{stamp}.json"
raw_file.write_text(json.dumps(payload, indent=2))

data = payload.get("data", [])
included = payload.get("included", [])

print("PROJECTIONS RETURNED:", len(data))
print("INCLUDED OBJECTS:", len(included))

# ---------------------------------------------------------
# Build JSON:API lookup
# ---------------------------------------------------------

lookup = {}

for obj in included:
    obj_type = str(obj.get("type", ""))
    obj_id = str(obj.get("id", ""))
    lookup[(obj_type, obj_id)] = obj.get("attributes", {}) or {}


def related_attributes(item, relationship_name):
    rel = (
        item.get("relationships", {})
        .get(relationship_name, {})
        .get("data")
    )

    if not rel:
        return {}

    if isinstance(rel, list):
        return [
            lookup.get(
                (str(x.get("type", "")), str(x.get("id", ""))),
                {}
            )
            for x in rel
        ]

    return lookup.get(
        (str(rel.get("type", "")), str(rel.get("id", ""))),
        {}
    )


def first_value(d, keys):
    if not isinstance(d, dict):
        return None

    for key in keys:
        value = d.get(key)
        if value not in (None, ""):
            return value

    return None


rows = []

for item in data:
    a = item.get("attributes", {}) or {}

    league = related_attributes(item, "league")
    player = related_attributes(item, "new_player")
    game = related_attributes(item, "game")

    league_name = first_value(
        league,
        ["name", "display_name", "league_name"]
    )

    player_name = first_value(
        player,
        ["name", "display_name", "full_name"]
    )

    team = first_value(
        player,
        ["team", "team_name", "team_abbreviation"]
    )

    position = first_value(
        player,
        ["position", "position_name"]
    )

    home_team = first_value(
        game,
        ["home_team", "home_team_name", "home_team_abbreviation"]
    )

    away_team = first_value(
        game,
        ["away_team", "away_team_name", "away_team_abbreviation"]
    )

    rows.append({
        "projection_id": item.get("id"),
        "league": league_name,
        "player": player_name,
        "team": team,
        "position": position,
        "description": a.get("description"),
        "stat": a.get("stat_display_name") or a.get("stat_type"),
        "stat_type": a.get("stat_type"),
        "line": a.get("line_score"),
        "start_time": a.get("start_time"),
        "end_time": a.get("end_time"),
        "status": a.get("status"),
        "projection_type": a.get("projection_type"),
        "allowed_wager_types": a.get("allowed_wager_types"),
        "odds_type": a.get("odds_type"),
        "adjusted_odds": a.get("adjusted_odds"),
        "group_key": a.get("group_key"),
        "rank": a.get("rank"),
        "trending_count": a.get("trending_count"),
        "is_promo": a.get("is_promo"),
        "discount_name": a.get("discount_name"),
        "discount_percentage": a.get("discount_percentage"),
        "flash_sale_line": a.get("flash_sale_line_score"),
        "game_id": a.get("game_id"),
        "home_team": home_team,
        "away_team": away_team,
        "updated_at": a.get("updated_at"),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    })

df = pd.DataFrame(rows)

if df.empty:
    raise SystemExit("NO PROJECTIONS NORMALIZED — RESULT: FAIL")

# ---------------------------------------------------------
# Clean
# ---------------------------------------------------------

df["league"] = df["league"].fillna("").astype(str)
df["player"] = df["player"].fillna("").astype(str)
df["stat"] = df["stat"].fillna("").astype(str)

df = df.drop_duplicates(
    subset=["projection_id"],
    keep="last"
).reset_index(drop=True)

# ---------------------------------------------------------
# Write master file
# ---------------------------------------------------------

all_file = OUT / "PRIZEPICKS_ALL.csv"
df.to_csv(all_file, index=False)

# ---------------------------------------------------------
# Canonical PrizePicks standard board
# ---------------------------------------------------------

standard = df[
    (df["odds_type"].fillna("").str.lower() == "standard") &
    (~df["is_promo"].fillna(False))
].copy()

standard = standard.sort_values(
    ["player", "stat", "start_time", "updated_at"],
    ascending=[True, True, True, False]
)

standard = standard.drop_duplicates(
    subset=["league", "player", "stat", "start_time"],
    keep="first"
)

standard_file = OUT / "PRIZEPICKS_STANDARD.csv"
standard.to_csv(standard_file, index=False)

# ---------------------------------------------------------
# Sport files
# ---------------------------------------------------------

def save_league(label, aliases):
    mask = df["league"].str.upper().isin(
        [x.upper() for x in aliases]
    )

    sport = df.loc[mask].copy()

    file = OUT / f"{label}_PRIZEPICKS.csv"
    sport.to_csv(file, index=False)

    print()
    print(label)
    print("ROWS:", len(sport))
    print("FILE:", file)

    if not sport.empty:
        print("TOP STATS:")
        print(
            sport["stat"]
            .value_counts()
            .head(12)
            .to_string()
        )

        print()
        print("SAMPLE:")
        cols = [
            "player",
            "team",
            "stat",
            "line",
            "description",
            "trending_count"
        ]

        print(
            sport[cols]
            .head(8)
            .to_string(index=False)
        )

    return len(sport)


nfl_rows = save_league(
    "NFL",
    ["NFL"]
)

mlb_rows = save_league(
    "MLB",
    ["MLB"]
)

print()
print("=" * 80)
print("ALL ROWS:", len(df))
print("NFL ROWS:", nfl_rows)
print("MLB ROWS:", mlb_rows)
print("RAW ARCHIVE:", raw_file)
print("MASTER:", all_file)
print("RESULT: PASS")
print("=" * 80)
