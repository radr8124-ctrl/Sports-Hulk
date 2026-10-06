#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timezone
import itertools
import json
import math
import re
import unicodedata

import pandas as pd


ROOT = Path("/home/ubuntu/sports-hulk")
MLB = ROOT / "mlb_live"
DEC = MLB / "decision"
DERIVED = MLB / "derived"
MARKETS = MLB / "markets" / "current"

GAME = MARKETS / "MLB_GAME_FUSION.csv"
PROP = MARKETS / "MLB_PROP_FUSION.csv"
PP = MARKETS / "MLB_PRIZEPICKS_FUSION.csv"
PLAYERS = DERIVED / "MLB_PLAYER_CONTEXT.csv"

GAME_DEC = DEC / "MLB_GAME_DECISIONS.csv"
GAME_FIN = DEC / "MLB_GAME_FINALISTS.csv"
PROP_DEC = DEC / "MLB_PROP_DECISIONS.csv"
PROP_FIN = DEC / "MLB_PROP_FINALISTS.csv"
PP_DEC = DEC / "MLB_PRIZEPICKS_DECISIONS.csv"
PP_FIN = DEC / "MLB_PRIZEPICKS_FINALISTS.csv"
FANTASY = DEC / "MLB_FANTASY_WATCHLIST.csv"
PARLAYS = DEC / "MLB_PARLAYS_TODAY.csv"
SUMMARY = DEC / "MLB_DECISION_SUMMARY.json"

NOW = pd.Timestamp.now(tz="UTC")
FINALIST_HOURS = 36


def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()


def ascii_text(value):
    return (
        unicodedata
        .normalize("NFKD", str(value or ""))
        .encode("ascii", "ignore")
        .decode()
    )


def norm(value):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        ascii_text(value).lower(),
    )


def num(value):
    try:
        x = float(value)
        if math.isnan(x):
            return None
        return x
    except Exception:
        return None


def hours_until(value):
    dt = pd.to_datetime(
        value,
        utc=True,
        errors="coerce",
        format="mixed",
    )
    if pd.isna(dt):
        return None
    return (dt - NOW).total_seconds() / 3600.0


def raw_market_support(price):
    price = num(price)
    if price is None:
        return None
    if price < 0:
        return -price / (-price + 100.0)
    if price > 0:
        return 100.0 / (price + 100.0)
    return 0.5


def team_side(selection, away, home):
    s = norm(selection)
    a = norm(away)
    h = norm(home)

    if not s:
        return ""

    if s == a:
        return "AWAY"

    if s == h:
        return "HOME"

    away_tokens = re.findall(
        r"[A-Za-z0-9]+",
        ascii_text(away).lower(),
    )
    home_tokens = re.findall(
        r"[A-Za-z0-9]+",
        ascii_text(home).lower(),
    )

    away_nick = norm(" ".join(away_tokens[-2:])) if len(away_tokens) >= 2 else a
    home_nick = norm(" ".join(home_tokens[-2:])) if len(home_tokens) >= 2 else h
    away_last = norm(away_tokens[-1]) if away_tokens else ""
    home_last = norm(home_tokens[-1]) if home_tokens else ""

    away_match = (
        (away_last and away_last in s)
        or (away_nick and away_nick in s)
    )
    home_match = (
        (home_last and home_last in s)
        or (home_nick and home_nick in s)
    )

    if away_match and not home_match:
        return "AWAY"

    if home_match and not away_match:
        return "HOME"

    return ""


def pitcher_lookup():
    d = read_csv(PLAYERS)
    if d.empty:
        return {}

    p = d[d["group"].astype(str).eq("PITCHING")].copy()

    out = {}
    for _, row in p.iterrows():
        key = norm(row.get("player"))
        if key:
            out[key] = row.to_dict()
    return out


