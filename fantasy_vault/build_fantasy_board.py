from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
DV = ROOT / "data_vault"
OUT = ROOT / "fantasy_vault" / "derived"
OUT.mkdir(parents=True, exist_ok=True)

print("=" * 76)
print("SPORTS HULK FANTASY BOARD BUILD")
print("=" * 76)

# ------------------------------------------------------------
# CURRENT 2026 ROSTER
# ------------------------------------------------------------

roster = pd.read_parquet(
    DV / "raw" / "rosters" / "rosters_2026.parquet"
)

# Keep fantasy positions only.
roster = roster[
    roster["position"].isin(["QB", "RB", "WR", "TE"])
].copy()

# Remove obvious non-active roster states.
bad_status = {
    "CUT",
    "DEV",
    "RET",
    "RES",
    "SUS",
}

roster["status_clean"] = roster["status"].astype(str).str.upper()

roster = roster[
    ~roster["status_clean"].isin(bad_status)
].copy()

# Deduplicate player/team rows.
roster = roster.sort_values(
    ["team", "full_name"]
).drop_duplicates(
    subset=["gsis_id", "full_name"],
    keep="last"
)

print("Roster fantasy players:", len(roster))


# ------------------------------------------------------------
# DEPTH CHART
# ------------------------------------------------------------

depth = pd.read_parquet(
    DV / "raw" / "depth_charts" / "depth_charts_2026.parquet"
)

depth = depth[
    depth["pos_abb"].isin(["QB", "RB", "WR", "TE"])
].copy()

depth["dt"] = pd.to_datetime(
    depth["dt"],
    errors="coerce",
    utc=True
)

depth = depth.sort_values("dt")

# latest recorded depth-chart row per player
depth_latest = depth.drop_duplicates(
    subset=["gsis_id"],
    keep="last"
)

depth_latest = depth_latest[
    [
        "gsis_id",
        "team",
        "pos_abb",
        "pos_slot",
        "pos_rank",
        "dt",
    ]
].rename(
    columns={
        "team": "depth_team",
        "pos_abb": "depth_pos",
        "pos_slot": "depth_slot",
        "pos_rank": "depth_rank",
        "dt": "depth_updated",
    }
)


# ------------------------------------------------------------
# PLAYER DIRECTORY
# ------------------------------------------------------------

players = pd.read_parquet(
    DV / "raw" / "players" / "players.parquet"
)

players = players[
    [
        "gsis_id",
        "display_name",
        "headshot",
        "rookie_season",
        "latest_team",
        "status",
        "years_of_experience",
        "draft_year",
        "draft_round",
        "draft_pick",
    ]
].copy()

players = players.drop_duplicates(
    subset=["gsis_id"],
    keep="last"
)


# ------------------------------------------------------------
# NGS 2025 RECENT PRODUCTION
# ------------------------------------------------------------

passing = pd.read_parquet(
    DV / "raw" / "ngs_passing" / "ngs_passing.parquet"
)
receiving = pd.read_parquet(
    DV / "raw" / "ngs_receiving" / "ngs_receiving.parquet"
)
rushing = pd.read_parquet(
    DV / "raw" / "ngs_rushing" / "ngs_rushing.parquet"
)

passing = passing[
    (passing["season"] == 2025) &
    (passing["season_type"] == "REG")
].copy()

receiving = receiving[
    (receiving["season"] == 2025) &
    (receiving["season_type"] == "REG")
].copy()

rushing = rushing[
    (rushing["season"] == 2025) &
    (rushing["season_type"] == "REG")
].copy()


# NGS contains a week=0 row that is already the full-season total.
# Never add week 0 to the individual weekly rows.
#
# Prefer the official week=0 season summary.
# If a player has no week=0 row, fall back to summing weekly rows.

