from pathlib import Path
from datetime import datetime, timezone, timedelta
import json
import math
import os
import re

import numpy as np
import pandas as pd
import requests

try:
    from dotenv import load_dotenv
    load_dotenv("/home/ubuntu/sports-hulk/.env")
except Exception:
    pass


ROOT = Path("/home/ubuntu/sports-hulk")

DEC = ROOT / "nfl_live/decision"
RAW = DEC / "raw"
HIST = DEC / "history"

GAME_FILE = (
    ROOT
    / "nfl_live/game_fusion/"
      "NFL_GAME_BETTING_RESEARCH.csv"
)

PROP_FILE = (
    ROOT
    / "nfl_live/fusion/"
      "NFL_PROP_CONTEXT_IDENTITY_LOCKED.csv"
)

PP_FILE = (
    ROOT
    / "nfl_live/fusion/"
      "NFL_PRIZEPICKS_RESEARCH.csv"
)

ALIAS_FILE = (
    ROOT
    / "nfl_live/identity/"
      "team_aliases.json"
)

NOW = datetime.now(timezone.utc)
STAMP = NOW.strftime("%Y%m%dT%H%M%SZ")
TIMEOUT = 30


# ==================================================
# GENERIC HELPERS
# ==================================================

def clean(v):
    if v is None or pd.isna(v):
        return ""
    return str(v).strip()


def norm_name(v):
    s = clean(v).lower()

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
    ALIAS_FILE.read_text()
)

TEAM_MAP = {}

def team_token(v):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        clean(v).lower(),
    )


for abbr, vals in aliases.items():

    TEAM_MAP[
        team_token(abbr)
    ] = abbr

    for v in vals:
        TEAM_MAP[
            team_token(v)
        ] = abbr


def canonical_team(v):
    k = team_token(v)

    if not k:
        return ""

    return TEAM_MAP.get(
        k,
        clean(v).upper(),
    )


def to_num(v):
    return pd.to_numeric(
        v,
        errors="coerce",
    )


def probability_pct(v):
    x = to_num(v)

    if pd.isna(x):
        return np.nan

    if x <= 1.0:
        return float(x * 100)

    return float(x)


def get_json(
    url,
    *,
    headers=None,
    params=None,
):
    try:
        r = requests.get(
            url,
            headers=headers or {},
            params=params or {},
            timeout=TIMEOUT,
        )

        try:
            payload = r.json()
        except Exception:
            payload = {}

        return r, payload

    except Exception:
        return None, {}


# ==================================================
# ESPN INJURY SCREEN
# ==================================================

print()
print("=== ESPN NFL INJURY SCREEN ===")

inj_url = (
    "https://site.api.espn.com/"
    "apis/site/v2/sports/football/nfl/injuries"
)

r, payload = get_json(
    inj_url
)

injury_http = (
    r.status_code
    if r is not None
    else None
)

print(
    "ESPN INJURY HTTP:",
    injury_http,
)

(
    RAW
    / f"ESPN_NFL_INJURIES_{STAMP}.json"
).write_text(
    json.dumps(
        payload,
        indent=2,
        default=str,
    )
)


injury_rows = []

groups = (
    payload.get(
        "injuries",
        []
    )
    if isinstance(
        payload,
        dict,
    )
    else []
)


for group in groups:

    team_obj = (
        group.get("team", {})
        if isinstance(
            group,
            dict,
        )
        else {}
    )

    team_abbr = canonical_team(
        team_obj.get(
            "abbreviation"
        )
        or team_obj.get(
            "displayName"
        )
        or team_obj.get(
            "name"
        )
    )

    entries = (
        group.get(
            "injuries",
            []
        )
        if isinstance(
            group,
            dict,
        )
        else []
    )

    for item in entries:

        athlete = (
            item.get(
                "athlete",
                {}
            )
            if isinstance(
                item,
                dict,
            )
            else {}
        )

        position = (
            athlete.get(
                "position",
                {}
            )
            if isinstance(
                athlete,
                dict,
            )
            else {}
        )

        details = (
            item.get(
                "details",
                {}
            )
            if isinstance(
                item,
                dict,
            )
            else {}
        )

        status = (
            item.get("status")
            or item.get(
                "type",
                {}
            ).get(
                "description"
            )
            if isinstance(
                item.get("type"),
                dict,
            )
            else item.get(
                "status"
            )
        )

        if not status:
            status = (
                details.get(
                    "status"
                )
                if isinstance(
                    details,
                    dict,
                )
                else ""
            )

        injury_rows.append({
            "player":
                athlete.get(
                    "fullName"
                )
                or athlete.get(
                    "displayName"
                ),

            "player_key":
                norm_name(
                    athlete.get(
                        "fullName"
                    )
                    or athlete.get(
                        "displayName"
                    )
                ),

            "team":
                team_abbr,

            "position":
                position.get(
                    "abbreviation"
                )
                if isinstance(
                    position,
                    dict,
                )
                else "",

            "status":
                clean(status),

            "injury_type":
                clean(
                    details.get(
                        "type"
                    )
                    if isinstance(
                        details,
                        dict,
                    )
                    else ""
                ),

            "detail":
                clean(
                    item.get(
                        "shortComment"
                    )
                    or item.get(
                        "longComment"
                    )
                ),
        })


