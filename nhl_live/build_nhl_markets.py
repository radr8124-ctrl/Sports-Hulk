#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
import os
import re
import time

import pandas as pd
import requests
from dotenv import load_dotenv


ROOT = Path("/home/ubuntu/sports-hulk")
NHL = ROOT / "nhl_live"
MARKETS = NHL / "markets"
CURRENT = MARKETS / "current"
HISTORY = MARKETS / "history"
RAW = MARKETS / "raw"
RECEIPTS = MARKETS / "receipts"

load_dotenv(ROOT / ".env")

STAMP = datetime.now(
    timezone.utc
).strftime("%Y%m%dT%H%M%SZ")

NOW = pd.Timestamp.now(tz="UTC")

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


def safe_json(
    response,
):
    try:
        return response.json()
    except Exception:
        return {}


def save_json(
    path,
    payload,
):
    Path(path).write_text(
        json.dumps(
            payload,
            indent=2,
            default=str,
        )
    )


def norm(
    value,
):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        str(value or "").lower(),
    )


def list_data(
    payload,
):
    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict):
        return []

    for key in [
        "data",
        "events",
        "fixtures",
        "items",
        "results",
    ]:
        value = payload.get(key)

        if isinstance(value, list):
            return value

    return []


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
            safe_json(r),
        )

    except Exception as exc:
        return (
            None,
            {
                "_error":
                    f"{type(exc).__name__}: {exc}"
            },
        )


# ============================================================
# OUTPUT ACCUMULATORS
# ============================================================

game_rows = []
prop_rows = []
pp_rows = []

report = {
    "generated_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "sport":
        "NHL",

    "providers": {},
}


