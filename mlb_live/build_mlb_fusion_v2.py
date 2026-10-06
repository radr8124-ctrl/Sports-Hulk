#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import math
import re
import unicodedata

import numpy as np
import pandas as pd
import requests


ROOT = Path("/home/ubuntu/sports-hulk")
MLB = ROOT / "mlb_live"
DERIVED = MLB / "derived"
MARKETS = MLB / "markets" / "current"
RECEIPTS = MLB / "markets" / "receipts"
BASEBALL = ROOT / "baseball_vault"

SCHEDULE = BASEBALL / "latest" / "MLB_SCHEDULE.csv"
BULLPEN = BASEBALL / "latest" / "MLB_BULLPEN_WORKLOAD.csv"
GAME_MASTER = BASEBALL / "derived" / "MLB_GAME_MASTER.csv"

RAW_GAME = MARKETS / "MLB_GAME_MARKET.csv"
RAW_PROP = MARKETS / "MLB_PLAYER_PROP_MARKET.csv"
RAW_PP = MARKETS / "MLB_PRIZEPICKS_MARKET.csv"

PLAYER_CONTEXT_OUT = DERIVED / "MLB_PLAYER_CONTEXT.csv"
GAME_CONTEXT_OUT = DERIVED / "MLB_GAME_CONTEXT.csv"
GAME_FUSION_OUT = MARKETS / "MLB_GAME_FUSION.csv"
PROP_FUSION_OUT = MARKETS / "MLB_PROP_FUSION.csv"
PP_FUSION_OUT = MARKETS / "MLB_PRIZEPICKS_FUSION.csv"
RECEIPT_OUT = RECEIPTS / "MLB_FUSION_RECEIPT_LATEST.json"

ET = ZoneInfo("America/New_York")
TODAY = datetime.now(ET).date()
RECENT_START = TODAY - timedelta(days=14)


STAT_MAP = {
    "PLAYER_TOTAL_HITS": ("hits_pg", "HITTING"),
    "PLAYER_TOTAL_RBIS": ("rbi_pg", "HITTING"),
    "PLAYER_TOTAL_RUNS": ("runs_pg", "HITTING"),
    "PLAYER_TOTAL_HITS_+_RUNS_+_RBIS": ("hrr_pg", "HITTING"),
    "PLAYER_TOTAL_SINGLES": ("singles_pg", "HITTING"),
    "PLAYER_TOTAL_DOUBLES": ("doubles_pg", "HITTING"),
    "PLAYER_TOTAL_HOME_RUNS": ("home_runs_pg", "HITTING"),
    "PLAYER_TOTAL_TOTAL_BASES": ("total_bases_pg", "HITTING"),
    "PLAYER_TOTAL_STOLEN_BASES": ("stolen_bases_pg", "HITTING"),
    "PLAYER_TOTAL_BATTER_WALKS": ("walks_pg", "HITTING"),
    "PLAYER_TOTAL_PITCHER_STRIKEOUTS": ("strikeouts_pg", "PITCHING"),
    "PLAYER_TOTAL_PITCHING_OUTS": ("outs_pg", "PITCHING"),
    "PLAYER_TOTAL_HITS_ALLOWED": ("hits_allowed_pg", "PITCHING"),
    "PLAYER_TOTAL_EARNED_RUNS_ALLOWED": ("earned_runs_pg", "PITCHING"),
    "PLAYER_TOTAL_WALKS_ALLOWED": ("walks_allowed_pg", "PITCHING"),
}


def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()


def ascii_text(value):
    value = str(value or "")
    return (
        unicodedata
        .normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode()
    )


def norm(value):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        ascii_text(value).lower(),
    )


def name_alias(value):
    parts = re.findall(
        r"[A-Za-z0-9]+",
        ascii_text(value).lower(),
    )
    if not parts:
        return ""
    return parts[0][0] + parts[-1]


def num(value):
    try:
        x = float(value)
        if math.isnan(x):
            return None
        return x
    except Exception:
        return None


def per_game(stat, field, denom):
    value = num(stat.get(field))
    if value is None or not denom:
        return None
    return value / denom


