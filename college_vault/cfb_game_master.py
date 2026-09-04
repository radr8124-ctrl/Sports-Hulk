from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
CV = ROOT / "college_vault"
DERIVED = CV / "derived"
META = CV / "meta"

SRC = DERIVED / "CFB_GAMES_HISTORY.parquet"

print("=" * 76)
print("SPORTS HULK CFB GAME MASTER + HISTORICAL COMPS")
print("=" * 76)

df = pd.read_parquet(SRC)

print("Raw historical games:", len(df))
print("Columns:", len(df.columns))

def first_col(frame, names):
    for n in names:
        if n in frame.columns:
            return n
    return None

date_col = first_col(df, [
    "startDate", "start_date", "startTime",
    "start_time", "date"
])

home_col = first_col(df, [
    "homeTeam", "home_team", "home"
])

away_col = first_col(df, [
    "awayTeam", "away_team", "away"
])

home_pts_col = first_col(df, [
    "homePoints", "home_points", "homeScore", "home_score"
])

away_pts_col = first_col(df, [
    "awayPoints", "away_points", "awayScore", "away_score"
])

season_col = first_col(df, [
    "season", "year", "source_year"
])

week_col = first_col(df, [
    "week"
])

neutral_col = first_col(df, [
    "neutralSite", "neutral_site", "neutral"
])

conference_game_col = first_col(df, [
    "conferenceGame", "conference_game"
])

required = {
    "date": date_col,
    "home": home_col,
    "away": away_col,
    "home_points": home_pts_col,
    "away_points": away_pts_col,
    "season": season_col,
}

missing = [k for k,v in required.items() if v is None]

if missing:
    raise SystemExit(
        "Missing required CFBD columns: " + ", ".join(missing)
    )

g = pd.DataFrame({
    "game_date": pd.to_datetime(df[date_col], errors="coerce", utc=True),
    "season": pd.to_numeric(df[season_col], errors="coerce"),
    "week": (
        pd.to_numeric(df[week_col], errors="coerce")
        if week_col else np.nan
    ),
    "home_team": df[home_col].astype(str),
    "away_team": df[away_col].astype(str),
    "home_points": pd.to_numeric(df[home_pts_col], errors="coerce"),
    "away_points": pd.to_numeric(df[away_pts_col], errors="coerce"),
    "neutral": (
        df[neutral_col].fillna(False).astype(bool)
        if neutral_col else False
    ),
    "conference_game": (
        df[conference_game_col].fillna(False).astype(bool)
        if conference_game_col else False
    ),
})

g = g.dropna(
    subset=[
        "game_date",
        "season",
        "home_points",
        "away_points"
    ]
).copy()

g = g[
    (g["home_team"].str.len() > 0) &
    (g["away_team"].str.len() > 0)
].copy()

g["season"] = g["season"].astype(int)

g["home_margin"] = g["home_points"] - g["away_points"]
g["total_points"] = g["home_points"] + g["away_points"]
g["home_win"] = (g["home_margin"] > 0).astype(int)

g = g.sort_values(
    ["game_date", "home_team", "away_team"]
).reset_index(drop=True)

print("Completed games:", len(g))


# -------------------------------------------------------------
# TEAM-GAME HISTORY
# -------------------------------------------------------------

home_rows = pd.DataFrame({
    "game_date": g["game_date"],
    "season": g["season"],
    "team": g["home_team"],
    "opponent": g["away_team"],
    "points_for": g["home_points"],
    "points_against": g["away_points"],
    "margin": g["home_margin"],
    "is_home": 1,
    "neutral": g["neutral"].astype(int),
})

away_rows = pd.DataFrame({
    "game_date": g["game_date"],
    "season": g["season"],
    "team": g["away_team"],
    "opponent": g["home_team"],
    "points_for": g["away_points"],
    "points_against": g["home_points"],
    "margin": -g["home_margin"],
    "is_home": 0,
    "neutral": g["neutral"].astype(int),
})

tg = pd.concat(
    [home_rows, away_rows],
    ignore_index=True
).sort_values(["team", "game_date"]).reset_index(drop=True)


# Every rolling stat is SHIFTED by one game.
# That prevents the current game's result leaking into its features.

grp = tg.groupby("team", group_keys=False)

tg["games_before"] = grp.cumcount()

for window in (3, 5, 8):
    tg[f"pf_last{window}"] = grp["points_for"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )

    tg[f"pa_last{window}"] = grp["points_against"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )

    tg[f"margin_last{window}"] = grp["margin"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).mean()
    )

