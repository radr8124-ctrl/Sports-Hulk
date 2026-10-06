#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

import json
import os
import re

import pandas as pd
import requests
from dotenv import load_dotenv


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

CBB = ROOT / "cbb_live"

MARKETS = CBB / "markets"
CURRENT = MARKETS / "current"
HISTORY = MARKETS / "history"
RAW = MARKETS / "raw"
RECEIPTS = MARKETS / "receipts"


for p in [
    CURRENT,
    HISTORY,
    RAW,
    RECEIPTS,
]:
    p.mkdir(
        parents=True,
        exist_ok=True,
    )


load_dotenv(
    ROOT / ".env"
)


STAMP = datetime.now(
    timezone.utc
).strftime(
    "%Y%m%dT%H%M%SZ"
)

NOW = pd.Timestamp.now(
    tz="UTC"
)


GAME_COLUMNS = [
    "provider",
    "sportsbook",
    "event_id",
    "start",
    "away_team",
    "home_team",
    "market",
    "market_subtype",
    "selection",
    "side",
    "line",
    "price_american",
    "captured_at",
]


def safe_json(
    response,
):

    try:

        return response.json()

    except Exception:

        return {}


def request(
    url,
    headers=None,
    params=None,
    timeout=30,
):

    try:

        r = requests.get(
            url,
            headers=headers or {},
            params=params or {},
            timeout=timeout,
        )

        return (
            r,
            safe_json(
                r
            ),
        )

    except Exception as exc:

        return (
            None,
            {
                "_error":
                    (
                        type(
                            exc
                        ).__name__
                        + ": "
                        + str(
                            exc
                        )
                    )
            },
        )


def list_data(
    payload,
):

    if isinstance(
        payload,
        list,
    ):

        return payload


    if not isinstance(
        payload,
        dict,
    ):

        return []


    for key in [
        "data",
        "sports",
        "events",
        "items",
        "results",
        "fixtures",
        "leagues",
    ]:

        value = payload.get(
            key
        )


        if isinstance(
            value,
            list,
        ):

            return value


    return []


def norm(
    value,
):

    return re.sub(
        r"[^a-z0-9]+",
        "",
        str(
            value or ""
        ).lower(),
    )


def save_json(
    path,
    payload,
):

    Path(
        path
    ).write_text(
        json.dumps(
            payload,
            indent=2,
            default=str,
        )
    )


def sw_page(
    base,
    path,
    headers,
    params,
    max_pages=3,
):

    rows = []

    cursor = None

    receipts = []


    for page in range(
        1,
        max_pages + 1,
    ):

        q = dict(
            params
        )


        if cursor:

            q[
                "cursor"
            ] = cursor


        r, payload = request(
            base + path,
            headers=headers,
            params=q,
        )


        code = (
            r.status_code
            if r is not None
            else None
        )


        data = list_data(
            payload
        )


        receipts.append({
            "page":
                page,

            "http":
                code,

            "rows":
                len(
                    data
                ),
        })


        if code != 200:

            break


        rows.extend(
            data
        )


        cursor = (
            payload.get(
                "nextCursor"
            )
            if isinstance(
                payload,
                dict,
            )
            else None
        )


        if not cursor:

            break


    return (
        rows,
        receipts,
    )


game_rows = []


report = {
    "generated_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "sport":
        "CBB",

    "providers": {},

    "policies": {
        "college_player_props":
            False,

        "college_prizepicks":
            False,

        "college_fantasy":
            False,

        "market_is_probability":
            False,

        "the_odds_api_reserved":
            True,
    },
}


# ============================================================
# SPORTWIZZARD
# Dynamic league discovery — do not hardcode seasonal league
# ============================================================

sw_key = (
    os.getenv(
        "SPORTWIZZARD_API_KEY"
    )
    or ""
).strip()


