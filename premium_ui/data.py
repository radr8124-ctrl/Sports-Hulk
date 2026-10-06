from pathlib import Path
from datetime import datetime, timezone
import json

import pandas as pd


ROOT = Path("/home/ubuntu/sports-hulk")
NFL = ROOT / "nfl_live/decision"
SURVIVOR = ROOT / "nfl_live/survivor_pool/derived"
SURVIVOR_LIVE = ROOT / "nfl_live/derived"
SPORTS_CONTENT = ROOT / "sports_content" / "derived"


def read_csv(path):
    path = Path(path)

    if (
        not path.exists()
        or path.stat().st_size <= 1
    ):
        return pd.DataFrame()

    try:
        return pd.read_csv(
            path,
            low_memory=False,
        )
    except Exception:
        return pd.DataFrame()


def read_json(path):
    path = Path(path)

    if not path.exists():
        return {}

    try:
        return json.loads(
            path.read_text()
        )
    except Exception:
        return {}


def age_text(path):
    path = Path(path)

    if not path.exists():
        return "Not available"

    now = datetime.now(
        timezone.utc
    ).timestamp()

    minutes = max(
        0,
        int(
            (
                now
                - path.stat().st_mtime
            )
            / 60
        ),
    )

    if minutes < 1:
        return "Updated just now"

    if minutes < 60:
        return (
            f"Updated {minutes} min ago"
        )

    hours = minutes // 60

    return f"Updated {hours}h ago"


def nfl_games():
    return read_csv(
        NFL
        / "NFL_GAME_FINALISTS.csv"
    )


def nfl_props():
    return read_csv(
        NFL
        / "NFL_PROP_FINALISTS.csv"
    )


def nfl_pickem():
    return read_csv(
        NFL
        / "NFL_PRIZEPICKS_FINALISTS.csv"
    )


def nfl_parlays():
    return read_csv(
        NFL
        / "NFL_PARLAYS_TODAY.csv"
    )


def nfl_fantasy():
    return read_csv(
        NFL
        / "NFL_FANTASY_WATCHLIST.csv"
    )


def nfl_score_snapshot():
    primary = (
        ROOT
        / "commercial_web"
        / "public"
        / "nfl_scores.json"
    )

    payload = read_json(
        primary
    )

    if not payload:
        payload = read_json(
            ROOT
            / "commercial_web"
            / "dist"
            / "nfl_scores.json"
        )

    return payload


def mlb_score_snapshot():
    primary = (
        ROOT
        / "commercial_web"
        / "public"
        / "mlb_scores.json"
    )

    payload = read_json(
        primary
    )

    if not payload:
        payload = read_json(
            ROOT
            / "commercial_web"
            / "dist"
            / "mlb_scores.json"
        )

    return payload


def sports_news_current():
    return read_csv(
        SPORTS_CONTENT
        / "SPORTS_NEWS_CURRENT.csv"
    )


def sports_facts_current():
    return read_csv(
        SPORTS_CONTENT
        / "SPORTS_FACTS_CURRENT.csv"
    )


def sports_article_drafts():
    return read_csv(
        SPORTS_CONTENT
        / "ARTICLE_DRAFTS.csv"
    )


def survivor_field():
    final = SURVIVOR / "WEEK3_FINAL_RESULTS.csv"
    if final.exists():
        return read_csv(final)
    return read_csv(
        SURVIVOR
        / "WEEK3_OFFICIAL_PICKS.csv"
    )


def survivor_summary():
    return read_json(
        SURVIVOR
        / "LATEST_OFFICIAL_POOL.json"
    )


def survivor_pick2():
    return read_csv(
        SURVIVOR
        / "WEEK3_PICK2_OWNERSHIP.csv"
    )


def survivor_pairs():
    return read_csv(
        SURVIVOR
        / "WEEK3_PAIR_OWNERSHIP.csv"
    )


def survivor_entries():
    return read_json(
        ROOT
        / "nfl_live"
        / "derived"
        / "SURVIVOR_ENTRIES.json"
    )


