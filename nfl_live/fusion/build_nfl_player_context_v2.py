from pathlib import Path
from datetime import datetime, timezone
import json
import re

import numpy as np
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")

RAW = ROOT / "nfl_live/player_context/raw"
CTX = ROOT / "nfl_live/player_context/derived"
FUSION = ROOT / "nfl_live/fusion"
QA = FUSION / "qa"

QA.mkdir(parents=True, exist_ok=True)

NOW = datetime.now(timezone.utc)


def norm_name(v):
    if pd.isna(v):
        return ""

    s = str(v).lower().strip()

    s = re.sub(
        r"\b(jr|sr|ii|iii|iv)\b\.?",
        "",
        s,
    )

    return re.sub(
        r"[^a-z0-9]+",
        "",
        s,
    )


def clean_text(v):
    if v is None or pd.isna(v):
        return ""

    s = str(v).strip()

    if s.lower() in {
        "",
        "nan",
        "none",
        "null",
        "n/a",
        "na",
    }:
        return ""

    return s


def to_num(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c],
                errors="coerce",
            )

    return df


# ==================================================
# LOAD WEEKLY PLAYER STATS
# ==================================================

stats_path = RAW / "player_stats.parquet"

if not stats_path.exists():
    raise SystemExit(
        "player_stats.parquet missing"
    )

stats = pd.read_parquet(stats_path)

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

if "season" in stats.columns:
    stats = stats[
        pd.to_numeric(
            stats["season"],
            errors="coerce",
        ).eq(2026)
    ].copy()

if "season_type" in stats.columns:
    reg = stats[
        stats["season_type"]
        .astype(str)
        .str.upper()
        .isin(
            [
                "REG",
                "REGULAR",
                "REGULAR SEASON",
            ]
        )
    ].copy()

    if not reg.empty:
        stats = reg


# ==================================================
# VERIFY COMPLETED GAMES FROM NFLVERSE SCHEDULE
# ==================================================

schedule_path = (
    ROOT
    / "nfl_live"
    / "derived"
    / "NFLVERSE_2026_SCHEDULE.csv"
)

completed_ids = set()

if schedule_path.exists():

    sched = pd.read_csv(
        schedule_path,
        low_memory=False,
    )

    if (
        "game_id" in sched.columns
        and
        "home_score" in sched.columns
        and
        "away_score" in sched.columns
    ):

        sched["home_score_num"] = (
            pd.to_numeric(
                sched["home_score"],
                errors="coerce",
            )
        )

        sched["away_score_num"] = (
            pd.to_numeric(
                sched["away_score"],
                errors="coerce",
            )
        )

        complete = sched[
            sched["home_score_num"]
            .notna()
            &
            sched["away_score_num"]
            .notna()
        ].copy()

        completed_ids = set(
            complete["game_id"]
            .astype(str)
        )

        print(
            "COMPLETED SCHEDULE GAMES:",
            len(completed_ids),
        )


stats_before = len(stats)

if (
    completed_ids
    and "game_id" in stats.columns
):

    stats = stats[
        stats["game_id"]
        .astype(str)
        .isin(completed_ids)
    ].copy()

print(
    "PLAYER STAT ROWS BEFORE COMPLETE FILTER:",
    stats_before,
)

print(
    "PLAYER STAT ROWS AFTER COMPLETE FILTER:",
    len(stats),
)


