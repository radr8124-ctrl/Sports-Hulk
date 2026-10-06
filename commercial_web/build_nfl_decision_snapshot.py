from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import math
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
DEC = ROOT / "nfl_live" / "decision"
DER = ROOT / "nfl_live" / "derived"


def clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if pd.isna(v):
        return None
    return v.item() if hasattr(v, "item") else v


def records(df, cols, limit=None):
    if df.empty:
        return []
    x = df[[c for c in cols if c in df.columns]].copy()
    if limit is not None:
        x = x.head(limit)
    return [
        {k: clean(v) for k, v in row.items()}
        for row in x.to_dict("records")
    ]


def file_age_hours(path):
    if not path.exists():
        return None
    mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    return round((datetime.now(timezone.utc) - mtime).total_seconds() / 3600, 2)


def main():
    props = pd.read_csv(DEC / "NFL_PROP_FINALISTS.csv", low_memory=False)
    survivor = pd.read_csv(DER / "NFL_SURVIVOR_HULK_DECISION.csv", low_memory=False)
    parlays = pd.read_csv(DEC / "NFL_PARLAYS_TODAY.csv", low_memory=False)
    games = pd.read_csv(DEC / "NFL_GAME_FINALISTS.csv", low_memory=False)

    if "newest_update" in props.columns:
        latest_prop = pd.to_datetime(props["newest_update"], errors="coerce", utc=True).max()
        prop_age = round((pd.Timestamp.now(tz="UTC") - latest_prop).total_seconds() / 3600, 2)
    else:
        prop_age = file_age_hours(DEC / "NFL_PROP_FINALISTS.csv")

    prop_status = "CURRENT" if prop_age is not None and prop_age <= 6 else "STALE"

    survivor_age = file_age_hours(DER / "NFL_SURVIVOR_HULK_DECISION.csv")
    survivor_status = "CURRENT" if survivor_age is not None and survivor_age <= 6 else "STALE"

    safe_parlays = parlays.copy()
    safe_parlays = safe_parlays.sort_values("parlay_score", ascending=False)

    game_research = games.copy()

    if "start" in game_research.columns:
        starts = pd.to_datetime(game_research["start"], errors="coerce", utc=True)
        current_mask = starts.isna() | (
            starts >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=4)
        )
        current_rows = game_research[current_mask].copy()
        if not current_rows.empty:
            game_research = current_rows

    game_research = game_research.sort_values(
        ["hulk_market_score", "market_implied_safety"],
        ascending=[False, False],
        na_position="last",
    )

    strong_props = props[
        props["decision"].isin(["STRONG_RESEARCH", "QUALIFIED_RESEARCH"])
    ].copy()
    strong_props = strong_props.sort_values(
        ["hulk_prop_score", "book_count"], ascending=[False, False]
    )

    survivor = survivor.sort_values(
        ["hulk_decision_tier", "hulk_context_score"],
        ascending=[True, False],
    )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health": {
            "props": {"status": prop_status, "age_hours": prop_age},
            "survivor": {"status": survivor_status, "age_hours": survivor_age},
            "game_bets": {
                "status": "CURRENT",
                "scope": "FULL_GAME_RESEARCH_BOARD",
                "reason": "Current moneyline, spread and total research from the same validated multi-provider game board used by the live app. Market-backed research is not a guaranteed outcome.",
            },
            "parlays": {
                "status": "CURRENT" if prop_status == "CURRENT" else "STALE",
                "scope": "QUALIFIED_TWO_LEG",
                "reason": "Qualified different-game two-leg combinations only. No fake probability or payout is calculated.",
            },
        },
        "games": records(
            game_research,
            [
                "game_key", "start", "market", "selection", "line",
                "market_implied_safety", "hulk_market_score", "decision",
                "market_data_quality", "provider_agreement", "sw_books",
                "therundown_verified", "oddspapi_status", "model_status",
                "home_spread_move", "total_move",
            ],
            60,
        ),
        "props": records(
            strong_props,
            [
                "player_dfs", "player_team", "away_team", "home_team", "start_dfs",
                "market", "stat_type", "side", "dfs_line", "sportsbook_line",
                "book_probability", "book_count", "books", "coverage_grade",
                "hulk_prop_score", "context_direction", "recent_metric",
                "dfs_line_advantage", "meaningful_completed_games",
                "espn_injury_gate", "decision", "newest_update",
                "context_sources", "context_coverage",
            ],
            12,
        ),
        "parlays": records(
            safe_parlays,
            [
                "parlay_type", "parlay_score", "leg1_label", "leg1_score",
                "leg2_label", "leg2_score", "correlation_status",
                "probability_status", "payout_status", "status", "generated_at",
            ],
            12,
        ),
        "survivor": records(
            survivor,
            [
                "start", "away_team", "home_team", "survivor_team",
                "market_prob_pct", "survivor_spread", "hulk_context_score",
                "context_delta", "hulk_disagreement", "hulk_decision_tier",
                "positive_signals", "risk_signals", "weather_status",
                "temperature_f", "precip_probability", "wind_mph",
                "wind_gust_mph", "venue_indoor", "team_prior_win_pct",
                "team_avg_point_diff", "rest_days", "collected_at",
            ],
            15,
        ),
    }

    text = json.dumps(payload, indent=2)
    for target in [
        ROOT / "commercial_web" / "public" / "nfl_decisions.json",
        ROOT / "commercial_web" / "dist" / "nfl_decisions.json",
    ]:
        if target.parent.exists():
            target.write_text(text)

    print(
        f"DECISION SNAPSHOT PASS games={len(payload['games'])} props={len(payload['props'])} "
        f"parlays={len(payload['parlays'])} survivor={len(payload['survivor'])}"
    )


if __name__ == "__main__":
    main()
