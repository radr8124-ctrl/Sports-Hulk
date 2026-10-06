from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import email.utils
import json
import re
import xml.etree.ElementTree as ET

import requests

ROOT = Path("/home/ubuntu/sports-hulk")
OUTS = [
    ROOT / "commercial_web" / "public" / "fantasy_news.json",
    ROOT / "commercial_web" / "dist" / "fantasy_news.json",
]

FEEDS = [
    ("CBS Sports NFL", "https://www.cbssports.com/rss/headlines/nfl/"),
    ("Pro Football Rumors", "https://www.profootballrumors.com/feed"),
    ("RotoBaller", "https://www.rotoballer.com/rss"),
    ("4for4 Fantasy Football", "https://www.4for4.com/rss.xml"),
]

KEYWORDS = {
    "INJURY": [
        "injury", "injured", "questionable", "doubtful", "out ", "inactive",
        "practice", "hamstring", "ankle", "knee", "concussion", "limited",
    ],
    "ROSTER MOVE": [
        "signed", "released", "waived", "activated", "practice squad",
        "promoted", "roster", "claimed",
    ],
    "TRADE": ["trade", "traded", "deal", "acquire", "acquired"],
    "DEPTH CHART": [
        "starter", "starting", "backup", "depth chart", "rb1", "rb2",
        "wr1", "wr2", "committee", "snap", "role",
    ],
    "WAIVER WATCH": [
        "breakout", "waiver", "sleeper", "targets", "touches", "usage",
        "opportunity", "workload",
    ],
    "START/SIT WATCH": [
        "start", "sit", "matchup", "fantasy", "projection", "points",
    ],
}

def parse_date(raw):
    if not raw:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return None

def clean_text(raw):
    text = re.sub(r"<[^>]+>", " ", raw or "")
    return re.sub(r"\s+", " ", text).strip()

def classify(title, desc):
    text = f"{title} {desc}".lower()
    tags = []
    for tag, words in KEYWORDS.items():
        if any(w in text for w in words):
            tags.append(tag)
    return tags[:4] or ["NEWS"]

def fetch_feed(source, url):
    r = requests.get(
        url,
        headers={"User-Agent": "Sports-HULK/1.0"},
        timeout=20,
    )
    r.raise_for_status()
    root = ET.fromstring(r.content)
    items = []
    for item in root.findall(".//item")[:40]:
        title = clean_text(item.findtext("title"))
        link = clean_text(item.findtext("link"))
        desc = clean_text(item.findtext("description"))
        published = (
            item.findtext("pubDate")
            or item.findtext("{http://purl.org/dc/elements/1.1/}date")
        )
        if not title or not link:
            continue
        items.append({
            "source": source,
            "title": title,
            "url": link,
            "published_at": parse_date(published),
            "impact_tags": classify(title, desc),
        })
    return items

def main():
    rows = []
    errors = []
    for source, url in FEEDS:
        try:
            rows.extend(fetch_feed(source, url))
        except Exception as exc:
            errors.append({"source": source, "error": str(exc)})

    deduped = {}
    for row in rows:
        key = re.sub(r"[^a-z0-9]+", "", row["title"].lower())
        if not key:
            continue
        current = deduped.get(key)
        if current is None:
            deduped[key] = row
        else:
            sources = set(str(current["source"]).split(" + "))
            sources.add(row["source"])
            current["source"] = " + ".join(sorted(sources))

    news = list(deduped.values())
    news.sort(key=lambda x: x.get("published_at") or "", reverse=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(FEEDS),
        "article_count": len(news),
        "errors": errors,
        "articles": news[:80],
    }

    text = json.dumps(payload, indent=2)
    for target in OUTS:
        if target.parent.exists():
            target.write_text(text)

    print(
        f"FANTASY NEWS PASS sources={len(FEEDS)} "
        f"articles={len(news)} errors={len(errors)}"
    )

if __name__ == "__main__":
    main()