tg["win"] = (tg["margin"] > 0).astype(int)

tg["winpct_last5"] = grp["win"].transform(
    lambda s: s.shift(1).rolling(5, min_periods=1).mean()
)

tg["winpct_last8"] = grp["win"].transform(
    lambda s: s.shift(1).rolling(8, min_periods=1).mean()
)

tg["previous_game_date"] = grp["game_date"].shift(1)

tg["rest_days"] = (
    tg["game_date"] - tg["previous_game_date"]
).dt.total_seconds() / 86400

tg["rest_days"] = tg["rest_days"].clip(lower=0, upper=30)

TEAM_FEATURES = DERIVED / "CFB_TEAM_GAME_FEATURES.parquet"
tg.to_parquet(TEAM_FEATURES, index=False)

print("Team-game feature rows:", len(tg))


# -------------------------------------------------------------
# MERGE PRE-GAME FEATURES BACK TO EACH GAME
# -------------------------------------------------------------

feature_cols = [
    "games_before",
    "pf_last3",
    "pa_last3",
    "margin_last3",
    "pf_last5",
    "pa_last5",
    "margin_last5",
    "pf_last8",
    "pa_last8",
    "margin_last8",
    "winpct_last5",
    "winpct_last8",
    "rest_days",
]

home_feat = tg[
    ["game_date", "team"] + feature_cols
].copy()

home_feat = home_feat.rename(
    columns={
        "team": "home_team",
        **{c: f"home_{c}" for c in feature_cols}
    }
)

away_feat = tg[
    ["game_date", "team"] + feature_cols
].copy()

away_feat = away_feat.rename(
    columns={
        "team": "away_team",
        **{c: f"away_{c}" for c in feature_cols}
    }
)

master = g.merge(
    home_feat,
    on=["game_date", "home_team"],
    how="left"
)

master = master.merge(
    away_feat,
    on=["game_date", "away_team"],
    how="left"
)


# -------------------------------------------------------------
# MATCHUP DIFFERENTIALS
# -------------------------------------------------------------

master["margin_form_gap_3"] = (
    master["home_margin_last3"] -
    master["away_margin_last3"]
)

master["margin_form_gap_5"] = (
    master["home_margin_last5"] -
    master["away_margin_last5"]
)

master["margin_form_gap_8"] = (
    master["home_margin_last8"] -
    master["away_margin_last8"]
)

master["offense_gap_5"] = (
    master["home_pf_last5"] -
    master["away_pf_last5"]
)

master["defense_gap_5"] = (
    master["away_pa_last5"] -
    master["home_pa_last5"]
)

master["winpct_gap_5"] = (
    master["home_winpct_last5"] -
    master["away_winpct_last5"]
)

master["rest_gap"] = (
    master["home_rest_days"] -
    master["away_rest_days"]
)

master["home_field"] = (~master["neutral"]).astype(int)

master["history_ready"] = (
    (master["home_games_before"] >= 3) &
    (master["away_games_before"] >= 3)
)

MASTER_CSV = DERIVED / "CFB_GAME_MASTER.csv"
MASTER_PARQUET = DERIVED / "CFB_GAME_MASTER.parquet"

master.to_csv(MASTER_CSV, index=False)
master.to_parquet(MASTER_PARQUET, index=False)

print("Game Master rows:", len(master))
print(
    "History-ready rows:",
    int(master["history_ready"].sum())
)


# -------------------------------------------------------------
# LEAKAGE-SAFE HISTORICAL COMPS / WALK-FORWARD
# -------------------------------------------------------------

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
    master["history_ready"]
].dropna(subset=features).copy()

usable = usable.sort_values("game_date").reset_index(drop=True)

# Global scales are only used for distance normalization,
# not for target/outcome estimation.

scale = usable[features].std(ddof=0).replace(0, 1).fillna(1)

X = usable[features].div(scale, axis=1).to_numpy(dtype=float)

dates = usable["game_date"].to_numpy()
seasons = usable["season"].to_numpy()

home_win = usable["home_win"].to_numpy(dtype=float)
margin = usable["home_margin"].to_numpy(dtype=float)
totals = usable["total_points"].to_numpy(dtype=float)

MIN_PRIOR = 100
K = 50

results = []

print()
print("Building leakage-safe historical comps...")
print("Eligible games:", len(usable))

