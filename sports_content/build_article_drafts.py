#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import math
import re

import pandas as pd


ROOT = Path("/home/ubuntu/sports-hulk")
CONTENT = ROOT / "sports_content"
DERIVED = CONTENT / "derived"
DRAFT_DIR = CONTENT / "drafts"

NEWS = DERIVED / "SPORTS_NEWS_CURRENT.csv"
FACTS = DERIVED / "SPORTS_FACTS_CURRENT.csv"
DRAFTS = DERIVED / "ARTICLE_DRAFTS.csv"
RECEIPT = DERIVED / "ARTICLE_ENGINE_RECEIPT.json"

NOW = datetime.now(timezone.utc)

SPORT_DATA = {
    "NFL": {
        "games": ROOT / "nfl_live/decision/NFL_GAME_FINALISTS.csv",
        "props": ROOT / "nfl_live/decision/NFL_PROP_FINALISTS.csv",
        "pickem": ROOT / "nfl_live/decision/NFL_PRIZEPICKS_FINALISTS.csv",
        "fantasy": ROOT / "nfl_live/decision/NFL_FANTASY_WATCHLIST.csv",
    },
    "MLB": {
        "games": ROOT / "mlb_live/decision/MLB_GAME_FINALISTS.csv",
        "props": ROOT / "mlb_live/decision/MLB_PROP_FINALISTS.csv",
        "pickem": ROOT / "mlb_live/decision/MLB_PRIZEPICKS_FINALISTS.csv",
        "fantasy": ROOT / "mlb_live/decision/MLB_FANTASY_WATCHLIST.csv",
    },
    "NBA": {
        "games": ROOT / "nba_live/decision/NBA_GAME_FINALISTS.csv",
        "props": ROOT / "nba_live/decision/NBA_PROP_FINALISTS.csv",
        "pickem": ROOT / "nba_live/decision/NBA_PRIZEPICKS_FINALISTS.csv",
        "fantasy": ROOT / "nba_live/decision/NBA_FANTASY_WATCHLIST.csv",
    },
    "NHL": {
        "games": ROOT / "nhl_live/decision/NHL_GAME_FINALISTS.csv",
        "props": ROOT / "nhl_live/decision/NHL_PROP_FINALISTS.csv",
        "pickem": ROOT / "nhl_live/decision/NHL_PRIZEPICKS_FINALISTS.csv",
        "fantasy": ROOT / "nhl_live/decision/NHL_FANTASY_WATCHLIST.csv",
    },
    "CFB": {
        "games": ROOT / "cfb_live/decision/CFB_GAME_FINALISTS.csv",
        "props": None,
        "pickem": None,
        "fantasy": None,
    },
    "CBB": {
        "games": ROOT / "cbb_live/decision/CBB_GAME_FINALISTS.csv",
        "props": None,
        "pickem": None,
        "fantasy": None,
    },
}


def read_csv(path):
    if not path:
        return pd.DataFrame()

    try:
        return pd.read_csv(
            path,
            low_memory=False,
        )
    except Exception:
        return pd.DataFrame()


def clean(value):
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    )


def num(value, digits=1):
    try:
        x = float(value)
        if math.isnan(x):
            return "—"

        if digits == 0:
            return str(int(round(x)))

        return f"{x:.{digits}f}"
    except Exception:
        return "—"


def slugify(value):
    return (
        re.sub(
            r"[^a-z0-9]+",
            "-",
            clean(value).lower(),
        )
        .strip("-")
    )[:90]


def stable_id(*parts):
    raw = "|".join(
        clean(x)
        for x in parts
    )

    return hashlib.sha256(
        raw.encode()
    ).hexdigest()[:20]


