from pathlib import Path
from datetime import datetime, timezone
import json
import re

import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")

IDENTITY = ROOT / "nfl_live/identity"
RAW = ROOT / "nfl_live/player_context/raw"
CTX = ROOT / "nfl_live/player_context/derived"
FUSION = ROOT / "nfl_live/fusion"
QA = FUSION / "qa"

NOW = datetime.now(timezone.utc)

TEAM_FILE = IDENTITY / "team_aliases.json"
PROP_FILE = FUSION / "NFL_PROP_CONTEXT_JOINED_V2.csv"
STATS_FILE = RAW / "player_stats.parquet"
SLEEPER_FILE = CTX / "NFL_SLEEPER_PLAYER_STATUS.csv"


def text(v):
    if v is None or pd.isna(v):
        return ""
    return str(v).strip()


def key(v):
    s = text(v).lower()

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


aliases = json.loads(
    TEAM_FILE.read_text()
)

TEAM_LOOKUP = {}

for abbr, values in aliases.items():

    TEAM_LOOKUP[key(abbr)] = abbr

    for value in values:
        TEAM_LOOKUP[key(value)] = abbr


def canonical_team(value):
    k = key(value)

    if not k:
        return ""

    return TEAM_LOOKUP.get(
        k,
        text(value).upper(),
    )


def pos_family(position):

    p = text(position).upper()

    if p == "QB":
        return "QB"

    if p in {"RB", "FB"}:
        return "RB"

    if p in {"WR", "TE"}:
        return "RECEIVER"

    if p in {"K", "PK"}:
        return "KICKER"

    if p == "P":
        return "PUNTER"

    if p in {
        "LB", "ILB", "OLB",
        "DE", "DT", "DL",
        "NT", "EDGE"
    }:
        return "DEF_FRONT"

    if p in {
        "CB", "S", "FS",
        "SS", "DB"
    }:
        return "DEF_BACK"

    return p or "UNKNOWN"


def market_role(market):

    m = text(market).upper()

    if any(
        x in m
        for x in [
            "PASS_YARDS",
            "PASS_ATTEMPTS",
            "PASS_COMPLETIONS",
            "PASS_TDS",
            "PASS_COMPLETION",
        ]
    ):
        return "QB"

    if (
        "INTERCEPTIONS" in m
        and "DEF_" not in m
    ):
        return "QB"

    if any(
        x in m
        for x in [
            "REC_YARDS",
            "RECEPTIONS",
            "RECEIVING",
            "TARGETS",
            "LONGEST_RECEPTION",
        ]
    ):
        return "RECEIVER"

    if any(
        x in m
        for x in [
            "RUSH_YARDS",
            "RUSH_ATTEMPTS",
            "LONGEST_RUSH",
        ]
    ):
        return "RUSHER"

    if any(
        x in m
        for x in [
            "FG_MADE",
            "KICK_POINTS",
            "PAT_MADE",
        ]
    ):
        return "KICKER"

    if "PUNT" in m:
        return "PUNTER"

    if any(
        x in m
        for x in [
            "TACKLE",
            "SACK",
            "QB_HIT",
        ]
    ):
        return "DEFENDER"

    return "ANY"


def compatible(position, role):

    family = pos_family(position)

    if role == "ANY":
        return True

    if role == "QB":
        return family == "QB"

    if role == "RECEIVER":
        return family in {
            "RECEIVER",
            "RB",
        }

    if role == "RUSHER":
        return family in {
            "RB",
            "QB",
            "RECEIVER",
        }

    if role == "KICKER":
        return family == "KICKER"

    if role == "PUNTER":
        return family == "PUNTER"

    if role == "DEFENDER":
        return family in {
            "DEF_FRONT",
            "DEF_BACK",
        }

    return True


# ==================================================
# NFLVERSE CURRENT PLAYER IDENTITY
# ==================================================

stats = pd.read_parquet(
    STATS_FILE
)

name_col = (
    "player_display_name"
    if "player_display_name" in stats.columns
    else "player_name"
)

stats = stats[
    pd.to_numeric(
        stats["season"],
        errors="coerce",
    ).eq(2026)
].copy()

stats["week_num"] = pd.to_numeric(
    stats["week"],
    errors="coerce",
)

stats["player_key"] = (
    stats[name_col]
    .map(key)
)

stats["canonical_team"] = (
    stats["team"]
    .map(canonical_team)
)

stats["position_family"] = (
    stats["position"]
    .map(pos_family)
)