def pitcher_quality(row):
    if not row:
        return None

    k = num(row.get("recent_strikeouts_pg"))
    er = num(row.get("recent_earned_runs_pg"))
    hits = num(row.get("recent_hits_allowed_pg"))
    outs = num(row.get("recent_outs_pg"))

    if k is None:
        k = num(row.get("season_strikeouts_pg"))
    if er is None:
        er = num(row.get("season_earned_runs_pg"))
    if hits is None:
        hits = num(row.get("season_hits_allowed_pg"))
    if outs is None:
        outs = num(row.get("season_outs_pg"))

    if all(x is None for x in [k, er, hits, outs]):
        return None

    return (
        (k or 0)
        + ((outs or 0) / 6.0)
        - 1.6 * (er or 0)
        - 0.35 * (hits or 0)
    )


def build_game_decisions():
    d = read_csv(GAME)

    if d.empty:
        d.to_csv(GAME_DEC, index=False)
        d.to_csv(GAME_FIN, index=False)
        return d, d

    p_lookup = pitcher_lookup()
    rows = []

    for _, r in d.iterrows():
        market = str(r.get("market_canonical") or "").upper()
        side = ""

        if market in {"MONEYLINE", "SPREAD"}:
            side = team_side(
                r.get("selection_canonical"),
                r.get("away_team"),
                r.get("home_team"),
            )

        books = int(num(r.get("sportsbook_count")) or 0)
        providers = int(num(r.get("provider_count")) or 0)
        price = num(r.get("median_price_american"))
        hours = hours_until(r.get("start_dt"))

        away_rd5 = num(r.get("away_run_diff_5"))
        home_rd5 = num(r.get("home_run_diff_5"))
        away_rd10 = num(r.get("away_run_diff_10"))
        home_rd10 = num(r.get("home_run_diff_10"))
        away_w5 = num(r.get("away_winpct_5"))
        home_w5 = num(r.get("home_winpct_5"))

        form_edge = None
        win_edge = None

        if side == "HOME":
            if home_rd5 is not None and away_rd5 is not None:
                form_edge = home_rd5 - away_rd5
            if home_w5 is not None and away_w5 is not None:
                win_edge = home_w5 - away_w5

        elif side == "AWAY":
            if home_rd5 is not None and away_rd5 is not None:
                form_edge = away_rd5 - home_rd5
            if home_w5 is not None and away_w5 is not None:
                win_edge = away_w5 - home_w5

        away_pitch = p_lookup.get(
            norm(r.get("away_probable_pitcher"))
        )
        home_pitch = p_lookup.get(
            norm(r.get("home_probable_pitcher"))
        )

        away_q = pitcher_quality(away_pitch)
        home_q = pitcher_quality(home_pitch)

        pitcher_edge = None

        if side == "HOME" and away_q is not None and home_q is not None:
            pitcher_edge = home_q - away_q

        elif side == "AWAY" and away_q is not None and home_q is not None:
            pitcher_edge = away_q - home_q

        score = 38.0

        if bool(r.get("official_match")):
            score += 10

        if str(r.get("context_status")) == "RESEARCH_READY":
            score += 10

        if books >= 10:
            score += 15
        elif books >= 5:
            score += 11
        elif books >= 3:
            score += 7
        elif books >= 2:
            score += 4

        if providers >= 2:
            score += 5

        if form_edge is not None:
            if form_edge >= 2:
                score += 10
            elif form_edge >= 0.75:
                score += 5
            elif form_edge <= -2:
                score -= 8

        if win_edge is not None:
            if win_edge >= 0.2:
                score += 6
            elif win_edge <= -0.2:
                score -= 5

        if pitcher_edge is not None:
            if pitcher_edge >= 2:
                score += 8
            elif pitcher_edge >= 0.75:
                score += 4
            elif pitcher_edge <= -2:
                score -= 6

        support = raw_market_support(price)
        if support is not None and support >= 0.56:
            score += 2

        score = max(0.0, min(100.0, score))

        if hours is None or hours < -1:
            decision = "CLOSED"
        elif hours > FINALIST_HOURS:
            decision = "EARLY_MARKET_WATCH"
        elif not bool(r.get("official_match")):
            decision = "IDENTITY_REVIEW"
        elif str(r.get("context_status")) != "RESEARCH_READY":
            decision = "INSUFFICIENT_CONTEXT"
        elif market != "MONEYLINE":
            decision = "MARKET_RESEARCH"
        elif not side:
            decision = "IDENTITY_REVIEW"
        elif price is not None and price <= -350:
            decision = "HIGH_JUICE"
        elif books < 3:
            decision = "WATCH"
        elif score >= 75:
            decision = "QUALIFIED_RESEARCH"
        elif score >= 65:
            decision = "MARKET_LEAN"
        else:
            decision = "WATCH"

        out = r.to_dict()
        out.update({
            "selection_side": side,
            "hours_to_start": hours,
            "raw_market_support": support,
            "form_edge": form_edge,
            "winpct_edge": win_edge,
            "pitcher_edge": pitcher_edge,
            "away_pitcher_quality": away_q,
            "home_pitcher_quality": home_q,
            "evidence_score": score,
            "decision": decision,
            "probability_claim": False,
            "spread_finalist_validated": False,
            "totals_finalist_validated": False,
        })

        rows.append(out)

    out = pd.DataFrame(rows)

    out = out.sort_values(
        ["evidence_score", "sportsbook_count"],
        ascending=[False, False],
    )

    finalists = (
        out[
            out["decision"].eq("QUALIFIED_RESEARCH")
            & out["market_canonical"].eq("MONEYLINE")
        ]
        .sort_values("evidence_score", ascending=False)
        .drop_duplicates(["game_key"], keep="first")
        .head(10)
    )

    out.to_csv(GAME_DEC, index=False)
    finalists.to_csv(GAME_FIN, index=False)

    return out, finalists