def season_total_or_weekly_sum(df, value_map, mean_cols=None):
    mean_cols = mean_cols or {}

    season_rows = (
        df[df["week"] == 0]
        .sort_values(["player_gsis_id", "week"])
        .drop_duplicates("player_gsis_id", keep="last")
        .copy()
    )

    weekly = df[df["week"] > 0].copy()

    weekly_aggs = {}

    for out_col, src_col in value_map.items():
        weekly_aggs[out_col] = (src_col, "sum")

    for out_col, src_col in mean_cols.items():
        weekly_aggs[out_col] = (src_col, "mean")

    weekly_agg = (
        weekly.groupby(
            "player_gsis_id",
            as_index=False
        )
        .agg(**weekly_aggs)
    )

    keep = ["player_gsis_id"]

    rename = {}

    for out_col, src_col in value_map.items():
        keep.append(src_col)
        rename[src_col] = out_col

    for out_col, src_col in mean_cols.items():
        keep.append(src_col)
        rename[src_col] = out_col

    season_agg = (
        season_rows[keep]
        .rename(columns=rename)
        .copy()
    )

    # Players with an official season-summary row use it.
    # Weekly aggregation is only a fallback.
    result = weekly_agg.merge(
        season_agg,
        on="player_gsis_id",
        how="outer",
        suffixes=("_weekly", "_season")
    )

    final = pd.DataFrame({
        "player_gsis_id": result["player_gsis_id"]
    })

    for out_col in list(value_map) + list(mean_cols):
        season_col = f"{out_col}_season"
        weekly_col = f"{out_col}_weekly"

        final[out_col] = result[season_col].combine_first(
            result[weekly_col]
        )

    return final


pass_agg = season_total_or_weekly_sum(
    passing,
    {
        "pass_attempts": "attempts",
        "pass_yards": "pass_yards",
        "pass_td": "pass_touchdowns",
        "interceptions": "interceptions",
    }
)

rec_agg = season_total_or_weekly_sum(
    receiving,
    {
        "targets": "targets",
        "receptions": "receptions",
        "rec_yards": "yards",
        "rec_td": "rec_touchdowns",
    },
    {
        "air_yard_share":
            "percent_share_of_intended_air_yards"
    }
)

rush_agg = season_total_or_weekly_sum(
    rushing,
    {
        "rush_attempts": "rush_attempts",
        "rush_yards": "rush_yards",
        "rush_td": "rush_touchdowns",
        "rush_yoe": "rush_yards_over_expected",
    }
)


# ------------------------------------------------------------
# MERGE
# ------------------------------------------------------------

board = roster.merge(
    depth_latest,
    on="gsis_id",
    how="left"
)

board = board.merge(
    players,
    on="gsis_id",
    how="left",
    suffixes=("", "_player")
)

board = board.merge(
    pass_agg,
    left_on="gsis_id",
    right_on="player_gsis_id",
    how="left"
).drop(
    columns=["player_gsis_id"],
    errors="ignore"
)

board = board.merge(
    rec_agg,
    left_on="gsis_id",
    right_on="player_gsis_id",
    how="left"
).drop(
    columns=["player_gsis_id"],
    errors="ignore"
)

board = board.merge(
    rush_agg,
    left_on="gsis_id",
    right_on="player_gsis_id",
    how="left"
).drop(
    columns=["player_gsis_id"],
    errors="ignore"
)

numeric_cols = [
    "pass_attempts",
    "pass_yards",
    "pass_td",
    "interceptions",
    "targets",
    "receptions",
    "rec_yards",
    "rec_td",
    "air_yard_share",
    "rush_attempts",
    "rush_yards",
    "rush_td",
    "rush_yoe",
]

for c in numeric_cols:
    board[c] = pd.to_numeric(
        board[c],
        errors="coerce"
    ).fillna(0)


# ------------------------------------------------------------
# PROVISIONAL HULK FANTASY SCORE
# ------------------------------------------------------------

board["depth_score"] = 0.0

# Lower depth rank is better.
depth_rank = pd.to_numeric(
    board["depth_rank"],
    errors="coerce"
)

board.loc[depth_rank == 1, "depth_score"] = 25
board.loc[depth_rank == 2, "depth_score"] = 16
board.loc[depth_rank == 3, "depth_score"] = 9
board.loc[depth_rank >= 4, "depth_score"] = 3

board["production_score"] = 0.0