# ============================================================
# SPORTWIZZARD
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


    def sw_page(
        path,
        params,
        max_pages=2,
    ):

        rows = []
        cursor = None
        receipts = []

        for page in range(
            1,
            max_pages + 1,
        ):

            q = dict(params)

            if cursor:
                q["cursor"] = cursor

            r, payload = request(
                SW + path,
                headers=SW_HEADERS,
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
                "page": page,
                "http": code,
                "rows": len(data),
            })

            if code != 200:
                break

            rows.extend(data)

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

        return rows, receipts


    # --------------------------
    # Events
    # --------------------------

    sw_events, sw_event_receipts = (
        sw_page(
            "/events",
            {
                "league":
                    "nhl",

                "limit":
                    100,
            },
            max_pages=2,
        )
    )

    event_map = {}

    for e in sw_events:

        event_id = e.get(
            "id"
        )

        if not event_id:
            continue

        event_map[
            event_id
        ] = {
            "start":
                e.get(
                    "startTime"
                ),

            "away_team":
                e.get(
                    "awayTeamName"
                ),

            "home_team":
                e.get(
                    "homeTeamName"
                ),
        }


    # --------------------------
    # Sportsbooks
    # --------------------------

    r, book_payload = request(
        SW + "/sportsbooks",
        headers=SW_HEADERS,
    )

    book_data = list_data(
        book_payload
    )

    available = {
        str(
            x.get(
                "id",
                "",
            )
        ).lower()

        for x in book_data
        if x.get("id")
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
        "betparx",
        "ballybet",
    ]

    selected = [
        x
        for x in preferred
        if x in available
    ]

    print(
        "SPORTWIZZARD NHL EVENTS:",
        len(sw_events),
    )

    print(
        "SPORTWIZZARD BOOKS:",
        selected,
    )


    # --------------------------
    # Multibook odds
    # --------------------------

    sw_book_receipts = {}

    for book in selected:

        rows, receipts = sw_page(
            "/odds",
            {
                "league":
                    "nhl",

                "scope":
                    "event",

                "sportsbook":
                    book,

                "limit":
                    500,
            },
            max_pages=3,
        )

        sw_book_receipts[
            book
        ] = {
            "rows":
                len(rows),

            "pages":
                receipts,
        }

        for x in rows:

            if x.get(
                "suspended"
            ) is True:
                continue

            event_id = x.get(
                "eventId"
            )

            ev = event_map.get(
                event_id,
                {},
            )

            start = pd.to_datetime(
                x.get(
                    "eventStartTime"
                )
                or ev.get(
                    "start"
                ),
                utc=True,
                errors="coerce",
            )

            if (
                pd.notna(start)
                and start < NOW
            ):
                continue

            market = str(
                x.get(
                    "market"
                )
                or ""
            ).upper()

            period = str(
                x.get(
                    "period"
                )
                or ""
            ).upper()

            if (
                period
                and period != "FULL"
            ):
                continue

            player = x.get(
                "playerName"
            )

            player_id = x.get(
                "playerId"
            )

            base = {
                "provider":
                    "sportwizzard",

                "sportsbook":
                    book,

                "event_id":
                    event_id,

                "start":
                    start,

                "away_team":
                    ev.get(
                        "away_team"
                    ),

                "home_team":
                    ev.get(
                        "home_team"
                    ),

                "market":
                    market,

                "market_subtype":
                    x.get(
                        "marketSubtype"
                    ),

                "selection":
                    x.get(
                        "selection"
                    ),

                "side":
                    x.get(
                        "side"
                    ),

                "line":
                    x.get(
                        "line"
                    ),

                "price_american":
                    x.get(
                        "priceAmerican"
                    ),

                "player_id":
                    player_id,

                "player":
                    player,
            }

            if player or player_id:

                prop_rows.append(
                    base
                )

            elif market in {
                "MONEYLINE",
                "SPREAD",
                "TOTAL",
            }:

                game_rows.append(
                    base
                )


    # --------------------------
    # PrizePicks
    # --------------------------

    sw_pp, sw_pp_receipts = sw_page(
        "/odds",
        {
            "league":
                "nhl",

            "scope":
                "event",

            "sportsbook":
                "prizepicks",

            "limit":
                500,
        },
        max_pages=3,
    )

    for x in sw_pp:

        if x.get(
            "suspended"
        ) is True:
            continue

        player = x.get(
            "playerName"
        )

        player_id = x.get(
            "playerId"
        )

        if not (
            player
            or player_id
        ):
            continue

        eid = x.get(
            "eventId"
        )

        ev = event_map.get(
            eid,
            {},
        )

        pp_rows.append({
            "provider":
                "sportwizzard",

            "sportsbook":
                "prizepicks",

            "event_id":
                eid,

            "start":
                x.get(
                    "eventStartTime"
                )
                or ev.get(
                    "start"
                ),

            "away_team":
                ev.get(
                    "away_team"
                ),

            "home_team":
                ev.get(
                    "home_team"
                ),

            "player_id":
                player_id,

            "player":
                player,

            "market":
                x.get(
                    "market"
                ),

            "market_subtype":
                x.get(
                    "marketSubtype"
                ),

            "selection":
                x.get(
                    "selection"
                ),

            "side":
                x.get(
                    "side"
                ),

            "line":
                x.get(
                    "line"
                ),

            "price_american":
                x.get(
                    "priceAmerican"
                ),
        })


    report[
        "providers"
    ][
        "sportwizzard"
    ] = {
        "events":
            len(sw_events),

        "sportsbooks":
            selected,

        "book_receipts":
            sw_book_receipts,

        "prizepicks_rows":
            len(sw_pp),

        "event_receipts":
            sw_event_receipts,
    }


# ============================================================
# PROPLINE
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
        PL + "/sports",
        headers=PL_HEADERS,
    )

    sports = list_data(
        sports_payload
    )

    nhl_sport = None

    for s in sports:

        blob = " ".join(
            str(
                s.get(k, "")
            )
            for k in [
                "key",
                "id",
                "sport",
                "title",
                "name",
                "description",
            ]
        ).lower()

        if (
            "nhl" in blob
            or "hockey" in blob
        ):

            nhl_sport = (
                s.get(
                    "key"
                )
                or s.get(
                    "id"
                )
                or s.get(
                    "sport"
                )
            )

            if nhl_sport:
                break


    # Expected fallback from PropLine sport naming.
    if not nhl_sport:
        nhl_sport = (
            "hockey_nhl"
        )


    r2, odds_payload = request(
        (
            PL
            + "/sports/"
            + str(nhl_sport)
            + "/odds"
        ),
        headers=PL_HEADERS,
        params={
            "markets":
                "h2h,spreads,totals"
        },
    )

    events = list_data(
        odds_payload
    )

    save_json(
        RAW
        / (
            "PROPLINE_NHL_"
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

        start = event.get(
            "commence_time"
        )

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

                        "player_id":
                            "",

                        "player":
                            "",
                    })


    report[
        "providers"
    ][
        "propline"
    ] = {
        "sport_key":
            nhl_sport,

        "sports_http":
            (
                r.status_code
                if r is not None
                else None
            ),

        "odds_http":
            (
                r2.status_code
                if r2 is not None
                else None
            ),

        "events":
            len(events),
    }