def direction_edges(row):
    line = num(row.get("line"))
    recent = num(row.get("recent_avg"))
    season = num(row.get("season_avg"))
    side = str(row.get("side") or "").upper()

    if line is None:
        return None, None

    if side == "OVER":
        return (
            recent - line if recent is not None else None,
            season - line if season is not None else None,
        )

    if side == "UNDER":
        return (
            line - recent if recent is not None else None,
            line - season if season is not None else None,
        )

    return None, None


def player_decisions(source, lane):
    d = read_csv(source)

    if d.empty:
        return d

    rows = []

    for _, r in d.iterrows():
        recent_edge, season_edge = direction_edges(r)

        books = int(num(r.get("sportsbook_count")) or 0)
        recent_games = int(num(r.get("recent_games")) or 0)
        season_games = int(num(r.get("season_games")) or 0)
        line = num(r.get("line"))
        price = num(r.get("median_price_american"))
        group = str(r.get("group") or "")

        min_recent = 2 if group == "PITCHING" else 4
        enough_recent = recent_games >= min_recent

        scale = max(abs(line or 0), 0.5)
        normalized_edge = (
            recent_edge / scale
            if recent_edge is not None
            else None
        )

        score = 35.0

        if season_games >= 20:
            score += 8

        if enough_recent:
            score += 10

        if books >= 4:
            score += 14
        elif books >= 3:
            score += 11
        elif books >= 2:
            score += 7

        both_support = (
            recent_edge is not None
            and season_edge is not None
            and recent_edge > 0
            and season_edge > 0
        )

        if both_support:
            score += 15

        if normalized_edge is not None:
            if normalized_edge >= 0.35:
                score += 12
            elif normalized_edge >= 0.20:
                score += 8
            elif normalized_edge >= 0.08:
                score += 4
            elif normalized_edge <= -0.20:
                score -= 10

        score = max(0.0, min(100.0, score))

        if not enough_recent:
            decision = "INSUFFICIENT_RECENT_CONTEXT"
        elif price is not None and price <= -400:
            decision = "HIGH_JUICE"
        elif lane == "PRIZEPICKS" and books < 2:
            decision = "WATCH"
        elif lane == "PROP" and books < 2:
            decision = "WATCH"
        elif not both_support:
            decision = "WATCH"
        elif score >= 75:
            decision = "QUALIFIED_RESEARCH"
        elif score >= 67:
            decision = "STRONG"
        else:
            decision = "WATCH"

        out = r.to_dict()
        out.update({
            "recent_edge": recent_edge,
            "season_edge": season_edge,
            "normalized_recent_edge": normalized_edge,
            "evidence_score": score,
            "decision": decision,
            "probability_claim": False,
        })
        rows.append(out)

    return pd.DataFrame(rows).sort_values(
        ["evidence_score", "sportsbook_count"],
        ascending=[False, False],
    )


