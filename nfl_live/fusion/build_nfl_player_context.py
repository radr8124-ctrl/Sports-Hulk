from pathlib import Path
from datetime import datetime, timezone
import re
import json
import numpy as np
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")

RAW = ROOT / "nfl_live/player_context/raw"
CTX = ROOT / "nfl_live/player_context/derived"
FUSION = ROOT / "nfl_live/fusion"

NOW = datetime.now(timezone.utc)


def norm_name(v):
    s = str(v or "").lower().strip()

    # normalize common suffixes
    s = re.sub(
        r"\b(jr|sr|ii|iii|iv)\b\.?",
        "",
        s,
    )

    s = re.sub(
        r"[^a-z0-9]+",
        "",
        s,
    )

    return s


def numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c],
                errors="coerce",
            )
    return df


def pct_numeric(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace("%", "", regex=False),
        errors="coerce",
    )


# ==================================================
# PLAYER WEEKLY STATS
# ==================================================

stats_file = RAW / "player_stats.parquet"

if not stats_file.exists():
    raise SystemExit(
        "player_stats.parquet missing"
    )

stats = pd.read_parquet(stats_file)

name_col = (
    "player_display_name"
    if "player_display_name" in stats.columns
    else "player_name"
)

stats["player_key"] = (
    stats[name_col]
    .map(norm_name)
)

stats["week"] = pd.to_numeric(
    stats["week"],
    errors="coerce",
)

stat_metrics = [
    "attempts",
    "completions",
    "passing_yards",
    "passing_tds",
    "passing_interceptions",
    "passing_air_yards",
    "passing_epa",
    "passing_cpoe",
    "carries",
    "rushing_yards",
    "rushing_tds",
    "rushing_epa",
    "receptions",
    "targets",
    "receiving_yards",
    "receiving_tds",
    "receiving_air_yards",
    "receiving_yards_after_catch",
    "receiving_epa",
    "target_share",
    "air_yards_share",
    "wopr",
    "def_tackles_solo",
    "def_tackles_with_assist",
    "def_tackle_assists",
    "def_sacks",
    "def_qb_hits",
]

stats = numeric(
    stats,
    stat_metrics,
)

stats = stats[
    stats["player_key"].ne("")
].copy()

stats = stats.sort_values(
    ["player_key", "week"]
)


# ==================================================
# SEASON AVERAGES
# ==================================================

available_metrics = [
    c for c in stat_metrics
    if c in stats.columns
]

season_avg = (
    stats.groupby(
        "player_key"
    )[available_metrics]
    .mean()
    .add_suffix(
        "_season_avg"
    )
    .reset_index()
)


# ==================================================
# LAST TWO GAMES
# ==================================================

last2_rows = (
    stats.groupby(
        "player_key",
        group_keys=False,
    )
    .tail(2)
)

last2 = (
    last2_rows.groupby(
        "player_key"
    )[available_metrics]
    .mean()
    .add_suffix(
        "_l2_avg"
    )
    .reset_index()
)


# ==================================================
# LATEST PLAYER RECORD
# ==================================================

latest_cols = [
    "player_key",
    name_col,
    "week",
    "team",
    "opponent_team",
    "position",
    "target_share",
    "air_yards_share",
    "wopr",
]

latest_cols = [
    c for c in latest_cols
    if c in stats.columns
]

latest = (
    stats[
        latest_cols
    ]
    .drop_duplicates(
        "player_key",
        keep="last",
    )
    .copy()
)

latest = latest.rename(
    columns={
        name_col:
            "player_name_stats",

        "week":
            "latest_stat_week",

        "team":
            "latest_team",

        "opponent_team":
            "latest_opponent",

        "position":
            "position_stats",

        "target_share":
            "latest_target_share",

        "air_yards_share":
            "latest_air_yards_share",

        "wopr":
            "latest_wopr",
    }
)


# ==================================================
# SNAP COUNTS
# ==================================================

snap_file = RAW / "snap_counts.parquet"

snap_context = pd.DataFrame(
    {"player_key": []}
)

