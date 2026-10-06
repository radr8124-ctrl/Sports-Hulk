from pathlib import Path
from datetime import datetime, timezone
import json
import requests
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")

RAW = (
    ROOT
    / "nfl_live"
    / "player_context"
    / "raw"
)

OUT = (
    ROOT
    / "nfl_live"
    / "player_context"
    / "derived"
)

RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

NOW = datetime.now(timezone.utc)

SEASON = 2026


SOURCES = {
    "player_stats": (
        "https://github.com/nflverse/"
        "nflverse-data/releases/download/"
        "stats_player/"
        "stats_player_week_2026.parquet"
    ),

    "snap_counts": (
        "https://github.com/nflverse/"
        "nflverse-data/releases/download/"
        "snap_counts/"
        "snap_counts_2026.parquet"
    ),

    "ngs_passing": (
        "https://github.com/nflverse/"
        "nflverse-data/releases/download/"
        "nextgen_stats/"
        "ngs_passing.parquet"
    ),

    "ngs_receiving": (
        "https://github.com/nflverse/"
        "nflverse-data/releases/download/"
        "nextgen_stats/"
        "ngs_receiving.parquet"
    ),

    "ngs_rushing": (
        "https://github.com/nflverse/"
        "nflverse-data/releases/download/"
        "nextgen_stats/"
        "ngs_rushing.parquet"
    ),
}


def download(name, url):

    print()
    print("FETCH:", name)

    r = requests.get(
        url,
        timeout=60,
    )

    print("HTTP:", r.status_code)
    print("BYTES:", len(r.content))

    r.raise_for_status()

    path = RAW / f"{name}.parquet"

    path.write_bytes(r.content)

    return path


report = {
    "generated_at": NOW.isoformat(),
    "season": SEASON,
    "sources": {},
}


# ==================================================
# NFLVERSE DATA
# ==================================================

frames = {}

for name, url in SOURCES.items():

    try:

        path = download(
            name,
            url,
        )

        df = pd.read_parquet(path)

        if "season" in df.columns:

            season_num = pd.to_numeric(
                df["season"],
                errors="coerce",
            )

            current = df[
                season_num.eq(SEASON)
            ].copy()

            if not current.empty:
                df = current

        frames[name] = df

        report["sources"][name] = {
            "status": "OK",
            "rows": len(df),
            "columns": list(
                map(str, df.columns)
            ),
        }

        print("ROWS:", len(df))

        print(
            "COLUMNS:",
            ", ".join(
                map(
                    str,
                    df.columns[:80],
                )
            ),
        )

        if "week" in df.columns:

            weeks = sorted(
                pd.to_numeric(
                    df["week"],
                    errors="coerce",
                )
                .dropna()
                .unique()
                .tolist()
            )

            print(
                "WEEKS:",
                weeks[-10:],
            )

    except Exception as exc:

        report["sources"][name] = {
            "status": "ERROR",
            "error": (
                f"{type(exc).__name__}: "
                f"{str(exc)[:250]}"
            ),
        }

        print(
            "ERROR:",
            type(exc).__name__,
            str(exc)[:250],
        )


# ==================================================
# SLEEPER PUBLIC PLAYER DATA
# ==================================================

print()
print("FETCH: sleeper_players")

try:

    r = requests.get(
        "https://api.sleeper.app/v1/players/nfl",
        params={
            "active": "true",
        },
        timeout=60,
    )

    print(
        "HTTP:",
        r.status_code,
    )

    r.raise_for_status()

    payload = r.json()

    sleeper_file = (
        RAW
        / "sleeper_players.json"
    )

    sleeper_file.write_text(
        json.dumps(
            payload,
            indent=2,
        )
    )

    rows = []

    for pid, p in payload.items():

        if not isinstance(p, dict):
            continue

        rows.append({
            "sleeper_id": pid,
            "full_name": (
                p.get("full_name")
                or (
                    str(
                        p.get(
                            "first_name",
                            "",
                        )
                    )
                    + " "
                    + str(
                        p.get(
                            "last_name",
                            "",
                        )
                    )
                ).strip()
            ),
            "team": p.get("team"),
            "position": p.get(
                "position"
            ),
            "active": p.get(
                "active"
            ),
            "status": p.get(
                "status"
            ),
            "injury_status": p.get(
                "injury_status"
            ),
            "injury_body_part": p.get(
                "injury_body_part"
            ),
            "practice_participation": (
                p.get(
                    "practice_participation"
                )
            ),
            "depth_chart_position": (
                p.get(
                    "depth_chart_position"
                )
            ),
            "depth_chart_order": (
                p.get(
                    "depth_chart_order"
                )
            ),
        })

    sleeper = pd.DataFrame(rows)

    sleeper.to_csv(
        OUT
        / "NFL_SLEEPER_PLAYER_STATUS.csv",
        index=False,
    )

    report["sources"][
        "sleeper_players"
    ] = {
        "status": "OK",
        "rows": len(sleeper),
        "columns": list(
            sleeper.columns
        ),
    }

    print(
        "ROWS:",
        len(sleeper),
    )

    if not sleeper.empty:

        injured = sleeper[
            sleeper[
                "injury_status"
            ].notna()
        ]

        print(
            "PLAYERS WITH "
            "INJURY STATUS:",
            len(injured),
        )

