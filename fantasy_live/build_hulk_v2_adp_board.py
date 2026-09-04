from pathlib import Path
import re
import unicodedata
import numpy as np
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")

HULK = ROOT / "fantasy_live/derived/FANTASY_HULK_PPR_V2.csv"
ADP = ROOT / "fantasy_live/derived/FANTASY_HULK_ADP_CONSENSUS.csv"
OUT = ROOT / "fantasy_live/derived"

def norm(v):
    if pd.isna(v):
        return ""

    s = unicodedata.normalize("NFKD", str(v))
    s = "".join(
        c for c in s
        if not unicodedata.combining(c)
    ).lower()

    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


print("=" * 80)
print("SPORTS HULK V2 + MULTI-SOURCE ADP")
print("=" * 80)

hulk = pd.read_csv(HULK)
adp = pd.read_csv(ADP)

hulk["_key"] = hulk["full_name"].map(norm)
adp["_key"] = adp["full_name"].map(norm)

# Keep only ADP / market columns from prior consensus file.
adp_cols = [
    "_key",
    "sleeper_ppr_adp",
    "sleeper_half_adp",
    "sleeper_std_adp",
    "espn_adp",
    "espn_ppr_room_rank",
    "yahoo_adp",
    "cbs_adp",
    "cbs_rank",
    "adp_source_count",
    "consensus_adp",
    "consensus_adp_median",
    "market_adp_low",
    "market_adp_high",
    "platform_spread",
]

adp_cols = [
    c for c in adp_cols
    if c in adp.columns
]

board = hulk.merge(
    adp[adp_cols],
    on="_key",
    how="left"
)

# Prefer Sleeper's current 2026 team where available.
board["roster_team"] = board["team"]

board["current_team"] = (
    board["sleeper_team"]
    .replace("", np.nan)
    .combine_first(board["team"])
)

team_alias = {
    "LA": "LAR",
    "LAR": "LAR",
}

roster_norm = (
    board["team"]
    .astype(str)
    .replace(team_alias)
)

sleeper_norm = (
    board["sleeper_team"]
    .astype(str)
    .replace(team_alias)
)

board["team_conflict"] = (
    board["sleeper_team"].notna()
    & board["team"].notna()
    & (sleeper_norm != roster_norm)
)

# Hulk value: positive means Hulk ranks player earlier than market.
board["hulk_value_vs_consensus"] = (
    board["consensus_adp"]
    - board["hulk_v2_rank"]
)

board["hulk_value_vs_espn_room"] = (
    board["espn_ppr_room_rank"]
    - board["hulk_v2_rank"]
)

board["hulk_value_vs_sleeper"] = (
    board["sleeper_ppr_adp"]
    - board["hulk_v2_rank"]
)

board["hulk_value_vs_yahoo"] = (
    board["yahoo_adp"]
    - board["hulk_v2_rank"]
)

board["hulk_value_vs_cbs"] = (
    board["cbs_adp"]
    - board["hulk_v2_rank"]
)

# Best place to draft based on deepest market position.
platform_map = {
    "Sleeper": "sleeper_ppr_adp",
    "ESPN": "espn_ppr_room_rank",
    "Yahoo": "yahoo_adp",
    "CBS": "cbs_adp",
}

best_platform = []
best_value = []

for _, row in board.iterrows():
    values = {}

    for platform, col in platform_map.items():
        v = row.get(col)

        if pd.notna(v) and pd.notna(row["hulk_v2_rank"]):
            values[platform] = v - row["hulk_v2_rank"]

    if values:
        winner = max(values, key=values.get)
        best_platform.append(winner)
        best_value.append(values[winner])
    else:
        best_platform.append(np.nan)
        best_value.append(np.nan)

board["best_value_platform"] = best_platform
board["best_platform_value"] = best_value

# Draft action layer.
def action(row):
    consensus = row.get("hulk_value_vs_consensus")
    best = row.get("best_platform_value")

    if pd.isna(consensus):
        return "NO MARKET"

    if consensus >= 18:
        return "PLATFORM STEAL"

    if consensus >= 8:
        return "VALUE"

    if consensus <= -18:
        return "REACH / WAIT"

    if best is not None and pd.notna(best) and best >= 12:
        return "WAIT"

    return "FAIR VALUE"

board["draft_action"] = board.apply(
    action,
    axis=1
)

board = board.sort_values(
    "hulk_v2_rank"
).reset_index(drop=True)

board.to_csv(
    OUT / "FANTASY_HULK_V2_ADP_BOARD.csv",
    index=False
)

board.to_parquet(
    OUT / "FANTASY_HULK_V2_ADP_BOARD.parquet",
    index=False
)

print()
print("ROWS:", len(board))

print(
    "3+ ADP SOURCES:",
    int((board["adp_source_count"] >= 3).sum())
)

print(
    "ALL 4 SOURCES:",
    int((board["adp_source_count"] == 4).sum())
)

print(
    "TEAM CONFLICTS:",
    int(board["team_conflict"].sum())
)

print()
print("=" * 80)
print("TOP 40 HULK V2 + MARKET")
print("=" * 80)

cols = [
    "hulk_v2_rank",
    "hulk_v2_position_rank",
    "full_name",
    "current_team",
    "position",
    "proj_ppr_points",
    "sleeper_ppr_adp",
    "espn_adp",
    "espn_ppr_room_rank",
    "yahoo_adp",
    "cbs_adp",
    "consensus_adp",
    "hulk_value_vs_consensus",
    "best_value_platform",
    "best_platform_value",
    "draft_action",
]

print(
    board.head(40)[cols]
    .to_string(index=False)
)

print()
print("=" * 80)
print("BIGGEST TEAM CONFLICTS")
print("=" * 80)

conflicts = board[
    board["team_conflict"]
][
    [
        "full_name",
        "roster_team",
        "sleeper_team",
        "position",
        "hulk_v2_rank",
    ]
].head(30)

print(conflicts.to_string(index=False))

print()
print("RESULT: PASS")
