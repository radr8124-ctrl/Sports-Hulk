from pathlib import Path
from datetime import datetime, timezone, timedelta
import sys
import json
import numpy as np
import pandas as pd
from dotenv import load_dotenv

ROOT = Path("/home/ubuntu/sports-hulk")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from connectors.cfbd import CFBDClient
from connectors.the_odds_api import TheOddsAPIClient
from college_logic import upcoming_games, college_game_rows
from odds_merge import merge_college_rows

load_dotenv(ROOT / ".env", override=True)

CV = ROOT / "college_vault"
DERIVED = CV / "derived"
DATA = ROOT / "data"

MASTER = DERIVED / "CFB_GAME_MASTER.parquet"
TEAM = DERIVED / "CFB_TEAM_GAME_FEATURES.parquet"

print("=" * 76)
print("SPORTS HULK CFB CURRENT INTELLIGENCE BOARD")
print("=" * 76)

cfbd = CFBDClient()
oddsapi = TheOddsAPIClient()

year = datetime.now(timezone.utc).year

# ------------------------------------------------------------
# LIVE CURRENT SLATE + RATINGS
# ------------------------------------------------------------

games = cfbd.games(
    year=year,
    season_type="regular",
    classification="fbs",
)

try:
    core = cfbd.core_ratings(year)
except Exception as e:
    print("CORE warning:", e)
    core = []

try:
    srs = cfbd.srs_ratings(year)
except Exception as e:
    print("SRS warning:", e)
    srs = []

(DATA / "cfbd_games.json").write_text(
    json.dumps(
        {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "year": year,
                "games": games,
            },
        },
        indent=2,
    )
)

(DATA / "cfbd_ratings.json").write_text(
    json.dumps(
        {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "year": year,
                "core": core,
                "srs": srs,
            },
        },
        indent=2,
    )
)

slate = upcoming_games(
    games,
    days_back=1,
    days_forward=10,
)

base_rows = college_game_rows(
    slate,
    core,
    srs,
)

print("Current/recent FBS games:", len(base_rows))


# ------------------------------------------------------------
# ODDS
# ------------------------------------------------------------

odds_events = []

try:
    if oddsapi.connected:
        result = oddsapi.ncaaf_odds()
        odds_events = result.get("data", [])

        (DATA / "ncaaf_odds.json").write_text(
            json.dumps(
                {
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                    "payload": {
                        "events": odds_events,
                        "usage": result.get("usage", {}),
                    },
                },
                indent=2,
            )
        )

        print("Fresh odds events:", len(odds_events))

except Exception as e:
    print("Odds refresh warning:", e)

if not odds_events:
    try:
        cache = json.loads(
            (DATA / "ncaaf_odds.json").read_text()
        )

        payload = cache.get("payload", cache)
        odds_events = payload.get("events", [])

        print("Cached odds events:", len(odds_events))

    except Exception:
        pass

rows = merge_college_rows(
    base_rows,
    odds_events,
)

current = pd.DataFrame(rows)

if current.empty:
    raise SystemExit("No current CFB games available.")

current["start_dt"] = pd.to_datetime(
    current["start"],
    errors="coerce",
    utc=True,
)


# ------------------------------------------------------------
# HISTORICAL MODEL
# ------------------------------------------------------------

master = pd.read_parquet(MASTER)
master["game_date"] = pd.to_datetime(
    master["game_date"],
    errors="coerce",
    utc=True,
)

features = [
    "margin_form_gap_3",
    "margin_form_gap_5",
    "margin_form_gap_8",
    "offense_gap_5",
    "defense_gap_5",
    "winpct_gap_5",
    "rest_gap",
    "home_field",
]

usable = master[
    master["history_ready"] == True
].dropna(subset=features).copy()

scale = (
    usable[features]
    .std(ddof=0)
    .replace(0, 1)
    .fillna(1)
)

X_hist = (
    usable[features]
    .div(scale, axis=1)
    .to_numpy(dtype=float)
)


# ------------------------------------------------------------
# BUILD CURRENT TEAM FORM DIRECTLY FROM COMPLETED HISTORY
# ------------------------------------------------------------

game_history = master[
    [
        "game_date",
        "home_team",
        "away_team",
        "home_points",
        "away_points",
        "home_margin",
    ]
].copy()

home = pd.DataFrame({
    "game_date": game_history["game_date"],
    "team": game_history["home_team"],
    "pf": game_history["home_points"],
    "pa": game_history["away_points"],
    "margin": game_history["home_margin"],
})

away = pd.DataFrame({
    "game_date": game_history["game_date"],
    "team": game_history["away_team"],
    "pf": game_history["away_points"],
    "pa": game_history["home_points"],
    "margin": -game_history["home_margin"],
})

team_history = pd.concat(
    [home, away],
    ignore_index=True,
).sort_values(["team", "game_date"])


