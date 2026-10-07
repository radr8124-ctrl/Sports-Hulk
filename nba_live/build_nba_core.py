#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timezone, timedelta

import json
import re

import pandas as pd
import requests


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

NBA = (
    ROOT
    / "nba_live"
)

DERIVED = (
    NBA
    / "derived"
)

HISTORY = (
    NBA
    / "history"
)

RECEIPTS = (
    NBA
    / "receipts"
)


CURRENT = (
    DERIVED
    / "NBA_GAMES_CURRENT.csv"
)

RESULTS = (
    HISTORY
    / "NBA_RESULTS_HISTORY.csv"
)


CORE = (
    "https://sports.core.api.espn.com/"
    "v2/sports/basketball/leagues/nba"
)


TIMEOUT = 25


SESSION = requests.Session()

SESSION.headers.update(
    {
        "User-Agent":
            "Sports-HULK/1.0 NBA-core",
    }
)


def https_ref(
    value,
):

    if not value:
        return ""

    return str(
        value
    ).replace(
        "http://",
        "https://",
        1,
    )


def get_json(
    url,
):

    response = SESSION.get(
        https_ref(
            url
        ),
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    return response.json()


def ref_json(
    obj,
):

    if not isinstance(
        obj,
        dict,
    ):
        return obj


    ref = obj.get(
        "$ref"
    )


    if ref:

        return get_json(
            ref
        )


    return obj


def clean(
    value,
):

    if value is None:
        return ""

    return str(
        value
    ).strip()


def num(
    value,
):

    try:

        return float(
            value
        )

    except Exception:

        return None


def score_value(
    value,
):

    if value is None:
        return None


    if isinstance(
        value,
        dict,
    ):

        try:
            value = ref_json(
                value
            )

        except Exception:
            pass


        for key in [
            "value",
            "displayValue",
            "score",
        ]:

            if key in value:

                result = num(
                    value.get(
                        key
                    )
                )

                if result is not None:

                    return result


    return num(
        value
    )


def team_info(
    competitor,
):

    team = competitor.get(
        "team"
    ) or {}


    try:

        team = ref_json(
            team
        )

    except Exception:

        pass


    return {
        "id":
            clean(
                team.get(
                    "id"
                )
            ),

        "abbr":
            clean(
                team.get(
                    "abbreviation"
                )
            ).upper(),

        "name":
            clean(
                team.get(
                    "displayName"
                )
                or team.get(
                    "name"
                )
            ),
    }


def status_info(
    competition,
):

    status = (
        competition.get(
            "status"
        )
        or {}
    )


    try:

        status = ref_json(
            status
        )

    except Exception:

        pass


    stype = (
        status.get(
            "type"
        )
        or {}
    )


    state = clean(
        stype.get(
            "state"
        )
    ).lower()


    name = clean(
        stype.get(
            "name"
        )
    ).upper()


    completed = bool(
        stype.get(
            "completed"
        )
    )


    final = (
        completed
        or state == "post"
        or "FINAL" in name
    )


    return {
        "state":
            state,

        "name":
            name,

        "description":
            clean(
                stype.get(
                    "description"
                )
                or status.get(
                    "displayClock"
                )
                or name
            ),

        "completed":
            final,
    }


def season_info(event):
    """Use the explicit ESPN event seasonType reference, never the game date."""
    season = event.get("season") or {}
    year = season.get("year") if isinstance(season, dict) else None
    raw_type = season.get("type") if isinstance(season, dict) else None
    if isinstance(raw_type, dict):
        raw_type = raw_type.get("type") or raw_type.get("name")

    type_ref = event.get("seasonType") or {}
    if isinstance(type_ref, dict):
        raw_reference = str(type_ref.get("$ref") or "")
        match = re.search(r"/seasons/(\d+)/types/([123])(?:\?|$)", raw_reference)
        if match:
            explicit_year = int(match.group(1))
            explicit_type = int(match.group(2))
            if year is not None and str(year) != str(explicit_year):
                return (year, None)
            if raw_type is not None and str(raw_type) != str(explicit_type):
                return (year or explicit_year, None)
            return (year or explicit_year, explicit_type)

        explicit_type = type_ref.get("type")
        if explicit_type in (1, 2, 3, "1", "2", "3"):
            if raw_type is not None and str(raw_type) != str(explicit_type):
                return (year, None)
            return (year, int(explicit_type))

    return (year, raw_type)


def parse_event(
    event,
):

    competitions = (
        event.get(
            "competitions"
        )
        or []
    )


    if not competitions:

        return None


    competition = ref_json(
        competitions[
            0
        ]
    )


    away = {
        "id": "",
        "abbr": "",
        "name": "",
        "score": None,
    }

    home = {
        "id": "",
        "abbr": "",
        "name": "",
        "score": None,
    }


    for competitor in (
        competition.get(
            "competitors"
        )
        or []
    ):

        info = team_info(
            competitor
        )


        info[
            "score"
        ] = score_value(
            competitor.get(
                "score"
            )
        )


        side = clean(
            competitor.get(
                "homeAway"
            )
        ).lower()


        if side == "home":
            home = info

        elif side == "away":
            away = info


    status = status_info(
        competition
    )


    season_year, season_type = (
        season_info(
            event
        )
    )


    start = clean(
        event.get(
            "date"
        )
        or competition.get(
            "date"
        )
    )


    event_id = clean(
        event.get(
            "id"
        )
        or competition.get(
            "id"
        )
    )


    winner = ""


    if (
        status[
            "completed"
        ]
        and home[
            "score"
        ] is not None
        and away[
            "score"
        ] is not None
    ):

        if (
            home[
                "score"
            ]
            > away[
                "score"
            ]
        ):

            winner = home[
                "abbr"
            ]


        elif (
            away[
                "score"
            ]
            > home[
                "score"
            ]
        ):

            winner = away[
                "abbr"
            ]


        else:

            winner = "TIE"


    return {
        "event_id":
            event_id,

        "start":
            start,

        "season":
            season_year,

        "season_type":
            season_type,

        "away_team_id":
            away[
                "id"
            ],

        "away_team":
            away[
                "abbr"
            ],

        "away_team_name":
            away[
                "name"
            ],

        "away_score":
            away[
                "score"
            ],

        "home_team_id":
            home[
                "id"
            ],

        "home_team":
            home[
                "abbr"
            ],

        "home_team_name":
            home[
                "name"
            ],

        "home_score":
            home[
                "score"
            ],

        "status_state":
            status[
                "state"
            ],

        "status_name":
            status[
                "name"
            ],

        "status":
            status[
                "description"
            ],

        "completed":
            status[
                "completed"
            ],

        "winner":
            winner,
    }


def fetch_date(
    date,
):

    url = (
        CORE
        + "/events"
        + "?dates="
        + date.strftime(
            "%Y%m%d"
        )
        + "&limit=100"
    )


    data = get_json(
        url
    )


    rows = []


    for item in (
        data.get(
            "items"
        )
        or []
    ):

        try:

            event = ref_json(
                item
            )


            row = parse_event(
                event
            )


            if row:

                rows.append(
                    row
                )


        except Exception as exc:

            print(
                "EVENT WARNING:",
                type(
                    exc
                ).__name__,
                str(
                    exc
                )[:150],
            )


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

    RECEIPTS.mkdir(
        parents=True,
        exist_ok=True,
    )


    now = datetime.now(
        timezone.utc
    )


    # Enough range for recently completed games
    # plus the upcoming preseason/regular schedule.
    dates = [
        (
            now.date()
            + timedelta(
                days=offset
            )
        )

        for offset in range(
            -3,
            8,
        )
    ]


    rows = []


    for date in dates:

        try:

            day_rows = fetch_date(
                date
            )


            print(
                date,
                "=>",
                len(
                    day_rows
                ),
                "NBA events",
            )


            rows.extend(
                day_rows
            )


        except Exception as exc:

            print(
                "DATE WARNING:",
                date,
                type(
                    exc
                ).__name__,
                str(
                    exc
                )[:160],
            )


    current = pd.DataFrame(
        rows
    )


    if not current.empty:

        current = (
            current
            .drop_duplicates(
                "event_id",
                keep="last",
            )
            .sort_values(
                "start"
            )
        )


    current.to_csv(
        CURRENT,
        index=False,
    )


    # Permanent completed-result history.
    finals = (
        current[
            current[
                "completed"
            ].astype(
                str
            ).str.lower().isin(
                [
                    "true",
                    "1",
                ]
            )
        ].copy()
        if not current.empty
        else pd.DataFrame()
    )


    old = pd.DataFrame()


    if RESULTS.exists():

        old = pd.read_csv(
            RESULTS,
            low_memory=False,
        )


    parts = [
        x
        for x in [
            old,
            finals,
        ]
        if not x.empty
    ]


    if parts:

        result_history = pd.concat(
            parts,
            ignore_index=True,
            sort=False,
        )


        result_history = (
            result_history
            .drop_duplicates(
                "event_id",
                keep="last",
            )
            .sort_values(
                "start"
            )
        )


    else:

        result_history = pd.DataFrame(
            columns=current.columns
        )


    result_history.to_csv(
        RESULTS,
        index=False,
    )


    receipt = {
        "generated_at":
            now.isoformat(),

        "source":
            "ESPN_CORE",

        "league":
            "NBA",

        "date_from":
            dates[
                0
            ].isoformat(),

        "date_to":
            dates[
                -1
            ].isoformat(),

        "current_rows":
            int(
                len(
                    current
                )
            ),

        "completed_current":
            int(
                len(
                    finals
                )
            ),

        "permanent_result_rows":
            int(
                len(
                    result_history
                )
            ),

        "official_nba_stats_used":
            False,
    }


    stamp = now.strftime(
        "%Y%m%dT%H%M%SZ"
    )


    receipt_path = (
        RECEIPTS
        / (
            "NBA_CORE_RECEIPT_"
            + stamp
            + ".json"
        )
    )


    receipt_path.write_text(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
    )


    (
        RECEIPTS
        / "NBA_CORE_RECEIPT_LATEST.json"
    ).write_text(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
    )


    print()
    print(
        "CURRENT NBA GAMES:",
        len(
            current
        ),
    )

    print(
        "CURRENT COMPLETED:",
        len(
            finals
        ),
    )

    print(
        "PERMANENT RESULT HISTORY:",
        len(
            result_history
        ),
    )

    print(
        "OFFICIAL NBA STATS USED: NO"
    )

    print(
        "RESULT: NBA_CORE_READY"
    )


if __name__ == "__main__":
    main()