def fetch_stats(group, stats, **extra):
    params = {
        "stats": stats,
        "group": group,
        "sportIds": 1,
        "playerPool": "ALL",
        "limit": 5000,
        **extra,
    }
    r = requests.get(
        "https://statsapi.mlb.com/api/v1/stats",
        params=params,
        headers={"User-Agent": "Sports-HULK/1.0"},
        timeout=30,
    )
    r.raise_for_status()
    payload = r.json()
    blocks = payload.get("stats") or []
    if not blocks:
        return []
    return blocks[0].get("splits") or []


def context_rows(splits, group, period):
    rows = []

    for split in splits:
        player = split.get("player") or {}
        team = split.get("team") or {}
        position = split.get("position") or {}
        stat = split.get("stat") or {}

        gp = int(num(stat.get("gamesPlayed")) or 0)

        if group == "PITCHING":
            gs = int(num(stat.get("gamesStarted")) or 0)
            # All *_pg fields are per pitching appearance. Using gamesStarted
            # here inflated swingmen/relievers who happened to make a start.
            denom = gp
        else:
            gs = 0
            denom = gp

        hits = num(stat.get("hits")) or 0
        doubles = num(stat.get("doubles")) or 0
        triples = num(stat.get("triples")) or 0
        homers = num(stat.get("homeRuns")) or 0
        singles = max(0, hits - doubles - triples - homers)

        outs = num(stat.get("outsPitched"))
        if outs is None:
            ip = str(stat.get("inningsPitched") or "")
            if "." in ip:
                a, b = ip.split(".", 1)
                try:
                    outs = int(a) * 3 + int((b or "0")[0])
                except Exception:
                    outs = None
            else:
                try:
                    outs = int(float(ip)) * 3
                except Exception:
                    outs = None

        rows.append({
            "player_id": player.get("id"),
            "player": player.get("fullName"),
            "player_key": norm(player.get("fullName")),
            "name_alias": name_alias(player.get("fullName")),
            "team": team.get("name"),
            "position": position.get("abbreviation"),
            "group": group,
            "period": period,
            "games": gp,
            "games_started": gs,
            "hits_pg": per_game(stat, "hits", denom),
            "runs_pg": per_game(stat, "runs", denom),
            "rbi_pg": per_game(stat, "rbi", denom),
            "doubles_pg": per_game(stat, "doubles", denom),
            "home_runs_pg": per_game(stat, "homeRuns", denom),
            "stolen_bases_pg": per_game(stat, "stolenBases", denom),
            "walks_pg": per_game(stat, "baseOnBalls", denom),
            "total_bases_pg": per_game(stat, "totalBases", denom),
            "singles_pg": (singles / denom) if denom else None,
            "hrr_pg": (
                (
                    (num(stat.get("hits")) or 0)
                    + (num(stat.get("runs")) or 0)
                    + (num(stat.get("rbi")) or 0)
                ) / denom
                if denom else None
            ),
            "strikeouts_pg": per_game(stat, "strikeOuts", denom),
            "outs_pg": (outs / denom) if outs is not None and denom else None,
            "hits_allowed_pg": per_game(stat, "hits", denom),
            "earned_runs_pg": per_game(stat, "earnedRuns", denom),
            "walks_allowed_pg": per_game(stat, "baseOnBalls", denom),
        })

    return rows


