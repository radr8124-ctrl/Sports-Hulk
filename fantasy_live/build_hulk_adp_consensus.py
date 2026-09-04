from pathlib import Path
import re
import unicodedata
from difflib import SequenceMatcher
import numpy as np
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")

HULK_FILE = ROOT / "fantasy_vault" / "derived" / "FANTASY_CURRENT_BOARD.csv"
SRC_DIR = ROOT / "fantasy_live" / "multisource"
OUT_DIR = ROOT / "fantasy_live" / "derived"

OUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def norm(v):
    if pd.isna(v):
        return ""

    s = unicodedata.normalize("NFKD", str(v))
    s = "".join(
        ch for ch in s
        if not unicodedata.combining(ch)
    ).lower()

    s = s.replace("&", " and ")

    s = re.sub(r"[^a-z0-9 ]+", " ", s)

    # Suffixes create lots of false non-matches:
    # James Cook / James Cook III
    # Marvin Harrison / Marvin Harrison Jr.
    s = re.sub(
        r"\b(jr|sr|ii|iii|iv|v)\b",
        " ",
        s
    )

    return re.sub(r"\s+", " ", s).strip()


def find_col(df, candidates):
    lower = {
        str(c).lower(): c
        for c in df.columns
    }

    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]

    return None


def num(v):
    return pd.to_numeric(v, errors="coerce")


def similarity(a, b):
    return SequenceMatcher(
        None,
        norm(a),
        norm(b)
    ).ratio()


# ============================================================
# LOAD HULK BOARD
# ============================================================

print("=" * 80)
print("SPORTS HULK MULTI-SOURCE ADP CONSENSUS")
print("=" * 80)

hulk = pd.read_csv(HULK_FILE)

print("HULK ROWS:", len(hulk))
print("HULK COLUMNS:")
print(" | ".join(map(str, hulk.columns)))

player_col = find_col(
    hulk,
    [
        "player",
        "player_name",
        "full_name",
        "name",
    ]
)

team_col = find_col(
    hulk,
    [
        "team",
        "club",
        "current_team",
    ]
)

pos_col = find_col(
    hulk,
    [
        "position",
        "pos",
        "position_group",
    ]
)

rank_col = find_col(
    hulk,
    [
        "overall_rank",
        "hulk_rank",
        "rank",
        "fantasy_rank",
    ]
)

if not player_col:
    raise SystemExit("NO HULK PLAYER COLUMN FOUND")

if not pos_col:
    raise SystemExit("NO HULK POSITION COLUMN FOUND")

if not rank_col:
    raise SystemExit("NO HULK RANK COLUMN FOUND")

print()
print("DETECTED:")
print("PLAYER:", player_col)
print("TEAM:", team_col)
print("POSITION:", pos_col)
print("HULK RANK:", rank_col)

board = hulk.copy()

board["_name_key"] = board[player_col].map(norm)
board["_position"] = (
    board[pos_col]
    .astype(str)
    .str.upper()
    .str.strip()
)

if team_col:
    board["_team"] = (
        board[team_col]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )
else:
    board["_team"] = ""

board["hulk_rank"] = num(board[rank_col])


# ============================================================
# LOAD SOURCES
# ============================================================

sleeper = pd.read_csv(
    SRC_DIR / "SLEEPER_ADP.csv"
)

espn = pd.read_csv(
    SRC_DIR / "ESPN_ADP.csv"
)

yahoo = pd.read_csv(
    SRC_DIR / "YAHOO_ADP.csv"
)

cbs = pd.read_csv(
    SRC_DIR / "CBS_ADP_RAW.csv"
)

for df in [sleeper, espn, yahoo]:
    df["_name_key"] = df["player"].map(norm)

    if "position" in df.columns:
        df["_position"] = (
            df["position"]
            .astype(str)
            .str.upper()
            .str.strip()
        )

    if "team" in df.columns:
        df["_team"] = (
            df["team"]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )


# ============================================================
# MATCH STANDARD SOURCES
# ============================================================