if sw_key:

    SW = (
        "https://api.sportwizzard.com"
        "/api/v1"
    )

    SW_HEADERS = {
        "X-Api-Key":
            sw_key,
    }


    r, league_payload = request(
        SW
        + "/leagues",
        headers=SW_HEADERS,
    )


    league_rows = list_data(
        league_payload
    )


    active_leagues = []


    for item in league_rows:

        if isinstance(
            item,
            str,
        ):

            active_leagues.append(
                item
            )

        elif isinstance(
            item,
            dict,
        ):

            value = (
                item.get(
                    "key"
                )
                or item.get(
                    "slug"
                )
                or item.get(
                    "league"
                )
                or item.get(
                    "name"
                )
            )


            if value:

                active_leagues.append(
                    str(
                        value
                    )
                )


    cbb_league = None


    for league in active_leagues:

        key = norm(
            league
        )


        if (
            "ncaab" in key
            or "ncaam" in key
            or (
                "college" in key
                and "basket" in key
            )
            or (
                "mens" in key
                and "basket" in key
            )
        ):

            cbb_league = league
            break


    sw_events = []
    sw_event_receipts = []
    sw_book_receipts = {}
    selected_books = []


    if cbb_league:

        (
            sw_events,
            sw_event_receipts,
        ) = sw_page(
            SW,
            "/events",
            SW_HEADERS,
            {
                "league":
                    cbb_league,

                "limit":
                    1000,
            },
            max_pages=2,
        )


        event_map = {}


        for event in sw_events:

            event_id = event.get(
                "id"
            )


            if not event_id:
                continue


            event_map[
                str(
                    event_id
                )
            ] = {
                "start":
                    event.get(
                        "startTime"
                    ),

                "away_team":
                    event.get(
                        "awayTeamName"
                    ),

                "home_team":
                    event.get(
                        "homeTeamName"
                    ),
            }


        r_books, books_payload = request(
            SW
            + "/sportsbooks",
            headers=SW_HEADERS,
        )


        books = list_data(
            books_payload
        )


        available = {
            str(
                item.get(
                    "id",
                    "",
                )
            ).lower()

            for item in books
            if isinstance(
                item,
                dict,
            )
            and item.get(
                "id"
            )
        }


        preferred = [
            "draftkings",
            "fanduel",
            "betmgm",
            "caesars",
            "fanatics",
            "hardrock",
            "pinnacle",
            "thescore",
        ]


        selected_books = [
            book
            for book in preferred
            if book in available
        ]


        for book in selected_books:

            rows, receipts = sw_page(
                SW,
                "/odds",
                SW_HEADERS,
                {
                    "league":
                        cbb_league,

                    "scope":
                        "event",

                    "sportsbook":
                        book,

                    "market":
                        "MONEYLINE,SPREAD,TOTAL",

                    "is_main":
                        "true",

                    "limit":
                        1000,
                },
                max_pages=3,
            )


            sw_book_receipts[
                book
            ] = {
                "rows":
                    len(
                        rows
                    ),

                "pages":
                    receipts,
            }


            for item in rows:

                if item.get(
                    "suspended"
                ) is True:

                    continue


                if item.get(
                    "marketScope"
                ):

                    # Futures/tournament markets
                    # are intentionally excluded.
                    continue


                if (
                    item.get(
                        "playerId"
                    )
                    or item.get(
                        "playerName"
                    )
                ):

                    # College player markets are
                    # intentionally excluded.
                    continue


                market = str(
                    item.get(
                        "market"
                    )
                    or ""
                ).upper()


                if market not in {
                    "MONEYLINE",
                    "SPREAD",
                    "TOTAL",
                }:

                    continue


                period = str(
                    item.get(
                        "period"
                    )
                    or ""
                ).upper()


                if (
                    period
                    and period != "FULL"
                ):

                    continue


                event_id = str(
                    item.get(
                        "eventId"
                    )
                    or ""
                )


                event = event_map.get(
                    event_id,
                    {},
                )


                start = pd.to_datetime(
                    item.get(
                        "eventStartTime"
                    )
                    or event.get(
                        "start"
                    ),
                    utc=True,
                    errors="coerce",
                )


                if (
                    pd.notna(
                        start
                    )
                    and start
                    < NOW
                    - pd.Timedelta(
                        hours=2
                    )
                ):

                    continue


                game_rows.append({
                    "provider":
                        "sportwizzard",

                    "sportsbook":
                        book,

                    "event_id":
                        event_id,

                    "start":
                        start,

                    "away_team":
                        event.get(
                            "away_team"
                        ),

                    "home_team":
                        event.get(
                            "home_team"
                        ),

                    "market":
                        market,

                    "market_subtype":
                        item.get(
                            "marketSubtype"
                        ),

                    "selection":
                        item.get(
                            "selection"
                        ),

                    "side":
                        item.get(
                            "side"
                        ),

                    "line":
                        item.get(
                            "line"
                        ),

                    "price_american":
                        item.get(
                            "priceAmerican"
                        ),
                })


    report[
        "providers"
    ][
        "sportwizzard"
    ] = {
        "connected":
            True,

        "leagues_http":
            (
                r.status_code
                if r is not None
                else None
            ),

        "active_leagues":
            active_leagues,

        "resolved_cbb_league":
            cbb_league,

        "events":
            len(
                sw_events
            ),

        "event_receipts":
            sw_event_receipts,

        "sportsbooks":
            selected_books,

        "book_receipts":
            sw_book_receipts,
    }