# QB
qb = board["position"] == "QB"
board.loc[qb, "production_score"] = (
    board.loc[qb, "pass_yards"] / 180
    + board.loc[qb, "pass_td"] * 2.2
    - board.loc[qb, "interceptions"] * 1.2
    + board.loc[qb, "rush_yards"] / 80
    + board.loc[qb, "rush_td"] * 2.5
)

# RB
rb = board["position"] == "RB"
board.loc[rb, "production_score"] = (
    board.loc[rb, "rush_yards"] / 70
    + board.loc[rb, "rush_td"] * 3
    + board.loc[rb, "targets"] / 5
    + board.loc[rb, "rec_yards"] / 85
    + board.loc[rb, "rec_td"] * 3
)

# WR
wr = board["position"] == "WR"
board.loc[wr, "production_score"] = (
    board.loc[wr, "targets"] / 4
    + board.loc[wr, "rec_yards"] / 65
    + board.loc[wr, "rec_td"] * 3
    + board.loc[wr, "air_yard_share"] / 5
)

# TE
te = board["position"] == "TE"
board.loc[te, "production_score"] = (
    board.loc[te, "targets"] / 4
    + board.loc[te, "rec_yards"] / 60
    + board.loc[te, "rec_td"] * 3.2
    + board.loc[te, "air_yard_share"] / 5
)

board["hulk_score"] = (
    board["depth_score"]
    + board["production_score"]
)

# Rookie/young-player flag
board["rookie_2026"] = (
    pd.to_numeric(
        board["rookie_season"],
        errors="coerce"
    ) == 2026
)

# Rank within position first.
board["position_rank"] = (
    board.groupby("position")["hulk_score"]
    .rank(
        method="first",
        ascending=False
    )
    .astype(int)
)

# Overall draft-value weighting by fantasy position.
position_multiplier = {
    "RB": 1.08,
    "WR": 1.08,
    "TE": 0.94,
    "QB": 0.88,
}

board["overall_score"] = (
    board["hulk_score"]
    * board["position"].map(position_multiplier).fillna(1)
)

board = board.sort_values(
    "overall_score",
    ascending=False
).reset_index(drop=True)

board["overall_rank"] = np.arange(
    1,
    len(board) + 1
)

# Simple tiers, position-specific.
def tier_from_rank(rank, pos):
    cuts = {
        "QB": [4, 10, 18, 28],
        "RB": [8, 20, 36, 55],
        "WR": [10, 24, 42, 65],
        "TE": [4, 10, 18, 28],
    }

    c = cuts.get(pos, [10, 25, 50, 80])

    if rank <= c[0]:
        return 1
    if rank <= c[1]:
        return 2
    if rank <= c[2]:
        return 3
    if rank <= c[3]:
        return 4
    return 5

board["tier"] = [
    tier_from_rank(r, p)
    for r, p in zip(
        board["position_rank"],
        board["position"]
    )
]

# ADP deliberately blank until live source is connected.
board["adp"] = np.nan
board["value_vs_adp"] = np.nan

keep = [
    "overall_rank",
    "position_rank",
    "tier",
    "full_name",
    "position",
    "team",
    "depth_rank",
    "status",
    "rookie_2026",
    "headshot_url",
    "headshot",
    "hulk_score",
    "overall_score",
    "adp",
    "value_vs_adp",
    "pass_yards",
    "pass_td",
    "rush_yards",
    "rush_td",
    "targets",
    "receptions",
    "rec_yards",
    "rec_td",
    "air_yard_share",
]

keep = [
    c for c in keep
    if c in board.columns
]

board = board[keep].copy()

board.to_csv(
    OUT / "FANTASY_CURRENT_BOARD.csv",
    index=False
)

board.to_parquet(
    OUT / "FANTASY_CURRENT_BOARD.parquet",
    index=False
)

print()
print("=" * 76)
print("FANTASY BOARD SUMMARY")
print("=" * 76)
print("Players:", len(board))

for pos in ["QB", "RB", "WR", "TE"]:
    print(
        pos,
        int((board["position"] == pos).sum())
    )

print(
    "Rookies:",
    int(board["rookie_2026"].sum())
)

print(
    "Top 250 available:",
    min(250, len(board))
)

print("ADP: PENDING LIVE SOURCE")
print("RESULT: PASS")
print("=" * 76)