# Current identity = latest observed 2026
# record for that stable NFLverse player ID.
nv = (
    stats.sort_values(
        [
            "player_id",
            "week_num",
        ]
    )
    .drop_duplicates(
        "player_id",
        keep="last",
    )
    [
        [
            "player_id",
            name_col,
            "player_key",
            "canonical_team",
            "position",
            "position_family",
            "week_num",
        ]
    ]
    .copy()
)

nv = nv.rename(
    columns={
        name_col: "nflverse_name",
        "week_num": "nflverse_latest_week",
    }
)


# ==================================================
# SLEEPER IDENTITY
# ==================================================

sl = pd.read_csv(
    SLEEPER_FILE,
    low_memory=False,
)

sl["player_key"] = (
    sl["full_name"]
    .map(key)
)

sl["canonical_team"] = (
    sl["team"]
    .map(canonical_team)
)

sl["position_family"] = (
    sl["position"]
    .map(pos_family)
)


# ==================================================
# LIVE PROP ROWS
# ==================================================

props = pd.read_csv(
    PROP_FILE,
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
        "Live prop player column missing."
    )

team_col = next(
    (
        c for c in [
            "player_team",
            "player_team_dfs",
            "team",
        ]
        if c in props.columns
    ),
    None,
)

if team_col is None:
    raise SystemExit(
        "Live prop team column missing."
    )

props["player_key"] = (
    props[player_col]
    .map(key)
)

props["prop_team_raw"] = (
    props[team_col]
)

props["prop_team"] = (
    props[team_col]
    .map(canonical_team)
)

props["market_role"] = (
    props["market"]
    .map(market_role)
)


# ==================================================
# RESOLVE EACH PROP IDENTITY
# ==================================================

def resolve(row):

    pkey = row["player_key"]
    pteam = row["prop_team"]
    role = row["market_role"]

    candidates = nv[
        nv["player_key"].eq(
            pkey
        )
    ].copy()

    if candidates.empty:
        return pd.Series({
            "identity_status":
                "BLOCK_NO_NFLVERSE_PLAYER",
            "nflverse_player_id":
                "",
            "identity_team":
                "",
            "identity_position":
                "",
            "sleeper_match_status":
                "NOT_CHECKED",
            "sleeper_id":
                "",
        })

    same_team = candidates[
        candidates[
            "canonical_team"
        ].eq(pteam)
    ].copy()

    if same_team.empty:
        return pd.Series({
            "identity_status":
                "BLOCK_TEAM_MISMATCH",
            "nflverse_player_id":
                "",
            "identity_team":
                "",
            "identity_position":
                "",
            "sleeper_match_status":
                "NOT_CHECKED",
            "sleeper_id":
                "",
        })

    role_ok = same_team[
        same_team[
            "position"
        ].map(
            lambda p:
                compatible(
                    p,
                    role,
                )
        )
    ].copy()

    if len(role_ok) == 1:
        chosen = role_ok.iloc[0]

    elif len(role_ok) > 1:
        return pd.Series({
            "identity_status":
                "BLOCK_AMBIGUOUS_TEAM_ROLE",
            "nflverse_player_id":
                "",
            "identity_team":
                pteam,
            "identity_position":
                "",
            "sleeper_match_status":
                "NOT_CHECKED",
            "sleeper_id":
                "",
        })

    elif len(same_team) == 1:

        chosen = same_team.iloc[0]

        if role != "ANY":
            return pd.Series({
                "identity_status":
                    "BLOCK_POSITION_ROLE_MISMATCH",
                "nflverse_player_id":
                    chosen["player_id"],
                "identity_team":
                    chosen["canonical_team"],
                "identity_position":
                    chosen["position"],
                "sleeper_match_status":
                    "NOT_CHECKED",
                "sleeper_id":
                    "",
            })

    else:
        return pd.Series({
            "identity_status":
                "BLOCK_AMBIGUOUS_NAME_TEAM",
            "nflverse_player_id":
                "",
            "identity_team":
                pteam,
            "identity_position":
                "",
            "sleeper_match_status":
                "NOT_CHECKED",
            "sleeper_id":
                "",
        })

    # Sleeper confirmation using
    # canonical team + compatible role.
    sleep = sl[
        sl["player_key"].eq(
            pkey
        )
        &
        sl["canonical_team"].eq(
            pteam
        )
    ].copy()

    if not sleep.empty:

        compatible_sleep = sleep[
            sleep["position"].map(
                lambda p:
                    compatible(
                        p,
                        role,
                    )
            )
        ]

        if len(
            compatible_sleep
        ) == 1:

            sleeper_status = (
                "CONFIRMED"
            )

            sleeper_id = str(
                compatible_sleep.iloc[0][
                    "sleeper_id"
                ]
            )

        elif len(
            compatible_sleep
        ) > 1:

            sleeper_status = (
                "AMBIGUOUS"
            )

            sleeper_id = ""

        else:

            sleeper_status = (
                "TEAM_MATCH_ROLE_MISMATCH"
            )

            sleeper_id = ""

    else:

        sleeper_status = (
            "NO_TEAM_MATCH"
        )

        sleeper_id = ""

    return pd.Series({
        "identity_status":
            "VERIFIED",
        "nflverse_player_id":
            chosen["player_id"],
        "identity_team":
            chosen["canonical_team"],
        "identity_position":
            chosen["position"],
        "sleeper_match_status":
            sleeper_status,
        "sleeper_id":
            sleeper_id,
    })