def top_row(df):
    if df.empty:
        return None

    d = df.copy()

    for score in [
        "evidence_score",
        "hulk_market_score",
        "hulk_prop_score",
        "recent_usage_index",
        "context_score",
    ]:
        if score in d.columns:
            d["_sort"] = pd.to_numeric(
                d[score],
                errors="coerce",
            )
            d = d.sort_values(
                "_sort",
                ascending=False,
            )
            break

    return d.iloc[0].to_dict()


def first(row, names):
    for name in names:
        value = row.get(name)
        if clean(value):
            return clean(value)

    return ""


def game_identity(sport, row):
    if sport == "NFL":
        key = clean(
            row.get("game_key")
        )
        away, home = (
            key.split("@", 1)
            if "@" in key
            else ("Away", "Home")
        )
        return away, home

    away = first(
        row,
        [
            "away_team_name",
            "away_team_canonical",
            "away_team",
        ],
    )

    home = first(
        row,
        [
            "home_team_name",
            "home_team_canonical",
            "home_team",
        ],
    )

    return (
        away or "Away",
        home or "Home",
    )


def game_selection(row):
    return first(
        row,
        [
            "selection_canonical",
            "selection",
        ],
    )


def game_market(row):
    return first(
        row,
        [
            "market_canonical",
            "market",
        ],
    )


def evidence_score(row):
    return first(
        row,
        [
            "evidence_score",
            "hulk_market_score",
        ],
    )


def books(row):
    return first(
        row,
        [
            "sportsbook_count",
            "approved_book_count",
            "sw_books",
            "book_count",
        ],
    )


def providers(row):
    return first(
        row,
        [
            "provider_count",
            "provider_evidence_count",
        ],
    )


def current_counts(sport):
    cfg = SPORT_DATA[sport]

    return {
        "game_finalists":
            len(read_csv(cfg["games"])),
        "prop_finalists":
            len(read_csv(cfg["props"])),
        "pickem_finalists":
            len(read_csv(cfg["pickem"])),
        "fantasy_rows":
            len(read_csv(cfg["fantasy"])),
    }