def team_state(team, before):
    d = team_history[
        (team_history["team"] == team) &
        (team_history["game_date"] < before)
    ].sort_values("game_date")

    if len(d) < 3:
        return None

    def avg(col, n):
        return float(d.tail(n)[col].mean())

    wins = (d["margin"] > 0).astype(float)

    last_date = d.iloc[-1]["game_date"]
    rest = (
        before - last_date
    ).total_seconds() / 86400

    return {
        "games": len(d),
        "pf3": avg("pf", 3),
        "pa3": avg("pa", 3),
        "m3": avg("margin", 3),

        "pf5": avg("pf", 5),
        "pa5": avg("pa", 5),
        "m5": avg("margin", 5),

        "pf8": avg("pf", 8),
        "pa8": avg("pa", 8),
        "m8": avg("margin", 8),

        "w5": float(wins.tail(5).mean()),
        "w8": float(wins.tail(8).mean()),

        "rest": float(
            np.clip(rest, 0, 30)
        ),
    }


# ------------------------------------------------------------
# HISTORICAL COMP LOOKUP
# ------------------------------------------------------------

def historical_comp(feature_row, before, k=50):
    prior_mask = (
        usable["game_date"] < before
    ).to_numpy()

    idx = np.where(prior_mask)[0]

    if len(idx) < 100:
        return None

    x = np.array(
        [feature_row[f] for f in features],
        dtype=float,
    )

    x = x / scale[features].to_numpy(dtype=float)

    delta = X_hist[idx] - x

    dist = np.sqrt(
        np.mean(delta * delta, axis=1)
    )

    k = min(k, len(idx))

    near_local = np.argpartition(
        dist,
        k - 1,
    )[:k]

    use_idx = idx[near_local]
    d = dist[near_local]

    weights = 1.0 / (d + 0.10)
    weights = weights / weights.sum()

    sample = usable.iloc[use_idx]

    p_home = float(
        np.sum(
            sample["home_win"].to_numpy(dtype=float)
            * weights
        )
    )

    margin = float(
        np.sum(
            sample["home_margin"].to_numpy(dtype=float)
            * weights
        )
    )

    total = float(
        np.sum(
            sample["total_points"].to_numpy(dtype=float)
            * weights
        )
    )

    return {
        "comp_samples": k,
        "comp_home_win_prob": p_home,
        "comp_projected_margin": margin,
        "comp_projected_total": total,
        "comp_median_distance": float(
            np.median(d)
        ),
    }


# ------------------------------------------------------------
# CURRENT BOARD
# ------------------------------------------------------------

out = []

for _, row in current.iterrows():

    start = row["start_dt"]

    if pd.isna(start):
        continue

    home_team = str(row["home"])
    away_team = str(row["away"])

    hs = team_state(
        home_team,
        start,
    )

    aws = team_state(
        away_team,
        start,
    )

    result = row.to_dict()

    if not hs or not aws:
        result.update({
            "model_status": "INSUFFICIENT_HISTORY",
            "research_lean": "UNKNOWN",
            "research_confidence": "LOW",
        })

        out.append(result)
        continue

    feature_row = {
        "margin_form_gap_3":
            hs["m3"] - aws["m3"],

        "margin_form_gap_5":
            hs["m5"] - aws["m5"],

        "margin_form_gap_8":
            hs["m8"] - aws["m8"],

        "offense_gap_5":
            hs["pf5"] - aws["pf5"],

        "defense_gap_5":
            aws["pa5"] - hs["pa5"],

        "winpct_gap_5":
            hs["w5"] - aws["w5"],

        "rest_gap":
            hs["rest"] - aws["rest"],

        "home_field":
            0 if bool(row.get("neutral", False))
            else 1,
    }

    comp = historical_comp(
        feature_row,
        start,
    )

    result.update(feature_row)

    if not comp:
        result.update({
            "model_status": "INSUFFICIENT_COMPS",
            "research_lean": "UNKNOWN",
            "research_confidence": "LOW",
        })

        out.append(result)
        continue

    result.update(comp)

    p = comp["comp_home_win_prob"]

    if p >= .50:
        lean = home_team
        strength = p
    else:
        lean = away_team
        strength = 1 - p

    if strength >= .68:
        confidence = "HIGH"
    elif strength >= .59:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    result["research_lean"] = lean
    result["research_confidence"] = confidence
    result["model_status"] = "RESEARCH_READY"

    # Market context stays explicitly separate.
    spread = pd.to_numeric(
        row.get("Home_spread"),
        errors="coerce",
    )

    if pd.notna(spread):
        result["model_vs_home_spread_edge"] = (
            comp["comp_projected_margin"] + spread
        )
    else:
        result["model_vs_home_spread_edge"] = np.nan

    out.append(result)


board = pd.DataFrame(out)

BOARD_CSV = DERIVED / "CFB_CURRENT_BOARD.csv"
BOARD_PARQUET = DERIVED / "CFB_CURRENT_BOARD.parquet"

board.to_csv(
    BOARD_CSV,
    index=False,
)

board.to_parquet(
    BOARD_PARQUET,
    index=False,
)

ready = int(
    (
        board["model_status"]
        == "RESEARCH_READY"
    ).sum()
)

print()
print("=" * 76)
print("CFB CURRENT BOARD SUMMARY")
print("=" * 76)

print("Games:", len(board))
print("Research-ready:", ready)

if "research_confidence" in board:
    print(
        "Confidence:",
        board[
            "research_confidence"
        ].value_counts().to_dict()
    )

if "Odds_matched" in board:
    print(
        "Odds matched:",
        int(
            board[
                "Odds_matched"
            ].fillna(False).sum()
        ),
        "/",
        len(board),
    )

print("OUTPUT:", BOARD_CSV)
print("RESULT: PASS")
print("=" * 76)