def build_player_context():
    season_hit = fetch_stats(
        "hitting",
        "season",
        season=2026,
    )
    season_pitch = fetch_stats(
        "pitching",
        "season",
        season=2026,
    )
    recent_hit = fetch_stats(
        "hitting",
        "byDateRange",
        startDate=RECENT_START.isoformat(),
        endDate=TODAY.isoformat(),
    )
    recent_pitch = fetch_stats(
        "pitching",
        "byDateRange",
        startDate=RECENT_START.isoformat(),
        endDate=TODAY.isoformat(),
    )

    rows = []
    rows += context_rows(season_hit, "HITTING", "SEASON")
    rows += context_rows(season_pitch, "PITCHING", "SEASON")
    rows += context_rows(recent_hit, "HITTING", "RECENT")
    rows += context_rows(recent_pitch, "PITCHING", "RECENT")

    raw = pd.DataFrame(rows)

    if raw.empty:
        raw.to_csv(PLAYER_CONTEXT_OUT, index=False)
        return raw

    metrics = [
        "hits_pg", "runs_pg", "rbi_pg", "doubles_pg",
        "home_runs_pg", "stolen_bases_pg", "walks_pg",
        "total_bases_pg", "singles_pg", "hrr_pg",
        "strikeouts_pg", "outs_pg", "hits_allowed_pg",
        "earned_runs_pg", "walks_allowed_pg",
    ]

    base_cols = [
        "player_id", "player", "player_key", "name_alias",
        "team", "position", "group",
    ]

    season = raw[raw["period"].eq("SEASON")].copy()
    recent = raw[raw["period"].eq("RECENT")].copy()

    season = season.rename(columns={
        "games": "season_games",
        "games_started": "season_games_started",
        **{m: "season_" + m for m in metrics},
    })

    recent = recent.rename(columns={
        "games": "recent_games",
        "games_started": "recent_games_started",
        **{m: "recent_" + m for m in metrics},
    })

    keep_recent = [
        "player_id", "group", "recent_games",
        "recent_games_started",
        *["recent_" + m for m in metrics],
    ]

    out = season[
        base_cols
        + ["season_games", "season_games_started"]
        + ["season_" + m for m in metrics]
    ].merge(
        recent[keep_recent],
        on=["player_id", "group"],
        how="left",
    )

    out.to_csv(PLAYER_CONTEXT_OUT, index=False)
    return out


def player_lookup(context):
    exact = {}
    alias = {}

    for _, row in context.iterrows():
        key = str(row.get("player_key") or "")
        group = str(row.get("group") or "")

        if key:
            exact.setdefault((key, group), []).append(row.to_dict())

        a = str(row.get("name_alias") or "")
        if a:
            alias.setdefault((a, group), []).append(row.to_dict())

    return exact, alias


def resolve_player(value, group, exact, alias):
    key = norm(value)
    matches = exact.get((key, group), [])

    if len(matches) == 1:
        return matches[0]

    a = name_alias(value)
    matches = alias.get((a, group), [])

    if len(matches) == 1:
        return matches[0]

    return None


def build_team_history():
    d = read_csv(GAME_MASTER)

    if d.empty:
        return pd.DataFrame()

    d["game_dt"] = pd.to_datetime(
        d["gameDate"],
        utc=True,
        errors="coerce",
    )
    d["home_score"] = pd.to_numeric(
        d["home_score"],
        errors="coerce",
    )
    d["away_score"] = pd.to_numeric(
        d["away_score"],
        errors="coerce",
    )
    d = d[
        d["home_score"].notna()
        & d["away_score"].notna()
    ].copy()

    home = pd.DataFrame({
        "game_dt": d["game_dt"],
        "team": d["home_team"],
        "runs_for": d["home_score"],
        "runs_against": d["away_score"],
        "margin": d["home_score"] - d["away_score"],
    })

    away = pd.DataFrame({
        "game_dt": d["game_dt"],
        "team": d["away_team"],
        "runs_for": d["away_score"],
        "runs_against": d["home_score"],
        "margin": d["away_score"] - d["home_score"],
    })

    x = pd.concat(
        [home, away],
        ignore_index=True,
    )
    x["win"] = (x["margin"] > 0).astype(int)
    return x.sort_values(["team", "game_dt"])


def team_state(history, team, before):
    d = history[
        history["team"].astype(str).eq(str(team))
        & history["game_dt"].lt(before)
    ].tail(10).copy()

    if len(d) < 5:
        return None

    def tail_avg(col, n):
        return float(
            pd.to_numeric(
                d.tail(n)[col],
                errors="coerce",
            ).mean()
        )

    return {
        "games_available": len(d),
        "winpct_5": tail_avg("win", 5),
        "run_diff_5": tail_avg("margin", 5),
        "run_diff_10": tail_avg("margin", 10),
        "runs_for_5": tail_avg("runs_for", 5),
        "runs_against_5": tail_avg("runs_against", 5),
        "rest_days": float(
            (before - d.iloc[-1]["game_dt"]).total_seconds()
            / 86400.0
        ),
    }