# ============================================================
# THERUNDOWN — NHL sport ID 6
# BOUNDED VERIFICATION CALL
# ============================================================

rd_key = (
    os.getenv(
        "THERUNDOWN_API_KEY"
    )
    or ""
).strip()

if rd_key:

    upcoming = (
        NHL
        / "derived"
        / "NHL_GAMES_CURRENT.csv"
    )

    date_to_query = (
        datetime.now(
            timezone.utc
        ).date()
    )

    if upcoming.exists():

        try:

            gd = pd.read_csv(
                upcoming,
                low_memory=False,
            )

            starts = pd.to_datetime(
                gd[
                    "start"
                ],
                utc=True,
                errors="coerce",
            ).dropna()

            future = starts[
                starts >= NOW
            ]

            if len(future):
                date_to_query = (
                    future.min().date()
                )

        except Exception:
            pass


    url = (
        "https://therundown.io/"
        "api/v2/sports/6/events/"
        + date_to_query.isoformat()
    )

    r, payload = request(
        url,
        headers={
            "X-TheRundown-Key":
                rd_key,
        },
        params={
            "market_ids":
                "1,2,3",

            "main_line":
                "true",

            "hide_closed":
                "true",
        },
    )

    rows = list_data(
        payload
    )

    save_json(
        RAW
        / (
            "THERUNDOWN_NHL_"
            + STAMP
            + ".json"
        ),
        payload,
    )


    report[
        "providers"
    ][
        "therundown"
    ] = {
        "date":
            date_to_query.isoformat(),

        "http":
            (
                r.status_code
                if r is not None
                else None
            ),

        "events":
            len(rows),

        "datapoints_used":
            (
                r.headers.get(
                    "X-Datapoints-Used"
                )
                if r is not None
                else None
            ),

        "datapoints_remaining":
            (
                r.headers.get(
                    "X-Datapoints-Remaining"
                )
                if r is not None
                else None
            ),

        "delay_seconds":
            (
                r.headers.get(
                    "X-Data-Delay-Seconds"
                )
                if r is not None
                else None
            ),
    }


# ============================================================
# ODDSPAPI — NHL sport 11 / tournament 132
# LIMITED TO FIRST 8 FIXTURES
# ============================================================

op_key = (
    os.getenv(
        "ODDSPAPI_API_KEY"
    )
    or ""
).strip()

if op_key:

    OP = (
        "https://api.oddspapi.io/v4"
    )

    r, fixtures_payload = request(
        OP + "/fixtures",
        params={
            "apiKey":
                op_key,

            "sportId":
                15,

            "tournamentId":
                234,

            "statusId":
                0,

            "hasOdds":
                "true",

            "language":
                "en",
        },
    )

    fixtures = list_data(
        fixtures_payload
    )

    save_json(
        RAW
        / (
            "ODDSPAPI_NHL_FIXTURES_"
            + STAMP
            + ".json"
        ),
        fixtures_payload,
    )

    odds_receipts = []

    for fixture in fixtures[
        :8
    ]:

        fixture_id = fixture.get(
            "fixtureId"
        )

        if not fixture_id:
            continue

        time.sleep(
            1.05
        )

        r2, odds_payload = request(
            OP + "/odds",
            params={
                "apiKey":
                    op_key,

                "fixtureId":
                    fixture_id,

                "oddsFormat":
                    "american",

                "language":
                    "en",

                "verbosity":
                    2,
            },
            timeout=45,
        )

        save_json(
            RAW
            / (
                "ODDSPAPI_NHL_ODDS_"
                + str(
                    fixture_id
                )
                + "_"
                + STAMP
                + ".json"
            ),
            odds_payload,
        )

        odds_receipts.append({
            "fixture_id":
                fixture_id,

            "http":
                (
                    r2.status_code
                    if r2 is not None
                    else None
                ),

            "rows":
                len(
                    list_data(
                        odds_payload
                    )
                ),
        })


    report[
        "providers"
    ][
        "oddspapi"
    ] = {
        "sport_id":
            15,

        "tournament_id":
            234,

        "fixtures_http":
            (
                r.status_code
                if r is not None
                else None
            ),

        "fixtures":
            len(fixtures),

        "odds_receipts":
            odds_receipts,
    }