injuries = pd.DataFrame(
    injury_rows
)

if injuries.empty:
    injuries = pd.DataFrame(
        columns=[
            "player",
            "player_key",
            "team",
            "position",
            "status",
            "injury_type",
            "detail",
        ]
    )


injuries.to_csv(
    DEC
    / "NFL_ESPN_INJURIES.csv",
    index=False,
)

print(
    "ESPN INJURY ROWS:",
    len(injuries),
)


def injury_gate(
    player_key,
    team_abbr,
):

    if injury_http != 200:
        return (
            "INJURY_FEED_UNVERIFIED",
            "",
        )

    x = injuries[
        injuries[
            "player_key"
        ].eq(player_key)
        &
        injuries[
            "team"
        ].eq(team_abbr)
    ]

    if x.empty:
        return (
            "NO_ESPN_LISTING",
            "",
        )

    text = " ".join(
        (
            x["status"]
            .fillna("")
            .astype(str)
            + " "
            + x[
                "injury_type"
            ]
            .fillna("")
            .astype(str)
            + " "
            + x[
                "detail"
            ]
            .fillna("")
            .astype(str)
        ).tolist()
    ).lower()

    hard = [
        "out",
        "doubtful",
        "injured reserve",
        "suspended",
        "pup",
        "inactive",
    ]

    review = [
        "questionable",
        "limited",
        "did not participate",
        "dnp",
    ]

    if any(
        w in text
        for w in hard
    ):
        return (
            "BLOCK",
            text[:300],
        )

    if any(
        w in text
        for w in review
    ):
        return (
            "REVIEW",
            text[:300],
        )

    return (
        "LISTED",
        text[:300],
    )


# ==================================================
# PLAYER PROP DECISION BRAIN
# ==================================================

print()
print("=== PLAYER PROP BRAIN ===")

props = pd.read_csv(
    PROP_FILE,
    low_memory=False,
)

player_col = next(
    c for c in [
        "player_dfs",
        "player",
        "player_sportsbook",
    ]
    if c in props.columns
)

props["player_key"] = (
    props[player_col]
    .map(norm_name)
)


def market_metric(
    row,
):

    market = clean(
        row.get(
            "market"
        )
    ).upper()

    choices = []

    if "PASS_YARDS" in market:
        choices = [
            "passing_yards_l2_avg"
        ]

    elif "PASS_ATTEMPTS" in market:
        choices = [
            "attempts_l2_avg"
        ]

    elif "PASS_COMPLETIONS" in market:
        choices = [
            "completions_l2_avg"
        ]

    elif "PASS_TDS" in market:
        choices = [
            "passing_tds_l2_avg"
        ]

    elif (
        "INTERCEPTIONS" in market
        and "DEF_" not in market
    ):
        choices = [
            "passing_interceptions_l2_avg"
        ]

    elif "RUSH_ATTEMPTS" in market:
        choices = [
            "carries_l2_avg"
        ]

    elif "RUSH_YARDS" in market:
        choices = [
            "rushing_yards_l2_avg"
        ]

    elif "REC_YARDS" in market:
        choices = [
            "receiving_yards_l2_avg"
        ]

    elif "RECEPTIONS" in market:
        choices = [
            "receptions_l2_avg"
        ]

    elif "TARGETS" in market:
        choices = [
            "targets_l2_avg"
        ]

    elif "SACKS" in market:
        choices = [
            "def_sacks_l2_avg"
        ]

    elif "TACKLES" in market:

        solo = to_num(
            row.get(
                "def_tackles_solo_l2_avg"
            )
        )

        assist = to_num(
            row.get(
                "def_tackle_assists_l2_avg"
            )
        )

        if (
            pd.notna(solo)
            or pd.notna(assist)
        ):
            return (
                (
                    0
                    if pd.isna(solo)
                    else solo
                )
                +
                (
                    0
                    if pd.isna(assist)
                    else assist
                )
            )

    for col in choices:

        if col in row.index:

            value = to_num(
                row.get(col)
            )

            if pd.notna(value):
                return float(value)

    return np.nan