def build_game_context(raw_game):
    schedule = read_csv(SCHEDULE)
    history = build_team_history()
    bullpen = read_csv(BULLPEN)

    if raw_game.empty:
        out = pd.DataFrame()
        out.to_csv(GAME_CONTEXT_OUT, index=False)
        return out

    schedule_map = {}

    if not schedule.empty:
        schedule["game_dt"] = pd.to_datetime(
            schedule["gameDate"],
            utc=True,
            errors="coerce",
        )

        for _, row in schedule.iterrows():
            key = (
                str(row.get("officialDate")),
                norm(row.get("away_team")),
                norm(row.get("home_team")),
            )
            schedule_map[key] = row.to_dict()

    bullpen_team = {}

    if not bullpen.empty:
        for team, group in bullpen.groupby("team"):
            bullpen_team[str(team)] = float(
                pd.to_numeric(
                    group["HULK_bullpen_workload_score"],
                    errors="coerce",
                ).fillna(0).sum()
            )

    raw = raw_game.copy()
    raw["start_dt"] = pd.to_datetime(
        raw["start"],
        utc=True,
        errors="coerce",
        format="mixed",
    )
    raw["game_date"] = raw["start_dt"].dt.tz_convert(ET).dt.date.astype(str)
    raw["away_key"] = raw["away_team"].map(norm)
    raw["home_key"] = raw["home_team"].map(norm)

    unique = (
        raw[
            [
                "game_date", "away_key", "home_key",
                "away_team", "home_team", "start_dt",
            ]
        ]
        .drop_duplicates(
            ["game_date", "away_key", "home_key"]
        )
    )

    rows = []

    for _, row in unique.iterrows():
        start = row.get("start_dt")
        away = row.get("away_team")
        home = row.get("home_team")

        if pd.isna(start):
            continue

        a = team_state(history, away, start)
        h = team_state(history, home, start)

        official = schedule_map.get(
            (
                row.get("game_date"),
                row.get("away_key"),
                row.get("home_key"),
            )
        )

        rows.append({
            "game_key":
                f"{row.get('game_date')}|{row.get('away_key')}|{row.get('home_key')}",
            "game_date": row.get("game_date"),
            "start_dt": start,
            "away_team": away,
            "home_team": home,
            "official_match": bool(official),
            "official_gamePk":
                official.get("gamePk") if official else None,
            "venue":
                official.get("venue") if official else None,
            "away_probable_pitcher":
                official.get("away_probable_pitcher") if official else None,
            "home_probable_pitcher":
                official.get("home_probable_pitcher") if official else None,
            "away_games_available":
                a["games_available"] if a else 0,
            "home_games_available":
                h["games_available"] if h else 0,
            "away_winpct_5":
                a["winpct_5"] if a else None,
            "home_winpct_5":
                h["winpct_5"] if h else None,
            "away_run_diff_5":
                a["run_diff_5"] if a else None,
            "home_run_diff_5":
                h["run_diff_5"] if h else None,
            "away_run_diff_10":
                a["run_diff_10"] if a else None,
            "home_run_diff_10":
                h["run_diff_10"] if h else None,
            "away_bullpen_workload":
                bullpen_team.get(str(away)),
            "home_bullpen_workload":
                bullpen_team.get(str(home)),
            "context_status":
                "RESEARCH_READY"
                if a and h
                else "INSUFFICIENT_RECENT_HISTORY",
        })

    out = pd.DataFrame(rows)
    out.to_csv(GAME_CONTEXT_OUT, index=False)
    return out