except Exception as exc:

    print(
        "SLEEPER ERROR:",
        type(exc).__name__,
        str(exc)[:250],
    )

    report["sources"][
        "sleeper_players"
    ] = {
        "status": "ERROR",
        "error": str(exc)[:250],
    }


# ==================================================
# PLAYER STATS — RECENT USAGE SNAPSHOT
# ==================================================

stats = frames.get(
    "player_stats"
)

if stats is not None and not stats.empty:

    week_col = (
        "week"
        if "week" in stats.columns
        else None
    )

    if week_col:

        stats["week"] = pd.to_numeric(
            stats["week"],
            errors="coerce",
        )

        latest_week = int(
            stats["week"]
            .dropna()
            .max()
        )

        recent_weeks = [
            w
            for w in [
                latest_week - 1,
                latest_week,
            ]
            if w > 0
        ]

        recent = stats[
            stats["week"].isin(
                recent_weeks
            )
        ].copy()

        recent.to_parquet(
            OUT
            / "NFL_PLAYER_STATS_RECENT.parquet",
            index=False,
        )

        recent.to_csv(
            OUT
            / "NFL_PLAYER_STATS_RECENT.csv",
            index=False,
        )

        print()
        print(
            "LATEST PLAYER-STATS WEEK:",
            latest_week,
        )

        print(
            "RECENT PLAYER ROWS:",
            len(recent),
        )


# ==================================================
# SNAP COUNTS — MOST RECENT WEEKS
# ==================================================

snaps = frames.get(
    "snap_counts"
)

if snaps is not None and not snaps.empty:

    if "week" in snaps.columns:

        snaps["week"] = pd.to_numeric(
            snaps["week"],
            errors="coerce",
        )

        latest = int(
            snaps["week"]
            .dropna()
            .max()
        )

        recent = snaps[
            snaps["week"]
            .ge(
                max(
                    1,
                    latest - 1,
                )
            )
        ].copy()

        recent.to_csv(
            OUT
            / "NFL_SNAP_COUNTS_RECENT.csv",
            index=False,
        )

        print()
        print(
            "LATEST SNAP WEEK:",
            latest,
        )

        print(
            "RECENT SNAP ROWS:",
            len(recent),
        )


# ==================================================
# NEXT GEN CURRENT SEASON OUTPUTS
# ==================================================

for name in [
    "ngs_passing",
    "ngs_receiving",
    "ngs_rushing",
]:

    df = frames.get(name)

    if df is None or df.empty:
        continue

    df.to_csv(
        OUT
        / (
            "NFL_"
            + name.upper()
            + "_2026.csv"
        ),
        index=False,
    )


# ==================================================
# RECEIPT
# ==================================================

receipt = (
    OUT
    / "NFL_FREE_PLAYER_SOURCES_RECEIPT.json"
)

receipt.write_text(
    json.dumps(
        report,
        indent=2,
        default=str,
    )
)


print()
print("==================================================")
print("FREE PLAYER SOURCE ACCEPTANCE")
print("==================================================")

for name, info in (
    report["sources"].items()
):

    print(
        name,
        "=>",
        info.get("status"),
        "| rows:",
        info.get("rows"),
    )


print()
print("IMPORTANT:")
print(
    "No sportsbook API was called."
)

print(
    "No recommendation was generated."
)

print(
    "No production betting or "
    "PrizePicks board was overwritten."
)

print(
    "These sources represent independent "
    "football/player context."
)