else:

    report[
        "providers"
    ][
        "sportwizzard"
    ] = {
        "connected":
            False,

        "reason":
            "API_KEY_MISSING",
    }


# ============================================================
# PROPLINE
# Dynamic /sports discovery.
# Game markets only.
# ============================================================

pl_key = (
    os.getenv(
        "PROPLINE_API_KEY"
    )
    or ""
).strip()


if pl_key:

    PL = (
        "https://api.prop-line.com/v1"
    )

    PL_HEADERS = {
        "X-API-Key":
            pl_key,

        "Accept":
            "application/json",

        "User-Agent":
            "Sports-HULK/1.0",
    }


    r, sports_payload = request(
        PL
        + "/sports",
        headers=PL_HEADERS,
    )


    sports = list_data(
        sports_payload
    )


    cbb_sport = None


    for sport in sports:

        if not isinstance(
            sport,
            dict,
        ):
            continue


        blob = " ".join(
            str(
                sport.get(
                    key,
                    "",
                )
            )
            for key in [
                "key",
                "id",
                "sport",
                "title",
                "name",
                "description",
            ]
        ).lower()


        if (
            "ncaab" in blob
            or "ncaam" in blob
            or (
                "ncaa" in blob
                and "basket" in blob
            )
            or (
                "college" in blob
                and "basket" in blob
            )
        ):

            cbb_sport = (
                sport.get(
                    "key"
                )
                or sport.get(
                    "id"
                )
                or sport.get(
                    "sport"
                )
            )

            if cbb_sport:
                break


    odds_http = None
    events = []


    if cbb_sport:

        r2, odds_payload = request(
            (
                PL
                + "/sports/"
                + str(
                    cbb_sport
                )
                + "/odds"
            ),
            headers=PL_HEADERS,
            params={
                "markets":
                    "h2h,spreads,totals"
            },
        )


        odds_http = (
            r2.status_code
            if r2 is not None
            else None
        )


        events = list_data(
            odds_payload
        )


        save_json(
            RAW
            / (
                "PROPLINE_CBB_"
                + STAMP
                + ".json"
            ),
            odds_payload,
        )


        for event in events:

            event_id = event.get(
                "id"
            )

            home = event.get(
                "home_team"
            )

            away = event.get(
                "away_team"
            )

            start = pd.to_datetime(
                event.get(
                    "commence_time"
                ),
                utc=True,
                errors="coerce",
            )


            if (
                pd.notna(
                    start
                )
                and start
                < NOW
                - pd.Timedelta(
                    hours=2
                )
            ):

                continue


            for book in (
                event.get(
                    "bookmakers"
                )
                or []
            ):

                book_name = (
                    book.get(
                        "key"
                    )
                    or book.get(
                        "title"
                    )
                    or ""
                )


                for market in (
                    book.get(
                        "markets"
                    )
                    or []
                ):

                    market_key = str(
                        market.get(
                            "key"
                        )
                        or ""
                    ).lower()


                    if market_key not in {
                        "h2h",
                        "spreads",
                        "totals",
                    }:

                        continue


                    for outcome in (
                        market.get(
                            "outcomes"
                        )
                        or []
                    ):

                        game_rows.append({
                            "provider":
                                "propline",

                            "sportsbook":
                                book_name,

                            "event_id":
                                event_id,

                            "start":
                                start,

                            "away_team":
                                away,

                            "home_team":
                                home,

                            "market":
                                market_key.upper(),

                            "market_subtype":
                                market_key,

                            "selection":
                                outcome.get(
                                    "name"
                                ),

                            "side":
                                outcome.get(
                                    "name"
                                ),

                            "line":
                                outcome.get(
                                    "point"
                                ),

                            "price_american":
                                outcome.get(
                                    "price"
                                ),
                        })


    report[
        "providers"
    ][
        "propline"
    ] = {
        "connected":
            True,

        "sports_http":
            (
                r.status_code
                if r is not None
                else None
            ),

        "resolved_sport_key":
            cbb_sport,

        "odds_http":
            odds_http,

        "events":
            len(
                events
            ),
    }


else:

    report[
        "providers"
    ][
        "propline"
    ] = {
        "connected":
            False,

        "reason":
            "API_KEY_MISSING",
    }