def build_game_fusion(raw, context):
    if raw.empty:
        out = pd.DataFrame()
        out.to_csv(GAME_FUSION_OUT, index=False)
        return out

    d = raw.copy()
    d["start_dt"] = pd.to_datetime(
        d["start"],
        utc=True,
        errors="coerce",
        format="mixed",
    )
    d["game_date"] = d["start_dt"].dt.tz_convert(ET).dt.date.astype(str)
    d["away_key"] = d["away_team"].map(norm)
    d["home_key"] = d["home_team"].map(norm)
    d["game_key"] = (
        d["game_date"]
        + "|"
        + d["away_key"]
        + "|"
        + d["home_key"]
    )

    def canonical_selection(row):
        market = str(row.get("market") or "").upper()
        side = str(row.get("side") or "").upper()
        selection = str(row.get("selection") or "")

        if market == "TOTAL":
            if "OVER" in side or "OVER" in selection.upper():
                return "OVER"
            if "UNDER" in side or "UNDER" in selection.upper():
                return "UNDER"

        return selection

    d["selection_canonical"] = d.apply(
        canonical_selection,
        axis=1,
    )
    d["line_num"] = pd.to_numeric(
        d["line"],
        errors="coerce",
    )
    d["price_num"] = pd.to_numeric(
        d["price_american"],
        errors="coerce",
    )

    out = (
        d.groupby(
            [
                "game_key", "game_date",
                "away_team", "home_team",
                "market", "selection_canonical",
                "line_num",
            ],
            dropna=False,
        )
        .agg(
            start_dt=("start_dt", "min"),
            sportsbook_count=("sportsbook", "nunique"),
            provider_count=("provider", "nunique"),
            median_price_american=("price_num", "median"),
            providers=(
                "provider",
                lambda s: "|".join(sorted(set(map(str, s)))),
            ),
            sportsbooks=(
                "sportsbook",
                lambda s: "|".join(sorted(set(map(str, s)))),
            ),
        )
        .reset_index()
        .rename(columns={
            "market": "market_canonical",
            "line_num": "line",
        })
    )

    if not context.empty:
        out = out.merge(
            context,
            on=[
                "game_key",
                "game_date",
                "away_team",
                "home_team",
                "start_dt",
            ],
            how="left",
        )

    out.to_csv(GAME_FUSION_OUT, index=False)
    return out


def build_prop_fusion(raw, context, exact, alias):
    if raw.empty:
        out = pd.DataFrame()
        out.to_csv(PROP_FUSION_OUT, index=False)
        return out

    rows = []

    for _, r in raw.iterrows():
        subtype = str(r.get("market_subtype") or "")
        mapped = STAT_MAP.get(subtype)

        if (
            str(r.get("market") or "").upper() != "PLAYER_TOTAL"
            or not mapped
        ):
            continue

        metric, group = mapped
        side = str(r.get("side") or "").upper()

        if side not in {"OVER", "UNDER"}:
            continue

        line = num(r.get("line"))
        if line is None:
            continue

        player = resolve_player(
            r.get("player"),
            group,
            exact,
            alias,
        )

        if not player:
            continue

        recent = num(
            player.get("recent_" + metric)
        )
        season = num(
            player.get("season_" + metric)
        )

        rows.append({
            "event_id": r.get("event_id"),
            "start": r.get("start"),
            "away_team": r.get("away_team"),
            "home_team": r.get("home_team"),
            "player_id": player.get("player_id"),
            "player": player.get("player"),
            "player_key": player.get("player_key"),
            "team": player.get("team"),
            "position": player.get("position"),
            "group": group,
            "market_subtype": subtype,
            "metric": metric,
            "side": side,
            "line": line,
            "sportsbook": r.get("sportsbook"),
            "provider": r.get("provider"),
            "price_american": num(r.get("price_american")),
            "season_games": player.get("season_games"),
            "recent_games": player.get("recent_games"),
            "season_avg": season,
            "recent_avg": recent,
        })

    d = pd.DataFrame(rows)

    if d.empty:
        d.to_csv(PROP_FUSION_OUT, index=False)
        return d

    out = (
        d.groupby(
            [
                "event_id", "start",
                "away_team", "home_team",
                "player_id", "player",
                "player_key", "team", "position",
                "group", "market_subtype", "metric",
                "side", "line",
                "season_games", "recent_games",
                "season_avg", "recent_avg",
            ],
            dropna=False,
        )
        .agg(
            sportsbook_count=("sportsbook", "nunique"),
            provider_count=("provider", "nunique"),
            median_price_american=("price_american", "median"),
            sportsbooks=(
                "sportsbook",
                lambda s: "|".join(sorted(set(map(str, s)))),
            ),
        )
        .reset_index()
    )

    out.to_csv(PROP_FUSION_OUT, index=False)
    return out


