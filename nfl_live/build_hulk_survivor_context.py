from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "nfl_live" / "derived"

SURVIVOR = OUT / "NFL_SURVIVOR_CONTEXT_WEATHER.csv"
SCHEDULE = OUT / "NFLVERSE_2026_SCHEDULE.csv"

if not SURVIVOR.exists():
    raise SystemExit("NFL_SURVIVOR_CONTEXT_WEATHER.csv missing")

if not SCHEDULE.exists():
    raise SystemExit("NFLVERSE_2026_SCHEDULE.csv missing")

df = pd.read_csv(SURVIVOR)
games = pd.read_csv(SCHEDULE)

df["start"] = pd.to_datetime(df["start"], utc=True, errors="coerce")
games["gameday"] = pd.to_datetime(games["gameday"], errors="coerce")

TEAM_MAP = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
}


def safe_float(v):
    try:
        return float(v)
    except Exception:
        return np.nan


def team_history(team_abbr, before_date):
    prior = games[
        (games["gameday"] < before_date)
        & (
            (games["home_team"] == team_abbr)
            | (games["away_team"] == team_abbr)
        )
    ].copy()

    # Only completed games.
    prior = prior[
        prior["home_score"].notna()
        & prior["away_score"].notna()
    ]

    if prior.empty:
        return {
            "games": 0,
            "wins": 0,
            "losses": 0,
            "win_pct": np.nan,
            "avg_point_diff": np.nan,
            "last_game": None,
        }

    wins = 0
    diffs = []

    for _, g in prior.iterrows():
        home = g["home_team"] == team_abbr

        scored = (
            safe_float(g["home_score"])
            if home
            else safe_float(g["away_score"])
        )

        allowed = (
            safe_float(g["away_score"])
            if home
            else safe_float(g["home_score"])
        )

        if pd.isna(scored) or pd.isna(allowed):
            continue

        diff = scored - allowed
        diffs.append(diff)

        if diff > 0:
            wins += 1

    played = len(diffs)

    return {
        "games": played,
        "wins": wins,
        "losses": played - wins,
        "win_pct": wins / played if played else np.nan,
        "avg_point_diff": float(np.mean(diffs)) if diffs else np.nan,
        "last_game": prior["gameday"].max() if played else None,
    }


rows = []