def context_support(
    row,
):

    metric = market_metric(
        row
    )

    line = to_num(
        row.get(
            "dfs_line"
        )
    )

    side = clean(
        row.get(
            "side"
        )
    ).upper()

    if (
        pd.isna(metric)
        or pd.isna(line)
    ):
        return (
            "NEUTRAL",
            0,
            metric,
        )

    # For very small lines ratio can
    # become misleading, so use a
    # modest absolute threshold too.
    delta = metric - line

    threshold = max(
        abs(line) * 0.08,
        0.5,
    )

    if side == "OVER":

        if delta >= threshold:
            return (
                "SUPPORT",
                15,
                metric,
            )

        if delta >= 0:
            return (
                "MILD_SUPPORT",
                8,
                metric,
            )

        if delta <= -threshold:
            return (
                "CONTRADICT",
                -10,
                metric,
            )

    if side == "UNDER":

        if delta <= -threshold:
            return (
                "SUPPORT",
                15,
                metric,
            )

        if delta <= 0:
            return (
                "MILD_SUPPORT",
                8,
                metric,
            )

        if delta >= threshold:
            return (
                "CONTRADICT",
                -10,
                metric,
            )

    return (
        "NEUTRAL",
        0,
        metric,
    )


def prop_score(
    row,
):

    prob = probability_pct(
        row.get(
            "book_probability"
        )
    )

    books = to_num(
        row.get(
            "book_count"
        )
    )

    coverage = clean(
        row.get(
            "coverage_grade"
        )
    ).upper()

    side = clean(
        row.get(
            "side"
        )
    ).upper()

    dfs_line = to_num(
        row.get(
            "dfs_line"
        )
    )

    book_line = to_num(
        row.get(
            "sportsbook_line"
        )
    )

    score = 0.0

    # Market support: maximum 35.
    if pd.notna(prob):
        score += max(
            0,
            min(
                35,
                (
                    prob - 50
                ) * 5,
            ),
        )

    # Independent sportsbook depth.
    if pd.notna(books):

        if books >= 5:
            score += 20

        elif books >= 4:
            score += 16

        elif books >= 3:
            score += 12

        elif books >= 2:
            score += 6

    score += {
        "HIGH": 15,
        "GOOD": 12,
        "LIMITED": 6,
        "SINGLE_BOOK": 2,
    }.get(
        coverage,
        0,
    )

    # DFS-vs-book line advantage.
    favorable_gap = np.nan

    if (
        pd.notna(dfs_line)
        and
        pd.notna(book_line)
    ):

        if side == "OVER":
            favorable_gap = (
                book_line
                - dfs_line
            )

        elif side == "UNDER":
            favorable_gap = (
                dfs_line
                - book_line
            )

    if pd.notna(
        favorable_gap
    ):

        if favorable_gap >= 1.0:
            score += 15

        elif favorable_gap >= 0.5:
            score += 11

        elif favorable_gap > 0:
            score += 8

        elif favorable_gap == 0:
            score += 4

        elif favorable_gap <= -1:
            score -= 8

        else:
            score -= 4

    support, points, metric = (
        context_support(
            row
        )
    )

    score += points

    context_cov = clean(
        row.get(
            "context_coverage"
        )
    ).upper()

    if context_cov == "RICH":
        score += 5

    elif context_cov == "GOOD":
        score += 3

    return (
        round(
            max(
                0,
                min(
                    100,
                    score,
                ),
            ),
            1,
        ),
        support,
        metric,
        favorable_gap,
    )