# ============================================================
# NORMALIZE / WRITE
# ============================================================

game = pd.DataFrame(
    game_rows
)

props = pd.DataFrame(
    prop_rows
)

pp = pd.DataFrame(
    pp_rows
)


def write_dataset(
    df,
    name,
):

    current_path = (
        CURRENT
        / f"{name}.csv"
    )

    history_path = (
        HISTORY
        / f"{name}_{STAMP}.csv"
    )


    if df.empty:

        # Preserve schema-less empty file safely.
        pd.DataFrame().to_csv(
            current_path,
            index=False,
        )

        pd.DataFrame().to_csv(
            history_path,
            index=False,
        )

        return


    df[
        "captured_at"
    ] = datetime.now(
        timezone.utc
    ).isoformat()


    df.to_csv(
        current_path,
        index=False,
    )

    df.to_csv(
        history_path,
        index=False,
    )


    try:

        df.to_parquet(
            current_path.with_suffix(
                ".parquet"
            ),
            index=False,
        )

    except Exception:
        pass


write_dataset(
    game,
    "NHL_GAME_MARKET",
)

write_dataset(
    props,
    "NHL_PLAYER_PROP_MARKET",
)

write_dataset(
    pp,
    "NHL_PRIZEPICKS_MARKET",
)


# ============================================================
# PROVIDER / COVERAGE MATRIX
# ============================================================

coverage = []


for provider in [
    "sportwizzard",
    "propline",
    "therundown",
    "oddspapi",
]:

    info = report[
        "providers"
    ].get(
        provider,
        {}
    )

    coverage.append({
        "provider":
            provider,

        "connected":
            bool(info),

        "game_market_rows":
            int(
                (
                    game[
                        "provider"
                    ].eq(
                        provider
                    )
                ).sum()
            )
            if (
                not game.empty
                and "provider"
                in game.columns
            )
            else 0,

        "player_prop_rows":
            int(
                (
                    props[
                        "provider"
                    ].eq(
                        provider
                    )
                ).sum()
            )
            if (
                not props.empty
                and "provider"
                in props.columns
            )
            else 0,

        "prizepicks_rows":
            int(
                (
                    pp[
                        "provider"
                    ].eq(
                        provider
                    )
                ).sum()
            )
            if (
                not pp.empty
                and "provider"
                in pp.columns
            )
            else 0,

        "details":
            json.dumps(
                info,
                default=str,
            ),
    })


coverage_df = pd.DataFrame(
    coverage
)

coverage_df.to_csv(
    CURRENT
    / "NHL_PROVIDER_COVERAGE.csv",
    index=False,
)


report[
    "normalized"
] = {
    "game_market_rows":
        int(
            len(game)
        ),

    "player_prop_rows":
        int(
            len(props)
        ),

    "prizepicks_rows":
        int(
            len(pp)
        ),
}


save_json(
    RECEIPTS
    / "NHL_MARKET_RECEIPT_LATEST.json",
    report,
)

save_json(
    RECEIPTS
    / (
        "NHL_MARKET_RECEIPT_"
        + STAMP
        + ".json"
    ),
    report,
)


print()
print(
    "NHL GAME MARKET ROWS:",
    len(game),
)

print(
    "NHL PLAYER PROP ROWS:",
    len(props),
)

print(
    "NHL PRIZEPICKS ROWS:",
    len(pp),
)

print()
print(
    coverage_df[
        [
            "provider",
            "connected",
            "game_market_rows",
            "player_prop_rows",
            "prizepicks_rows",
        ]
    ].to_string(
        index=False
    )
)

print()
print(
    "RESULT: NHL_MARKETS_COLLECTED"
)