if snap_file.exists():

    snaps = pd.read_parquet(
        snap_file
    )

    snaps["player_key"] = (
        snaps["player"]
        .map(norm_name)
    )

    snaps["week"] = pd.to_numeric(
        snaps["week"],
        errors="coerce",
    )

    if "offense_pct" in snaps.columns:
        snaps["offense_pct_num"] = (
            pct_numeric(
                snaps[
                    "offense_pct"
                ]
            )
        )
    else:
        snaps[
            "offense_pct_num"
        ] = np.nan

    snaps["offense_snaps"] = (
        pd.to_numeric(
            snaps.get(
                "offense_snaps"
            ),
            errors="coerce",
        )
    )

    snaps = snaps.sort_values(
        ["player_key", "week"]
    )

    latest_snap = (
        snaps.groupby(
            "player_key",
            group_keys=False,
        )
        .tail(1)
        [
            [
                "player_key",
                "week",
                "offense_pct_num",
                "offense_snaps",
            ]
        ]
        .rename(
            columns={
                "week":
                    "latest_snap_week",
                "offense_pct_num":
                    "latest_offense_pct",
                "offense_snaps":
                    "latest_offense_snaps",
            }
        )
    )

    previous_snap = (
        snaps.groupby(
            "player_key",
            group_keys=False,
        )
        .tail(2)
        .groupby(
            "player_key",
            group_keys=False,
        )
        .head(1)
        [
            [
                "player_key",
                "offense_pct_num",
            ]
        ]
        .rename(
            columns={
                "offense_pct_num":
                    "previous_offense_pct"
            }
        )
    )

    snap_context = (
        latest_snap.merge(
            previous_snap,
            on="player_key",
            how="left",
        )
    )

    snap_context[
        "offense_pct_change"
    ] = (
        snap_context[
            "latest_offense_pct"
        ]
        - snap_context[
            "previous_offense_pct"
        ]
    )


# ==================================================
# NEXT GEN PASSING
# ==================================================

def latest_ngs(
    filename,
    prefix,
    wanted,
):

    path = CTX / filename

    if not path.exists():
        return pd.DataFrame(
            {"player_key": []}
        )

    df = pd.read_csv(
        path,
        low_memory=False,
    )

    df["player_key"] = (
        df["player_display_name"]
        .map(norm_name)
    )

    df["week"] = pd.to_numeric(
        df["week"],
        errors="coerce",
    )

    # Week 0 may be a summary record.
    weekly = df[
        df["week"].gt(0)
    ].copy()

    weekly = weekly.sort_values(
        ["player_key", "week"]
    )

    cols = [
        "player_key",
        "week",
    ]

    cols += [
        c for c in wanted
        if c in weekly.columns
    ]

    out = (
        weekly[cols]
        .drop_duplicates(
            "player_key",
            keep="last",
        )
    )

    rename = {
        "week":
            f"{prefix}_latest_week"
    }

    for c in wanted:
        if c in out.columns:
            rename[c] = (
                f"{prefix}_{c}"
            )

    return out.rename(
        columns=rename
    )


ngs_pass = latest_ngs(
    "NFL_NGS_PASSING_2026.csv",
    "ngs_pass",
    [
        "avg_time_to_throw",
        "avg_completed_air_yards",
        "avg_intended_air_yards",
        "aggressiveness",
        "completion_percentage",
        "expected_completion_percentage",
        "completion_percentage_above_expectation",
        "passer_rating",
    ],
)

ngs_rec = latest_ngs(
    "NFL_NGS_RECEIVING_2026.csv",
    "ngs_rec",
    [
        "avg_cushion",
        "avg_separation",
        "avg_intended_air_yards",
        "percent_share_of_intended_air_yards",
        "catch_percentage",
        "avg_yac",
        "avg_expected_yac",
        "avg_yac_above_expectation",
    ],
)

ngs_rush = latest_ngs(
    "NFL_NGS_RUSHING_2026.csv",
    "ngs_rush",
    [
        "efficiency",
        "percent_attempts_gte_eight_defenders",
        "avg_time_to_los",
        "expected_rush_yards",
        "rush_yards_over_expected",
        "rush_yards_over_expected_per_att",
        "rush_pct_over_expected",
    ],
)


# ==================================================
# SLEEPER PLAYER STATUS
# ==================================================

sleeper_file = (
    CTX
    / "NFL_SLEEPER_PLAYER_STATUS.csv"
)

