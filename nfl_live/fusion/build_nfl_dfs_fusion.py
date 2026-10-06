from pathlib import Path
from datetime import datetime, timezone
import json
import re

import numpy as np
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")

QUALITY = (
    ROOT
    / "nfl_live"
    / "multisource"
    / "quality"
)

OUT = (
    ROOT
    / "nfl_live"
    / "fusion"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)

PP_FILE = (
    QUALITY
    / "NFL_PRIZEPICKS_ALL_PAGED.csv"
)

EDGE_FILE = (
    QUALITY
    / "NFL_DFS_EDGES_ALL_PAGED.csv"
)

HIST_FILE = (
    ROOT
    / "prop_intelligence"
    / "derived"
    / "HULK_PROP_SIGNALS.csv"
)

NOW = datetime.now(timezone.utc)


def norm_text(value):
    value = str(value or "").strip().lower()

    value = re.sub(
        r"[^a-z0-9]+",
        "",
        value,
    )

    return value


def num(series):
    return pd.to_numeric(
        series,
        errors="coerce",
    )


if not PP_FILE.exists():
    raise SystemExit(
        "PrizePicks paged audit file missing."
    )

if not EDGE_FILE.exists():
    raise SystemExit(
        "DFS edge paged audit file missing."
    )


# ==================================================
# LOAD PRIZEPICKS
# ==================================================

pp = pd.read_csv(
    PP_FILE,
    low_memory=False,
)

pp["start"] = pd.to_datetime(
    pp["start"],
    utc=True,
    errors="coerce",
)

pp["line"] = num(
    pp["line"]
)

pp["period"] = (
    pp["period"]
    .fillna("")
    .astype(str)
    .str.upper()
    .str.strip()
)

pp["side"] = (
    pp["side"]
    .fillna("")
    .astype(str)
    .str.upper()
    .str.strip()
)

pp["market_subtype"] = (
    pp["market_subtype"]
    .fillna("")
    .astype(str)
    .str.upper()
    .str.strip()
)

pp["suspended"] = (
    pp["suspended"]
    .fillna(False)
    .astype(str)
    .str.lower()
    .isin(
        ["true", "1", "yes"]
    )
)

pp["player_key"] = (
    pp["player"]
    .map(norm_text)
)

pp["line_key"] = (
    pp["line"]
    .round(3)
)


# ==================================================
# HARD SAFETY FILTERS
# ==================================================

pp_live = pp[
    pp["start"].notna()
    & (
        pp["start"]
        >= pd.Timestamp(NOW)
    )
    & (
        pp["period"] == "FULL"
    )
    & (
        pp["suspended"] == False
    )
    & pp["player_key"].ne("")
    & pp["market_subtype"].ne("")
    & pp["side"].isin(
        ["OVER", "UNDER"]
    )
    & pp["line"].notna()
].copy()


# No quarter / half props allowed through.
bad_periods = {
    "1Q",
    "2Q",
    "3Q",
    "4Q",
    "1H",
    "2H",
}

assert not (
    pp_live["period"]
    .isin(bad_periods)
    .any()
)


# ==================================================
# LOAD DFS EDGE DATA
# ==================================================

edges = pd.read_csv(
    EDGE_FILE,
    low_memory=False,
)

edges["start"] = pd.to_datetime(
    edges["start"],
    utc=True,
    errors="coerce",
)

edges["line"] = num(
    edges["line"]
)

edges["book_probability"] = num(
    edges["book_probability"]
)

edges["period"] = (
    edges["period"]
    .fillna("")
    .astype(str)
    .str.upper()
    .str.strip()
)

edges["side"] = (
    edges["side"]
    .fillna("")
    .astype(str)
    .str.upper()
    .str.strip()
)

edges["market"] = (
    edges["market"]
    .fillna("")
    .astype(str)
    .str.upper()
    .str.strip()
)

edges["dfs_source"] = (
    edges["dfs_source"]
    .fillna("")
    .astype(str)
    .str.lower()
    .str.strip()
)

edges["book_source"] = (
    edges["book_source"]
    .fillna("")
    .astype(str)
    .str.lower()
    .str.strip()
)

edges["player_key"] = (
    edges["player"]
    .map(norm_text)
)

edges["line_key"] = (
    edges["line"]
    .round(3)
)


edges_live = edges[
    edges["start"].notna()
    & (
        edges["start"]
        >= pd.Timestamp(NOW)
    )
    & (
        edges["period"] == "FULL"
    )
    & edges["player_key"].ne("")
    & edges["market"].ne("")
    & edges["side"].isin(
        ["OVER", "UNDER"]
    )
    & edges["line"].notna()
    & edges[
        "book_probability"
    ].notna()
].copy()


# ==================================================
# BUILD CROSS-DFS SUPPORT
# ==================================================

group_cols = [
    "event_id",
    "player_key",
    "market",
    "period",
    "side",
    "line_key",
]