def build_prop_and_pp():
    prop = player_decisions(PROP, "PROP")
    pp = player_decisions(PP, "PRIZEPICKS")

    if prop.empty:
        prop_fin = prop.copy()
    else:
        prop_fin = (
            prop[
                prop["decision"].eq("QUALIFIED_RESEARCH")
            ]
            .drop_duplicates(
                ["event_id", "player_id", "metric"],
                keep="first",
            )
            .head(25)
        )

    if pp.empty:
        pp_fin = pp.copy()
    else:
        pp_fin = (
            pp[
                pp["decision"].eq("QUALIFIED_RESEARCH")
                & pd.to_numeric(
                    pp["sportsbook_count"],
                    errors="coerce",
                ).ge(2)
            ]
            .drop_duplicates(
                ["event_id", "player_id", "metric"],
                keep="first",
            )
            .head(25)
        )

    prop.to_csv(PROP_DEC, index=False)
    prop_fin.to_csv(PROP_FIN, index=False)
    pp.to_csv(PP_DEC, index=False)
    pp_fin.to_csv(PP_FIN, index=False)

    return prop, prop_fin, pp, pp_fin


def build_fantasy():
    players = read_csv(PLAYERS)
    prop = read_csv(PROP)

    if players.empty or prop.empty:
        out = pd.DataFrame()
        out.to_csv(FANTASY, index=False)
        return out

    active_ids = set(
        pd.to_numeric(
            prop["player_id"],
            errors="coerce",
        )
        .dropna()
        .astype(int)
        .tolist()
    )

    d = players[
        pd.to_numeric(
            players["player_id"],
            errors="coerce",
        )
        .fillna(-1)
        .astype(int)
        .isin(active_ids)
    ].copy()

    rows = []

    for _, r in d.iterrows():
        group = str(r.get("group") or "")
        recent_games = int(num(r.get("recent_games")) or 0)

        if group == "HITTING":
            if recent_games < 4:
                continue

            recent = (
                (num(r.get("recent_total_bases_pg")) or 0)
                + (num(r.get("recent_hits_pg")) or 0)
                + (num(r.get("recent_runs_pg")) or 0)
                + (num(r.get("recent_rbi_pg")) or 0)
                + 2 * (num(r.get("recent_stolen_bases_pg")) or 0)
            )

            season = (
                (num(r.get("season_total_bases_pg")) or 0)
                + (num(r.get("season_hits_pg")) or 0)
                + (num(r.get("season_runs_pg")) or 0)
                + (num(r.get("season_rbi_pg")) or 0)
                + 2 * (num(r.get("season_stolen_bases_pg")) or 0)
            )

        else:
            if recent_games < 2:
                continue

            recent = (
                (num(r.get("recent_strikeouts_pg")) or 0)
                + (num(r.get("recent_outs_pg")) or 0) / 3.0
                - 2 * (num(r.get("recent_earned_runs_pg")) or 0)
            )

            season = (
                (num(r.get("season_strikeouts_pg")) or 0)
                + (num(r.get("season_outs_pg")) or 0) / 3.0
                - 2 * (num(r.get("season_earned_runs_pg")) or 0)
            )

        rows.append({
            "player_id": r.get("player_id"),
            "player": r.get("player"),
            "team": r.get("team"),
            "position": r.get("position"),
            "group": group,
            "recent_games": recent_games,
            "context_score": recent,
            "season_context_score": season,
            "trend_vs_season": recent - season,
            "fantasy_points_claim": False,
        })

    out = pd.DataFrame(rows)

    if not out.empty:
        out = out.sort_values(
            ["context_score", "trend_vs_season"],
            ascending=[False, False],
        ).head(60)

    out.to_csv(FANTASY, index=False)
    return out