sleeper_context = pd.DataFrame(
    {"player_key": []}
)

if sleeper_file.exists():

    sl = pd.read_csv(
        sleeper_file,
        low_memory=False,
    )

    sl["player_key"] = (
        sl["full_name"]
        .map(norm_name)
    )

    if "depth_chart_order" in sl.columns:

        sl[
            "depth_chart_order"
        ] = pd.to_numeric(
            sl[
                "depth_chart_order"
            ],
            errors="coerce",
        )

    sl["_active_rank"] = (
        sl["active"]
        .astype(str)
        .str.lower()
        .map({
            "true": 0,
            "1": 0,
            "false": 1,
            "0": 1,
        })
        .fillna(2)
    )

    sl = sl.sort_values(
        [
            "player_key",
            "_active_rank",
            "depth_chart_order",
        ],
        na_position="last",
    )

    keep = [
        "player_key",
        "team",
        "position",
        "active",
        "status",
        "injury_status",
        "injury_body_part",
        "practice_participation",
        "depth_chart_position",
        "depth_chart_order",
    ]

    keep = [
        c for c in keep
        if c in sl.columns
    ]

    sleeper_context = (
        sl[keep]
        .drop_duplicates(
            "player_key",
            keep="first",
        )
        .rename(
            columns={
                "team":
                    "sleeper_team",
                "position":
                    "sleeper_position",
                "active":
                    "sleeper_active",
                "status":
                    "sleeper_status",
            }
        )
    )


# ==================================================
# BUILD MASTER PLAYER CONTEXT
# ==================================================

master = latest.copy()

for df in [
    season_avg,
    last2,
    snap_context,
    ngs_pass,
    ngs_rec,
    ngs_rush,
    sleeper_context,
]:

    if (
        df is not None
        and not df.empty
    ):
        master = master.merge(
            df,
            on="player_key",
            how="outer",
        )


# ==================================================
# SOURCE COVERAGE
# ==================================================

def has_any(row, prefix):
    return any(
        pd.notna(row.get(c))
        for c in row.index
        if c.startswith(prefix)
    )


def source_list(row):

    sources = []

    if pd.notna(
        row.get(
            "latest_stat_week"
        )
    ):
        sources.append(
            "nflverse_stats"
        )

    if pd.notna(
        row.get(
            "latest_snap_week"
        )
    ):
        sources.append(
            "snap_counts"
        )

    if (
        has_any(
            row,
            "ngs_pass_",
        )
        or has_any(
            row,
            "ngs_rec_",
        )
        or has_any(
            row,
            "ngs_rush_",
        )
    ):
        sources.append(
            "next_gen_stats"
        )

    if (
        pd.notna(
            row.get(
                "sleeper_active"
            )
        )
        or pd.notna(
            row.get(
                "sleeper_status"
            )
        )
    ):
        sources.append(
            "sleeper"
        )

    return ",".join(sources)


master[
    "context_sources"
] = master.apply(
    source_list,
    axis=1,
)

master[
    "context_source_count"
] = master[
    "context_sources"
].apply(
    lambda x:
        0 if not x
        else len(
            x.split(",")
        )
)


def coverage_grade(n):

    if n >= 4:
        return "RICH"

    if n >= 3:
        return "GOOD"

    if n >= 2:
        return "BASIC"

    return "THIN"


master[
    "context_coverage"
] = master[
    "context_source_count"
].map(
    coverage_grade
)


# ==================================================
# AVAILABILITY / INJURY REVIEW
# ==================================================

def injury_flag(row):

    injury = str(
        row.get(
            "injury_status"
        )
        or ""
    ).strip()

    status = str(
        row.get(
            "sleeper_status"
        )
        or ""
    ).strip()

    practice = str(
        row.get(
            "practice_participation"
        )
        or ""
    ).strip()

    combined = (
        injury
        + " "
        + status
        + " "
        + practice
    ).lower()

    high_risk = [
        "out",
        "injured reserve",
        "ir",
        "suspended",
        "pup",
        "inactive",
        "doubtful",
    ]

    if any(
        x in combined
        for x in high_risk
    ):
        return "BLOCK_OR_REVIEW"

    if (
        injury
        or practice
    ):
        return "INJURY_REVIEW"

    return "NO_SLEEPER_FLAG"


