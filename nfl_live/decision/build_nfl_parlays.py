from pathlib import Path
from datetime import datetime, timezone
from itertools import combinations
import json
import re

import numpy as np
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
DEC = ROOT / "nfl_live/decision"

NOW = datetime.now(timezone.utc)


def clean(v):
    if v is None or pd.isna(v):
        return ""
    return str(v).strip()


def num(v):
    return pd.to_numeric(
        v,
        errors="coerce",
    )


def norm_name(v):
    x = clean(v).lower()

    return re.sub(
        r"[^a-z0-9]+",
        "",
        x,
    )


def first_value(row, names):

    for name in names:

        if name not in row.index:
            continue

        value = row.get(name)

        if (
            value is not None
            and not pd.isna(value)
            and clean(value)
        ):
            return clean(value)

    return ""


def event_key(row):

    # Prefer a provider event ID.
    value = first_value(
        row,
        [
            "event_id_dfs",
            "event_id",
            "event_id_sportsbook",
            "canonical_event_id",
        ],
    )

    if value:
        return value

    # Fallback to matchup identity.
    away = first_value(
        row,
        [
            "away_team_dfs",
            "away_team_sportsbook",
            "away_team",
        ],
    )

    home = first_value(
        row,
        [
            "home_team_dfs",
            "home_team_sportsbook",
            "home_team",
        ],
    )

    if away and home:
        return (
            away.lower()
            + "@"
            + home.lower()
        )

    return ""


# ==================================================
# LOAD FINALISTS
# ==================================================

prop_file = DEC / "NFL_PROP_FINALISTS.csv"
pp_file = DEC / "NFL_PRIZEPICKS_FINALISTS.csv"
game_file = DEC / "NFL_GAME_FINALISTS.csv"

props = pd.read_csv(
    prop_file,
    low_memory=False,
)

pp = (
    pd.read_csv(
        pp_file,
        low_memory=False,
    )
    if pp_file.exists()
    and pp_file.stat().st_size > 1
    else pd.DataFrame()
)

