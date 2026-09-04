from pathlib import Path
import re
import unicodedata
import requests
import numpy as np
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")

OLD_BOARD = (
    ROOT /
    "fantasy_vault/derived/FANTASY_CURRENT_BOARD.csv"
)

OUT_DIR = ROOT / "fantasy_live/derived"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEASON = 2026


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def norm(v):
    if pd.isna(v):
        return ""

    s = unicodedata.normalize(
        "NFKD",
        str(v)
    )

    s = "".join(
        x for x in s
        if not unicodedata.combining(x)
    )

    s = s.lower()

    s = re.sub(
        r"[^a-z0-9 ]+",
        " ",
        s
    )

    s = re.sub(
        r"\b(jr|sr|ii|iii|iv|v)\b",
        " ",
        s
    )

    return re.sub(
        r"\s+",
        " ",
        s
    ).strip()


# ------------------------------------------------------------
# LOAD HULK ROSTER FOUNDATION
# ------------------------------------------------------------

board = pd.read_csv(
    OLD_BOARD
)

board["_name_key"] = (
    board["full_name"]
    .map(norm)
)

board["_pos"] = (
    board["position"]
    .astype(str)
    .str.upper()
)


# ------------------------------------------------------------
# GET SLEEPER 2026 PROJECTIONS
# ------------------------------------------------------------

print("=" * 80)
print("SPORTS HULK PPR MODEL V2")
print("=" * 80)

url = (
    f"https://api.sleeper.com/"
    f"projections/nfl/{SEASON}"
)

r = requests.get(
    url,
    params={
        "season_type": "regular"
    },
    timeout=40
)

print("SLEEPER HTTP:", r.status_code)

if r.status_code != 200:
    raise SystemExit("SLEEPER PROJECTION FETCH FAILED")

payload = r.json()

rows = []

for item in payload:

    player = item.get("player") or {}
    stats = item.get("stats") or {}

    name = (
        player.get("full_name")
        or player.get("name")
        or (
            str(player.get("first_name") or "")
            + " "
            + str(player.get("last_name") or "")
        ).strip()
    )

    pos = (
        player.get("position")
        or (
            player.get("fantasy_positions") or [None]
        )[0]
    )

    if pos not in {
        "QB", "RB", "WR", "TE"
    }:
        continue

    pts = pd.to_numeric(
        stats.get("pts_ppr"),
        errors="coerce"
    )

    # Only use real fantasy projection rows.
    if pd.isna(pts):
        continue

    rows.append({
        "sleeper_player_id":
            item.get("player_id"),

        "sleeper_name":
            name,

        "_name_key":
            norm(name),

        "sleeper_team":
            item.get("team"),

        "_pos":
            pos,

        "proj_ppr_points":
            pts,

        "proj_games":
            pd.to_numeric(
                stats.get("gp"),
                errors="coerce"
            ),

        "proj_pass_yd":
            pd.to_numeric(
                stats.get("pass_yd"),
                errors="coerce"
            ),

        "proj_pass_td":
            pd.to_numeric(
                stats.get("pass_td"),
                errors="coerce"
            ),

        "proj_pass_int":
            pd.to_numeric(
                stats.get("pass_int"),
                errors="coerce"
            ),

        "proj_rush_att":
            pd.to_numeric(
                stats.get("rush_att"),
                errors="coerce"
            ),

        "proj_rush_yd":
            pd.to_numeric(
                stats.get("rush_yd"),
                errors="coerce"
            ),

        "proj_rush_td":
            pd.to_numeric(
                stats.get("rush_td"),
                errors="coerce"
            ),

        "proj_rec":
            pd.to_numeric(
                stats.get("rec"),
                errors="coerce"
            ),

        "proj_rec_yd":
            pd.to_numeric(
                stats.get("rec_yd"),
                errors="coerce"
            ),

        "proj_rec_td":
            pd.to_numeric(
                stats.get("rec_td"),
                errors="coerce"
            ),
    })


proj = pd.DataFrame(rows)

proj = (
    proj
    .sort_values(
        "proj_ppr_points",
        ascending=False
    )
    .drop_duplicates(
        subset=[
            "_name_key",
            "_pos"
        ],
        keep="first"
    )
)

print(
    "SLEEPER PPR PROJECTION PLAYERS:",
    len(proj)
)


# ------------------------------------------------------------
# MERGE
# Exact normalized name + position first
# ------------------------------------------------------------

board = board.merge(
    proj,
    on=[
        "_name_key",
        "_pos"
    ],
    how="left"
)

print(
    "HULK PLAYERS WITH PROJECTION:",
    board["proj_ppr_points"]
    .notna()
    .sum(),
    "/",
    len(board)
)


# ------------------------------------------------------------
# DEPTH ROLE ADJUSTMENT
#
# Depth is a modifier, not the model.
# ------------------------------------------------------------

depth = pd.to_numeric(
    board["depth_rank"],
    errors="coerce"
)

board["role_adjustment"] = 0.0

board.loc[
    depth == 1,
    "role_adjustment"
] = 6.0

board.loc[
    depth == 2,
    "role_adjustment"
] = 2.0

board.loc[
    depth == 3,
    "role_adjustment"
] = 0.0