master[
    "availability_flag"
] = master.apply(
    injury_flag,
    axis=1,
)


# ==================================================
# MARKET-SPECIFIC CONTEXT SUMMARY
# ==================================================

def fmt(v, digits=1):

    try:
        if pd.isna(v):
            return "—"

        return str(
            round(
                float(v),
                digits,
            )
        )

    except Exception:
        return "—"


def prop_context(row):

    market = str(
        row.get("market", "")
    ).upper()

    if (
        "REC_YARDS" in market
        or "RECEPTIONS" in market
        or "TARGET" in market
    ):
        return (
            "REC: "
            f"L2 targets "
            f"{fmt(row.get('targets_l2_avg'))}; "
            f"L2 rec yds "
            f"{fmt(row.get('receiving_yards_l2_avg'))}; "
            f"target share "
            f"{fmt(row.get('latest_target_share'),3)}; "
            f"air share "
            f"{fmt(row.get('latest_air_yards_share'),3)}; "
            f"snap% "
            f"{fmt(row.get('latest_offense_pct'))}; "
            f"NGS sep "
            f"{fmt(row.get('ngs_rec_avg_separation'))}"
        )

    if (
        "RUSH_YARDS" in market
        or "RUSH_ATTEMPTS" in market
    ):
        return (
            "RUSH: "
            f"L2 carries "
            f"{fmt(row.get('carries_l2_avg'))}; "
            f"L2 rush yds "
            f"{fmt(row.get('rushing_yards_l2_avg'))}; "
            f"snap% "
            f"{fmt(row.get('latest_offense_pct'))}; "
            f"snap Δ "
            f"{fmt(row.get('offense_pct_change'))}; "
            f"NGS RYOE/att "
            f"{fmt(row.get('ngs_rush_rush_yards_over_expected_per_att'))}"
        )

    if (
        "PASS_YARDS" in market
        or "PASS_ATTEMPTS" in market
        or "PASS_COMPLETIONS" in market
        or "PASS_TDS" in market
        or "INTERCEPTIONS" in market
    ):
        return (
            "PASS: "
            f"L2 attempts "
            f"{fmt(row.get('attempts_l2_avg'))}; "
            f"L2 pass yds "
            f"{fmt(row.get('passing_yards_l2_avg'))}; "
            f"CPOE "
            f"{fmt(row.get('ngs_pass_completion_percentage_above_expectation'))}; "
            f"intended air yds "
            f"{fmt(row.get('ngs_pass_avg_intended_air_yards'))}"
        )

    if (
        "SACK" in market
        or "TACKLE" in market
    ):
        return (
            "DEF: "
            f"L2 sacks "
            f"{fmt(row.get('def_sacks_l2_avg'))}; "
            f"L2 solo tackles "
            f"{fmt(row.get('def_tackles_solo_l2_avg'))}; "
            f"L2 QB hits "
            f"{fmt(row.get('def_qb_hits_l2_avg'))}"
        )

    return (
        "General player context available; "
        "market-specific usage model not yet assigned."
    )


# Save master context first.
master.to_csv(
    CTX
    / "NFL_PLAYER_CONTEXT_MASTER.csv",
    index=False,
)


# ==================================================
# JOIN TO DFS ↔ SPORTSBOOK MATCHES
# ==================================================

match_file = (
    FUSION
    / "NFL_DFS_VS_MULTIBOOK.csv"
)

if not match_file.exists():
    raise SystemExit(
        "NFL_DFS_VS_MULTIBOOK.csv missing."
    )

props = pd.read_csv(
    match_file,
    low_memory=False,
)

player_col = None

for candidate in [
    "player_dfs",
    "player",
    "player_sportsbook",
]:

    if candidate in props.columns:
        player_col = candidate
        break

if player_col is None:
    raise SystemExit(
        "Could not locate player column "
        "in DFS sportsbook match file."
    )

props["player_key"] = (
    props[player_col]
    .map(norm_name)
)


joined = props.merge(
    master,
    on="player_key",
    how="left",
)


# ==================================================
# CONTEXT COVERAGE FOR EACH PROP
# ==================================================

joined[
    "context_coverage"
] = joined[
    "context_coverage"
].fillna(
    "NO_MATCH"
)

