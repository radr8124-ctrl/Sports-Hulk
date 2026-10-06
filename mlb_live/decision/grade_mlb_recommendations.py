#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import math
import re
import unicodedata

import pandas as pd
import requests


ROOT = Path("/home/ubuntu/sports-hulk")
MLB = ROOT / "mlb_live"
DEC = MLB / "decision"
HIST = DEC / "history"
BASEBALL = ROOT / "baseball_vault"

LEDGER = HIST / "MLB_RECOMMENDATION_LEDGER.csv"
RESULTS = BASEBALL / "history" / "MLB_RESULTS_HISTORY.csv"
SCHEDULE = BASEBALL / "latest" / "MLB_SCHEDULE.csv"

EPISODES = HIST / "MLB_RECOMMENDATION_EPISODES.csv"
GRADED = HIST / "MLB_GRADED_RECOMMENDATIONS.csv"
OUTCOMES = HIST / "MLB_OUTCOME_REVIEW.csv"
SIGNALS = HIST / "MLB_SIGNAL_PERFORMANCE.csv"
PROP_SIGNALS = HIST / "MLB_PROP_SIGNAL_PERFORMANCE.csv"
SUMMARY = HIST / "MLB_LEARNING_SUMMARY.json"

ET = ZoneInfo("America/New_York")
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Sports-HULK-MLB/1.0",
    "Accept": "application/json",
})


def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()


def clean(value):
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def norm(value):
    text = unicodedata.normalize(
        "NFKD",
        str(value or ""),
    ).encode(
        "ascii",
        "ignore",
    ).decode().lower()

    return re.sub(
        r"[^a-z0-9]+",
        "",
        text,
    )


def num(value):
    try:
        x = float(value)
        if math.isnan(x):
            return None
        return x
    except Exception:
        return None


def id_key(value):
    x = num(value)

    if x is not None and float(x).is_integer():
        return str(int(x))

    return clean(value)


def truth(value):
    return str(value).lower() in {
        "true",
        "1",
        "yes",
    }


def payload(row):
    try:
        return json.loads(
            row.get("payload_json") or "{}"
        )
    except Exception:
        return {}


def schedule_index():
    parts = []

    for path in [RESULTS, SCHEDULE]:
        d = read_csv(path)
        if not d.empty:
            parts.append(d)

    if not parts:
        return {}, {}

    d = pd.concat(
        parts,
        ignore_index=True,
        sort=False,
    )

    if "gamePk" not in d.columns:
        return {}, {}

    d["gamePk_key"] = pd.to_numeric(
        d["gamePk"],
        errors="coerce",
    ).astype("Int64").astype(str)

    if "officialDate" not in d.columns:
        d["officialDate"] = ""

    d["_away"] = d.get(
        "away_team",
        pd.Series(index=d.index, dtype=object),
    ).map(norm)

    d["_home"] = d.get(
        "home_team",
        pd.Series(index=d.index, dtype=object),
    ).map(norm)

    d["_score_known"] = (
        pd.to_numeric(
            d.get("home_score"),
            errors="coerce",
        ).notna()
        &
        pd.to_numeric(
            d.get("away_score"),
            errors="coerce",
        ).notna()
    )

    d = (
        d
        .sort_values(
            ["gamePk_key", "_score_known"]
        )
        .drop_duplicates(
            "gamePk_key",
            keep="last",
        )
    )

    by_pk = {
        str(row["gamePk_key"]):
            row.to_dict()
        for _, row in d.iterrows()
        if str(row["gamePk_key"]) not in {
            "",
            "<NA>",
            "nan",
        }
    }

    by_match = {}

    for _, row in d.iterrows():
        date = clean(row.get("officialDate"))
        away = clean(row.get("_away"))
        home = clean(row.get("_home"))

        if date and away and home:
            by_match[
                (date, away, home)
            ] = row.to_dict()

    return by_pk, by_match


def final_game(game):
    if not game:
        return False

    home = num(game.get("home_score"))
    away = num(game.get("away_score"))

    if home is None or away is None:
        return False

    status = str(
        game.get("status") or ""
    ).lower()

    return (
        "final" in status
        or status in {
            "game over",
            "completed early",
            "completed",
        }
    )