def match_source(
    board,
    source,
    source_name,
    value_columns
):

    matched = {}
    methods = {}

    # Prevent reusing one source row for multiple Hulk players
    used = set()

    # --------------------------------------------------------
    # 1. EXACT normalized name + position
    # --------------------------------------------------------

    lookup = {}

    for idx, row in source.iterrows():
        key = (
            row.get("_name_key", ""),
            row.get("_position", "")
        )

        lookup.setdefault(
            key,
            []
        ).append(idx)

    for bi, brow in board.iterrows():

        key = (
            brow["_name_key"],
            brow["_position"]
        )

        choices = lookup.get(key, [])

        choices = [
            i for i in choices
            if i not in used
        ]

        if len(choices) == 1:
            si = choices[0]

            matched[bi] = si
            methods[bi] = "exact_name_pos"
            used.add(si)

    # --------------------------------------------------------
    # 2. EXACT name, team preference
    # --------------------------------------------------------

    for bi, brow in board.iterrows():

        if bi in matched:
            continue

        candidates = source[
            source["_name_key"]
            == brow["_name_key"]
        ]

        if candidates.empty:
            continue

        if (
            "_team" in source.columns
            and brow["_team"]
        ):
            team_hits = candidates[
                candidates["_team"]
                == brow["_team"]
            ]

            if len(team_hits) == 1:
                si = team_hits.index[0]

                if si not in used:
                    matched[bi] = si
                    methods[bi] = "exact_name_team"
                    used.add(si)
                    continue

        free = [
            i for i in candidates.index
            if i not in used
        ]

        if len(free) == 1:
            si = free[0]

            matched[bi] = si
            methods[bi] = "exact_name"
            used.add(si)

    # --------------------------------------------------------
    # 3. CONSERVATIVE fuzzy
    # Position must agree.
    # Team agreement gets bonus.
    # --------------------------------------------------------

    for bi, brow in board.iterrows():

        if bi in matched:
            continue

        candidates = source[
            source["_position"]
            == brow["_position"]
        ]

        if candidates.empty:
            continue

        best_idx = None
        best_score = 0

        for si, srow in candidates.iterrows():

            if si in used:
                continue

            score = similarity(
                brow[player_col],
                srow["player"]
            )

            if (
                "_team" in source.columns
                and brow["_team"]
                and srow.get("_team", "")
                == brow["_team"]
            ):
                score += 0.04

            if score > best_score:
                best_score = score
                best_idx = si

        # High bar so we do NOT force bad matches
        if (
            best_idx is not None
            and best_score >= 0.91
        ):
            matched[bi] = best_idx
            methods[bi] = (
                f"fuzzy_{best_score:.3f}"
            )
            used.add(best_idx)

    # --------------------------------------------------------
    # WRITE VALUES
    # --------------------------------------------------------

    board[
        f"{source_name}_match"
    ] = "unmatched"

    board[
        f"{source_name}_source_player"
    ] = pd.Series(
        [None] * len(board),
        index=board.index,
        dtype="object"
    )

    for dest in value_columns:
        board[dest] = np.nan

    for bi, si in matched.items():

        row = source.loc[si]

        board.at[
            bi,
            f"{source_name}_match"
        ] = methods[bi]

        board.at[
            bi,
            f"{source_name}_source_player"
        ] = row.get("player")

        for dest, src in value_columns.items():

            board.at[
                bi,
                dest
            ] = num(
                row.get(src)
            )

    return board


board = match_source(
    board,
    sleeper,
    "sleeper",
    {
        "sleeper_ppr_adp":
            "sleeper_ppr_adp",

        "sleeper_half_adp":
            "sleeper_half_adp",

        "sleeper_std_adp":
            "sleeper_std_adp",
    }
)

board = match_source(
    board,
    espn,
    "espn",
    {
        "espn_adp":
            "espn_adp",

        "espn_ppr_room_rank":
            "espn_ppr_room_rank",
    }
)

board = match_source(
    board,
    yahoo,
    "yahoo",
    {
        "yahoo_adp":
            "yahoo_adp",
    }
)


# ============================================================
# CBS MATCHING
#
# CBS raw cells actually contain the full player name,
# position and team, plus sometimes injury text.
#
# Example:
# J. Chase WR CIN Knee... Ja'Marr Chase WR CIN Knee...
#
# Instead of trying to parse the ugly cell first, match
# Hulk's normalized full name INSIDE the normalized CBS text.
# ============================================================

board["cbs_match"] = "unmatched"
board["cbs_source_player"] = pd.Series(
    [None] * len(board),
    index=board.index,
    dtype="object"
)
board["cbs_adp"] = np.nan
board["cbs_rank"] = np.nan

cbs["_raw_key"] = (
    cbs["cbs_raw_player"]
    .fillna("")
    .map(norm)
)

used_cbs = set()

for bi, brow in board.iterrows():

    name_key = brow["_name_key"]

    if len(name_key) < 4:
        continue

    candidates = []

    for ci, crow in cbs.iterrows():

        if ci in used_cbs:
            continue

        raw = crow["_raw_key"]

        # full normalized Hulk name appears
        # inside CBS player cell
        if name_key in raw:
            candidates.append(ci)

    if len(candidates) == 1:

        ci = candidates[0]
        crow = cbs.loc[ci]

        board.at[
            bi,
            "cbs_match"
        ] = "name_inside_cbs"

        board.at[
            bi,
            "cbs_source_player"
        ] = crow["cbs_raw_player"]

        board.at[
            bi,
            "cbs_adp"
        ] = num(crow["cbs_adp"])

        board.at[
            bi,
            "cbs_rank"
        ] = num(crow["cbs_rank"])

        used_cbs.add(ci)