support = (
    edges_live
    .groupby(
        group_cols,
        dropna=False,
    )
    .agg(
        dfs_source_count=(
            "dfs_source",
            "nunique",
        ),
        book_source_count=(
            "book_source",
            "nunique",
        ),
        book_probability_median=(
            "book_probability",
            "median",
        ),
        book_probability_max=(
            "book_probability",
            "max",
        ),
        book_probability_min=(
            "book_probability",
            "min",
        ),
        edge_rows=(
            "book_probability",
            "size",
        ),
        dfs_sources=(
            "dfs_source",
            lambda x: ",".join(
                sorted(
                    set(
                        str(v)
                        for v in x
                        if str(v)
                    )
                )
            ),
        ),
        book_sources=(
            "book_source",
            lambda x: ",".join(
                sorted(
                    set(
                        str(v)
                        for v in x
                        if str(v)
                    )
                )
            ),
        ),
    )
    .reset_index()
)


# ==================================================
# PRIZEPICKS-SPECIFIC EDGE
# ==================================================

pp_edges = edges_live[
    edges_live[
        "dfs_source"
    ].eq("prizepicks")
].copy()

pp_edge_best = (
    pp_edges
    .sort_values(
        "book_probability",
        ascending=False,
    )
    .drop_duplicates(
        subset=group_cols,
        keep="first",
    )
)

pp_edge_best = pp_edge_best[
    group_cols
    + [
        "book_source",
        "book_probability",
    ]
].rename(
    columns={
        "book_source":
            "pp_reference_book",
        "book_probability":
            "pp_book_implied_support",
    }
)


# ==================================================
# JOIN PRIZEPICKS TO EDGE EVIDENCE
# ==================================================

board = pp_live.merge(
    support,
    left_on=[
        "event_id",
        "player_key",
        "market_subtype",
        "period",
        "side",
        "line_key",
    ],
    right_on=[
        "event_id",
        "player_key",
        "market",
        "period",
        "side",
        "line_key",
    ],
    how="left",
)

board = board.merge(
    pp_edge_best,
    left_on=[
        "event_id",
        "player_key",
        "market_subtype",
        "period",
        "side",
        "line_key",
    ],
    right_on=[
        "event_id",
        "player_key",
        "market",
        "period",
        "side",
        "line_key",
    ],
    how="left",
    suffixes=(
        "",
        "_ppedge",
    ),
)


# ==================================================
# OPTIONAL HISTORICAL HULK CONTEXT
# ==================================================

historical_cols = [
    "l3",
    "l5",
    "l10",
    "l20",
    "season",
    "h2h",
    "recent_avg",
    "season_avg",
]

for c in historical_cols:
    board[c] = np.nan

if HIST_FILE.exists():

    try:
        hist = pd.read_csv(
            HIST_FILE,
            low_memory=False,
        )

        if (
            "player" in hist.columns
            and "canonical_market"
            in hist.columns
        ):

            hist["player_key"] = (
                hist["player"]
                .map(norm_text)
            )

            hist[
                "canonical_market"
            ] = (
                hist[
                    "canonical_market"
                ]
                .fillna("")
                .astype(str)
                .str.upper()
                .str.strip()
            )

            keep = [
                "player_key",
                "canonical_market",
            ]

            for c in historical_cols:
                if c in hist.columns:
                    keep.append(c)

            h = (
                hist[keep]
                .drop_duplicates(
                    subset=[
                        "player_key",
                        "canonical_market",
                    ],
                    keep="first",
                )
            )

            board = board.merge(
                h,
                left_on=[
                    "player_key",
                    "market_subtype",
                ],
                right_on=[
                    "player_key",
                    "canonical_market",
                ],
                how="left",
                suffixes=(
                    "",
                    "_hist",
                ),
            )

            for c in historical_cols:
                hc = c + "_hist"

                if hc in board.columns:
                    board[c] = board[
                        hc
                    ]

    except Exception as exc:
        print(
            "Historical context warning:",
            type(exc).__name__,
            str(exc)[:150],
        )


# ==================================================
# TRANSPARENT QUALIFICATION
# ==================================================

board[
    "pp_book_implied_support"
] = num(
    board[
        "pp_book_implied_support"
    ]
)

board[
    "book_probability_median"
] = num(
    board[
        "book_probability_median"
    ]
)

board[
    "dfs_source_count"
] = num(
    board[
        "dfs_source_count"
    ]
).fillna(0)

board[
    "book_source_count"
] = num(
    board[
        "book_source_count"
    ]
).fillna(0)


def classify(row):

    prob = row.get(
        "pp_book_implied_support"
    )

    dfs_count = row.get(
        "dfs_source_count",
        0,
    )

    if pd.isna(prob):
        return "NO_BOOK_MATCH"

    # This is raw book-implied support,
    # NOT a calibrated Hulk win probability.
    if (
        prob >= 56.0
        and dfs_count >= 2
    ):
        return "STRONG_RESEARCH"

    if prob >= 55.0:
        return "QUALIFIED_RESEARCH"

    if prob >= 53.5:
        return "WATCH"

    return "PASS"


board["signal"] = board.apply(
    classify,
    axis=1,
)