def game_preview(sport):
    cfg = SPORT_DATA[sport]
    df = read_csv(cfg["games"])
    row = top_row(df)

    if not row:
        return None

    away, home = game_identity(
        sport,
        row,
    )

    selection = game_selection(row)
    market = game_market(row)
    score = evidence_score(row)
    book_count = books(row)
    provider_count = providers(row)

    details = []

    if sport == "NFL":
        details.append(
            "The market-data quality is "
            + clean(
                row.get("market_data_quality")
                or "not labeled"
            )
            + ", with provider agreement marked "
            + clean(
                row.get("provider_agreement")
                or "not labeled"
            )
            + "."
        )

        model_status = clean(
            row.get("model_status")
        )

        if model_status:
            details.append(
                "The current model note is: "
                + model_status
                + "."
            )

    elif sport == "MLB":
        details.append(
            "Recent-form edge: "
            + num(row.get("form_edge"))
            + "; recent win-rate edge: "
            + num(row.get("winpct_edge"))
            + "; probable-pitcher context edge: "
            + num(row.get("pitcher_edge"))
            + "."
        )

        away_pitcher = clean(
            row.get("away_probable_pitcher")
        )
        home_pitcher = clean(
            row.get("home_probable_pitcher")
        )

        if away_pitcher or home_pitcher:
            details.append(
                "The current probable-pitcher listing is "
                + (away_pitcher or "TBD")
                + " vs. "
                + (home_pitcher or "TBD")
                + "."
            )

    elif sport == "CFB":
        details.append(
            "Current Elo edge: "
            + num(row.get("current_elo_edge"))
            + "; current SRS edge: "
            + num(row.get("current_srs_edge"))
            + "."
        )

        support = row.get(
            "historical_comp_selected_support"
        )

        if clean(support):
            details.append(
                "The leakage-safe historical-comparison set "
                "supports the selected side at "
                + num(
                    float(support) * 100,
                    1,
                )
                + "% within that comparison sample. "
                "That figure is historical-comparison frequency, "
                "not a Sports HULK win probability."
            )

    elif sport in {"NBA", "NHL"}:
        context = clean(
            row.get("context_direction")
        )

        if context:
            details.append(
                "Independent historical context is currently "
                + context.lower()
                + "."
            )

        if sport == "NHL":
            details.append(
                "Injury blocks on the current matchup: away "
                + num(
                    row.get("away_injury_blocks"),
                    0,
                )
                + ", home "
                + num(
                    row.get("home_injury_blocks"),
                    0,
                )
                + "."
            )

    title = (
        f"{away} at {home}: "
        "What Sports HULK Is Watching"
    )

    body = (
        f"## The matchup\n\n"
        f"Sports HULK currently has **{selection}** in its "
        f"{market.lower() if market else 'game'} research lane for "
        f"{away} at {home}. The current evidence score is **{score}**. "
        "That score is a research-ranking signal, not a win probability.\n\n"
        "## What is supporting the research\n\n"
        + (
            f"The current market snapshot includes {book_count or 'multiple'} "
            f"sportsbooks"
            + (
                f" across {provider_count} data providers"
                if provider_count
                else ""
            )
            + ". "
        )
        + " ".join(details)
        + "\n\n"
        "## What could change\n\n"
        "Sports HULK continues to re-check live market data, current "
        "availability, recent performance and the sport-specific historical "
        "context. A later injury, lineup change, goalie or pitcher update, "
        "or meaningful market move can change the qualification status.\n\n"
        "## HULK read\n\n"
        "This is the strongest current game-level research signal in this "
        f"{sport} snapshot. It is presented as analysis, not a guarantee, "
        "and it will remain tied to the underlying data that produced it."
    )

    return {
        "sport": sport,
        "article_type": "GAME_PREVIEW",
        "topic_key":
            clean(row.get("game_key"))
            or f"{away}|{home}",
        "title": title,
        "dek":
            (
                "Current matchup intelligence, market context "
                "and the signals behind Sports HULK's research."
            ),
        "body_markdown": body,
        "source_urls": "[]",
        "source_headlines": "[]",
        "hulk_data_files": json.dumps(
            [str(cfg["games"])],
        ),
        "factual_basis":
            "SPORTS_HULK_DERIVED_INTELLIGENCE",
        "keywords":
            f"{sport},{away},{home},sports analysis,game preview",
    }