# ============================================================
# CONSENSUS
# ============================================================

adp_cols = [
    "sleeper_ppr_adp",
    "espn_adp",
    "yahoo_adp",
    "cbs_adp",
]

for c in adp_cols:
    board[c] = pd.to_numeric(
        board[c],
        errors="coerce"
    )

board["adp_source_count"] = (
    board[adp_cols]
    .notna()
    .sum(axis=1)
)

# Mean gives each platform equal weight.
board["consensus_adp"] = (
    board[adp_cols]
    .mean(axis=1)
)

# Median protects against one weird source.
board["consensus_adp_median"] = (
    board[adp_cols]
    .median(axis=1)
)

board["market_adp_low"] = (
    board[adp_cols]
    .min(axis=1)
)

board["market_adp_high"] = (
    board[adp_cols]
    .max(axis=1)
)

board["platform_spread"] = (
    board["market_adp_high"]
    - board["market_adp_low"]
)

# Positive = Hulk likes player MORE than market.
#
# Example:
# Hulk #20
# Consensus ADP #35
# Value = +15
board["hulk_value_vs_consensus"] = (
    board["consensus_adp"]
    - board["hulk_rank"]
)

# ESPN draft-room-specific value
board["hulk_value_vs_espn_room"] = (
    board["espn_ppr_room_rank"]
    - board["hulk_rank"]
)


# ============================================================
# FIND PLATFORM WITH MOST ROOM
# ============================================================

platform_cols = {
    "Sleeper":
        "sleeper_ppr_adp",
    "ESPN":
        "espn_adp",
    "Yahoo":
        "yahoo_adp",
    "CBS":
        "cbs_adp",
}

best_platform = []
best_platform_value = []

for _, row in board.iterrows():

    values = {}

    for platform, col in platform_cols.items():

        v = row.get(col)

        if pd.notna(v) and pd.notna(
            row["hulk_rank"]
        ):
            values[platform] = (
                v - row["hulk_rank"]
            )

    if values:

        winner = max(
            values,
            key=values.get
        )

        best_platform.append(winner)
        best_platform_value.append(
            values[winner]
        )

    else:

        best_platform.append(np.nan)
        best_platform_value.append(np.nan)

board[
    "best_value_platform"
] = best_platform

board[
    "best_platform_value"
] = best_platform_value


# ============================================================
# OUTPUT
# ============================================================

out = (
    OUT_DIR /
    "FANTASY_HULK_ADP_CONSENSUS.csv"
)

board.to_csv(
    out,
    index=False
)

board.to_parquet(
    OUT_DIR /
    "FANTASY_HULK_ADP_CONSENSUS.parquet",
    index=False
)


# ============================================================
# MATCH AUDIT
# ============================================================

print()
print("=" * 80)
print("MATCH AUDIT")
print("=" * 80)

for source in [
    "sleeper",
    "espn",
    "yahoo",
    "cbs",
]:

    col = f"{source}_match"

    matched = (
        board[col] != "unmatched"
    ).sum()

    print(
        f"{source.upper():8s}: "
        f"{matched:3d} / {len(board)} "
        f"({matched / len(board) * 100:.1f}%)"
    )

print()
print(
    "3+ ADP SOURCES:",
    int(
        (
            board["adp_source_count"]
            >= 3
        ).sum()
    )
)

print(
    "ALL 4 SOURCES:",
    int(
        (
            board["adp_source_count"]
            == 4
        ).sum()
    )
)

print(
    "NO ADP SOURCE:",
    int(
        (
            board["adp_source_count"]
            == 0
        ).sum()
    )
)


# ============================================================
# TOP CONSENSUS SAMPLE
# ============================================================

print()
print("=" * 80)
print("TOP 40 CONSENSUS")
print("=" * 80)

show = [
    rank_col,
    player_col,
]

if team_col:
    show.append(team_col)

show += [
    pos_col,
    "sleeper_ppr_adp",
    "espn_adp",
    "espn_ppr_room_rank",
    "yahoo_adp",
    "cbs_adp",
    "consensus_adp",
    "adp_source_count",
    "hulk_value_vs_consensus",
    "best_value_platform",
]

sample = (
    board[
        board[
            "adp_source_count"
        ] >= 2
    ]
    .sort_values(
        "consensus_adp"
    )
    .head(40)
)

print(
    sample[show]
    .to_string(index=False)
)

print()
print("OUTPUT:", out)
print("RESULT: PASS")