def build_parlays(game_fin, prop_fin):
    legs = []

    for _, r in game_fin.iterrows():
        legs.append({
            "lane": "GAME",
            "game": r.get("game_key"),
            "subject": r.get("game_key"),
            "market": r.get("market_canonical"),
            "selection": r.get("selection_canonical"),
            "line": r.get("line"),
            "score": r.get("evidence_score"),
        })

    for _, r in prop_fin.iterrows():
        game = (
            str(r.get("start"))
            + "|"
            + norm(r.get("away_team"))
            + "|"
            + norm(r.get("home_team"))
        )
        legs.append({
            "lane": "PROP",
            "game": game,
            "subject": r.get("player"),
            "market": r.get("metric"),
            "selection": r.get("side"),
            "line": r.get("line"),
            "score": r.get("evidence_score"),
        })

    rows = []

    for a, b in itertools.combinations(legs, 2):
        if a["game"] == b["game"]:
            continue

        rows.append({
            "leg1_lane": a["lane"],
            "leg1_game": a["game"],
            "leg1_subject": a["subject"],
            "leg1_market": a["market"],
            "leg1_selection": a["selection"],
            "leg1_line": a["line"],
            "leg1_score": a["score"],
            "leg2_lane": b["lane"],
            "leg2_game": b["game"],
            "leg2_subject": b["subject"],
            "leg2_market": b["market"],
            "leg2_selection": b["selection"],
            "leg2_line": b["line"],
            "leg2_score": b["score"],
            "evidence_score":
                (float(a["score"]) + float(b["score"])) / 2.0,
            "status": "RESEARCH_COMBO",
            "probability_claim": False,
            "payout_claim": False,
        })

    out = pd.DataFrame(rows)

    if not out.empty:
        out = out.sort_values(
            "evidence_score",
            ascending=False,
        ).head(30)

    out.to_csv(PARLAYS, index=False)
    return out


def main():
    DEC.mkdir(parents=True, exist_ok=True)

    game_dec, game_fin = build_game_decisions()
    prop_dec, prop_fin, pp_dec, pp_fin = build_prop_and_pp()
    fantasy = build_fantasy()
    parlays = build_parlays(game_fin, prop_fin)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "game_decisions": int(len(game_dec)),
        "game_finalists": int(len(game_fin)),
        "prop_decisions": int(len(prop_dec)),
        "prop_finalists": int(len(prop_fin)),
        "prizepicks_decisions": int(len(pp_dec)),
        "prizepicks_finalists": int(len(pp_fin)),
        "fantasy_rows": int(len(fantasy)),
        "parlays": int(len(parlays)),
        "automatic_model_adjustment": False,
        "market_is_probability": False,
        "evidence_score_is_probability": False,
        "fantasy_points_claim": False,
        "spread_finalist_validated": False,
        "totals_finalist_validated": False,
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

    for k, v in summary.items():
        print(k.upper(), "=>", v)

    if not prop_dec.empty:
        print("PROP STATUS =>", prop_dec["decision"].value_counts().to_dict())

    if not pp_dec.empty:
        print("PP STATUS =>", pp_dec["decision"].value_counts().to_dict())

    print("RESULT: MLB_DECISION_BRAIN_READY")


if __name__ == "__main__":
    main()