joined[
    "availability_flag"
] = joined[
    "availability_flag"
].fillna(
    "NO_PLAYER_STATUS"
)

joined[
    "market_context"
] = joined.apply(
    prop_context,
    axis=1,
)


# ==================================================
# PROP READINESS
# ==================================================

def readiness(row):

    injury = row.get(
        "availability_flag"
    )

    coverage = row.get(
        "context_coverage"
    )

    book_count = pd.to_numeric(
        row.get(
            "book_count"
        ),
        errors="coerce",
    )

    if injury == "BLOCK_OR_REVIEW":
        return "INJURY_BLOCK"

    if coverage == "NO_MATCH":
        return "CONTEXT_MISSING"

    if (
        pd.notna(book_count)
        and book_count >= 3
        and coverage in {
            "RICH",
            "GOOD",
        }
    ):
        return "CONTEXT_READY"

    if coverage in {
        "RICH",
        "GOOD",
        "BASIC",
    }:
        return "REVIEW"

    return "THIN_DATA"


joined[
    "context_readiness"
] = joined.apply(
    readiness,
    axis=1,
)


# ==================================================
# DEDUPE IDENTICAL PROP CANDIDATES
# ==================================================

dedupe_cols = [
    player_col,
    "market",
    "side",
    "dfs_line",
    "sportsbook_line",
]

dedupe_cols = [
    c for c in dedupe_cols
    if c in joined.columns
]

joined = (
    joined
    .sort_values(
        [
            "book_count",
            "book_probability",
        ],
        ascending=[
            False,
            False,
        ],
    )
    .drop_duplicates(
        subset=dedupe_cols,
        keep="first",
    )
)


joined.to_csv(
    FUSION
    / "NFL_PROP_CONTEXT_JOINED.csv",
    index=False,
)


ready = joined[
    joined[
        "context_readiness"
    ].eq(
        "CONTEXT_READY"
    )
].copy()

ready.to_csv(
    FUSION
    / "NFL_PROP_CONTEXT_READY.csv",
    index=False,
)


# ==================================================
# ACCEPTANCE
# ==================================================

print()
print("==================================================")
print("NFL PLAYER CONTEXT FUSION")
print("==================================================")

print(
    "Master players:",
    len(master),
)

print(
    "Market/DFS rows before join:",
    len(props),
)

print(
    "Unique candidates after dedupe:",
    len(joined),
)

print(
    "CONTEXT_READY:",
    len(ready),
)

print()
print("CONTEXT COVERAGE:")

print(
    joined[
        "context_coverage"
    ]
    .value_counts()
    .to_string()
)

print()
print("READINESS:")

print(
    joined[
        "context_readiness"
    ]
    .value_counts()
    .to_string()
)

print()
print("AVAILABILITY FLAGS:")

print(
    joined[
        "availability_flag"
    ]
    .value_counts()
    .to_string()
)


print()
print("=== SAMPLE CONTEXT-READY PROPS ===")

cols = [
    player_col,
    "market",
    "side",
    "dfs_line",
    "sportsbook_line",
    "book_count",
    "coverage_grade",
    "book_probability",
    "context_coverage",
    "availability_flag",
    "market_context",
]

cols = [
    c for c in cols
    if c in ready.columns
]

print(
    ready[
        cols
    ]
    .head(30)
    .to_string(
        index=False
    )
)


receipt = {
    "generated_at":
        NOW.isoformat(),

    "master_players":
        len(master),

    "market_dfs_rows":
        len(props),

    "deduped_candidates":
        len(joined),

    "context_ready":
        len(ready),

    "injury_blocks":
        int(
            (
                joined[
                    "context_readiness"
                ]
                == "INJURY_BLOCK"
            ).sum()
        ),

    "important": (
        "Context readiness is not a "
        "bet probability or recommendation."
    ),
}

(
    FUSION
    / "NFL_PLAYER_CONTEXT_RECEIPT.json"
).write_text(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print("IMPORTANT:")
print(
    "Player context is independent "
    "of sportsbook pricing."
)

print(
    "Sleeper injury status is a "
    "screening flag, not a replacement "
    "for official game-day injury reports."
)

print(
    "No pick has been promoted."
)

print(
    "No parlay generated."
)

print(
    "No production UI changed."
)