def fantasy_article(sport):
    cfg = SPORT_DATA[sport]

    if not cfg["fantasy"]:
        if sport != "NFL":
            return None

        d = read_csv(
            ROOT
            / "nfl_live"
            / "decision"
            / "NFL_PROP_FINALISTS.csv"
        )

        if d.empty:
            return None

        players = (
            d["player_dfs"]
            .dropna()
            .astype(str)
            .drop_duplicates()
            .head(3)
            .tolist()
        )

        if not players:
            return None

        body = (
            "## Players on the current usage/prop radar\n\n"
            + "\n".join(
                f"- **{player}** is appearing in the current "
                "qualified player-research set."
                for player in players
            )
            + "\n\n"
            "## Why this matters for fantasy\n\n"
            "Sports HULK treats fantasy context as a separate layer from "
            "sportsbook or pick'em qualification. Usage, snap share, role, "
            "injury status and recent opportunity are the inputs that matter "
            "here. A prop appearing in the research set is not automatically "
            "a start/sit recommendation.\n\n"
            "## HULK watch\n\n"
            "The system will keep re-checking availability and usage before "
            "these players' games. The goal is to surface changing opportunity, "
            "not manufacture a fantasy call when the evidence is incomplete."
        )

        return {
            "sport": "NFL",
            "article_type": "FANTASY_WATCH",
            "topic_key": "|".join(players),
            "title":
                "NFL Fantasy Watch: Players Moving Onto the HULK Radar",
            "dek":
                "Usage and player-research signals worth monitoring.",
            "body_markdown": body,
            "source_urls": "[]",
            "source_headlines": "[]",
            "hulk_data_files":
                json.dumps(
                    [
                        str(
                            ROOT
                            / "nfl_live"
                            / "decision"
                            / "NFL_PROP_FINALISTS.csv"
                        )
                    ]
                ),
            "factual_basis":
                "SPORTS_HULK_DERIVED_INTELLIGENCE",
            "keywords":
                "NFL,fantasy football,usage,player props",
        }

    d = read_csv(cfg["fantasy"])

    if d.empty:
        return None

    d = d.head(3)

    players = []

    for _, row in d.iterrows():
        player = first(
            row,
            [
                "player",
                "player_current",
                "player_history",
            ],
        )

        if not player:
            continue

        team = first(
            row,
            [
                "team",
                "team_current",
                "team_history",
            ],
        )

        trend = first(
            row,
            [
                "fantasy_trend",
                "fantasy_context_score",
                "trend_vs_season",
                "recent_usage_index",
            ],
        )

        players.append(
            (
                player,
                team,
                trend,
            )
        )

    if not players:
        return None

    bullets = []

    for player, team, trend in players:
        line = (
            f"- **{player}**"
            + (
                f" ({team})"
                if team
                else ""
            )
            + " is in the current fantasy-context watchlist."
        )

        if trend:
            line += (
                " Current context/trend marker: "
                + clean(trend)
                + "."
            )

        bullets.append(line)

    body = (
        "## Current watchlist\n\n"
        + "\n".join(bullets)
        + "\n\n"
        "## What Sports HULK is measuring\n\n"
        "The fantasy layer looks for opportunity and role signals in the "
        "current data rather than copying a generic ranking list. Recent "
        "usage and performance are compared with longer-run context, while "
        "availability information remains a separate gate.\n\n"
        "## Important distinction\n\n"
        "These are research-context signals. Sports HULK is not claiming a "
        "specific fantasy-platform point total, and the watchlist is not an "
        "automatic start/sit instruction."
    )

    names = [
        x[0]
        for x in players
    ]

    return {
        "sport": sport,
        "article_type": "FANTASY_WATCH",
        "topic_key": "|".join(names),
        "title":
            f"{sport} Fantasy Watch: "
            + ", ".join(names[:3]),
        "dek":
            "Players currently standing out in Sports HULK's usage and opportunity context.",
        "body_markdown": body,
        "source_urls": "[]",
        "source_headlines": "[]",
        "hulk_data_files":
            json.dumps(
                [str(cfg["fantasy"])]
            ),
        "factual_basis":
            "SPORTS_HULK_DERIVED_INTELLIGENCE",
        "keywords":
            f"{sport},fantasy,{','.join(names)}",
    }