def survivor_strategy():
    return read_csv(
        ROOT
        / "nfl_live"
        / "derived"
        / "NFL_SURVIVOR_HULK_STRATEGY.csv"
    )


def survivor_pool_current():
    return read_csv(
        ROOT
        / "nfl_live"
        / "survivor_pool"
        / "derived"
        / "SURVIVOR_POOL_CURRENT.csv"
    )


def survivor_pool_ownership():
    return read_csv(
        ROOT
        / "nfl_live"
        / "survivor_pool"
        / "derived"
        / "SURVIVOR_POOL_OWNERSHIP.csv"
    )


# NBA_DATA_BUILD_6
NBA_DECISION = (
    ROOT
    / "nba_live"
    / "decision"
)

NBA_DERIVED = (
    ROOT
    / "nba_live"
    / "derived"
)


def nba_games_current():
    return read_csv(
        NBA_DERIVED
        / "NBA_GAMES_CURRENT.csv"
    )


def nba_game_finalists():
    return read_csv(
        NBA_DECISION
        / "NBA_GAME_FINALISTS.csv"
    )


def nba_prop_decisions():
    return read_csv(
        NBA_DECISION
        / "NBA_PROP_DECISIONS.csv"
    )


def nba_prop_finalists():
    return read_csv(
        NBA_DECISION
        / "NBA_PROP_FINALISTS.csv"
    )


def nba_pickem_decisions():
    return read_csv(
        NBA_DECISION
        / "NBA_PRIZEPICKS_DECISIONS.csv"
    )


def nba_pickem_finalists():
    return read_csv(
        NBA_DECISION
        / "NBA_PRIZEPICKS_FINALISTS.csv"
    )


def nba_parlays():
    return read_csv(
        NBA_DECISION
        / "NBA_PARLAYS_TODAY.csv"
    )


def nba_fantasy():
    return read_csv(
        NBA_DECISION
        / "NBA_FANTASY_WATCHLIST.csv"
    )


def nba_learning_summary():
    return read_json(
        NBA_DECISION
        / "history"
        / "NBA_LEARNING_SUMMARY.json"
    )


# NHL_DATA_BUILD_6
NHL_DECISION = (
    ROOT
    / "nhl_live"
    / "decision"
)

NHL_DERIVED = (
    ROOT
    / "nhl_live"
    / "derived"
)


def nhl_games_current():
    return read_csv(
        NHL_DERIVED
        / "NHL_GAMES_CURRENT.csv"
    )


def nhl_game_finalists():
    return read_csv(
        NHL_DECISION
        / "NHL_GAME_FINALISTS.csv"
    )


def nhl_prop_decisions():
    return read_csv(
        NHL_DECISION
        / "NHL_PROP_DECISIONS.csv"
    )


def nhl_prop_finalists():
    return read_csv(
        NHL_DECISION
        / "NHL_PROP_FINALISTS.csv"
    )


def nhl_pickem_decisions():
    return read_csv(
        NHL_DECISION
        / "NHL_PRIZEPICKS_DECISIONS.csv"
    )


def nhl_pickem_finalists():
    return read_csv(
        NHL_DECISION
        / "NHL_PRIZEPICKS_FINALISTS.csv"
    )


def nhl_parlays():
    return read_csv(
        NHL_DECISION
        / "NHL_PARLAYS_TODAY.csv"
    )


def nhl_fantasy():
    return read_csv(
        NHL_DECISION
        / "NHL_FANTASY_WATCHLIST.csv"
    )


def nhl_learning_summary():
    return read_json(
        NHL_DECISION
        / "history"
        / "NHL_LEARNING_SUMMARY.json"
    )


# CBB_DATA_BUILD_5
CBB_DECISION = (
    ROOT
    / "cbb_live"
    / "decision"
)

CBB_DERIVED = (
    ROOT
    / "cbb_live"
    / "derived"
)


def cbb_games_current():
    return read_csv(
        CBB_DERIVED
        / "CBB_GAMES_CURRENT.csv"
    )


def cbb_game_decisions():
    return read_csv(
        CBB_DECISION
        / "CBB_GAME_DECISIONS.csv"
    )