def game_from_prop(row, by_match):
    p = payload(row)

    start = pd.to_datetime(
        p.get("start"),
        utc=True,
        errors="coerce",
        format="mixed",
    )

    if pd.isna(start):
        return None

    date = (
        start
        .tz_convert(ET)
        .date()
        .isoformat()
    )

    return by_match.get(
        (
            date,
            norm(p.get("away_team")),
            norm(p.get("home_team")),
        )
    )


_BOX_CACHE = {}


def boxscore(game_pk):
    key = clean(game_pk)

    if not key:
        return {}

    if key in _BOX_CACHE:
        return _BOX_CACHE[key]

    try:
        r = SESSION.get(
            f"https://statsapi.mlb.com/api/v1/game/{key}/boxscore",
            timeout=25,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        data = {}

    _BOX_CACHE[key] = data
    return data


def player_stats(game_pk, player_id):
    data = boxscore(game_pk)

    if not data:
        return None

    player_key = "ID" + clean(player_id).split(".")[0]

    for side in ["away", "home"]:
        team = (
            data.get("teams", {})
            .get(side, {})
        )

        player = (
            team.get("players", {})
            .get(player_key)
        )

        if player:
            return player.get("stats") or {}

    return None


def innings_to_outs(value):
    if value in {None, ""}:
        return None

    text = str(value)

    try:
        if "." in text:
            a, b = text.split(".", 1)
            return int(a) * 3 + int((b or "0")[0])
        return int(float(text)) * 3
    except Exception:
        return None


def metric_value(stats, metric):
    if not stats:
        return None

    batting = stats.get("batting") or {}
    pitching = stats.get("pitching") or {}

    if metric == "hits_pg":
        return num(batting.get("hits"))

    if metric == "rbi_pg":
        return num(batting.get("rbi"))

    if metric == "runs_pg":
        return num(batting.get("runs"))

    if metric == "hrr_pg":
        values = [
            num(batting.get("hits")),
            num(batting.get("runs")),
            num(batting.get("rbi")),
        ]
        if all(v is None for v in values):
            return None
        return sum(v or 0 for v in values)

    if metric == "singles_pg":
        hits = num(batting.get("hits"))
        if hits is None:
            return None
        return max(
            0,
            hits
            - (num(batting.get("doubles")) or 0)
            - (num(batting.get("triples")) or 0)
            - (num(batting.get("homeRuns")) or 0),
        )

    if metric == "doubles_pg":
        return num(batting.get("doubles"))

    if metric == "home_runs_pg":
        return num(batting.get("homeRuns"))

    if metric == "total_bases_pg":
        return num(batting.get("totalBases"))

    if metric == "stolen_bases_pg":
        return num(batting.get("stolenBases"))

    if metric == "walks_pg":
        return num(batting.get("baseOnBalls"))

    if metric == "strikeouts_pg":
        return num(pitching.get("strikeOuts"))

    if metric == "outs_pg":
        return innings_to_outs(
            pitching.get("inningsPitched")
        )

    if metric == "hits_allowed_pg":
        return num(pitching.get("hits"))

    if metric == "earned_runs_pg":
        return num(pitching.get("earnedRuns"))

    if metric == "walks_allowed_pg":
        return num(pitching.get("baseOnBalls"))

    return None


def grade_line(actual, line, side):
    if actual is None or line is None:
        return "UNRESOLVED"

    side = str(side or "").upper()

    if actual == line:
        return "PUSH"

    if side == "OVER":
        return (
            "WIN"
            if actual > line
            else "LOSS"
        )

    if side == "UNDER":
        return (
            "WIN"
            if actual < line
            else "LOSS"
        )

    return "UNRESOLVED"


def game_grade(row, by_pk):
    p = payload(row)

    game_pk = id_key(
        row.get("official_gamePk")
    )

    game = by_pk.get(
        game_pk
    )

    if not game:
        return {
            "grade": "PENDING_GAME_MATCH",
            "context_status": "NO_GAME_MATCH",
        }

    if not final_game(game):
        return {
            "grade": "PENDING",
            "context_status": "GAME_NOT_FINAL",
            "result_gamePk": game_pk,
        }

    away_score = num(
        game.get("away_score")
    )
    home_score = num(
        game.get("home_score")
    )

    market = str(
        row.get("market")
        or p.get("market_canonical")
        or ""
    ).upper()

    side = str(
        p.get("selection_side")
        or ""
    ).upper()

    line = num(
        row.get("line")
    )

    if market == "MONEYLINE":
        if side == "HOME":
            actual = home_score - away_score
        elif side == "AWAY":
            actual = away_score - home_score
        else:
            return {
                "grade": "UNRESOLVED_SELECTION",
                "context_status": "TEAM_SIDE_UNKNOWN",
                "result_gamePk": game_pk,
            }

        grade = (
            "WIN"
            if actual > 0
            else "LOSS"
        )

    elif market == "SPREAD":
        if side == "HOME":
            margin = home_score - away_score
        elif side == "AWAY":
            margin = away_score - home_score
        else:
            return {
                "grade": "UNRESOLVED_SELECTION",
                "context_status": "TEAM_SIDE_UNKNOWN",
                "result_gamePk": game_pk,
            }

        actual = margin

        if line is None:
            grade = "UNRESOLVED"
        else:
            covered = margin + line
            grade = (
                "WIN"
                if covered > 0
                else "LOSS"
                if covered < 0
                else "PUSH"
            )

    elif market == "TOTAL":
        actual = away_score + home_score
        grade = grade_line(
            actual,
            line,
            row.get("selection"),
        )

    else:
        actual = None
        grade = "UNSUPPORTED_MARKET"

    return {
        "grade": grade,
        "context_status": "OFFICIAL_FINAL",
        "result_gamePk": game_pk,
        "away_score": away_score,
        "home_score": home_score,
        "actual_value": actual,
    }


def player_grade(row, by_match):
    game = game_from_prop(
        row,
        by_match,
    )

    if not game:
        return {
            "grade": "PENDING_GAME_MATCH",
            "context_status": "NO_GAME_MATCH",
        }

    game_pk = clean(
        game.get("gamePk_key")
        or game.get("gamePk")
    )

    if not final_game(game):
        return {
            "grade": "PENDING",
            "context_status": "GAME_NOT_FINAL",
            "result_gamePk": game_pk,
        }

    stats = player_stats(
        game_pk,
        row.get("player_id"),
    )

    if stats is None:
        return {
            "grade": "DNP",
            "context_status": "PLAYER_NOT_IN_BOXSCORE",
            "result_gamePk": game_pk,
        }

    actual = metric_value(
        stats,
        clean(row.get("metric")),
    )

    if actual is None:
        return {
            "grade": "DNP",
            "context_status": "NO_RELEVANT_STAT_APPEARANCE",
            "result_gamePk": game_pk,
        }

    grade = grade_line(
        actual,
        num(row.get("line")),
        row.get("selection"),
    )

    return {
        "grade": grade,
        "context_status": (
            "OFFICIAL_MLB_STAT_ANALYTIC_GRADE"
            if row.get("lane") == "PROP"
            else "OFFICIAL_MLB_STAT_PP_ANALYTIC_GRADE"
        ),
        "result_gamePk": game_pk,
        "actual_value": actual,
    }


def same_number(a, b):
    x = num(a)
    y = num(b)

    if x is None and y is None:
        return True

    if x is None or y is None:
        return False

    return abs(x - y) < 0.001


def parlay_grade(row, graded_rows):
    p = payload(row)
    leg_grades = []

    for leg in [1, 2]:
        lane = str(
            p.get(f"leg{leg}_lane") or ""
        ).upper()
        game = clean(
            p.get(f"leg{leg}_game")
        )
        market = clean(
            p.get(f"leg{leg}_market")
        )
        selection = clean(
            p.get(f"leg{leg}_selection")
        )
        line = p.get(
            f"leg{leg}_line"
        )
        subject = clean(
            p.get(f"leg{leg}_subject")
        )

        found = None

        for candidate in graded_rows:
            if str(candidate.get("lane") or "").upper() != lane:
                continue

            if clean(candidate.get("game_key")) != game:
                continue

            if lane == "GAME":
                if clean(candidate.get("market")) != market:
                    continue
                if clean(candidate.get("selection")) != selection:
                    continue
            else:
                if clean(candidate.get("metric")) != market:
                    continue
                if clean(candidate.get("selection")) != selection:
                    continue
                if clean(candidate.get("player")) != subject:
                    continue

            if not same_number(
                candidate.get("line"),
                line,
            ):
                continue

            found = candidate
            break

        leg_grades.append(
            found.get("grade")
            if found
            else "UNRESOLVED"
        )

    if "LOSS" in leg_grades:
        grade = "LOSS"
    elif all(x == "WIN" for x in leg_grades):
        grade = "WIN"
    elif "DNP" in leg_grades:
        grade = "DNP_REVIEW"
    elif "PENDING" in leg_grades:
        grade = "PENDING"
    elif "PUSH" in leg_grades:
        grade = "REVIEW"
    else:
        grade = "UNRESOLVED"

    return {
        "grade": grade,
        "context_status": "ANALYTIC_PARLAY_GRADE_NO_PAYOUT_CLAIM",
        "leg1_grade": leg_grades[0],
        "leg2_grade": leg_grades[1],
    }


def signal_table(graded):
    columns = [
        "lane",
        "market",
        "decision",
        "samples",
        "wins",
        "losses",
        "pushes",
        "dnps",
        "hit_rate",
        "adjustment_eligible",
        "lane_validation_eligible",
    ]

    if graded.empty:
        return pd.DataFrame(
            columns=columns
        )

    rows = []

    for keys, group in graded.groupby(
        ["lane", "market", "decision"],
        dropna=False,
    ):
        lane, market, decision = keys

        wins = int(
            group["grade"].eq("WIN").sum()
        )
        losses = int(
            group["grade"].eq("LOSS").sum()
        )
        pushes = int(
            group["grade"].eq("PUSH").sum()
        )
        dnps = int(
            group["grade"].astype(str).str.startswith("DNP").sum()
        )

        settled = wins + losses

        rows.append({
            "lane": lane,
            "market": market,
            "decision": decision,
            "samples": int(len(group)),
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "dnps": dnps,
            "hit_rate":
                wins / settled
                if settled
                else None,
            "adjustment_eligible":
                settled >= 25,
            "lane_validation_eligible":
                settled >= 100,
        })

    return pd.DataFrame(rows)


def prop_signal_table(graded):
    columns = [
        "lane",
        "metric",
        "side",
        "decision",
        "samples",
        "wins",
        "losses",
        "pushes",
        "dnps",
        "pending",
        "settled",
        "hit_rate",
        "sample_maturity",
        "adjustment_eligible",
        "lane_validation_eligible",
    ]

    if graded.empty:
        return pd.DataFrame(columns=columns)

    props = graded[
        graded["lane"].astype(str).str.upper().isin(["PROP", "PRIZEPICKS"])
    ].copy()

    if props.empty:
        return pd.DataFrame(columns=columns)

    def prop_side(payload):
        try:
            value = json.loads(payload or "{}").get("side")
            return str(value).upper() if value else "UNKNOWN"
        except Exception:
            return "UNKNOWN"

    props["_prop_side"] = props["payload_json"].map(prop_side)

    rows = []
    for keys, group in props.groupby(
        ["lane", "metric", "_prop_side", "decision"],
        dropna=False,
    ):
        lane, metric, side, decision = keys
        wins = int(group["grade"].eq("WIN").sum())
        losses = int(group["grade"].eq("LOSS").sum())
        pushes = int(group["grade"].eq("PUSH").sum())
        dnps = int(group["grade"].astype(str).str.startswith("DNP").sum())
        pending = int(group["grade"].isin(["PENDING", "UNRESOLVED", "REVIEW"]).sum())
        settled = wins + losses
        rows.append({
            "lane": lane,
            "metric": metric,
            "side": side,
            "decision": decision,
            "samples": int(len(group)),
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "dnps": dnps,
            "pending": pending,
            "settled": settled,
            "hit_rate": wins / settled if settled else None,
            "sample_maturity": (
                "VALIDATION_READY"
                if settled >= 100
                else "ADJUSTMENT_READY"
                if settled >= 25
                else "DEVELOPING"
                if settled >= 10
                else "EXPLORATORY"
            ),
            "adjustment_eligible": settled >= 25,
            "lane_validation_eligible": settled >= 100,
        })

    return (
        pd.DataFrame(rows)
        .sort_values(["lane", "settled", "metric"], ascending=[True, False, True])
        .reset_index(drop=True)
    )


def main():
    HIST.mkdir(parents=True, exist_ok=True)

    ledger = read_csv(LEDGER)

    if ledger.empty:
        episodes = pd.DataFrame()
        graded = pd.DataFrame()
        signals = signal_table(graded)
        episodes.to_csv(EPISODES, index=False)
        graded.to_csv(GRADED, index=False)
        graded.to_csv(OUTCOMES, index=False)
        signals.to_csv(SIGNALS, index=False)
        prop_signal_table(graded).to_csv(PROP_SIGNALS, index=False)

        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ledger_rows": 0,
            "unique_recommendations": 0,
            "graded_rows": 0,
            "settled": 0,
            "grade_counts": {},
            "signal_rows": 0,
            "minimum_samples_before_adjustment": 25,
            "minimum_samples_before_lane_validation": 100,
            "automatic_model_adjustment": False,
            "dnp_is_not_loss": True,
            "spread_model_validated": False,
            "totals_model_validated": False,
            "prizepicks_platform_settlement_claim": False,
            "parlay_payout_claim": False,
        }

        SUMMARY.write_text(
            json.dumps(
                summary,
                indent=2,
                sort_keys=True,
            )
        )

        print("LEDGER ROWS: 0")
        print("RESULT: MLB_LEARNING_READY")
        return

    ledger["_snapshot"] = pd.to_datetime(
        ledger["snapshot_at"],
        utc=True,
        errors="coerce",
    )

    episodes = (
        ledger
        .sort_values("_snapshot")
        .drop_duplicates(
            "recommendation_key",
            keep="last",
        )
        .drop(
            columns=["_snapshot"]
        )
    )

    episodes.to_csv(
        EPISODES,
        index=False,
    )

    by_pk, by_match = schedule_index()
    graded_rows = []

    for _, row in episodes.iterrows():
        lane = str(
            row.get("lane") or ""
        ).upper()

        if lane == "PARLAY":
            continue

        if lane == "GAME":
            result = game_grade(
                row.to_dict(),
                by_pk,
            )
        else:
            result = player_grade(
                row.to_dict(),
                by_match,
            )

        graded_rows.append({
            **row.to_dict(),
            **result,
        })

    base_grades = list(
        graded_rows
    )

    for _, row in episodes.iterrows():
        if str(
            row.get("lane") or ""
        ).upper() != "PARLAY":
            continue

        graded_rows.append({
            **row.to_dict(),
            **parlay_grade(
                row.to_dict(),
                base_grades,
            ),
        })

    graded = pd.DataFrame(
        graded_rows
    )

    graded.to_csv(
        GRADED,
        index=False,
    )

    outcome = graded.copy()

    if not outcome.empty:
        outcome["outcome_review"] = outcome["grade"].map(
            lambda x:
                "SETTLED"
                if x in {"WIN", "LOSS", "PUSH"}
                else "DNP_NOT_LOSS"
                if str(x).startswith("DNP")
                else "UNSETTLED"
        )

    outcome.to_csv(
        OUTCOMES,
        index=False,
    )

    signals = signal_table(
        graded
    )

    signals.to_csv(
        SIGNALS,
        index=False,
    )

    prop_signals = prop_signal_table(graded)
    prop_signals.to_csv(
        PROP_SIGNALS,
        index=False,
    )

    counts = (
        graded["grade"]
        .fillna("UNKNOWN")
        .value_counts()
        .to_dict()
    )

    settled = int(
        graded["grade"].isin(
            ["WIN", "LOSS", "PUSH"]
        ).sum()
    )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ledger_rows": int(len(ledger)),
        "unique_recommendations": int(len(episodes)),
        "graded_rows": int(len(graded)),
        "settled": settled,
        "grade_counts": {
            str(k): int(v)
            for k, v in counts.items()
        },
        "signal_rows": int(len(signals)),
        "prop_metric_signal_rows": int(len(prop_signals)),
        "minimum_samples_before_adjustment": 25,
        "minimum_samples_before_lane_validation": 100,
        "automatic_model_adjustment": False,
        "dnp_is_not_loss": True,
        "spread_model_validated": False,
        "totals_model_validated": False,
        "prizepicks_platform_settlement_claim": False,
        "parlay_payout_claim": False,
    }

    SUMMARY.write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )

    print("LEDGER ROWS:", len(ledger))
    print("UNIQUE RECOMMENDATIONS:", len(episodes))
    print("GRADED ROWS:", len(graded))
    print("SETTLED:", settled)
    print("GRADE COUNTS:", counts)
    print("SIGNAL GROUPS:", len(signals))
    print("RESULT: MLB_LEARNING_READY")


if __name__ == "__main__":
    main()