for _, row in df.iterrows():
    out = row.to_dict()

    survivor = row["survivor_team"]
    home = row["home_team"]
    away = row["away_team"]

    surv_abbr = TEAM_MAP.get(survivor)
    opp_name = away if survivor == home else home
    opp_abbr = TEAM_MAP.get(opp_name)

    game_date = row["start"].tz_convert("America/New_York").date()
    game_date = pd.Timestamp(game_date)

    surv_hist = (
        team_history(surv_abbr, game_date)
        if surv_abbr
        else {}
    )

    opp_hist = (
        team_history(opp_abbr, game_date)
        if opp_abbr
        else {}
    )

    is_home = survivor == home

    flags = []

    # --------------------------------------------------------
    # MARKET STRENGTH
    # --------------------------------------------------------

    prob = safe_float(row.get("survivor_win_prob"))
    spread = safe_float(row.get("survivor_spread"))

    if not pd.isna(prob):
        if prob >= 0.80:
            flags.append("ELITE_MARKET_FAVORITE")
        elif prob >= 0.75:
            flags.append("STRONG_MARKET_FAVORITE")

    if not pd.isna(spread) and spread <= -7:
        flags.append("TD_PLUS_FAVORITE")

    # --------------------------------------------------------
    # HOME / ROAD
    # --------------------------------------------------------

    if is_home:
        flags.append("HOME")
    else:
        flags.append("ROAD_FAVORITE")

    # --------------------------------------------------------
    # RECENT FORM
    # --------------------------------------------------------

    wp = surv_hist.get("win_pct", np.nan)
    pdiff = surv_hist.get("avg_point_diff", np.nan)

    if not pd.isna(wp):
        if wp >= 0.75:
            flags.append("STRONG_RECENT_RECORD")
        elif wp <= 0.25:
            flags.append("WEAK_RECENT_RECORD")

    if not pd.isna(pdiff):
        if pdiff >= 7:
            flags.append("STRONG_POINT_DIFFERENTIAL")
        elif pdiff <= -7:
            flags.append("NEGATIVE_POINT_DIFFERENTIAL")

    # --------------------------------------------------------
    # WEATHER / VENUE
    # --------------------------------------------------------

    indoor = str(row.get("venue_indoor")).lower() == "true"

    if indoor:
        flags.append("INDOOR")
    else:
        wind = safe_float(row.get("wind_mph"))
        gust = safe_float(row.get("wind_gust_mph"))
        precip = safe_float(row.get("precip_probability"))

        if not pd.isna(gust) and gust >= 30:
            flags.append("HIGH_WIND_RISK")
        elif not pd.isna(gust) and gust >= 20:
            flags.append("WIND_CAUTION")

        if not pd.isna(precip) and precip >= 40:
            flags.append("PRECIP_RISK")
        elif not pd.isna(precip) and precip >= 20:
            flags.append("PRECIP_CAUTION")

    # --------------------------------------------------------
    # REST
    # --------------------------------------------------------

    rest_days = np.nan

    last_game = surv_hist.get("last_game")

    if last_game is not None and not pd.isna(last_game):
        rest_days = (game_date - pd.Timestamp(last_game)).days

        if rest_days <= 5:
            flags.append("SHORT_REST")
        elif rest_days >= 9:
            flags.append("REST_ADVANTAGE")

    # --------------------------------------------------------
    # CONTEXT SCORE
    #
    # Separate from survivor probability.
    # This is an explanatory context index only.
    # --------------------------------------------------------

    context_score = 50.0

    if not pd.isna(prob):
        context_score += (prob - 0.50) * 80

    if is_home:
        context_score += 3
    else:
        context_score -= 2

    if not pd.isna(wp):
        context_score += (wp - 0.50) * 12

    if not pd.isna(pdiff):
        context_score += np.clip(pdiff / 3, -5, 5)

    if "HIGH_WIND_RISK" in flags:
        context_score -= 5

    if "WIND_CAUTION" in flags:
        context_score -= 2

    if "PRECIP_RISK" in flags:
        context_score -= 3

    if "SHORT_REST" in flags:
        context_score -= 3

    if "REST_ADVANTAGE" in flags:
        context_score += 2

    context_score = float(
        np.clip(context_score, 0, 100)
    )

    out.update({
        "survivor_team_abbr": surv_abbr,
        "opponent": opp_name,
        "opponent_abbr": opp_abbr,
        "survivor_is_home": is_home,

        "team_prior_games": surv_hist.get("games"),
        "team_prior_wins": surv_hist.get("wins"),
        "team_prior_losses": surv_hist.get("losses"),
        "team_prior_win_pct": surv_hist.get("win_pct"),
        "team_avg_point_diff": surv_hist.get("avg_point_diff"),

        "opp_prior_win_pct": opp_hist.get("win_pct"),
        "opp_avg_point_diff": opp_hist.get("avg_point_diff"),

        "rest_days": rest_days,

        "hulk_context_score": round(context_score, 1),
        "hulk_context_flags": "|".join(flags),
    })

    rows.append(out)


result = pd.DataFrame(rows)

result = result.sort_values(
    ["hulk_context_score", "survivor_win_prob"],
    ascending=[False, False],
)

result.to_csv(
    OUT / "NFL_SURVIVOR_HULK_CONTEXT.csv",
    index=False,
)

result.to_parquet(
    OUT / "NFL_SURVIVOR_HULK_CONTEXT.parquet",
    index=False,
)

print("=" * 100)
print("SPORTS HULK — SURVIVOR CONTEXT BOARD")
print("=" * 100)

show = result.copy()

show["market_prob_pct"] = (
    show["survivor_win_prob"] * 100
).round(1)

show["record"] = (
    show["team_prior_wins"].fillna(0).astype(int).astype(str)
    + "-"
    + show["team_prior_losses"].fillna(0).astype(int).astype(str)
)

cols = [
    "survivor_team",
    "opponent",
    "market_prob_pct",
    "survivor_spread",
    "record",
    "team_avg_point_diff",
    "rest_days",
    "hulk_context_score",
    "hulk_context_flags",
]

print(show[cols].to_string(index=False))

print()
print("IMPORTANT:")
print("HULK context score is NOT yet replacing market win probability.")
print("RESULT: CONTEXT_ENGINE_READY")