prop_scores = props.apply(
    prop_score,
    axis=1,
)

props[
    "hulk_prop_score"
] = [
    x[0]
    for x in prop_scores
]

props[
    "context_direction"
] = [
    x[1]
    for x in prop_scores
]

props[
    "recent_metric"
] = [
    x[2]
    for x in prop_scores
]

props[
    "dfs_line_advantage"
] = [
    x[3]
    for x in prop_scores
]


# ESPN injury join/gate.
inj_results = []

for _, row in (
    props.iterrows()
):

    gate, detail = injury_gate(
        row[
            "player_key"
        ],
        canonical_team(
            row.get(
                "identity_team"
            )
        ),
    )

    inj_results.append(
        (
            gate,
            detail,
        )
    )


props[
    "espn_injury_gate"
] = [
    x[0]
    for x in inj_results
]

props[
    "espn_injury_detail"
] = [
    x[1]
    for x in inj_results
]


def prop_decision(
    row,
):

    score = to_num(
        row.get(
            "hulk_prop_score"
        )
    )

    books = to_num(
        row.get(
            "book_count"
        )
    )

    identity = clean(
        row.get(
            "identity_status"
        )
    )

    injury = clean(
        row.get(
            "espn_injury_gate"
        )
    )

    sleeper = clean(
        row.get(
            "availability_flag"
        )
    )

    context_dir = clean(
        row.get(
            "context_direction"
        )
    )

    if identity != "VERIFIED":
        return "BLOCK_IDENTITY"

    if injury == "BLOCK":
        return "BLOCK_INJURY"

    if sleeper in {
        "BLOCK_OR_OFFICIAL_REVIEW",
        "OFFICIAL_INJURY_REVIEW",
    }:
        return "INJURY_REVIEW"

    if injury == "REVIEW":
        return "INJURY_REVIEW"

    if (
        pd.isna(books)
        or books < 3
    ):
        return "PASS"

    if (
        score >= 75
        and books >= 4
        and context_dir in {
            "SUPPORT",
            "MILD_SUPPORT",
        }
    ):
        return "STRONG_RESEARCH"

    if score >= 65:
        return "QUALIFIED_RESEARCH"

    if score >= 55:
        return "WATCH"

    return "PASS"


props[
    "decision"
] = props.apply(
    prop_decision,
    axis=1,
)


# Dedupe identical selections.
dedupe_cols = [
    player_col,
    "market",
    "side",
    "dfs_line",
]

dedupe_cols = [
    c
    for c in dedupe_cols
    if c in props.columns
]