def evidence(row):

    prob = row.get(
        "pp_book_implied_support"
    )

    book = row.get(
        "pp_reference_book"
    )

    dfs_count = int(
        row.get(
            "dfs_source_count",
            0,
        )
        or 0
    )

    if pd.isna(prob):
        return (
            "No matching sportsbook "
            "edge evidence."
        )

    return (
        f"Full-game PrizePicks line; "
        f"book support {prob:.2f}; "
        f"reference book {book}; "
        f"{dfs_count} DFS source(s) "
        f"show same line/side."
    )


board["evidence"] = board.apply(
    evidence,
    axis=1,
)


# ==================================================
# DEDUPE
# ==================================================

board = (
    board
    .sort_values(
        [
            "signal",
            "pp_book_implied_support",
        ],
        ascending=[
            True,
            False,
        ],
    )
    .drop_duplicates(
        subset=[
            "event_id",
            "player_key",
            "market_subtype",
            "side",
            "line_key",
        ],
        keep="first",
    )
)


# ==================================================
# OUTPUT
# ==================================================

cols = [
    "event_id",
    "start",
    "player",
    "market_subtype",
    "side",
    "line",
    "signal",
    "pp_book_implied_support",
    "pp_reference_book",
    "dfs_source_count",
    "dfs_sources",
    "book_source_count",
    "book_sources",
    "book_probability_median",
    "book_probability_max",
    "l3",
    "l5",
    "l10",
    "l20",
    "season",
    "h2h",
    "recent_avg",
    "season_avg",
    "evidence",
]

cols = [
    c for c in cols
    if c in board.columns
]

board = board[cols].copy()


signal_order = {
    "STRONG_RESEARCH": 0,
    "QUALIFIED_RESEARCH": 1,
    "WATCH": 2,
    "PASS": 3,
    "NO_BOOK_MATCH": 4,
}

board["_rank"] = (
    board["signal"]
    .map(signal_order)
    .fillna(99)
)

board = board.sort_values(
    [
        "_rank",
        "pp_book_implied_support",
    ],
    ascending=[
        True,
        False,
    ],
).drop(
    columns="_rank"
)


board.to_csv(
    OUT
    / "NFL_PRIZEPICKS_RESEARCH.csv",
    index=False,
)

qualified = board[
    board["signal"].isin(
        [
            "STRONG_RESEARCH",
            "QUALIFIED_RESEARCH",
        ]
    )
].copy()

qualified.to_csv(
    OUT
    / "NFL_PRIZEPICKS_QUALIFIED.csv",
    index=False,
)


# All DFS apps research, not just PrizePicks.
dfs_out = edges_live.copy()

dfs_out = dfs_out.sort_values(
    "book_probability",
    ascending=False,
)

dfs_out.to_csv(
    OUT
    / "NFL_DFS_ALL_RESEARCH.csv",
    index=False,
)


receipt = {
    "generated_at":
        NOW.isoformat(),

    "source_prizepicks_rows":
        len(pp),

    "full_game_future_unsuspended":
        len(pp_live),

    "live_edge_rows":
        len(edges_live),

    "prizepicks_book_matches":
        int(
            board[
                "pp_book_implied_support"
            ]
            .notna()
            .sum()
        ),

    "strong_research":
        int(
            (
                board["signal"]
                == "STRONG_RESEARCH"
            ).sum()
        ),

    "qualified_research":
        int(
            (
                board["signal"]
                == "QUALIFIED_RESEARCH"
            ).sum()
        ),

    "watch":
        int(
            (
                board["signal"]
                == "WATCH"
            ).sum()
        ),

    "important": (
        "Book implied support is not "
        "a calibrated Hulk probability."
    ),
}

(
    OUT
    / "NFL_DFS_FUSION_RECEIPT.json"
).write_text(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print("==================================================")
print("NFL PRIZEPICKS / DFS FUSION")
print("==================================================")

print(
    "PrizePicks raw rows:",
    len(pp),
)

print(
    "Full-game future unsuspended:",
    len(pp_live),
)

print(
    "Live full-game DFS edge rows:",
    len(edges_live),
)

print(
    "PrizePicks matched to book evidence:",
    receipt[
        "prizepicks_book_matches"
    ],
)

print(
    "STRONG_RESEARCH:",
    receipt[
        "strong_research"
    ],
)

print(
    "QUALIFIED_RESEARCH:",
    receipt[
        "qualified_research"
    ],
)

print(
    "WATCH:",
    receipt["watch"],
)


print()
print("=== TOP QUALIFIED PRIZEPICKS ===")

show = [
    "start",
    "player",
    "market_subtype",
    "side",
    "line",
    "signal",
    "pp_book_implied_support",
    "pp_reference_book",
    "dfs_source_count",
]

print(
    qualified[
        [
            c for c in show
            if c in qualified.columns
        ]
    ]
    .head(30)
    .to_string(
        index=False
    )
)


print()
print("IMPORTANT:")
print(
    "These are research-qualified "
    "line comparisons."
)

print(
    "Book implied support is NOT "
    "a calibrated win probability."
)

print(
    "Quarter and half props are excluded."
)

print(
    "Suspended and started events "
    "are excluded."
)

print(
    "No parlay has been generated."
)

print(
    "No production UI has been changed."
)
