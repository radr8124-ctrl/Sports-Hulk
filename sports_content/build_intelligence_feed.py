#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import html
import json
import re

import pandas as pd
import requests


ROOT = Path("/home/ubuntu/sports-hulk")
CONTENT = ROOT / "sports_content"
DERIVED = CONTENT / "derived"
HISTORY = CONTENT / "history"

NEWS_OUT = DERIVED / "SPORTS_NEWS_CURRENT.csv"
FACTS_OUT = DERIVED / "SPORTS_FACTS_CURRENT.csv"
NEWS_HISTORY = HISTORY / "SPORTS_NEWS_HISTORY.csv"
FACT_HISTORY = HISTORY / "SPORTS_FACT_HISTORY.csv"
RECEIPT = DERIVED / "CONTENT_INGEST_RECEIPT.json"

NOW = datetime.now(timezone.utc)

SPORTS = {
    "NFL": ("football", "nfl"),
    "MLB": ("baseball", "mlb"),
    "NBA": ("basketball", "nba"),
    "NHL": ("hockey", "nhl"),
    "CFB": ("football", "college-football"),
    "CBB": ("basketball", "mens-college-basketball"),
}

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Sports-HULK-Content/1.0",
}


def clean(value, limit=None):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    value = html.unescape(str(value)).strip()

    if value.lower() in {"nan", "none", "nat", "<na>"}:
        return ""

    value = re.sub(r"\s+", " ", value)

    if limit and len(value) > limit:
        value = value[:limit].rsplit(" ", 1)[0] + "…"

    return value


def norm(value):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        clean(value).lower(),
    )


def stable_id(*parts):
    raw = "|".join(
        clean(x)
        for x in parts
    )
    return hashlib.sha256(
        raw.encode()
    ).hexdigest()[:20]


def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()


def append_dedup(current, history_path, key):
    old = read_csv(history_path)

    if old.empty:
        out = current.copy()
    elif current.empty:
        out = old.copy()
    else:
        out = pd.concat(
            [old, current],
            ignore_index=True,
            sort=False,
        ).drop_duplicates(
            key,
            keep="last",
        )

    out.to_csv(
        history_path,
        index=False,
    )

    return out


def web_url(article):
    links = article.get("links") or {}
    web = links.get("web") or {}

    if isinstance(web, dict):
        return clean(web.get("href"))

    return ""


def categories(article):
    output = []

    for item in article.get("categories") or []:
        if not isinstance(item, dict):
            continue

        value = (
            item.get("description")
            or item.get("type")
            or item.get("sportId")
            or item.get("teamId")
        )

        if value:
            output.append(clean(value))

    return "|".join(
        sorted(set(output))
    )


def classify_news(headline, description, article_type):
    text = (
        clean(headline)
        + " "
        + clean(description)
    ).lower()

    injury_tokens = [
        "injur",
        "questionable",
        "doubtful",
        "out for",
        "ruled out",
        "injured reserve",
        "concussion",
        "surgery",
        "day-to-day",
    ]

    if (
        any(
            token in text
            for token in injury_tokens
        )
        or re.search(
            r"(?<![a-z0-9])ir(?![a-z0-9])",
            text,
        )
    ):
        return "INJURY"

    if any(
        token in text
        for token in [
            "trade", "traded", "waive", "waived",
            "signs", "signed", "released",
            "suspend", "suspended", "transaction",
        ]
    ):
        return "TRANSACTION"

    if "fantasy" in text:
        return "FANTASY"

    if any(
        token in text
        for token in [
            "lineup", "starter", "starting",
            "depth chart", "rotation",
        ]
    ):
        return "LINEUP_ROLE"

    if str(article_type).lower() == "recap":
        return "RECAP"

    if any(
        token in text
        for token in [
            "ranking", "rankings", "top 25",
            "poll",
        ]
    ):
        return "RANKINGS"

    return "NEWS"