def build_pp_fusion(raw, prop, exact, alias):
    if raw.empty:
        out = pd.DataFrame()
        out.to_csv(PP_FUSION_OUT, index=False)
        return out

    rows = []

    for _, r in raw.iterrows():
        subtype = str(r.get("market_subtype") or "")
        mapped = STAT_MAP.get(subtype)

        if (
            str(r.get("market") or "").upper() != "PLAYER_TOTAL"
            or not mapped
        ):
            continue

        metric, group = mapped
        side = str(r.get("side") or "").upper()

        if side not in {"OVER", "UNDER"}:
            continue

        line = num(r.get("line"))
        if line is None:
            continue

        player = resolve_player(
            r.get("player"),
            group,
            exact,
            alias,
        )

        if not player:
            continue

        rows.append({
            "event_id": r.get("event_id"),
            "start": r.get("start"),
            "away_team": r.get("away_team"),
            "home_team": r.get("home_team"),
            "player_id": player.get("player_id"),
            "player": player.get("player"),
            "player_key": player.get("player_key"),
            "team": player.get("team"),
            "position": player.get("position"),
            "group": group,
            "market_subtype": subtype,
            "metric": metric,
            "side": side,
            "line": line,
            "season_games": player.get("season_games"),
            "recent_games": player.get("recent_games"),
            "season_avg": num(
                player.get("season_" + metric)
            ),
            "recent_avg": num(
                player.get("recent_" + metric)
            ),
        })

    out = pd.DataFrame(rows)

    if out.empty:
        out.to_csv(PP_FUSION_OUT, index=False)
        return out

    if not prop.empty:
        book = prop[
            [
                "event_id", "player_key", "metric",
                "side", "line", "sportsbook_count",
                "provider_count", "median_price_american",
                "sportsbooks",
            ]
        ].copy()

        out = out.merge(
            book,
            on=[
                "event_id", "player_key",
                "metric", "side", "line",
            ],
            how="left",
        )

    out["sportsbook_count"] = pd.to_numeric(
        out.get("sportsbook_count"),
        errors="coerce",
    ).fillna(0)

    out = out.drop_duplicates(
        [
            "event_id", "player_key",
            "metric", "side", "line",
        ],
        keep="last",
    )

    out.to_csv(PP_FUSION_OUT, index=False)
    return out


def main():
    DERIVED.mkdir(parents=True, exist_ok=True)

    context = build_player_context()
    exact, alias = player_lookup(context)

    raw_game = read_csv(RAW_GAME)
    raw_prop = read_csv(RAW_PROP)
    raw_pp = read_csv(RAW_PP)

    game_context = build_game_context(raw_game)
    game = build_game_fusion(raw_game, game_context)
    prop = build_prop_fusion(raw_prop, context, exact, alias)
    pp = build_pp_fusion(raw_pp, prop, exact, alias)

    receipt = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "player_context_rows": int(len(context)),
        "game_context_rows": int(len(game_context)),
        "game_fusion_rows": int(len(game)),
        "prop_fusion_rows": int(len(prop)),
        "prizepicks_fusion_rows": int(len(pp)),
        "prop_players": int(prop["player_id"].nunique()) if not prop.empty else 0,
        "prizepicks_players": int(pp["player_id"].nunique()) if not pp.empty else 0,
        "official_game_matches": (
            int(game_context["official_match"].astype(bool).sum())
            if not game_context.empty
            else 0
        ),
        "fantasy_points_market_supported": False,
        "market_is_probability": False,
    }

    RECEIPT_OUT.write_text(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
    )

    for k, v in receipt.items():
        print(k.upper(), "=>", v)

    print("RESULT: MLB_FUSION_READY")


if __name__ == "__main__":
    main()
