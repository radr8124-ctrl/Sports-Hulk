#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timezone
import json
import os
import re

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path("/home/ubuntu/sports-hulk")
MLB = ROOT / "mlb_live"
MARKETS = MLB / "markets"
CURRENT = MARKETS / "current"
HISTORY = MARKETS / "history"
RAW = MARKETS / "raw"
RECEIPTS = MARKETS / "receipts"

for p in [CURRENT, HISTORY, RAW, RECEIPTS]:
    p.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
NOW = pd.Timestamp.now(tz="UTC")
HORIZON = NOW + pd.Timedelta(days=10)


def safe_json(r):
    try:
        return r.json()
    except Exception:
        return {}


def request(url, headers=None, params=None, timeout=30):
    try:
        r = requests.get(
            url,
            headers=headers or {},
            params=params or {},
            timeout=timeout,
        )
        return r, safe_json(r)
    except Exception as exc:
        return None, {"_error": f"{type(exc).__name__}: {exc}"}


def list_data(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ["data", "events", "items", "results", "fixtures", "sports"]:
        v = payload.get(key)
        if isinstance(v, list):
            return v
    return []


def save_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, default=str)
    )


def in_window(value):
    dt = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(dt):
        return True
    return (
        dt >= NOW - pd.Timedelta(hours=2)
        and dt <= HORIZON
    )


game_rows = []
prop_rows = []
pp_rows = []

report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "sport": "MLB",
    "providers": {},
}


# ============================================================
# SPORTWIZZARD
# ============================================================

sw_key = (os.getenv("SPORTWIZZARD_API_KEY") or "").strip()

if sw_key:
    SW = "https://api.sportwizzard.com/api/v1"
    HEADERS = {"X-Api-Key": sw_key}

    def sw_page(path, params, max_pages=3):
        out = []
        receipts = []
        cursor = None

        for page in range(1, max_pages + 1):
            q = dict(params)
            if cursor:
                q["cursor"] = cursor

            r, payload = request(
                SW + path,
                headers=HEADERS,
                params=q,
            )
            code = r.status_code if r is not None else None
            rows = list_data(payload)
            receipts.append({
                "page": page,
                "http": code,
                "rows": len(rows),
            })

            if code != 200:
                break

            out.extend(rows)

            cursor = (
                payload.get("nextCursor")
                if isinstance(payload, dict)
                else None
            )

            if not cursor:
                break

        return out, receipts

    events, event_receipts = sw_page(
        "/events",
        {
            "league": "mlb",
            "limit": 100,
        },
        max_pages=2,
    )

    event_map = {}

    for e in events:
        eid = e.get("id")
        if not eid:
            continue
        event_map[str(eid)] = {
            "start": e.get("startTime"),
            "away_team": e.get("awayTeamName"),
            "home_team": e.get("homeTeamName"),
        }

    r, books_payload = request(
        SW + "/sportsbooks",
        headers=HEADERS,
    )

    books = list_data(books_payload)

    available = {
        str(x.get("id", "")).lower()
        for x in books
        if isinstance(x, dict) and x.get("id")
    }

    preferred = [
        "draftkings",
        "fanduel",
        "betmgm",
        "caesars",
        "fanatics",
        "hardrock",
        "pinnacle",
        "bet365",
        "thescore",
    ]

    selected = [
        b for b in preferred
        if b in available
    ]

    book_receipts = {}

    for book in selected:
        rows, receipts = sw_page(
            "/odds",
            {
                "league": "mlb",
                "scope": "event",
                "sportsbook": book,
                "is_main": "true",
                "limit": 1000,
            },
            max_pages=3,
        )

        book_receipts[book] = {
            "rows": len(rows),
            "pages": receipts,
        }

        for x in rows:
            if x.get("suspended") is True:
                continue

            eid = str(x.get("eventId") or "")
            ev = event_map.get(eid, {})

            start = (
                x.get("eventStartTime")
                or ev.get("start")
            )

            if not in_window(start):
                continue

            period = str(
                x.get("period") or ""
            ).upper()

            if period and period != "FULL":
                continue

            market = str(
                x.get("market") or ""
            ).upper()

            base = {
                "provider": "sportwizzard",
                "sportsbook": book,
                "event_id": eid,
                "start": start,
                "away_team": ev.get("away_team"),
                "home_team": ev.get("home_team"),
                "market": market,
                "market_subtype": x.get("marketSubtype"),
                "selection": x.get("selection"),
                "side": x.get("side"),
                "line": x.get("line"),
                "price_american": x.get("priceAmerican"),
                "player_id": x.get("playerId"),
                "player": x.get("playerName"),
            }

            if base["player"] or base["player_id"]:
                prop_rows.append(base)

            elif market in {
                "MONEYLINE",
                "SPREAD",
                "TOTAL",
            }:
                game_rows.append(base)

    pp_raw, pp_receipts = sw_page(
        "/odds",
        {
            "league": "mlb",
            "scope": "event",
            "sportsbook": "prizepicks",
            "limit": 1000,
        },
        max_pages=3,
    )

    for x in pp_raw:
        if x.get("suspended") is True:
            continue

        player = x.get("playerName")
        player_id = x.get("playerId")

        if not (player or player_id):
            continue

        eid = str(x.get("eventId") or "")
        ev = event_map.get(eid, {})

        start = (
            x.get("eventStartTime")
            or ev.get("start")
        )

        if not in_window(start):
            continue

        pp_rows.append({
            "provider": "sportwizzard",
            "sportsbook": "prizepicks",
            "event_id": eid,
            "start": start,
            "away_team": ev.get("away_team"),
            "home_team": ev.get("home_team"),
            "player_id": player_id,
            "player": player,
            "market": x.get("market"),
            "market_subtype": x.get("marketSubtype"),
            "selection": x.get("selection"),
            "side": x.get("side"),
            "line": x.get("line"),
            "price_american": x.get("priceAmerican"),
        })

    report["providers"]["sportwizzard"] = {
        "events": len(events),
        "sportsbooks": selected,
        "book_receipts": book_receipts,
        "prizepicks_rows": len(pp_raw),
        "event_receipts": event_receipts,
        "prizepicks_receipts": pp_receipts,
    }