def fetch_news(sport, family, league):
    url = (
        "https://site.api.espn.com/"
        f"apis/site/v2/sports/{family}/{league}/news"
    )

    r = requests.get(
        url,
        params={"limit": 30},
        headers=HEADERS,
        timeout=20,
    )
    r.raise_for_status()

    rows = []

    for article in r.json().get("articles") or []:
        source_id = clean(article.get("id"))
        headline = clean(
            article.get("headline"),
            240,
        )
        description = clean(
            article.get("description"),
            450,
        )
        article_type = clean(
            article.get("type")
        )

        if not headline:
            continue

        published = clean(
            article.get("published")
        )

        rows.append({
            "news_id":
                stable_id(
                    sport,
                    "ESPN",
                    source_id,
                    headline,
                ),
            "sport": sport,
            "source": "ESPN",
            "source_tier": "EXTERNAL_NEWS",
            "source_id": source_id,
            "headline": headline,
            "description": description,
            "news_type": classify_news(
                headline,
                description,
                article_type,
            ),
            "provider_type": article_type,
            "byline": clean(
                article.get("byline"),
                120,
            ),
            "categories": categories(article),
            "published_at": published,
            "source_url": web_url(article),
            "premium_source": bool(
                article.get("premium", False)
            ),
            "ingested_at": NOW.isoformat(),
            "body_ingested": False,
            "provenance_status": "SOURCE_LINK_PRESERVED",
        })

    return rows


def injury_facts():
    specs = [
        (
            "NFL",
            ROOT / "nfl_live" / "decision"
            / "NFL_ESPN_INJURIES.csv",
        ),
        (
            "NBA",
            ROOT / "nba_live" / "derived"
            / "NBA_INJURIES_CURRENT.csv",
        ),
        (
            "NHL",
            ROOT / "nhl_live" / "derived"
            / "NHL_INJURIES_CURRENT.csv",
        ),
    ]

    rows = []

    for sport, path in specs:
        d = read_csv(path)

        if d.empty:
            continue

        for _, r in d.iterrows():
            status = clean(r.get("status"))
            injury = clean(
                r.get("injury_type")
            )
            player = clean(r.get("player"))
            team = clean(
                r.get("team")
                or r.get("team_name")
            )
            detail = clean(
                r.get("detail"),
                350,
            )

            if not player:
                continue

            if sport == "NFL" and status.lower() == "active":
                continue

            severity = "REVIEW"

            gate = clean(
                r.get("injury_gate")
            ).upper()

            if (
                gate == "BLOCK"
                or status.lower() in {
                    "out",
                    "injured reserve",
                    "suspension",
                }
            ):
                severity = "HIGH"

            elif any(
                token in status.lower()
                for token in [
                    "questionable",
                    "day-to-day",
                    "doubtful",
                ]
            ):
                severity = "MEDIUM"

            text = (
                player
                + " — "
                + status
                + (
                    " (" + injury + ")"
                    if injury
                    else ""
                )
            )

            if detail and detail.lower() not in {
                status.lower(),
                "not specified",
            }:
                text += ". " + detail

            rows.append({
                "fact_id":
                    stable_id(
                        sport,
                        "INJURY",
                        player,
                        team,
                        status,
                        injury,
                        detail,
                    ),
                "sport": sport,
                "fact_type": "INJURY",
                "severity": severity,
                "subject": player,
                "team": team,
                "fact_text": clean(text, 500),
                "source": clean(
                    r.get("source")
                )
                or "ESPN injury context",
                "source_tier": "FACT_CONTEXT",
                "source_url": "",
                "event_id": clean(
                    r.get("event_id")
                ),
                "effective_at": clean(
                    r.get("updated")
                    or r.get("start")
                ),
                "return_date": clean(
                    r.get("return_date")
                ),
                "verified_status":
                    "CURRENT_SOURCE_RECORD",
                "ingested_at":
                    NOW.isoformat(),
            })

    return rows


def mlb_availability_facts():
    d = read_csv(
        ROOT
        / "baseball_vault"
        / "latest"
        / "MLB_SCHEDULE.csv"
    )

    rows = []

    if d.empty:
        return rows

    for _, r in d.iterrows():
        game_pk = clean(r.get("gamePk"))
        start = clean(r.get("gameDate"))

        for side in ["away", "home"]:
            player = clean(
                r.get(
                    f"{side}_probable_pitcher"
                )
            )

            team = clean(
                r.get(
                    f"{side}_team"
                )
            )

            if not player:
                continue

            text = (
                player
                + " is listed as the probable pitcher for "
                + team
                + "."
            )

            rows.append({
                "fact_id":
                    stable_id(
                        "MLB",
                        "PROBABLE_PITCHER",
                        game_pk,
                        side,
                        player,
                    ),
                "sport": "MLB",
                "fact_type":
                    "PROBABLE_PITCHER",
                "severity": "CONTEXT",
                "subject": player,
                "team": team,
                "fact_text": text,
                "source": "MLB StatsAPI",
                "source_tier": "OFFICIAL_FACT",
                "source_url": "",
                "event_id": game_pk,
                "effective_at": start,
                "return_date": "",
                "verified_status":
                    "OFFICIAL_LISTING",
                "ingested_at":
                    NOW.isoformat(),
            })

    return rows