games = pd.read_csv(
    game_file,
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


# ==================================================
# PROP LEG POOL
# ==================================================

prop_legs = []

for _, r in props.iterrows():

    if clean(
        r.get("decision")
    ) not in {
        "STRONG_RESEARCH",
        "QUALIFIED_RESEARCH",
    }:
        continue

    sample = num(
        r.get(
            "meaningful_completed_games"
        )
    )

    if (
        pd.isna(sample)
        or sample < 2
    ):
        continue

    if clean(
        r.get(
            "espn_injury_gate"
        )
    ) in {
        "BLOCK",
        "REVIEW",
        "INJURY_FEED_UNVERIFIED",
    }:
        continue

    ek = event_key(r)

    # For an actual qualified parlay,
    # game identity must be known.
    if not ek:
        continue

    player = clean(
        r.get(player_col)
    )

    market = clean(
        r.get("market")
    )

    side = clean(
        r.get("side")
    )

    line = num(
        r.get("dfs_line")
    )

    score = num(
        r.get(
            "hulk_prop_score"
        )
    )

    books = num(
        r.get("book_count")
    )

    prop_legs.append({
        "kind": "PROP",
        "event_key": ek,
        "player": player,
        "player_key":
            norm_name(player),
        "market": market,
        "selection": side,
        "line": line,
        "score": score,
        "book_count": books,
        "decision":
            clean(
                r.get(
                    "decision"
                )
            ),
        "label": (
            f"{player} "
            f"{side} {line} "
            f"{market}"
        ),
    })


# ==================================================
# PRIZEPICKS LEG POOL
# ==================================================

pp_legs = []

if not pp.empty:

    for _, r in pp.iterrows():

        if clean(
            r.get("decision")
        ) not in {
            "STRONG_RESEARCH",
            "QUALIFIED_RESEARCH",
        }:
            continue

        sample = num(
            r.get(
                "meaningful_completed_games"
            )
        )

        if (
            pd.isna(sample)
            or sample < 2
        ):
            continue

        if clean(
            r.get(
                "espn_injury_gate"
            )
        ) in {
            "BLOCK",
            "REVIEW",
            "INJURY_FEED_UNVERIFIED",
        }:
            continue

        ek = event_key(r)

        if not ek:
            continue

        player = clean(
            r.get("player")
        )

        market = clean(
            r.get(
                "market_subtype"
            )
        )

        side = clean(
            r.get("side")
        )

        line = num(
            r.get("line")
        )

        pp_legs.append({
            "kind":
                "PRIZEPICKS",
            "event_key":
                ek,
            "player":
                player,
            "player_key":
                norm_name(
                    player
                ),
            "market":
                market,
            "selection":
                side,
            "line":
                line,
            "score":
                num(
                    r.get(
                        "hulk_prop_score"
                    )
                ),
            "book_count":
                num(
                    r.get(
                        "book_count"
                    )
                ),
            "decision":
                clean(
                    r.get(
                        "decision"
                    )
                ),
            "label": (
                f"{player} "
                f"{side} {line} "
                f"{market}"
            ),
        })


# ==================================================
# GAME LEG POOL
# ==================================================

game_legs = []

for _, r in games.iterrows():

    market = clean(
        r.get("market")
    ).upper()

    decision = clean(
        r.get("decision")
    )

    # We intentionally do not use NFL
    # spreads/totals in qualified parlays
    # until an ATS/totals model is validated.
    if market != "MONEYLINE":
        continue

    if decision not in {
        "QUALIFIED_RESEARCH",
        "HIGH_JUICE_SAFETY",
    }:
        continue

    gkey = clean(
        r.get("game_key")
    )

    if not gkey:
        continue

    selection = clean(
        r.get("selection")
    )

    line = num(
        r.get("line")
    )

    score = num(
        r.get(
            "hulk_market_score"
        )
    )

    game_legs.append({
        "kind":
            "GAME_ML",
        "event_key":
            gkey,
        "player":
            "",
        "player_key":
            "",
        "market":
            "MONEYLINE",
        "selection":
            selection,
        "line":
            line,
        "score":
            score,
        "book_count":
            num(
                r.get(
                    "sw_books"
                )
            ),
        "decision":
            decision,
        "label": (
            f"{selection} ML "
            f"({line:+.0f})"
        )
        if pd.notna(line)
        else f"{selection} ML",
    })


# ==================================================
# BUILD TWO-LEG PARLAYS
# ==================================================

rows = []


def append_parlay(
    parlay_type,
    a,
    b,
):

    # Absolutely no duplicate player.
    if (
        a["player_key"]
        and
        a["player_key"]
        == b["player_key"]
    ):
        return

    # Only different-game parlays are
    # considered qualified at launch.
    if (
        not a["event_key"]
        or
        not b["event_key"]
        or
        a["event_key"]
        == b["event_key"]
    ):
        return

    scores = [
        x
        for x in [
            num(
                a.get("score")
            ),
            num(
                b.get("score")
            ),
        ]
        if pd.notna(x)
    ]

    if len(scores) != 2:
        return

    avg_score = (
        scores[0]
        + scores[1]
    ) / 2

    floor_score = min(
        scores
    )

    # Reward two independently good
    # legs; do not calculate a fake
    # parlay win probability.
    parlay_score = round(
        (
            avg_score * 0.65
            + floor_score * 0.35
        ),
        1,
    )

    rows.append({
        "parlay_type":
            parlay_type,
        "leg_count":
            2,
        "parlay_score":
            parlay_score,
        "correlation_status":
            "VERIFIED_DIFFERENT_GAMES",
        "probability_status":
            "NOT_CALCULATED",
        "payout_status":
            "VERIFY_AT_SPORTSBOOK",
        "leg1_kind":
            a["kind"],
        "leg1_event":
            a["event_key"],
        "leg1_player":
            a["player"],
        "leg1_market":
            a["market"],
        "leg1_selection":
            a["selection"],
        "leg1_line":
            a["line"],
        "leg1_score":
            a["score"],
        "leg1_label":
            a["label"],
        "leg2_kind":
            b["kind"],
        "leg2_event":
            b["event_key"],
        "leg2_player":
            b["player"],
        "leg2_market":
            b["market"],
        "leg2_selection":
            b["selection"],
        "leg2_line":
            b["line"],
        "leg2_score":
            b["score"],
        "leg2_label":
            b["label"],
        "leg_summary":
            (
                a["label"]
                + " + "
                + b["label"]
            ),
        "status":
            "QUALIFIED_RESEARCH",
        "generated_at":
            NOW.isoformat(),
    })


# Player-prop parlays.
for a, b in combinations(
    prop_legs,
    2,
):
    append_parlay(
        "PLAYER_PROP_2_LEG",
        a,
        b,
    )


# PrizePicks cards.
pp_rows = []

for a, b in combinations(
    pp_legs,
    2,
):

    before = len(rows)

    append_parlay(
        "PRIZEPICKS_2_PICK",
        a,
        b,
    )

    if len(rows) > before:
        pp_rows.append(
            rows[-1].copy()
        )


# Game ML parlays.
for a, b in combinations(
    game_legs,
    2,
):
    append_parlay(
        "GAME_ML_2_LEG",
        a,
        b,
    )


# Mixed ML + prop parlays.
for a in game_legs:
    for b in prop_legs:

        append_parlay(
            "MIXED_ML_PROP_2_LEG",
            a,
            b,
        )


parlays = pd.DataFrame(rows)


if parlays.empty:
    raise SystemExit(
        "No qualified NFL parlay "
        "combinations produced."
    )


# ==================================================
# PARLAY DEDUPE
# ==================================================

def canonical_legs(r):

    return "||".join(
        sorted(
            [
                clean(
                    r[
                        "leg1_label"
                    ]
                ),
                clean(
                    r[
                        "leg2_label"
                    ]
                ),
            ]
        )
    )


parlays[
    "_canonical"
] = parlays.apply(
    canonical_legs,
    axis=1,
)

parlays = (
    parlays
    .sort_values(
        "parlay_score",
        ascending=False,
    )
    .drop_duplicates(
        "_canonical",
        keep="first",
    )
    .drop(
        columns=[
            "_canonical"
        ]
    )
)


# Limit the production research board
# while preserving full candidates.
parlays.to_csv(
    DEC
    / "NFL_PARLAY_CANDIDATES.csv",
    index=False,
)


top_parts = []

for ptype, n in [
    ("PLAYER_PROP_2_LEG", 8),
    ("PRIZEPICKS_2_PICK", 8),
    ("GAME_ML_2_LEG", 6),
    ("MIXED_ML_PROP_2_LEG", 8),
]:

    x = parlays[
        parlays[
            "parlay_type"
        ].eq(ptype)
    ].head(n)

    if not x.empty:
        top_parts.append(x)


today = (
    pd.concat(
        top_parts,
        ignore_index=True,
    )
    if top_parts
    else pd.DataFrame()
)

today = today.sort_values(
    "parlay_score",
    ascending=False,
)

today.to_csv(
    DEC
    / "NFL_PARLAYS_TODAY.csv",
    index=False,
)


pp_cards = parlays[
    parlays[
        "parlay_type"
    ].eq(
        "PRIZEPICKS_2_PICK"
    )
].copy()

pp_cards.to_csv(
    DEC
    / "NFL_PRIZEPICKS_CARDS.csv",
    index=False,
)


# ==================================================
# RECEIPT
# ==================================================

receipt = {
    "generated_at":
        NOW.isoformat(),

    "qualified_prop_legs":
        len(prop_legs),

    "qualified_prizepicks_legs":
        len(pp_legs),

    "qualified_game_ml_legs":
        len(game_legs),

    "candidate_parlays":
        len(parlays),

    "today_parlays":
        len(today),

    "prizepicks_cards":
        len(pp_cards),

    "parlay_types":
        parlays[
            "parlay_type"
        ]
        .value_counts()
        .to_dict(),

    "rules": {
        "leg_count":
            2,
        "different_games_required":
            True,
        "same_player_forbidden":
            True,
        "spreads_allowed":
            False,
        "totals_allowed":
            False,
        "fake_probability_allowed":
            False,
        "fake_payout_allowed":
            False,
    },
}

(
    DEC
    / "NFL_PARLAY_RECEIPT.json"
).write_text(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print("==================================================")
print("NFL PARLAY ENGINE")
print("==================================================")

print(
    "Qualified prop legs:",
    len(prop_legs),
)

print(
    "Qualified PrizePicks legs:",
    len(pp_legs),
)

print(
    "Qualified game ML legs:",
    len(game_legs),
)

print(
    "Parlay candidates:",
    len(parlays),
)

print()
print("PARLAY TYPES:")

print(
    parlays[
        "parlay_type"
    ]
    .value_counts()
    .to_string()
)


print()
print("=== TOP PARLAYS ===")

print(
    today[
        [
            "parlay_type",
            "parlay_score",
            "leg1_label",
            "leg2_label",
            "correlation_status",
        ]
    ]
    .head(25)
    .to_string(
        index=False
    )
)


print()
print("IMPORTANT:")
print(
    "Parlay score is an evidence score, "
    "not a win probability."
)

print(
    "No sportsbook payout is fabricated."
)

print(
    "All qualified launch parlays use "
    "different games."
)

print(
    "Spread and total legs remain excluded "
    "until those models are validated."
)