def news_impact_articles(news):
    if news.empty:
        return []

    d = news.copy()
    d["_published"] = pd.to_datetime(
        d["published_at"],
        utc=True,
        errors="coerce",
    )

    priority = {
        "INJURY": 0,
        "TRANSACTION": 1,
        "LINEUP_ROLE": 2,
        "FANTASY": 3,
        "NEWS": 4,
        "RECAP": 5,
        "RANKINGS": 6,
    }

    d["_priority"] = (
        d["news_type"]
        .map(priority)
        .fillna(9)
    )

    d = d.sort_values(
        ["sport", "_priority", "_published"],
        ascending=[True, True, False],
    )

    output = []

    for sport in SPORT_DATA:
        subset = d[
            d["sport"].eq(sport)
        ].head(2)

        counts = current_counts(
            sport
        )

        for _, row in subset.iterrows():
            headline = clean(
                row.get("headline")
            )

            url = clean(
                row.get("source_url")
            )

            source = clean(
                row.get("source")
            ) or "External source"

            news_type = clean(
                row.get("news_type")
            ) or "NEWS"

            title = (
                f"{sport} News Impact Watch: "
                + headline
            )

            body = (
                "## What was reported\n\n"
                f"**{source}** reported: **{headline}**\n\n"
                "Sports HULK stores the source, publication time and link "
                "with the fact record. It does not copy the publisher's "
                "article body into the HULK database.\n\n"
                "## Why Sports HULK is tracking it\n\n"
            )

            if news_type == "INJURY":
                body += (
                    "Availability news can affect player usage, lineup "
                    "assumptions, fantasy context and game-level research. "
                    "The report is treated as sourced context; it does not "
                    "automatically become a pick or force a model change.\n\n"
                )

            elif news_type == "TRANSACTION":
                body += (
                    "Roster movement can alter role, depth and matchup "
                    "assumptions. Sports HULK keeps the report separate from "
                    "its own analysis until current data reflects the change.\n\n"
                )

            elif news_type == "LINEUP_ROLE":
                body += (
                    "Role and lineup information can change opportunity "
                    "before a game. The system will compare the report with "
                    "the next official/current data refresh.\n\n"
                )

            elif news_type == "FANTASY":
                body += (
                    "Fantasy news matters when it corresponds with a change "
                    "in real usage, role or availability. HULK uses it as a "
                    "lead to investigate, not as a substitute for the data.\n\n"
                )

            else:
                body += (
                    "The story is relevant to the current sport feed and is "
                    "being retained as attributed context for game, player "
                    "and fantasy intelligence.\n\n"
                )

            body += (
                "## Current HULK state\n\n"
                f"At generation time, {sport} has "
                f"**{counts['game_finalists']}** qualified game research "
                f"items, **{counts['prop_finalists']}** qualified player-prop "
                f"items and **{counts['pickem_finalists']}** qualified "
                "pick'em items. Those counts may change as new facts and "
                "market data arrive.\n\n"
                "## What happens next\n\n"
                "The next refresh checks whether this report is supported by "
                "current availability, lineup, usage or market evidence. "
                "Sports HULK's analysis remains distinct from the publisher's "
                "report, and any later HULK conclusion will retain the source "
                "that triggered the review."
            )

            output.append({
                "sport": sport,
                "article_type":
                    "NEWS_IMPACT",
                "topic_key":
                    clean(
                        row.get("news_id")
                    ),
                "title": title,
                "dek":
                    (
                        "A sourced development and the specific "
                        "Sports HULK intelligence lanes it may affect."
                    ),
                "body_markdown": body,
                "source_urls":
                    json.dumps(
                        [url]
                        if url
                        else []
                    ),
                "source_headlines":
                    json.dumps(
                        [headline]
                    ),
                "hulk_data_files":
                    json.dumps(
                        [
                            str(
                                SPORT_DATA[
                                    sport
                                ][
                                    "games"
                                ]
                            )
                        ]
                    ),
                "factual_basis":
                    "ATTRIBUTED_EXTERNAL_REPORT_PLUS_HULK_STATE",
                "keywords":
                    f"{sport},{news_type.lower()},sports news,{headline[:60]}",
            })

    return output


def prepare_draft(item):
    fingerprint = stable_id(
        item["sport"],
        item["article_type"],
        item["topic_key"],
        item["title"],
    )

    slug = slugify(
        item["title"]
    )

    return {
        "draft_id":
            fingerprint,
        "created_at":
            NOW.isoformat(),
        "updated_at":
            NOW.isoformat(),
        "status":
            "DRAFT",
        "sport":
            item["sport"],
        "article_type":
            item["article_type"],
        "slug":
            slug,
        "title":
            item["title"],
        "dek":
            item["dek"],
        "body_markdown":
            item["body_markdown"],
        "source_urls":
            item["source_urls"],
        "source_headlines":
            item["source_headlines"],
        "hulk_data_files":
            item["hulk_data_files"],
        "factual_basis":
            item["factual_basis"],
        "keywords":
            item["keywords"],
        "requires_approval":
            True,
        "approved_at":
            "",
        "published_at":
            "",
        "publish_destination":
            "",
        "publish_url":
            "",
        "generation_mode":
            "HULK_STRUCTURED_ORIGINAL",
        "external_article_body_copied":
            False,
        "evidence_score_is_probability":
            False,
    }