# ============================================================
# PROPLINE — GAME MARKETS ONLY
# ============================================================

pl_key = (os.getenv("PROPLINE_API_KEY") or "").strip()

if pl_key:
    PL = "https://api.prop-line.com/v1"
    HEADERS = {
        "X-API-Key": pl_key,
        "Accept": "application/json",
        "User-Agent": "Sports-HULK/1.0",
    }

    r, sports_payload = request(
        PL + "/sports",
        headers=HEADERS,
    )

    sport = None

    for s in list_data(sports_payload):
        blob = " ".join(
            str(s.get(k, ""))
            for k in [
                "key", "id", "sport",
                "title", "name", "description",
            ]
        ).lower()

        if "mlb" in blob or "baseball" in blob:
            sport = (
                s.get("key")
                or s.get("id")
                or s.get("sport")
            )
            if sport:
                break

    if not sport:
        sport = "baseball_mlb"

    r2, payload = request(
        f"{PL}/sports/{sport}/odds",
        headers=HEADERS,
        params={
            "markets": "h2h,spreads,totals",
        },
    )

    events = list_data(payload)

    save_json(
        RAW / f"PROPLINE_MLB_{STAMP}.json",
        payload,
    )

    for event in events:
        start = event.get("commence_time")

        if not in_window(start):
            continue

        for book in event.get("bookmakers") or []:
            book_name = (
                book.get("key")
                or book.get("title")
                or ""
            )

            for market in book.get("markets") or []:
                key = str(
                    market.get("key") or ""
                ).lower()

                if key not in {
                    "h2h",
                    "spreads",
                    "totals",
                }:
                    continue

                line_type = str(
                    market.get("line_type") or ""
                ).lower()

                if line_type and line_type != "main":
                    continue

                canonical = {
                    "h2h": "MONEYLINE",
                    "spreads": "SPREAD",
                    "totals": "TOTAL",
                }[key]

                for outcome in market.get("outcomes") or []:
                    game_rows.append({
                        "provider": "propline",
                        "sportsbook": book_name,
                        "event_id": event.get("id"),
                        "start": start,
                        "away_team": event.get("away_team"),
                        "home_team": event.get("home_team"),
                        "market": canonical,
                        "market_subtype": key,
                        "selection": outcome.get("name"),
                        "side": outcome.get("side"),
                        "line": outcome.get("point"),
                        "price_american": outcome.get("price"),
                        "player_id": None,
                        "player": None,
                    })

    report["providers"]["propline"] = {
        "resolved_sport": sport,
        "events": len(events),
        "http": r2.status_code if r2 is not None else None,
    }


def write(df, name):
    current = CURRENT / f"{name}.csv"
    hist = HISTORY / f"{name}_{STAMP}.csv"

    if df.empty:
        df.to_csv(current, index=False)
        return

    df = df.copy()
    df["start"] = pd.to_datetime(
        df["start"],
        utc=True,
        errors="coerce",
        format="mixed",
    )
    df["captured_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    subset = [
        c for c in [
            "provider",
            "sportsbook",
            "event_id",
            "market",
            "player",
            "selection",
            "side",
            "line",
            "price_american",
        ]
        if c in df.columns
    ]

    df = df.drop_duplicates(
        subset,
        keep="last",
    )

    df.to_csv(current, index=False)
    df.to_csv(hist, index=False)


game = pd.DataFrame(game_rows)
props = pd.DataFrame(prop_rows)
pp = pd.DataFrame(pp_rows)

write(game, "MLB_GAME_MARKET")
write(props, "MLB_PLAYER_PROP_MARKET")
write(pp, "MLB_PRIZEPICKS_MARKET")

report["normalized"] = {
    "game_rows": int(len(game)),
    "prop_rows": int(len(props)),
    "prizepicks_rows": int(len(pp)),
}

(
    RECEIPTS
    / "MLB_MARKET_RECEIPT_LATEST.json"
).write_text(
    json.dumps(
        report,
        indent=2,
        sort_keys=True,
        default=str,
    )
)

print("MLB GAME MARKET ROWS:", len(game))
print("MLB PLAYER PROP ROWS:", len(props))
print("MLB PRIZEPICKS ROWS:", len(pp))
print("RESULT: MLB_MARKETS_READY")