# ============================================================
# THERUNDOWN
# Metadata discovery only at this stage.
# Do NOT spend full CBB snapshot datapoints one month early.
# ============================================================

rd_key = (
    os.getenv(
        "THERUNDOWN_API_KEY"
    )
    or ""
).strip()


if rd_key:

    r, payload = request(
        "https://therundown.io/api/v2/sports",
        headers={
            "X-TheRundown-Key":
                rd_key,
        },
    )


    sports = list_data(
        payload
    )

    rd_cbb = None


    for sport in sports:

        if not isinstance(
            sport,
            dict,
        ):
            continue


        blob = str(
            sport
        ).lower()


        if (
            "ncaab" in blob
            or (
                "college" in blob
                and "basket" in blob
            )
        ):

            rd_cbb = sport
            break


    report[
        "providers"
    ][
        "therundown"
    ] = {
        "connected":
            True,

        "metadata_http":
            (
                r.status_code
                if r is not None
                else None
            ),

        "resolved":
            rd_cbb,

        "odds_snapshot_queried":
            False,

        "reason":
            "DATAPOINTS_RESERVED_UNTIL_GAME_WINDOW",
    }


else:

    report[
        "providers"
    ][
        "therundown"
    ] = {
        "connected":
            False,

        "reason":
            "API_KEY_MISSING",
    }


# ============================================================
# RESERVED PROVIDERS
# ============================================================

report[
    "providers"
][
    "the_odds_api"
] = {
    "connected":
        bool(
            (
                os.getenv(
                    "THE_ODDS_API_KEY"
                )
                or ""
            ).strip()
        ),

    "queried":
        False,

    "reason":
        "CREDITS_RESERVED",
}


report[
    "providers"
][
    "oddspapi"
] = {
    "connected":
        bool(
            (
                os.getenv(
                    "ODDSPAPI_API_KEY"
                )
                or ""
            ).strip()
        ),

    "queried":
        False,

    "reason":
        "NOT_NEEDED_FOR_BUILD_2",
}


# ============================================================
# WRITE
# ============================================================

game = pd.DataFrame(
    game_rows
)


if game.empty:

    game = pd.DataFrame(
        columns=GAME_COLUMNS
    )

else:

    game[
        "captured_at"
    ] = datetime.now(
        timezone.utc
    ).isoformat()


    game[
        "start"
    ] = pd.to_datetime(
        game[
            "start"
        ],
        utc=True,
        errors="coerce",
        format="mixed",
    )


    game = game.drop_duplicates(
        [
            "provider",
            "sportsbook",
            "event_id",
            "market",
            "selection",
            "line",
            "price_american",
        ],
        keep="last",
    )


current_path = (
    CURRENT
    / "CBB_GAME_MARKET.csv"
)

history_path = (
    HISTORY
    / (
        "CBB_GAME_MARKET_"
        + STAMP
        + ".csv"
    )
)


game.to_csv(
    current_path,
    index=False,
)

game.to_csv(
    history_path,
    index=False,
)


coverage_rows = []


for provider in [
    "sportwizzard",
    "propline",
    "therundown",
    "the_odds_api",
    "oddspapi",
]:

    info = report[
        "providers"
    ].get(
        provider,
        {},
    )


    rows = (
        int(
            game[
                "provider"
            ]
            .eq(
                provider
            )
            .sum()
        )
        if (
            not game.empty
            and "provider"
            in game.columns
        )
        else 0
    )


    coverage_rows.append({
        "provider":
            provider,

        "connected":
            bool(
                info.get(
                    "connected",
                    False,
                )
            ),

        "game_market_rows":
            rows,

        "counted_as_market_evidence":
            rows > 0,

        "details":
            json.dumps(
                info,
                default=str,
            ),
    })


coverage = pd.DataFrame(
    coverage_rows
)


coverage.to_csv(
    CURRENT
    / "CBB_PROVIDER_COVERAGE.csv",
    index=False,
)


report[
    "normalized"
] = {
    "game_market_rows":
        int(
            len(
                game
            )
        ),

    "player_prop_rows":
        0,

    "prizepicks_rows":
        0,
}


save_json(
    RECEIPTS
    / "CBB_MARKET_RECEIPT_LATEST.json",
    report,
)


print(
    "CBB GAME MARKET ROWS:",
    len(
        game
    )
)

print()
print(
    coverage[
        [
            "provider",
            "connected",
            "game_market_rows",
            "counted_as_market_evidence",
        ]
    ].to_string(
        index=False
    )
)

print()
print(
    "RESULT: CBB_GAME_MARKET_FOUNDATION_READY"
)