for i in range(len(usable)):

    # Strictly earlier games only.
    prior = np.where(dates < dates[i])[0]

    if len(prior) < MIN_PRIOR:
        continue

    delta = X[prior] - X[i]
    dist = np.sqrt(np.mean(delta * delta, axis=1))

    k = min(K, len(prior))

    nearest_local = np.argpartition(
        dist,
        k - 1
    )[:k]

    idx = prior[nearest_local]
    d = dist[nearest_local]

    # closer comps receive somewhat more weight
    weights = 1.0 / (d + 0.10)
    weights = weights / weights.sum()

    pred_home_win = float(
        np.sum(home_win[idx] * weights)
    )

    pred_margin = float(
        np.sum(margin[idx] * weights)
    )

    pred_total = float(
        np.sum(totals[idx] * weights)
    )

    nearest_dist = float(np.median(d))

    row = usable.iloc[i]

    results.append({
        "game_date": row["game_date"],
        "season": int(row["season"]),
        "week": row["week"],
        "away_team": row["away_team"],
        "home_team": row["home_team"],
        "actual_home_win": int(row["home_win"]),
        "actual_home_margin": row["home_margin"],
        "actual_total": row["total_points"],
        "comp_samples": k,
        "comp_home_win_prob": pred_home_win,
        "comp_projected_margin": pred_margin,
        "comp_projected_total": pred_total,
        "comp_median_distance": nearest_dist,
    })

comps = pd.DataFrame(results)

if comps.empty:
    raise SystemExit("No historical comp rows generated.")

comps["pred_home_win"] = (
    comps["comp_home_win_prob"] >= 0.50
).astype(int)

comps["winner_correct"] = (
    comps["pred_home_win"] ==
    comps["actual_home_win"]
).astype(int)

comps["margin_abs_error"] = (
    comps["comp_projected_margin"] -
    comps["actual_home_margin"]
).abs()

comps["total_abs_error"] = (
    comps["comp_projected_total"] -
    comps["actual_total"]
).abs()

COMPS_CSV = DERIVED / "CFB_HISTORICAL_COMPS.csv"
COMPS_PARQUET = DERIVED / "CFB_HISTORICAL_COMPS.parquet"

comps.to_csv(COMPS_CSV, index=False)
comps.to_parquet(COMPS_PARQUET, index=False)


# -------------------------------------------------------------
# CALIBRATION REPORT
# -------------------------------------------------------------

summary_rows = []

for season, d in comps.groupby("season"):
    summary_rows.append({
        "season": int(season),
        "samples": len(d),
        "winner_accuracy": d["winner_correct"].mean(),
        "margin_mae": d["margin_abs_error"].mean(),
        "total_mae": d["total_abs_error"].mean(),
        "avg_comp_distance": d["comp_median_distance"].mean(),
    })

summary_rows.append({
    "season": "ALL",
    "samples": len(comps),
    "winner_accuracy": comps["winner_correct"].mean(),
    "margin_mae": comps["margin_abs_error"].mean(),
    "total_mae": comps["total_abs_error"].mean(),
    "avg_comp_distance": comps["comp_median_distance"].mean(),
})

cal = pd.DataFrame(summary_rows)

CAL_CSV = DERIVED / "CFB_CALIBRATION.csv"
cal.to_csv(CAL_CSV, index=False)

overall = cal[
    cal["season"].astype(str) == "ALL"
].iloc[0]

meta = {
    "historical_games": int(len(master)),
    "history_ready_games": int(master["history_ready"].sum()),
    "walkforward_games": int(len(comps)),
    "winner_accuracy": float(overall["winner_accuracy"]),
    "margin_mae": float(overall["margin_mae"]),
    "total_mae": float(overall["total_mae"]),
    "comp_features": features,
    "comp_k": K,
    "method": "prior-games-only nearest historical comps",
}

(META / "CFB_MODEL_SUMMARY.json").write_text(
    json.dumps(meta, indent=2),
    encoding="utf-8",
)

print()
print("=" * 76)
print("CFB MODEL SUMMARY")
print("=" * 76)
print("Historical games:", len(master))
print(
    "History-ready games:",
    int(master["history_ready"].sum())
)
print("Walk-forward games:", len(comps))
print(
    "Winner accuracy:",
    f"{float(overall['winner_accuracy']):.3f}"
)
print(
    "Margin MAE:",
    f"{float(overall['margin_mae']):.3f}"
)
print(
    "Total MAE:",
    f"{float(overall['total_mae']):.3f}"
)
print()
print("GAME MASTER:", MASTER_PARQUET)
print("COMPS:", COMPS_PARQUET)
print("CALIBRATION:", CAL_CSV)
print("RESULT: PASS")
print("=" * 76)