def cbb_game_finalists():
    return read_csv(
        CBB_DECISION
        / "CBB_GAME_FINALISTS.csv"
    )


def cbb_parlays():
    return read_csv(
        CBB_DECISION
        / "CBB_PARLAYS_TODAY.csv"
    )


def cbb_team_context():
    return read_csv(
        CBB_DECISION
        / "CBB_TEAM_CONTEXT.csv"
    )


def cbb_team_research():
    return read_csv(
        CBB_DECISION
        / "CBB_TEAM_RESEARCH.csv"
    )


def cbb_preseason_baseline():
    return read_csv(
        CBB_DECISION
        / "CBB_PRESEASON_BASELINE.csv"
    )


def cbb_rankings():
    return read_csv(
        CBB_DERIVED
        / "CBB_RANKINGS_CURRENT.csv"
    )


def cbb_learning_summary():
    return read_json(
        CBB_DECISION
        / "history"
        / "CBB_LEARNING_SUMMARY.json"
    )


# CFB_DATA_BUILD_5
CFB_DECISION = (
    ROOT
    / "cfb_live"
    / "decision"
)

CFB_DERIVED = (
    ROOT
    / "cfb_live"
    / "derived"
)


def cfb_games_current():
    return read_csv(
        CFB_DERIVED
        / "CFB_GAMES_CURRENT.csv"
    )


def cfb_game_decisions():
    return read_csv(
        CFB_DECISION
        / "CFB_GAME_DECISIONS.csv"
    )


def cfb_game_finalists():
    return read_csv(
        CFB_DECISION
        / "CFB_GAME_FINALISTS.csv"
    )


def cfb_parlays():
    return read_csv(
        CFB_DECISION
        / "CFB_PARLAYS_TODAY.csv"
    )


def cfb_team_context():
    return read_csv(
        CFB_DECISION
        / "CFB_TEAM_CONTEXT.csv"
    )


def cfb_team_research():
    return read_csv(
        CFB_DECISION
        / "CFB_TEAM_RESEARCH.csv"
    )


def cfb_rankings():
    return read_csv(
        CFB_DERIVED
        / "CFB_RANKINGS_CURRENT.csv"
    )


def cfb_learning_summary():
    return read_json(
        CFB_DECISION
        / "history"
        / "CFB_LEARNING_SUMMARY.json"
    )


# MLB_DATA_BUILD_V2
MLB_DECISION = (
    ROOT
    / "mlb_live"
    / "decision"
)

MLB_DERIVED = (
    ROOT
    / "mlb_live"
    / "derived"
)

MLB_LATEST = (
    ROOT
    / "baseball_vault"
    / "latest"
)


def mlb_games_current():
    return read_csv(
        MLB_LATEST
        / "MLB_SCHEDULE.csv"
    )


def mlb_game_decisions():
    return read_csv(
        MLB_DECISION
        / "MLB_GAME_DECISIONS.csv"
    )


def mlb_game_finalists():
    return read_csv(
        MLB_DECISION
        / "MLB_GAME_FINALISTS.csv"
    )


def mlb_prop_decisions():
    return read_csv(
        MLB_DECISION
        / "MLB_PROP_DECISIONS.csv"
    )


def mlb_prop_finalists():
    return read_csv(
        MLB_DECISION
        / "MLB_PROP_FINALISTS.csv"
    )


def mlb_pickem_decisions():
    return read_csv(
        MLB_DECISION
        / "MLB_PRIZEPICKS_DECISIONS.csv"
    )


def mlb_pickem_finalists():
    return read_csv(
        MLB_DECISION
        / "MLB_PRIZEPICKS_FINALISTS.csv"
    )


def mlb_fantasy():
    return read_csv(
        MLB_DECISION
        / "MLB_FANTASY_WATCHLIST.csv"
    )


def mlb_parlays():
    return read_csv(
        MLB_DECISION
        / "MLB_PARLAYS_TODAY.csv"
    )


def mlb_learning_summary():
    return read_json(
        MLB_DECISION
        / "history"
        / "MLB_LEARNING_SUMMARY.json"
    )