board.loc[
    depth >= 4,
    "role_adjustment"
] = -2.0


# ------------------------------------------------------------
# VALUE OVER REPLACEMENT
#
# Default 12-team, 1QB PPR baseline.
#
# QB12
# RB30
# WR36
# TE12
# ------------------------------------------------------------

replacement_slot = {
    "QB": 12,
    "RB": 30,
    "WR": 36,
    "TE": 12,
}

replacement_points = {}

for pos, slot in replacement_slot.items():

    x = (
        board[
            (board["_pos"] == pos) &
            board["proj_ppr_points"].notna()
        ]
        .sort_values(
            "proj_ppr_points",
            ascending=False
        )
    )

    if len(x) >= slot:

        replacement_points[pos] = (
            x.iloc[slot - 1]
            ["proj_ppr_points"]
        )

    elif len(x):

        replacement_points[pos] = (
            x["proj_ppr_points"]
            .min()
        )

    else:

        replacement_points[pos] = 0


print()
print("REPLACEMENT BASELINES")

for pos, pts in replacement_points.items():
    print(
        f"{pos}: {pts:.1f} PPR pts"
    )


board["replacement_points"] = (
    board["_pos"]
    .map(replacement_points)
)

board["vorp"] = (
    board["proj_ppr_points"]
    - board["replacement_points"]
)


# ------------------------------------------------------------
# POSITION SCARCITY
#
# Small adjustments only.
# Main signal remains VORP.
# ------------------------------------------------------------

scarcity_multiplier = {
    "RB": 1.08,
    "WR": 1.00,
    "TE": 1.05,
    "QB": 0.90,
}

board["scarcity_multiplier"] = (
    board["_pos"]
    .map(scarcity_multiplier)
    .fillna(1.0)
)


# ------------------------------------------------------------
# HULK V2 SCORE
#
# NO ADP IS USED HERE.
# ------------------------------------------------------------

board["hulk_v2_score"] = (
    board["vorp"]
    * board["scarcity_multiplier"]
    + board["role_adjustment"]
)


# Players without a 2026 projection
# remain below players with real projections.
board.loc[
    board["proj_ppr_points"].isna(),
    "hulk_v2_score"
] = -999


# ------------------------------------------------------------
# POSITION RANK
# ------------------------------------------------------------

board["hulk_v2_position_rank"] = (
    board.groupby("_pos")[
        "hulk_v2_score"
    ]
    .rank(
        method="first",
        ascending=False
    )
    .astype(int)
)


# ------------------------------------------------------------
# OVERALL RANK
# ------------------------------------------------------------

board = (
    board
    .sort_values(
        [
            "hulk_v2_score",
            "proj_ppr_points"
        ],
        ascending=[
            False,
            False
        ]
    )
    .reset_index(drop=True)
)

board["hulk_v2_rank"] = (
    np.arange(
        1,
        len(board) + 1
    )
)


# ------------------------------------------------------------
# TIERS
# Position-specific
# ------------------------------------------------------------

def tier_from_rank(r):

    if r <= 5:
        return 1
    if r <= 12:
        return 2
    if r <= 24:
        return 3
    if r <= 36:
        return 4
    if r <= 60:
        return 5

    return 6


board["hulk_v2_tier"] = (
    board[
        "hulk_v2_position_rank"
    ]
    .map(tier_from_rank)
)


# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

keep_extra = [
    "sleeper_player_id",
    "sleeper_name",
    "sleeper_team",
    "proj_ppr_points",
    "proj_games",
    "proj_pass_yd",
    "proj_pass_td",
    "proj_pass_int",
    "proj_rush_att",
    "proj_rush_yd",
    "proj_rush_td",
    "proj_rec",
    "proj_rec_yd",
    "proj_rec_td",
    "replacement_points",
    "vorp",
    "role_adjustment",
    "scarcity_multiplier",
    "hulk_v2_score",
    "hulk_v2_rank",
    "hulk_v2_position_rank",
    "hulk_v2_tier",
]

drop_helpers = [
    "_name_key",
    "_pos",
]

out = board.drop(
    columns=drop_helpers,
    errors="ignore"
)

out.to_csv(
    OUT_DIR /
    "FANTASY_HULK_PPR_V2.csv",
    index=False
)

out.to_parquet(
    OUT_DIR /
    "FANTASY_HULK_PPR_V2.parquet",
    index=False
)


# ------------------------------------------------------------
# AUDIT
# ------------------------------------------------------------

print()
print("=" * 80)
print("HULK V2 TOP 50 POSITION MIX")
print("=" * 80)

print(
    out.nsmallest(
        50,
        "hulk_v2_rank"
    )["position"]
    .value_counts()
    .to_string()
)

print()
print("=" * 80)
print("HULK V2 TOP 40")
print("=" * 80)

cols = [
    "hulk_v2_rank",
    "hulk_v2_position_rank",
    "full_name",
    "team",
    "position",
    "proj_ppr_points",
    "replacement_points",
    "vorp",
    "role_adjustment",
    "hulk_v2_score",
]

print(
    out.nsmallest(
        40,
        "hulk_v2_rank"
    )[cols]
    .to_string(index=False)
)

print()
print("RESULT: PASS")