def write_markdown(draft):
    path = (
        DRAFT_DIR
        / (
            draft["draft_id"]
            + ".md"
        )
    )

    source_urls = json.loads(
        draft.get("source_urls")
        or "[]"
    )

    sources = (
        "\n".join(
            "- " + url
            for url in source_urls
            if url
        )
        or "- Internal Sports HULK intelligence"
    )

    text = (
        "# "
        + draft["title"]
        + "\n\n"
        + draft["dek"]
        + "\n\n"
        + draft["body_markdown"]
        + "\n\n"
        "## Sources / provenance\n\n"
        + sources
        + "\n\n"
        "_Draft status: "
        + draft["status"]
        + " · Human approval required before publishing._\n"
    )

    path.write_text(
        text,
        encoding="utf-8",
    )


def main():
    DRAFT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    news = read_csv(
        NEWS
    )

    generated = []

    for sport in SPORT_DATA:
        preview = game_preview(
            sport
        )

        if preview:
            generated.append(
                preview
            )

        if sport in {
            "NFL",
            "MLB",
            "NBA",
            "NHL",
        }:
            fantasy = fantasy_article(
                sport
            )

            if fantasy:
                generated.append(
                    fantasy
                )

    generated += news_impact_articles(
        news
    )

    new = pd.DataFrame(
        [
            prepare_draft(item)
            for item in generated
        ]
    )

    old = read_csv(
        DRAFTS
    )

    if old.empty:
        merged = new.copy()

    else:
        preserve = {
            str(row["draft_id"]):
                row.to_dict()
            for _, row in old.iterrows()
        }

        rows = []

        for _, row in new.iterrows():
            item = row.to_dict()
            prior = preserve.get(
                str(item["draft_id"])
            )

            if prior:
                for field in [
                    "created_at",
                    "status",
                    "approved_at",
                    "published_at",
                    "publish_destination",
                    "publish_url",
                ]:
                    item[field] = prior.get(
                        field,
                        item.get(field),
                    )

            rows.append(item)

        current_ids = {
            str(x)
            for x in new["draft_id"]
        }

        for _, row in old.iterrows():
            if str(row["draft_id"]) not in current_ids:
                rows.append(
                    row.to_dict()
                )

        merged = pd.DataFrame(
            rows
        )

    merged = (
        merged
        .drop_duplicates(
            "draft_id",
            keep="last",
        )
        .sort_values(
            "created_at",
            ascending=False,
        )
    )

    merged.to_csv(
        DRAFTS,
        index=False,
    )

    for _, row in merged.iterrows():
        write_markdown(
            row.to_dict()
        )

    receipt = {
        "generated_at":
            NOW.isoformat(),
        "new_generation_candidates":
            int(len(new)),
        "total_drafts":
            int(len(merged)),
        "draft_status_counts":
            {
                str(k):
                    int(v)
                for k, v in (
                    merged["status"]
                    .value_counts()
                    .to_dict()
                ).items()
            },
        "generation_mode":
            "HULK_STRUCTURED_ORIGINAL",
        "llm_api_required":
            False,
        "human_approval_required":
            True,
        "external_article_bodies_copied":
            False,
    }

    RECEIPT.write_text(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
    )

    print(
        "NEW GENERATION CANDIDATES:",
        len(new),
    )
    print(
        "TOTAL ARTICLE DRAFTS:",
        len(merged),
    )
    print(
        "STATUS:",
        receipt[
            "draft_status_counts"
        ],
    )
    print(
        "RESULT: ARTICLE_DRAFT_ENGINE_READY"
    )


if __name__ == "__main__":
    main()