props = (
    props
    .sort_values(
        [
            "hulk_prop_score",
            "book_count",
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


props.to_csv(
    DEC
    / "NFL_PROP_DECISIONS.csv",
    index=False,
)


prop_final = props[
    props[
        "decision"
    ].isin(
        [
            "STRONG_RESEARCH",
            "QUALIFIED_RESEARCH",
        ]
    )
].copy()

prop_final.to_csv(
    DEC
    / "NFL_PROP_FINALISTS.csv",
    index=False,
)


# ==================================================
# PRIZEPICKS DECISION BOARD
# ==================================================

print()
print("=== PRIZEPICKS BRAIN ===")

pp_decisions = pd.DataFrame()

if PP_FILE.exists():

    pp = pd.read_csv(
        PP_FILE,
        low_memory=False,
    )

    pp[
        "player_key"
    ] = (
        pp["player"]
        .map(norm_name)
    )

    pp[
        "market_key"
    ] = (
        pp[
            "market_subtype"
        ]
        .fillna("")
        .astype(str)
        .str.upper()
    )

    pp["side_key"] = (
        pp["side"]
        .fillna("")
        .astype(str)
        .str.upper()
    )

    pp["line_key"] = (
        pd.to_numeric(
            pp["line"],
            errors="coerce",
        )
        .round(3)
    )

    props[
        "market_key"
    ] = (
        props["market"]
        .fillna("")
        .astype(str)
        .str.upper()
    )

    props[
        "side_key"
    ] = (
        props["side"]
        .fillna("")
        .astype(str)
        .str.upper()
    )

    props[
        "line_key"
    ] = (
        pd.to_numeric(
            props[
                "dfs_line"
            ],
            errors="coerce",
        )
        .round(3)
    )

    scored = props[
        [
            "player_key",
            "market_key",
            "side_key",
            "line_key",
            "identity_status",
            "identity_team",
            "hulk_prop_score",
            "context_direction",
            "recent_metric",
            "dfs_line_advantage",
            "book_count",
            "books",
            "coverage_grade",
            "book_probability",
            "espn_injury_gate",
            "decision",
        ]
    ].drop_duplicates(
        [
            "player_key",
            "market_key",
            "side_key",
            "line_key",
        ]
    )

    pp_decisions = pp.merge(
        scored,
        on=[
            "player_key",
            "market_key",
            "side_key",
            "line_key",
        ],
        how="left",
    )

    pp_decisions[
        "decision"
    ] = pp_decisions[
        "decision"
    ].fillna(
        "NO_FULL_EVIDENCE_MATCH"
    )

    pp_decisions.to_csv(
        DEC
        / "NFL_PRIZEPICKS_DECISIONS.csv",
        index=False,
    )

    pp_final = pp_decisions[
        pp_decisions[
            "decision"
        ].isin(
            [
                "STRONG_RESEARCH",
                "QUALIFIED_RESEARCH",
            ]
        )
    ].copy()

    pp_final.to_csv(
        DEC
        / "NFL_PRIZEPICKS_FINALISTS.csv",
        index=False,
    )

else:

    pp_final = pd.DataFrame()


# ==================================================
# GAME DECISION BRAIN
# ==================================================

print()
print("=== GAME BETTING BRAIN ===")

games = pd.read_csv(
    GAME_FILE,
    low_memory=False,
)

games["start"] = pd.to_datetime(
    games["start"],
    utc=True,
    errors="coerce",
)


def agreement_points(v):

    v = clean(v).upper()

    return {
        "AGREE": 20,
        "CLOSE": 12,
        "DISAGREE": 0,
    }.get(
        v,
        0,
    )


def quality_points(v):

    return {
        "HIGH": 25,
        "GOOD": 20,
        "LIMITED": 10,
        "INSUFFICIENT": 0,
    }.get(
        clean(v).upper(),
        0,
    )


def base_game_score(
    row,
    agreement_col,
):

    score = quality_points(
        row.get(
            "market_data_quality"
        )
    )

    score += agreement_points(
        row.get(
            agreement_col
        )
    )

    books = to_num(
        row.get(
            "sw_unique_books"
        )
    )

    if pd.notna(books):

        if books >= 8:
            score += 15

        elif books >= 5:
            score += 12

        elif books >= 3:
            score += 8

    if pd.notna(
        row.get(
            "therundown_event_id"
        )
    ):
        score += 10

    pl_books = to_num(
        row.get(
            "sportsbooks"
        )
    )

    if pd.notna(pl_books):

        if pl_books >= 20:
            score += 10

        elif pl_books >= 10:
            score += 6

    if (
        clean(
            row.get(
                "independent_context_source"
            )
        )
        not in {
            "",
            "NONE",
        }
    ):
        score += 5

    return score


game_candidates = []


for _, row in (
    games.iterrows()
):

    home_ml = to_num(
        row.get(
            "home_moneyline"
        )
    )

    away_ml = to_num(
        row.get(
            "away_moneyline"
        )
    )

    home_prob = to_num(
        row.get(
            "propline_home_devig_prob"
        )
    )

    away_prob = to_num(
        row.get(
            "propline_away_devig_prob"
        )
    )

    # ----------------------------------------------
    # MONEYLINE
    # ----------------------------------------------

    if (
        pd.notna(home_prob)
        and
        pd.notna(away_prob)
    ):

        if home_prob >= away_prob:

            selection = row[
                "home_team"
            ]

            price = home_ml
            prob = home_prob

        else:

            selection = row[
                "away_team"
            ]

            price = away_ml
            prob = away_prob

        score = base_game_score(
            row,
            "moneyline_provider_agreement",
        )

        # Probability here is market-implied
        # safety, not Hulk edge.
        if prob >= 0.70:
            score += 15

        elif prob >= 0.60:
            score += 10

        elif prob >= 0.55:
            score += 5

        score = min(
            score,
            100,
        )

        if (
            price <= -400
        ):
            decision = (
                "HIGH_JUICE_SAFETY"
            )

        elif score >= 75:
            decision = (
                "QUALIFIED_RESEARCH"
            )

        elif score >= 65:
            decision = (
                "MARKET_LEAN"
            )

        else:
            decision = "WATCH"

        game_candidates.append({
            "game_key":
                row["game_key"],

            "start":
                row["start"],

            "market":
                "MONEYLINE",

            "selection":
                selection,

            "line":
                price,

            "market_implied_safety":
                round(
                    prob * 100,
                    2,
                ),

            "hulk_market_score":
                round(
                    score,
                    1,
                ),

            "decision":
                decision,

            "market_data_quality":
                row.get(
                    "market_data_quality"
                ),

            "provider_agreement":
                row.get(
                    "moneyline_provider_agreement"
                ),

            "sw_books":
                row.get(
                    "sw_unique_books"
                ),

            "therundown_verified":
                pd.notna(
                    row.get(
                        "therundown_event_id"
                    )
                ),

            "home_spread_move":
                row.get(
                    "home_spread_move"
                ),

            "total_move":
                row.get(
                    "total_move"
                ),

            "model_status":
                (
                    "MARKET_BACKED_RESEARCH;"
                    " NOT A VALIDATED ATS MODEL"
                ),
        })


    # ----------------------------------------------
    # SPREAD — RESEARCH ONLY
    # ----------------------------------------------

    home_spread = to_num(
        row.get(
            "home_spread"
        )
    )

    away_spread = to_num(
        row.get(
            "away_spread"
        )
    )

    if (
        pd.notna(home_spread)
        and
        pd.notna(away_spread)
    ):

        if home_spread < 0:

            selection = row[
                "home_team"
            ]

            line = home_spread

        elif away_spread < 0:

            selection = row[
                "away_team"
            ]

            line = away_spread

        else:

            selection = None
            line = np.nan

        if selection:

            score = base_game_score(
                row,
                "spread_provider_agreement",
            )

            diff = to_num(
                row.get(
                    "spread_difference"
                )
            )

            if (
                pd.notna(diff)
                and diff <= 0.5
            ):
                score += 8

            elif (
                pd.notna(diff)
                and diff <= 1
            ):
                score += 4

            score = min(
                score,
                100,
            )

            # No validated ATS model:
            # never promote this to
            # STRONG_RESEARCH.
            decision = (
                "MARKET_LEAN"
                if score >= 65
                else "WATCH"
            )

            game_candidates.append({
                "game_key":
                    row["game_key"],

                "start":
                    row["start"],

                "market":
                    "SPREAD",

                "selection":
                    selection,

                "line":
                    line,

                "market_implied_safety":
                    np.nan,

                "hulk_market_score":
                    round(
                        score,
                        1,
                    ),

                "decision":
                    decision,

                "market_data_quality":
                    row.get(
                        "market_data_quality"
                    ),

                "provider_agreement":
                    row.get(
                        "spread_provider_agreement"
                    ),

                "sw_books":
                    row.get(
                        "sw_unique_books"
                    ),

                "therundown_verified":
                    pd.notna(
                        row.get(
                            "therundown_event_id"
                        )
                    ),

                "home_spread_move":
                    row.get(
                        "home_spread_move"
                    ),

                "total_move":
                    row.get(
                        "total_move"
                    ),

                "model_status":
                    (
                        "MARKET-BACKED SPREAD "
                        "RESEARCH ONLY"
                    ),
            })


    # ----------------------------------------------
    # TOTAL — REQUIRE REAL MOVEMENT
    # ----------------------------------------------

    total = to_num(
        row.get(
            "total"
        )
    )

    move = to_num(
        row.get(
            "total_move"
        )
    )

    if (
        pd.notna(total)
        and
        pd.notna(move)
        and
        abs(move) >= 0.5
    ):

        direction = (
            "OVER"
            if move > 0
            else "UNDER"
        )

        score = base_game_score(
            row,
            "total_provider_agreement",
        )

        if abs(move) >= 1.5:
            score += 12

        elif abs(move) >= 1:
            score += 8

        else:
            score += 5

        score = min(
            score,
            100,
        )

        decision = (
            "MARKET_LEAN"
            if score >= 65
            else "WATCH"
        )

        game_candidates.append({
            "game_key":
                row["game_key"],

            "start":
                row["start"],

            "market":
                "TOTAL",

            "selection":
                direction,

            "line":
                total,

            "market_implied_safety":
                np.nan,

            "hulk_market_score":
                round(
                    score,
                    1,
                ),

            "decision":
                decision,

            "market_data_quality":
                row.get(
                    "market_data_quality"
                ),

            "provider_agreement":
                row.get(
                    "total_provider_agreement"
                ),

            "sw_books":
                row.get(
                    "sw_unique_books"
                ),

            "therundown_verified":
                pd.notna(
                    row.get(
                        "therundown_event_id"
                    )
                ),

            "home_spread_move":
                row.get(
                    "home_spread_move"
                ),

            "total_move":
                move,

            "model_status":
                (
                    "MARKET-MOVEMENT TOTAL "
                    "RESEARCH ONLY"
                ),
        })


game_decisions = pd.DataFrame(
    game_candidates
)

game_decisions = (
    game_decisions
    .sort_values(
        "hulk_market_score",
        ascending=False,
    )
)


# ==================================================
# ODDSPAPI SPOT VERIFY TOP GAME FINALISTS
# ==================================================

print()
print(
    "=== ODDSPAPI FINALIST SPOT CHECK ==="
)

op_key = (
    os.getenv(
        "ODDSPAPI_API_KEY"
    )
    or ""
).strip()

game_decisions[
    "oddspapi_status"
] = "NOT_CHECKED"

game_decisions[
    "oddspapi_bookmaker_count"
] = np.nan


if op_key and not game_decisions.empty:

    later = (
        NOW
        + timedelta(
            hours=48
        )
    )

    r, fixture_payload = get_json(
        "https://api.oddspapi.io/v4/fixtures",
        params={
            "apiKey":
                op_key,

            "sportId":
                14,

            "from":
                NOW.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),

            "to":
                later.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),

            "statusId":
                0,

            "hasOdds":
                "true",

            "language":
                "en",
        },
    )

    fixtures = (
        fixture_payload
        if isinstance(
            fixture_payload,
            list,
        )
        else fixture_payload.get(
            "data",
            fixture_payload.get(
                "fixtures",
                [],
            ),
        )
        if isinstance(
            fixture_payload,
            dict,
        )
        else []
    )

    fixture_map = {}

    for f in fixtures:

        away = canonical_team(
            f.get(
                "participant1Name"
            )
        )

        home = canonical_team(
            f.get(
                "participant2Name"
            )
        )

        key1 = (
            away
            + "@"
            + home
        )

        fixture_map[
            key1
        ] = f.get(
            "fixtureId"
        )


    checked_games = set()

    for idx, row in (
        game_decisions
        .sort_values(
            "hulk_market_score",
            ascending=False,
        )
        .iterrows()
    ):

        gkey = row[
            "game_key"
        ]

        if gkey in checked_games:
            continue

        if len(
            checked_games
        ) >= 5:
            break

        fid = fixture_map.get(
            gkey
        )

        if not fid:
            game_decisions.loc[
                game_decisions[
                    "game_key"
                ].eq(gkey),
                "oddspapi_status",
            ] = "NO_FIXTURE_MATCH"

            checked_games.add(
                gkey
            )
            continue

        r2, odds_payload = (
            get_json(
                "https://api.oddspapi.io/v4/odds",
                params={
                    "apiKey":
                        op_key,

                    "fixtureId":
                        fid,

                    "oddsFormat":
                        "american",

                    "language":
                        "en",

                    "verbosity":
                        2,
                },
            )
        )

        if (
            r2 is not None
            and
            r2.status_code == 200
        ):

            books_obj = (
                odds_payload.get(
                    "bookmakerOdds"
                )
                if isinstance(
                    odds_payload,
                    dict,
                )
                else None
            )

            if isinstance(
                books_obj,
                dict,
            ):
                count = len(
                    books_obj
                )

            elif isinstance(
                books_obj,
                list,
            ):
                count = len(
                    books_obj
                )

            else:
                count = 0

            status = (
                "LIVE_ODDS_PRESENT"
                if count > 0
                else "NO_BOOKMAKER_ODDS"
            )

            (
                RAW
                / (
                    "ODDSPAPI_"
                    + str(fid)
                    + "_"
                    + STAMP
                    + ".json"
                )
            ).write_text(
                json.dumps(
                    odds_payload,
                    indent=2,
                    default=str,
                )
            )

        else:

            status = (
                "HTTP_ERROR"
            )

            count = 0

        game_decisions.loc[
            game_decisions[
                "game_key"
            ].eq(gkey),
            "oddspapi_status",
        ] = status

        game_decisions.loc[
            game_decisions[
                "game_key"
            ].eq(gkey),
            "oddspapi_bookmaker_count",
        ] = count

        checked_games.add(
            gkey
        )


game_decisions.to_csv(
    DEC
    / "NFL_GAME_DECISIONS.csv",
    index=False,
)


game_final = game_decisions[
    game_decisions[
        "decision"
    ].isin(
        [
            "QUALIFIED_RESEARCH",
            "MARKET_LEAN",
            "HIGH_JUICE_SAFETY",
        ]
    )
].copy()

game_final.to_csv(
    DEC
    / "NFL_GAME_FINALISTS.csv",
    index=False,
)


# ==================================================
# RECEIPT / ACCEPTANCE
# ==================================================

receipt = {
    "generated_at":
        NOW.isoformat(),

    "espn_injury_http":
        injury_http,

    "espn_injury_rows":
        len(injuries),

    "prop_candidates":
        len(props),

    "prop_strong":
        int(
            (
                props[
                    "decision"
                ]
                == "STRONG_RESEARCH"
            ).sum()
        ),

    "prop_qualified":
        int(
            (
                props[
                    "decision"
                ]
                == "QUALIFIED_RESEARCH"
            ).sum()
        ),

    "prop_injury_review":
        int(
            props[
                "decision"
            ]
            .isin(
                [
                    "INJURY_REVIEW",
                    "BLOCK_INJURY",
                ]
            )
            .sum()
        ),

    "prizepicks_finalists":
        int(
            len(
                pp_final
            )
        ),

    "game_candidates":
        int(
            len(
                game_decisions
            )
        ),

    "game_finalists":
        int(
            len(
                game_final
            )
        ),

    "rules": {
        "hulk_score_is_probability":
            False,

        "ats_model_validated":
            False,

        "identity_required":
            True,

        "injury_gate_required":
            True,

        "parlays_allowed":
            False,
    },
}

(
    DEC
    / "NFL_DECISION_BRAIN_RECEIPT.json"
).write_text(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print("==================================================")
print("BUILD 18 — HULK DECISION BRAIN")
print("==================================================")

print(
    "ESPN injury rows:",
    len(injuries),
)

print()
print("PROP DECISIONS:")

print(
    props[
        "decision"
    ]
    .value_counts()
    .to_string()
)

print()
print("TOP PROP FINALISTS:")

prop_show = [
    player_col,
    "market",
    "side",
    "dfs_line",
    "sportsbook_line",
    "book_count",
    "book_probability",
    "recent_metric",
    "context_direction",
    "hulk_prop_score",
    "espn_injury_gate",
    "decision",
]

prop_show = [
    c
    for c in prop_show
    if c in prop_final.columns
]

print(
    prop_final[
        prop_show
    ]
    .head(30)
    .to_string(
        index=False
    )
)


print()
print(
    "PRIZEPICKS FINALISTS:",
    len(
        pp_final
    ),
)

if not pp_final.empty:

    pp_show = [
        "player",
        "market_subtype",
        "side",
        "line",
        "book_count",
        "book_probability",
        "hulk_prop_score",
        "espn_injury_gate",
        "decision",
    ]

    pp_show = [
        c
        for c in pp_show
        if c in pp_final.columns
    ]

    print(
        pp_final[
            pp_show
        ]
        .head(30)
        .to_string(
            index=False
        )
    )


print()
print("GAME DECISIONS:")

print(
    game_decisions[
        "decision"
    ]
    .value_counts()
    .to_string()
)

print()
print("TOP GAME RESEARCH:")

print(
    game_final[
        [
            "game_key",
            "market",
            "selection",
            "line",
            "hulk_market_score",
            "decision",
            "market_data_quality",
            "provider_agreement",
            "therundown_verified",
            "oddspapi_status",
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
    "HULK scores are evidence scores, "
    "NOT probabilities."
)

print(
    "NFL spreads/totals remain "
    "market-backed research."
)

print(
    "No parlay has been generated."
)

print(
    "No production UI has been changed."
)