metrics = [
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

stats = to_num(
    stats,
    metrics,
)

available = [
    c for c in metrics
    if c in stats.columns
]

stats = stats[
    stats["player_key"].ne("")
].sort_values(
    [
        "player_key",
        "week",
    ]
)


# ==================================================
# COMPLETED-GAME PLAYER AVERAGES
# ==================================================

season_avg = (
    stats.groupby(
        "player_key"
    )[available]
    .mean()
    .add_suffix(
        "_season_avg"
    )
    .reset_index()
)


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
    )[available]
    .mean()
    .add_suffix(
        "_l2_avg"
    )
    .reset_index()
)


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
    stats[latest_cols]
    .drop_duplicates(
        "player_key",
        keep="last",
    )
    .rename(
        columns={
            name_col:
                "player_name_stats",
            "week":
                "latest_completed_week",
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
)


# ==================================================
# SNAP COUNTS — COMPLETED GAMES ONLY
# ==================================================

snap_path = RAW / "snap_counts.parquet"

snap_context = pd.DataFrame(
    {"player_key": []}
)

if snap_path.exists():

    snaps = pd.read_parquet(
        snap_path
    )

    snaps["player_key"] = (
        snaps["player"]
        .map(norm_name)
    )

    snaps["week"] = pd.to_numeric(
        snaps["week"],
        errors="coerce",
    )

    if (
        completed_ids
        and "game_id" in snaps.columns
    ):
        snaps = snaps[
            snaps["game_id"]
            .astype(str)
            .isin(completed_ids)
        ].copy()

    raw_pct = pd.to_numeric(
        snaps.get(
            "offense_pct"
        ),
        errors="coerce",
    )

    # nflverse may represent this as
    # either 0.75 or 75.
    snaps[
        "offense_pct_normalized"
    ] = np.where(
        raw_pct.le(1.5),
        raw_pct * 100,
        raw_pct,
    )

    snaps[
        "offense_snaps"
    ] = pd.to_numeric(
        snaps.get(
            "offense_snaps"
        ),
        errors="coerce",
    )

    snaps = snaps.sort_values(
        [
            "player_key",
            "week",
        ]
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
                "offense_pct_normalized",
                "offense_snaps",
            ]
        ]
        .rename(
            columns={
                "week":
                    "latest_snap_week",
                "offense_pct_normalized":
                    "latest_offense_pct",
                "offense_snaps":
                    "latest_offense_snaps",
            }
        )
    )

    previous = (
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
                "offense_pct_normalized",
            ]
        ]
        .rename(
            columns={
                "offense_pct_normalized":
                    "previous_offense_pct"
            }
        )
    )

    snap_context = (
        latest_snap.merge(
            previous,
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
        -
        snap_context[
            "previous_offense_pct"
        ]
    )


# ==================================================
# NGS
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

    df = df[
        df["week"].gt(0)
    ].copy()

    df = df.sort_values(
        [
            "player_key",
            "week",
        ]
    )

    cols = [
        "player_key",
        "week",
    ]

    cols += [
        c
        for c in wanted
        if c in df.columns
    ]

    out = (
        df[cols]
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
# SLEEPER — CORRECT MISSING VALUE HANDLING
# ==================================================

sleeper_path = (
    CTX
    / "NFL_SLEEPER_PLAYER_STATUS.csv"
)

sleeper = pd.DataFrame(
    {"player_key": []}
)

if sleeper_path.exists():

    sl = pd.read_csv(
        sleeper_path,
        low_memory=False,
    )

    sl["player_key"] = (
        sl["full_name"]
        .map(norm_name)
    )

    for c in [
        "status",
        "injury_status",
        "injury_body_part",
        "practice_participation",
        "depth_chart_position",
    ]:
        if c in sl.columns:
            sl[c] = (
                sl[c]
                .map(clean_text)
            )

    sl[
        "depth_chart_order"
    ] = pd.to_numeric(
        sl.get(
            "depth_chart_order"
        ),
        errors="coerce",
    )

    sl = sl.sort_values(
        [
            "player_key",
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

    sleeper = (
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
# MASTER
# ==================================================

master = latest.copy()

for frame in [
    season_avg,
    last2,
    snap_context,
    ngs_pass,
    ngs_rec,
    ngs_rush,
    sleeper,
]:

    if (
        frame is not None
        and not frame.empty
    ):
        master = master.merge(
            frame,
            on="player_key",
            how="outer",
        )


# ==================================================
# TRUE AVAILABILITY FLAGS
# ==================================================

def availability(row):

    injury = clean_text(
        row.get(
            "injury_status"
        )
    ).lower()

    practice = clean_text(
        row.get(
            "practice_participation"
        )
    ).lower()

    status = clean_text(
        row.get(
            "sleeper_status"
        )
    ).lower()

    active = clean_text(
        row.get(
            "sleeper_active"
        )
    ).lower()

    combined = " ".join(
        [
            injury,
            practice,
            status,
        ]
    )

    hard_block = [
        "out",
        "doubtful",
        "injured reserve",
        "inactive",
        "suspended",
        "pup",
    ]

    if any(
        x in combined
        for x in hard_block
    ):
        return "BLOCK_OR_OFFICIAL_REVIEW"

    caution = [
        "questionable",
        "limited",
        "did not participate",
        "dnp",
    ]

    if any(
        x in combined
        for x in caution
    ):
        return "OFFICIAL_INJURY_REVIEW"

    if (
        injury
        or practice
    ):
        return "STATUS_REVIEW"

    if active in {
        "false",
        "0",
    }:
        return "ACTIVE_STATUS_REVIEW"

    return "CLEAR_SLEEPER_SCREEN"


master[
    "availability_flag"
] = master.apply(
    availability,
    axis=1,
)


# ==================================================
# SOURCE COVERAGE
# ==================================================

def source_count(row):

    sources = []

    if pd.notna(
        row.get(
            "latest_completed_week"
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

    ngs_cols = [
        c for c in row.index
        if c.startswith(
            "ngs_"
        )
    ]

    if any(
        pd.notna(
            row.get(c)
        )
        for c in ngs_cols
    ):
        sources.append(
            "next_gen_stats"
        )

    if (
        clean_text(
            row.get(
                "sleeper_team"
            )
        )
        or clean_text(
            row.get(
                "sleeper_position"
            )
        )
    ):
        sources.append(
            "sleeper"
        )

    return sources


master[
    "context_sources"
] = master.apply(
    lambda r:
        ",".join(
            source_count(r)
        ),
    axis=1,
)

master[
    "context_source_count"
] = master.apply(
    lambda r:
        len(
            source_count(r)
        ),
    axis=1,
)


master[
    "context_coverage"
] = master[
    "context_source_count"
].map(
    lambda n:
        "RICH"
        if n >= 4
        else
        "GOOD"
        if n >= 3
        else
        "BASIC"
        if n >= 2
        else
        "THIN"
)


master.to_csv(
    CTX
    / "NFL_PLAYER_CONTEXT_MASTER_V2.csv",
    index=False,
)


# ==================================================
# JOIN WITH LIVE PROP MATCHES
# ==================================================

match_path = (
    FUSION
    / "NFL_DFS_VS_MULTIBOOK.csv"
)

props = pd.read_csv(
    match_path,
    low_memory=False,
)

player_col = next(
    (
        c for c in [
            "player_dfs",
            "player",
            "player_sportsbook",
        ]
        if c in props.columns
    ),
    None,
)

if player_col is None:
    raise SystemExit(
        "Player column missing"
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
    "NO_STATUS_MATCH"
)


def readiness(row):

    status = row[
        "availability_flag"
    ]

    coverage = row[
        "context_coverage"
    ]

    books = pd.to_numeric(
        row.get(
            "book_count"
        ),
        errors="coerce",
    )

    if status in {
        "BLOCK_OR_OFFICIAL_REVIEW",
        "OFFICIAL_INJURY_REVIEW",
    }:
        return "OFFICIAL_INJURY_GATE"

    if coverage == "NO_MATCH":
        return "CONTEXT_MISSING"

    if (
        pd.notna(books)
        and books >= 3
        and coverage in {
            "RICH",
            "GOOD",
        }
    ):
        return "CONTEXT_READY"

    return "REVIEW"


joined[
    "context_readiness"
] = joined.apply(
    readiness,
    axis=1,
)


dedupe = [
    c for c in [
        player_col,
        "market",
        "side",
        "dfs_line",
        "sportsbook_line",
    ]
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
        subset=dedupe,
        keep="first",
    )
)


joined.to_csv(
    FUSION
    / "NFL_PROP_CONTEXT_JOINED_V2.csv",
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
    / "NFL_PROP_CONTEXT_READY_V2.csv",
    index=False,
)


# ==================================================
# QA IMPORTANT PLAYERS
# ==================================================

qa_names = [
    "Kyler Murray",
    "Geno Smith",
    "Ladd McConkey",
    "Justin Jefferson",
    "Josh Allen",
    "Dalton Kincaid",
]

qa_keys = {
    norm_name(x)
    for x in qa_names
}

qa_stats = stats[
    stats[
        "player_key"
    ].isin(
        qa_keys
    )
].copy()

qa_cols = [
    name_col,
    "week",
    "game_id",
    "team",
    "opponent_team",
    "attempts",
    "passing_yards",
    "carries",
    "rushing_yards",
    "targets",
    "receptions",
    "receiving_yards",
]

qa_cols = [
    c for c in qa_cols
    if c in qa_stats.columns
]

qa_stats[
    qa_cols
].to_csv(
    QA
    / "NFL_PLAYER_COMPLETED_GAME_QA.csv",
    index=False,
)


print()
print("==================================================")
print("PLAYER CONTEXT V2 ACCEPTANCE")
print("==================================================")

print(
    "Master players:",
    len(master),
)

print(
    "Deduped candidates:",
    len(joined),
)

print(
    "Context ready:",
    len(ready),
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
print("READINESS:")

print(
    joined[
        "context_readiness"
    ]
    .value_counts()
    .to_string()
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
print("=== COMPLETED GAME QA ===")

if not qa_stats.empty:

    print(
        qa_stats[
            qa_cols
        ]
        .sort_values(
            [
                name_col,
                "week",
            ]
        )
        .to_string(
            index=False
        )
    )


receipt = {
    "generated_at":
        NOW.isoformat(),

    "completed_stat_rows":
        len(stats),

    "master_players":
        len(master),

    "deduped_candidates":
        len(joined),

    "context_ready":
        len(ready),

    "official_injury_gate":
        int(
            (
                joined[
                    "context_readiness"
                ]
                == "OFFICIAL_INJURY_GATE"
            ).sum()
        ),

    "clear_sleeper_screen":
        int(
            (
                joined[
                    "availability_flag"
                ]
                == "CLEAR_SLEEPER_SCREEN"
            ).sum()
        ),

    "important":
        (
            "Only completed-game stats "
            "feed recent averages. "
            "Official injury reports remain "
            "required before promotion."
        ),
}

(
    FUSION
    / "NFL_PLAYER_CONTEXT_V2_RECEIPT.json"
).write_text(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print("IMPORTANT:")
print(
    "Current/upcoming games do not feed "
    "recent player averages."
)

print(
    "Sleeper status is only a screening "
    "layer."
)

print(
    "Official game-day injury confirmation "
    "will remain mandatory before PLAY."
)

print(
    "No recommendation generated."
)

print(
    "No production UI changed."
)