resolved = props.apply(
    resolve,
    axis=1,
)

locked = pd.concat(
    [
        props.reset_index(
            drop=True
        ),
        resolved.reset_index(
            drop=True
        ),
    ],
    axis=1,
)


# ==================================================
# ADD STABLE PLAYER IDENTITY KEY
# ==================================================

locked[
    "canonical_player_identity"
] = locked.apply(
    lambda r:
        (
            str(
                r.get(
                    "nflverse_player_id",
                    "",
                )
            )
            + "|"
            + str(
                r.get(
                    "identity_team",
                    "",
                )
            )
        )
        if (
            r.get(
                "identity_status"
            )
            == "VERIFIED"
        )
        else "",
    axis=1,
)


verified = locked[
    locked[
        "identity_status"
    ].eq("VERIFIED")
].copy()


# ==================================================
# OUTPUTS
# ==================================================

locked.to_csv(
    IDENTITY
    / "NFL_PROP_IDENTITY_AUDIT_V2.csv",
    index=False,
)

verified.to_csv(
    FUSION
    / "NFL_PROP_CONTEXT_IDENTITY_LOCKED.csv",
    index=False,
)


identity_map = (
    verified[
        [
            player_col,
            "player_key",
            "prop_team",
            "market_role",
            "nflverse_player_id",
            "identity_position",
            "sleeper_id",
            "sleeper_match_status",
            "canonical_player_identity",
        ]
    ]
    .drop_duplicates()
)

identity_map.to_csv(
    IDENTITY
    / "NFL_PLAYER_IDENTITY_MAP.csv",
    index=False,
)


# ==================================================
# QA
# ==================================================

print()
print("==================================================")
print("NFL PLAYER IDENTITY LOCK")
print("==================================================")

print(
    "Prop candidates:",
    len(locked),
)

print(
    "Verified:",
    len(verified),
)

print()
print("IDENTITY STATUS:")

print(
    locked[
        "identity_status"
    ]
    .value_counts()
    .to_string()
)

print()
print("SLEEPER CROSS-CHECK:")

print(
    verified[
        "sleeper_match_status"
    ]
    .value_counts()
    .to_string()
)


qa_names = {
    key(x)
    for x in [
        "Kyler Murray",
        "Geno Smith",
        "Ladd McConkey",
        "Justin Jefferson",
        "Josh Allen",
        "Dalton Kincaid",
        "Chris Moore",
    ]
}

show = [
    player_col,
    "prop_team_raw",
    "prop_team",
    "market",
    "market_role",
    "identity_status",
    "nflverse_player_id",
    "identity_team",
    "identity_position",
    "sleeper_match_status",
    "sleeper_id",
]

print()
print("=== IDENTITY QA PLAYERS ===")

print(
    locked[
        locked[
            "player_key"
        ].isin(qa_names)
    ][show]
    .drop_duplicates()
    .head(80)
    .to_string(
        index=False
    )
)


receipt = {
    "generated_at":
        NOW.isoformat(),
    "prop_candidates":
        len(locked),
    "verified":
        len(verified),
    "blocked":
        int(
            len(locked)
            - len(verified)
        ),
    "verified_pct":
        round(
            (
                len(verified)
                / len(locked)
                * 100
            )
            if len(locked)
            else 0,
            2,
        ),
    "rule":
        (
            "Player prop identity requires "
            "canonical name + canonical team "
            "+ market-compatible position."
        ),
}

(
    IDENTITY
    / "NFL_IDENTITY_LOCK_RECEIPT.json"
).write_text(
    json.dumps(
        receipt,
        indent=2,
    )
)