def news_as_facts(news):
    rows = []

    for r in news:
        if r["news_type"] not in {
            "INJURY",
            "TRANSACTION",
            "LINEUP_ROLE",
        }:
            continue

        rows.append({
            "fact_id":
                stable_id(
                    r["sport"],
                    "NEWS_FACT",
                    r["news_id"],
                ),
            "sport": r["sport"],
            "fact_type": r["news_type"],
            "severity":
                "HIGH"
                if r["news_type"] == "INJURY"
                else "REVIEW",
            "subject": r["headline"],
            "team": "",
            "fact_text": r["description"]
                or r["headline"],
            "source": r["source"],
            "source_tier":
                "EXTERNAL_NEWS",
            "source_url":
                r["source_url"],
            "event_id": "",
            "effective_at":
                r["published_at"],
            "return_date": "",
            "verified_status":
                "ATTRIBUTED_NEWS_REPORT",
            "ingested_at":
                NOW.isoformat(),
        })

    return rows


def main():
    DERIVED.mkdir(
        parents=True,
        exist_ok=True,
    )
    HISTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    news = []

    for sport, (
        family,
        league,
    ) in SPORTS.items():
        try:
            rows = fetch_news(
                sport,
                family,
                league,
            )
        except Exception as exc:
            print(
                sport,
                "news warning:",
                type(exc).__name__,
            )
            rows = []

        news.extend(rows)
        print(
            sport,
            "NEWS:",
            len(rows),
        )

    news_df = pd.DataFrame(news)

    if not news_df.empty:
        news_df = (
            news_df
            .drop_duplicates(
                "news_id",
                keep="last",
            )
            .sort_values(
                "published_at",
                ascending=False,
            )
        )

    news_df.to_csv(
        NEWS_OUT,
        index=False,
    )

    facts = []
    facts += injury_facts()
    facts += mlb_availability_facts()
    facts += news_as_facts(news)

    facts_df = pd.DataFrame(facts)

    if not facts_df.empty:
        facts_df = (
            facts_df
            .drop_duplicates(
                "fact_id",
                keep="last",
            )
            .sort_values(
                ["sport", "fact_type", "effective_at"],
                ascending=[True, True, False],
            )
        )

    facts_df.to_csv(
        FACTS_OUT,
        index=False,
    )

    news_history = append_dedup(
        news_df,
        NEWS_HISTORY,
        "news_id",
    )

    fact_history = append_dedup(
        facts_df,
        FACT_HISTORY,
        "fact_id",
    )

    receipt = {
        "generated_at":
            NOW.isoformat(),
        "current_news_rows":
            int(len(news_df)),
        "current_fact_rows":
            int(len(facts_df)),
        "news_history_rows":
            int(len(news_history)),
        "fact_history_rows":
            int(len(fact_history)),
        "sports":
            {
                sport:
                    int(
                        news_df[
                            "sport"
                        ].eq(sport).sum()
                    )
                    if not news_df.empty
                    else 0
                for sport in SPORTS
            },
        "full_article_bodies_ingested":
            False,
        "source_links_preserved":
            True,
        "external_content_republished":
            False,
    }

    RECEIPT.write_text(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
    )

    print()
    print(
        "NEWS CURRENT:",
        len(news_df),
    )
    print(
        "FACTS CURRENT:",
        len(facts_df),
    )
    print(
        "NEWS HISTORY:",
        len(news_history),
    )
    print(
        "FACT HISTORY:",
        len(fact_history),
    )
    print(
        "RESULT: CONTENT_INTELLIGENCE_READY"
    )


if __name__ == "__main__":
    main()
