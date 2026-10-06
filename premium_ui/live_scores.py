from datetime import datetime
from html import escape
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import json
import requests
import re

import streamlit as st

from premium_ui.html_render import html


ET = ZoneInfo("America/New_York")


# ============================================================
# TEAM NORMALIZATION
# ============================================================

TEAM_ALIASES = {
    # NFL
    "ARI": "ARI",
    "CARDINALS": "ARI",
    "ARIZONACARDINALS": "ARI",

    "ATL": "ATL",
    "FALCONS": "ATL",
    "ATLANTAFALCONS": "ATL",

    "BAL": "BAL",
    "RAVENS": "BAL",
    "BALTIMORERAVENS": "BAL",

    "BUF": "BUF",
    "BILLS": "BUF",
    "BUFFALOBILLS": "BUF",

    "CAR": "CAR",
    "PANTHERS": "CAR",
    "CAROLINAPANTHERS": "CAR",

    "CHI": "CHI",
    "BEARS": "CHI",
    "CHICAGOBEARS": "CHI",

    "CIN": "CIN",
    "BENGALS": "CIN",
    "CINCINNATIBENGALS": "CIN",

    "CLE": "CLE",
    "BROWNS": "CLE",
    "CLEVELANDBROWNS": "CLE",

    "DAL": "DAL",
    "COWBOYS": "DAL",
    "DALLASCOWBOYS": "DAL",

    "DEN": "DEN",
    "BRONCOS": "DEN",
    "DENVERBRONCOS": "DEN",

    "DET": "DET",
    "LIONS": "DET",
    "DETROITLIONS": "DET",

    "GB": "GB",
    "PACKERS": "GB",
    "GREENBAYPACKERS": "GB",

    "HOU": "HOU",
    "TEXANS": "HOU",
    "HOUSTONTEXANS": "HOU",

    "IND": "IND",
    "COLTS": "IND",
    "INDIANAPOLISCOLTS": "IND",

    "JAC": "JAC",
    "JAX": "JAC",
    "JAGS": "JAC",
    "JAGUARS": "JAC",
    "JACKSONVILLEJAGUARS": "JAC",

    "KC": "KC",
    "CHIEFS": "KC",
    "KANSASCITYCHIEFS": "KC",

    "LV": "LV",
    "RAIDERS": "LV",
    "LASVEGASRAIDERS": "LV",

    "LAC": "LAC",
    "CHARGERS": "LAC",
    "LOSANGELESCHARGERS": "LAC",

    "LAR": "LAR",
    "LA": "LAR",
    "RAMS": "LAR",
    "LOSANGELESRAMS": "LAR",

    "MIA": "MIA",
    "DOLPHINS": "MIA",
    "MIAMIDOLPHINS": "MIA",

    "MIN": "MIN",
    "VIKINGS": "MIN",
    "MINNESOTAVIKINGS": "MIN",

    "NE": "NE",
    "PATRIOTS": "NE",
    "NEWENGLANDPATRIOTS": "NE",

    "NO": "NO",
    "SAINTS": "NO",
    "NEWORLEANSSAINTS": "NO",

    "NYG": "NYG",
    "GIANTS": "NYG",
    "NEWYORKGIANTS": "NYG",

    "NYJ": "NYJ",
    "JETS": "NYJ",
    "NEWYORKJETS": "NYJ",

    "PHI": "PHI",
    "EAGLES": "PHI",
    "PHILADELPHIAEAGLES": "PHI",

    "PIT": "PIT",
    "STEELERS": "PIT",
    "PITTSBURGHSTEELERS": "PIT",

    "SEA": "SEA",
    "SEAHAWKS": "SEA",
    "SEATTLESEAHAWKS": "SEA",

    "SF": "SF",
    "49ERS": "SF",
    "SANFRANCISCO49ERS": "SF",

    "TB": "TB",
    "BUCCANEERS": "TB",
    "BUCS": "TB",
    "TAMPABAYBUCCANEERS": "TB",

    "TEN": "TEN",
    "TITANS": "TEN",
    "TENNESSEETITANS": "TEN",

    "WAS": "WAS",
    "COMMANDERS": "WAS",
    "WASHINGTONCOMMANDERS": "WAS",

    # NBA_ALIASES_BUILD_6
    # NBA
    "ATLANTAHAWKS": "ATL",
    "HAWKS": "ATL",

    "BOSTONCELTICS": "BOS",
    "CELTICS": "BOS",

    "BROOKLYNNETS": "BKN",
    "NETS": "BKN",

    "CHARLOTTEHORNETS": "CHA",
    "HORNETS": "CHA",

    "CHICAGOBULLS": "CHI",
    "BULLS": "CHI",

    "CLEVELANDCAVALIERS": "CLE",
    "CAVALIERS": "CLE",
    "CAVS": "CLE",

    "DALLASMAVERICKS": "DAL",
    "MAVERICKS": "DAL",
    "MAVS": "DAL",

    "DENVERNUGGETS": "DEN",
    "NUGGETS": "DEN",

    "DETROITPISTONS": "DET",
    "PISTONS": "DET",

    "GOLDENSTATEWARRIORS": "GSW",
    "WARRIORS": "GSW",
    "GS": "GSW",
    "GSW": "GSW",

    "HOUSTONROCKETS": "HOU",
    "ROCKETS": "HOU",

    "INDIANAPACERS": "IND",
    "PACERS": "IND",

    "LACLIPPERS": "LAC",
    "LOSANGELESCLIPPERS": "LAC",
    "CLIPPERS": "LAC",

    "LOSANGELESLAKERS": "LAL",
    "LAKERS": "LAL",

    "MEMPHISGRIZZLIES": "MEM",
    "GRIZZLIES": "MEM",

    "MIAMIHEAT": "MIA",
    "HEAT": "MIA",

    "MILWAUKEEBUCKS": "MIL",
    "BUCKS": "MIL",

    "MINNESOTATIMBERWOLVES": "MIN",
    "TIMBERWOLVES": "MIN",

    "NEWORLEANSPELICANS": "NOP",
    "PELICANS": "NOP",
    "NO": "NOP",
    "NOP": "NOP",

    "NEWYORKKNICKS": "NYK",
    "KNICKS": "NYK",
    "NY": "NYK",
    "NYK": "NYK",

    "OKLAHOMACITYTHUNDER": "OKC",
    "THUNDER": "OKC",

    "ORLANDOMAGIC": "ORL",
    "MAGIC": "ORL",

    "PHILADELPHIA76ERS": "PHI",
    "76ERS": "PHI",
    "SIXERS": "PHI",

    "PHOENIXSUNS": "PHX",
    "SUNS": "PHX",

    "PORTLANDTRAILBLAZERS": "POR",
    "TRAILBLAZERS": "POR",
    "BLAZERS": "POR",

    "SACRAMENTOKINGS": "SAC",
    "KINGS": "SAC",

    "SANANTONIOSPURS": "SAS",
    "SPURS": "SAS",
    "SA": "SAS",
    "SAS": "SAS",

    "TORONTORAPTORS": "TOR",
    "RAPTORS": "TOR",

    "UTAHJAZZ": "UTA",
    "JAZZ": "UTA",
    "UTAH": "UTA",
    "UTA": "UTA",

    "WASHINGTONWIZARDS": "WAS",
    "WIZARDS": "WAS",
    "WSH": "WAS",
    "WAS": "WAS",

    # NHL_ALIASES_BUILD_6
    "ANA": "ANA",
    "ANAHEIMDUCKS": "ANA",

    "BOS": "BOS",
    "BOSTONBRUINS": "BOS",

    "BUF": "BUF",
    "BUFFALOSABRES": "BUF",

    "CAR": "CAR",
    "CAROLINAHURRICANES": "CAR",

    "CBJ": "CBJ",
    "COLUMBUSBLUEJACKETS": "CBJ",

    "CGY": "CGY",
    "CALGARYFLAMES": "CGY",

    "CHI": "CHI",
    "CHICAGOBLACKHAWKS": "CHI",

    "COL": "COL",
    "COLORADOAVALANCHE": "COL",

    "DAL": "DAL",
    "DALLASSTARS": "DAL",

    "DET": "DET",
    "DETROITREDWINGS": "DET",

    "EDM": "EDM",
    "EDMONTONOILERS": "EDM",

    "FLA": "FLA",
    "FLORIDAPANTHERS": "FLA",

    "LAK": "LAK",
    "LOSANGELESKINGS": "LAK",

    "MIN": "MIN",
    "MINNESOTAWILD": "MIN",

    "MTL": "MTL",
    "MONTREALCANADIENS": "MTL",

    "NJD": "NJD",
    "NEWJERSEYDEVILS": "NJD",

    "NSH": "NSH",
    "NASHVILLEPREDATORS": "NSH",

    "NYI": "NYI",
    "NEWYORKISLANDERS": "NYI",

    "NYR": "NYR",
    "NEWYORKRANGERS": "NYR",

    "OTT": "OTT",
    "OTTAWASENATORS": "OTT",

    "PHI": "PHI",
    "PHILADELPHIAFLYERS": "PHI",

    "PIT": "PIT",
    "PITTSBURGHPENGUINS": "PIT",

    "SEA": "SEA",
    "SEATTLEKRAKEN": "SEA",

    "SJS": "SJS",
    "SANJOSESHARKS": "SJS",

    "STL": "STL",
    "STLOUISBLUES": "STL",

    "TBL": "TBL",
    "TAMPABAYLIGHTNING": "TBL",

    "TOR": "TOR",
    "TORONTOMAPLELEAFS": "TOR",

    "UTA": "UTA",
    "UTAHMAMMOTH": "UTA",
    "UTAHHOCKEYCLUB": "UTA",

    "VAN": "VAN",
    "VANCOUVERCANUCKS": "VAN",

    "VGK": "VGK",
    "VEGASGOLDENKNIGHTS": "VGK",

    "WPG": "WPG",
    "WINNIPEGJETS": "WPG",

    "WSH": "WSH",
    "WASHINGTONCAPITALS": "WSH",

    # Common MLB favorites
    "YANKEES": "NYY",
    "NEWYORKYANKEES": "NYY",
    "NYY": "NYY",

    "METS": "NYM",
    "NEWYORKMETS": "NYM",
    "NYM": "NYM",

    "DODGERS": "LAD",
    "LOSANGELESDODGERS": "LAD",
    "LAD": "LAD",

    "RED SOX": "BOS",
    "REDSOX": "BOS",
    "BOSTONREDSOX": "BOS",
    "BOS": "BOS",
}


def compact(value):
    return re.sub(
        r"[^A-Z0-9]+",
        "",
        str(value or "").upper(),
    )


def team_key(value):
    raw = compact(value)

    return TEAM_ALIASES.get(
        raw,
        raw,
    )


# ============================================================
# HTTP
# ============================================================

def get_json(url):
    """
    Sports HULK public-score HTTP client.

    Use requests rather than urllib because some
    public sports endpoints reject urllib's request
    fingerprint from cloud/VPS hosts.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/154.0 Safari/537.36"
        ),
        "Accept":
            "application/json,text/plain,*/*",
        "Accept-Language":
            "en-US,en;q=0.9",
        "Cache-Control":
            "no-cache",
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=15,
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# NFL — ESPN PUBLIC SCOREBOARD
# ============================================================

@st.cache_data(
    ttl=20,
    show_spinner=False,
)
def _https_ref(value):
    if isinstance(value, dict):
        value = value.get(
            "$ref",
            "",
        )

    return str(
        value or ""
    ).replace(
        "http://",
        "https://",
    )


def _score_value(payload):
    if not isinstance(
        payload,
        dict,
    ):
        return None

    for key in [
        "displayValue",
        "value",
        "score",
    ]:
        value = payload.get(
            key
        )

        if value not in (
            None,
            "",
        ):
            try:
                number = float(
                    value
                )

                if number.is_integer():
                    return str(
                        int(number)
                    )

                return str(number)

            except Exception:
                return str(value)

    return None


def _parse_core_event(
    event_ref,
):
    """
    Expand one ESPN Core NFL event.

    Event -> competition -> status +
    home/away score refs.

    Individual event failures are withheld
    rather than breaking the entire scoreboard.
    """

    try:

        event_url = _https_ref(
            event_ref
        )

        event = get_json(
            event_url
        )

        event_id = str(
            event.get(
                "id",
                "",
            )
        )

        if not event_id:
            return None


        # ------------------------------------
        # Names / abbreviations
        # ------------------------------------

        full_name = str(
            event.get(
                "name",
                "",
            )
        )

        short_name = str(
            event.get(
                "shortName",
                "",
            )
        )


        away_name = ""
        home_name = ""

        if " at " in full_name:

            away_name, home_name = (
                full_name.split(
                    " at ",
                    1,
                )
            )


        away_abbr = ""
        home_abbr = ""

        if " @ " in short_name:

            away_abbr, home_abbr = (
                short_name.split(
                    " @ ",
                    1,
                )
            )


        # ------------------------------------
        # Competition
        # ------------------------------------

        competitions = event.get(
            "competitions",
            [],
        )

        competition_url = ""

        if competitions:

            first_comp = competitions[0]

            competition_url = (
                _https_ref(
                    first_comp
                )
            )


        if not competition_url:

            competition_url = (
                "https://sports.core.api.espn.com/"
                "v2/sports/football/leagues/nfl/"
                f"events/{event_id}/"
                f"competitions/{event_id}"
                "?lang=en&region=us"
            )


        competition = get_json(
            competition_url
        )


        # ------------------------------------
        # Status
        # ------------------------------------

        status_ref = _https_ref(
            competition.get(
                "status",
                {}
            )
        )

        status_payload = (
            get_json(
                status_ref
            )
            if status_ref
            else {}
        )


        status_type = (
            status_payload.get(
                "type",
                {}
            )
        )

        if not isinstance(
            status_type,
            dict,
        ):
            status_type = {}


        state = str(
            status_type.get(
                "state",
                ""
            )
            or ""
        ).lower()


        completed = bool(
            status_type.get(
                "completed",
                False,
            )
        )


        if completed and not state:
            state = "post"


        period = status_payload.get(
            "period"
        )

        clock = (
            status_payload.get(
                "displayClock"
            )
            or ""
        )


        detail = (
            status_type.get(
                "shortDetail"
            )
            or
            status_type.get(
                "detail"
            )
            or
            status_type.get(
                "description"
            )
            or ""
        )


        # Build useful fallback live text.
        if (
            state == "in"
            and not detail
        ):

            pieces = []

            if period not in (
                None,
                "",
                0,
            ):
                pieces.append(
                    f"Q{period}"
                )

            if clock:
                pieces.append(
                    str(clock)
                )

            detail = " ".join(
                pieces
            )


        # ------------------------------------
        # Competitors / scores
        # ------------------------------------

        home_item = None
        away_item = None

        for item in competition.get(
            "competitors",
            [],
        ):

            side = str(
                item.get(
                    "homeAway",
                    "",
                )
            ).lower()

            if side == "home":
                home_item = item

            elif side == "away":
                away_item = item


        def competitor_score(
            item,
        ):

            if not item:
                return None

            score_ref = _https_ref(
                item.get(
                    "score",
                    {}
                )
            )

            if not score_ref:
                return None

            payload = get_json(
                score_ref
            )

            return _score_value(
                payload
            )


        home_score = competitor_score(
            home_item
        )

        away_score = competitor_score(
            away_item
        )


        # ------------------------------------
        # Additional name fallback
        # ------------------------------------

        if (
            not away_name
            or not home_name
        ):

            # shortName is still better than
            # showing a blank team.
            away_name = (
                away_name
                or away_abbr
                or "Away"
            )

            home_name = (
                home_name
                or home_abbr
                or "Home"
            )


        live = (
            state == "in"
        )

        final = (
            state == "post"
            or completed
        )


        # Upcoming display fallback.
        if (
            not live
            and not final
            and not detail
        ):

            event_date = event.get(
                "date"
            )

            if event_date:

                try:
                    dt = (
                        datetime
                        .fromisoformat(
                            str(
                                event_date
                            ).replace(
                                "Z",
                                "+00:00",
                            )
                        )
                        .astimezone(
                            ET
                        )
                    )

                    detail = dt.strftime(
                        "%-I:%M %p ET"
                    )

                except Exception:
                    pass


        return {
            "sport":
                "NFL",

            "event_id":
                event_id,

            "start_time":
                event.get("date"),

            "away":
                away_name,

            "away_abbr":
                away_abbr,

            "away_score":
                away_score,

            "home":
                home_name,

            "home_abbr":
                home_abbr,

            "home_score":
                home_score,

            "state":
                state
                or "pre",

            "status":
                detail,

            "live":
                live,

            "final":
                final,

            "source":
                "ESPN Core",
        }


    except Exception:

        # One malformed/unavailable event
        # never kills the scoreboard.
        return None


@st.cache_data(
    ttl=20,
    show_spinner=False,
)
def fetch_nfl_scores():

    from concurrent.futures import (
        ThreadPoolExecutor,
    )

    today = datetime.now(
        ET
    ).strftime(
        "%Y%m%d"
    )

    url = (
        "https://sports.core.api.espn.com/"
        "v2/sports/football/leagues/nfl/events"
        f"?dates={today}"
        "&limit=50"
        "&lang=en"
        "&region=us"
    )

    payload = get_json(
        url
    )

    refs = []

    for item in payload.get(
        "items",
        [],
    ):

        ref = _https_ref(
            item
        )

        if ref:
            refs.append(
                ref
            )


    # Parallel expansion keeps the scoreboard
    # responsive while avoiding the blocked
    # site.api endpoint entirely.
    with ThreadPoolExecutor(
        max_workers=8
    ) as pool:

        games = list(
            pool.map(
                _parse_core_event,
                refs,
            )
        )


    games = [
        game
        for game in games
        if game
    ]


    return games


# ============================================================
# CFB — ESPN FBS SCOREBOARD
# ============================================================

# CFB_LIVE_SCORE_BUILD_5
@st.cache_data(
    ttl=20,
    show_spinner=False,
)
def fetch_cfb_scores():

    today = datetime.now(
        ET
    ).strftime(
        "%Y%m%d"
    )

    url = (
        "https://site.api.espn.com/"
        "apis/site/v2/sports/football/"
        "college-football/scoreboard"
        f"?dates={today}"
        "&groups=80"
        "&limit=400"
    )

    payload = get_json(
        url
    )

    games = []


    for event in (
        payload.get(
            "events"
        )
        or []
    ):

        competitions = (
            event.get(
                "competitions"
            )
            or []
        )


        if not competitions:
            continue


        competition = competitions[
            0
        ]


        status = (
            competition.get(
                "status"
            )
            or {}
        )


        status_type = (
            status.get(
                "type"
            )
            or {}
        )


        state = str(
            status_type.get(
                "state",
                "pre",
            )
        ).lower()


        completed = bool(
            status_type.get(
                "completed",
                False,
            )
        )


        live = (
            state == "in"
        )


        final = (
            state == "post"
            or completed
        )


        detail = (
            status_type.get(
                "shortDetail"
            )
            or status_type.get(
                "detail"
            )
            or status_type.get(
                "description"
            )
            or ""
        )


        away_item = None
        home_item = None


        for competitor in (
            competition.get(
                "competitors"
            )
            or []
        ):

            side = str(
                competitor.get(
                    "homeAway",
                    "",
                )
            ).lower()


            if side == "away":

                away_item = competitor


            elif side == "home":

                home_item = competitor


        def team_payload(
            item,
            fallback,
        ):

            item = item or {}

            team = (
                item.get(
                    "team"
                )
                or {}
            )


            return {
                "name":
                    (
                        team.get(
                            "displayName"
                        )
                        or fallback
                    ),

                "abbr":
                    (
                        team.get(
                            "abbreviation"
                        )
                        or ""
                    ),

                "score":
                    item.get(
                        "score"
                    ),
            }


        away = team_payload(
            away_item,
            "Away",
        )

        home = team_payload(
            home_item,
            "Home",
        )


        if (
            not live
            and not final
        ):

            event_date = event.get(
                "date"
            )


            if event_date:

                try:

                    dt = (
                        datetime
                        .fromisoformat(
                            str(
                                event_date
                            ).replace(
                                "Z",
                                "+00:00",
                            )
                        )
                        .astimezone(
                            ET
                        )
                    )

                    detail = dt.strftime(
                        "%-I:%M %p ET"
                    )

                except Exception:

                    pass


        games.append({
            "sport":
                "CFB",

            "event_id":
                str(
                    event.get(
                        "id",
                        "",
                    )
                ),

            "start_time":
                event.get(
                    "date"
                ),

            "away":
                away[
                    "name"
                ],

            "away_abbr":
                away[
                    "abbr"
                ],

            "away_score":
                away[
                    "score"
                ],

            "home":
                home[
                    "name"
                ],

            "home_abbr":
                home[
                    "abbr"
                ],

            "home_score":
                home[
                    "score"
                ],

            "state":
                state,

            "status":
                detail,

            "live":
                live,

            "final":
                final,

            "source":
                "ESPN FBS",
        })


    return games


# ============================================================
# CBB — ESPN DIVISION I SCOREBOARD
# ============================================================

# CBB_LIVE_SCORE_BUILD_5
@st.cache_data(
    ttl=20,
    show_spinner=False,
)
def fetch_cbb_scores():

    today = datetime.now(
        ET
    ).strftime(
        "%Y%m%d"
    )

    url = (
        "https://site.api.espn.com/"
        "apis/site/v2/sports/basketball/"
        "mens-college-basketball/scoreboard"
        f"?dates={today}"
        "&groups=50"
        "&limit=400"
    )

    payload = get_json(
        url
    )

    games = []


    for event in (
        payload.get(
            "events"
        )
        or []
    ):

        competitions = (
            event.get(
                "competitions"
            )
            or []
        )


        if not competitions:
            continue


        competition = competitions[
            0
        ]


        status = (
            competition.get(
                "status"
            )
            or {}
        )


        status_type = (
            status.get(
                "type"
            )
            or {}
        )


        state = str(
            status_type.get(
                "state",
                "pre",
            )
        ).lower()


        completed = bool(
            status_type.get(
                "completed",
                False,
            )
        )


        live = (
            state == "in"
        )


        final = (
            state == "post"
            or completed
        )


        detail = (
            status_type.get(
                "shortDetail"
            )
            or status_type.get(
                "detail"
            )
            or status_type.get(
                "description"
            )
            or ""
        )


        away_item = None
        home_item = None


        for competitor in (
            competition.get(
                "competitors"
            )
            or []
        ):

            side = str(
                competitor.get(
                    "homeAway",
                    "",
                )
            ).lower()


            if side == "away":

                away_item = competitor


            elif side == "home":

                home_item = competitor


        def team_payload(
            item,
            fallback,
        ):

            item = item or {}

            team = (
                item.get(
                    "team"
                )
                or {}
            )


            return {
                "name":
                    (
                        team.get(
                            "displayName"
                        )
                        or fallback
                    ),

                "abbr":
                    (
                        team.get(
                            "abbreviation"
                        )
                        or ""
                    ),

                "score":
                    item.get(
                        "score"
                    ),
            }


        away = team_payload(
            away_item,
            "Away",
        )

        home = team_payload(
            home_item,
            "Home",
        )


        if (
            not live
            and not final
        ):

            event_date = event.get(
                "date"
            )


            if event_date:

                try:

                    dt = (
                        datetime
                        .fromisoformat(
                            str(
                                event_date
                            ).replace(
                                "Z",
                                "+00:00",
                            )
                        )
                        .astimezone(
                            ET
                        )
                    )

                    detail = dt.strftime(
                        "%-I:%M %p ET"
                    )

                except Exception:

                    pass


        games.append({
            "sport":
                "CBB",

            "event_id":
                str(
                    event.get(
                        "id",
                        "",
                    )
                ),

            "start_time":
                event.get(
                    "date"
                ),

            "away":
                away[
                    "name"
                ],

            "away_abbr":
                away[
                    "abbr"
                ],

            "away_score":
                away[
                    "score"
                ],

            "home":
                home[
                    "name"
                ],

            "home_abbr":
                home[
                    "abbr"
                ],

            "home_score":
                home[
                    "score"
                ],

            "state":
                state,

            "status":
                detail,

            "live":
                live,

            "final":
                final,

            "source":
                "ESPN Division I",
        })


    return games


# ============================================================
# NBA — ESPN SCOREBOARD
# ============================================================

# NBA_LIVE_SCORE_BUILD_6
@st.cache_data(
    ttl=20,
    show_spinner=False,
)
def fetch_nba_scores():

    today = datetime.now(
        ET
    ).strftime(
        "%Y%m%d"
    )

    url = (
        "https://site.api.espn.com/"
        "apis/site/v2/sports/basketball/"
        "nba/scoreboard"
        f"?dates={today}"
        "&limit=50"
    )

    payload = get_json(
        url
    )

    games = []

    for event in payload.get(
        "events",
        [],
    ):

        competitions = event.get(
            "competitions",
            [],
        )

        if not competitions:
            continue

        competition = competitions[0]

        status = competition.get(
            "status",
            {},
        )

        status_type = status.get(
            "type",
            {},
        )

        state = str(
            status_type.get(
                "state",
                "pre",
            )
        ).lower()

        completed = bool(
            status_type.get(
                "completed",
                False,
            )
        )

        live = (
            state == "in"
        )

        final = (
            state == "post"
            or completed
        )

        detail = (
            status_type.get(
                "shortDetail"
            )
            or status_type.get(
                "detail"
            )
            or status_type.get(
                "description"
            )
            or ""
        )

        away_item = None
        home_item = None

        for competitor in competition.get(
            "competitors",
            [],
        ):

            side = str(
                competitor.get(
                    "homeAway",
                    "",
                )
            ).lower()

            if side == "away":
                away_item = competitor

            elif side == "home":
                home_item = competitor


        def team_payload(
            item,
            fallback,
        ):

            item = item or {}

            team = item.get(
                "team",
                {},
            )

            return {
                "name":
                    team.get(
                        "displayName",
                        fallback,
                    ),

                "abbr":
                    team.get(
                        "abbreviation",
                        "",
                    ),

                "score":
                    item.get(
                        "score"
                    ),
            }


        away = team_payload(
            away_item,
            "Away",
        )

        home = team_payload(
            home_item,
            "Home",
        )


        if (
            not live
            and not final
        ):

            event_date = event.get(
                "date"
            )

            if event_date:

                try:

                    dt = (
                        datetime
                        .fromisoformat(
                            str(
                                event_date
                            ).replace(
                                "Z",
                                "+00:00",
                            )
                        )
                        .astimezone(
                            ET
                        )
                    )

                    detail = dt.strftime(
                        "%-I:%M %p ET"
                    )

                except Exception:
                    pass


        games.append({
            "sport":
                "NBA",

            "event_id":
                str(
                    event.get(
                        "id",
                        "",
                    )
                ),

            "start_time":
                event.get(
                    "date"
                ),

            "away":
                away[
                    "name"
                ],

            "away_abbr":
                away[
                    "abbr"
                ],

            "away_score":
                away[
                    "score"
                ],

            "home":
                home[
                    "name"
                ],

            "home_abbr":
                home[
                    "abbr"
                ],

            "home_score":
                home[
                    "score"
                ],

            "state":
                state,

            "status":
                detail,

            "live":
                live,

            "final":
                final,

            "source":
                "ESPN",
        })


    return games


# ============================================================
# NHL — OFFICIAL NHL SCORE API
# ============================================================

# NHL_LIVE_SCORE_BUILD_6
@st.cache_data(
    ttl=20,
    show_spinner=False,
)
def fetch_nhl_scores():

    today = datetime.now(
        ET
    ).strftime(
        "%Y-%m-%d"
    )

    url = (
        "https://api-web.nhle.com/"
        "v1/score/"
        + today
    )

    payload = get_json(
        url
    )

    games = []


    def localized(
        value,
    ):

        if isinstance(
            value,
            dict,
        ):

            return (
                value.get(
                    "default"
                )
                or ""
            )

        return str(
            value
            or ""
        )


    def team_payload(
        obj,
        fallback,
    ):

        obj = obj or {}

        place = localized(
            obj.get(
                "placeName"
            )
        )

        common = localized(
            obj.get(
                "commonName"
            )
        )

        full = (
            place
            + " "
            + common
        ).strip()

        return {
            "name":
                full
                or fallback,

            "abbr":
                obj.get(
                    "abbrev",
                    "",
                ),

            "score":
                obj.get(
                    "score"
                ),
        }


    for game in (
        payload.get(
            "games"
        )
        or []
    ):

        raw_state = str(
            game.get(
                "gameState",
                "",
            )
        ).upper()


        live = raw_state in {
            "LIVE",
            "CRIT",
        }


        final = raw_state in {
            "OFF",
            "FINAL",
        }


        state = (
            "in"
            if live
            else
            "post"
            if final
            else
            "pre"
        )


        away = team_payload(
            game.get(
                "awayTeam"
            ),
            "Away",
        )

        home = team_payload(
            game.get(
                "homeTeam"
            ),
            "Home",
        )


        if live:

            period = (
                game.get(
                    "periodDescriptor"
                )
                or {}
            )

            period_number = (
                period.get(
                    "number"
                )
            )

            period_type = str(
                period.get(
                    "periodType",
                    "",
                )
            ).upper()

            clock = (
                game.get(
                    "clock"
                )
                or {}
            )

            remaining = (
                clock.get(
                    "timeRemaining"
                )
                or ""
            )


            if period_type in {
                "OT",
                "SO",
            }:

                period_label = (
                    period_type
                )

            elif period_number:

                period_label = (
                    "P"
                    + str(
                        period_number
                    )
                )

            else:

                period_label = "LIVE"


            detail = (
                period_label
                + (
                    " "
                    + str(
                        remaining
                    )
                    if remaining
                    else ""
                )
            ).strip()


        elif final:

            outcome = (
                game.get(
                    "gameOutcome"
                )
                or {}
            )

            last_type = str(
                outcome.get(
                    "lastPeriodType",
                    "",
                )
            ).upper()


            if last_type == "OT":

                detail = "Final/OT"

            elif last_type == "SO":

                detail = "Final/SO"

            else:

                detail = "Final"


        else:

            detail = str(
                game.get(
                    "gameScheduleState",
                    ""
                )
            )


            start_time = game.get(
                "startTimeUTC"
            )


            if start_time:

                try:

                    dt = (
                        datetime
                        .fromisoformat(
                            str(
                                start_time
                            ).replace(
                                "Z",
                                "+00:00",
                            )
                        )
                        .astimezone(
                            ET
                        )
                    )

                    detail = dt.strftime(
                        "%-I:%M %p ET"
                    )

                except Exception:

                    pass


        games.append({
            "sport":
                "NHL",

            "event_id":
                str(
                    game.get(
                        "id",
                        "",
                    )
                ),

            "start_time":
                game.get(
                    "startTimeUTC"
                ),

            "away":
                away[
                    "name"
                ],

            "away_abbr":
                away[
                    "abbr"
                ],

            "away_score":
                away[
                    "score"
                ],

            "home":
                home[
                    "name"
                ],

            "home_abbr":
                home[
                    "abbr"
                ],

            "home_score":
                home[
                    "score"
                ],

            "state":
                state,

            "status":
                detail,

            "live":
                live,

            "final":
                final,

            "source":
                "NHL Official",
        })


    return games


# ============================================================
# MLB — MLB STATS API
# ============================================================

@st.cache_data(
    ttl=20,
    show_spinner=False,
)
def fetch_mlb_scores():

    today = datetime.now(
        ET
    ).strftime(
        "%Y-%m-%d"
    )

    url = (
        "https://statsapi.mlb.com/"
        "api/v1/schedule"
        "?sportId=1"
        f"&date={today}"
        "&hydrate=linescore"
    )

    payload = get_json(url)

    games = []

    for date_block in payload.get(
        "dates",
        [],
    ):

        for game in date_block.get(
            "games",
            [],
        ):

            teams = game.get(
                "teams",
                {},
            )

            away = teams.get(
                "away",
                {},
            )

            home = teams.get(
                "home",
                {},
            )

            status = game.get(
                "status",
                {},
            )

            abstract = status.get(
                "abstractGameState",
                "",
            )

            detailed = status.get(
                "detailedState",
                "",
            )

            live = (
                abstract == "Live"
            )

            final = (
                abstract == "Final"
                or detailed.startswith(
                    "Final"
                )
            )

            linescore = game.get(
                "linescore",
                {},
            )

            if live:

                inning_state = (
                    linescore.get(
                        "inningState",
                        ""
                    )
                )

                inning = (
                    linescore.get(
                        "currentInningOrdinal",
                        ""
                    )
                )

                shown_status = (
                    f"{inning_state} {inning}"
                ).strip()

                if not shown_status:
                    shown_status = detailed

            elif final:

                shown_status = detailed

            else:

                shown_status = detailed

                game_date = game.get(
                    "gameDate"
                )

                if game_date:

                    try:
                        dt = (
                            datetime
                            .fromisoformat(
                                game_date.replace(
                                    "Z",
                                    "+00:00",
                                )
                            )
                            .astimezone(
                                ET
                            )
                        )

                        shown_status = (
                            dt.strftime(
                                "%-I:%M %p ET"
                            )
                        )

                    except Exception:
                        pass

            away_name = (
                away.get(
                    "team",
                    {}
                )
                .get(
                    "name",
                    "Away",
                )
            )

            home_name = (
                home.get(
                    "team",
                    {}
                )
                .get(
                    "name",
                    "Home",
                )
            )

            games.append({
                "sport":
                    "MLB",

                "event_id":
                    str(
                        game.get(
                            "gamePk",
                            "",
                        )
                    ),

                "away":
                    away_name,

                "away_abbr":
                    team_key(
                        away_name
                    ),

                "away_score":
                    away.get(
                        "score"
                    ),

                "home":
                    home_name,

                "home_abbr":
                    team_key(
                        home_name
                    ),

                "home_score":
                    home.get(
                        "score"
                    ),

                "state":
                    (
                        "in"
                        if live
                        else
                        "post"
                        if final
                        else
                        "pre"
                    ),

                "status":
                    shown_status,

                "live":
                    live,

                "final":
                    final,

                "source":
                    "MLB",
            })

    return games


# ============================================================
# COMMON
# ============================================================

def get_scores(
    sport,
):
    if sport == "NFL":
        return fetch_nfl_scores()

    if sport == "MLB":
        return fetch_mlb_scores()

    if sport == "NBA":
        return fetch_nba_scores()

    if sport == "NHL":
        return fetch_nhl_scores()

    if sport == "CBB":
        return fetch_cbb_scores()

    if sport == "CFB":
        return fetch_cfb_scores()

    return []


def game_team_keys(
    game,
):
    return {
        team_key(
            game.get(
                "away_abbr"
            )
            or game.get(
                "away"
            )
        ),
        team_key(
            game.get(
                "home_abbr"
            )
            or game.get(
                "home"
            )
        ),
    }


def game_has_team(
    game,
    team,
):
    return (
        team_key(team)
        in game_team_keys(
            game
        )
    )


def favorite_teams_from_session():

    raw = st.session_state.get(
        "member_teams",
        "",
    )

    if not raw:
        return []

    pieces = re.split(
        r"[,;]+",
        str(raw),
    )

    return [
        x.strip()
        for x in pieces
        if x.strip()
    ]


def game_rank(
    game,
    pinned_keys,
):
    teams = game_team_keys(
        game
    )

    pinned = bool(
        teams
        & pinned_keys
    )

    if pinned:
        pin_rank = 0
    else:
        pin_rank = 1

    if game.get("live"):
        state_rank = 0

    elif game.get("state") == "pre":
        state_rank = 1

    elif game.get("final"):
        state_rank = 2

    else:
        state_rank = 3

    return (
        pin_rank,
        state_rank,
    )


def sort_games(
    games,
    pinned_teams=None,
):
    pinned_teams = (
        pinned_teams
        or []
    )

    pinned_keys = {
        team_key(x)
        for x in pinned_teams
    }

    return sorted(
        games,
        key=lambda game:
            game_rank(
                game,
                pinned_keys,
            ),
    )


# ============================================================
# SCORE CARD
# ============================================================

def score_card(
    game,
    pinned_teams=None,
):
    pinned_teams = (
        pinned_teams
        or []
    )

    pinned_keys = {
        team_key(x)
        for x in pinned_teams
    }

    is_pinned = bool(
        game_team_keys(
            game
        )
        & pinned_keys
    )

    live = bool(
        game.get(
            "live"
        )
    )

    final = bool(
        game.get(
            "final"
        )
    )


    # --------------------------------------------------------
    # STATUS COLORS
    # --------------------------------------------------------

    if live:
        badge = "LIVE"
        fg = "#A6293D"
        bg = "#FFE9EE"
        border = "#F4BCC7"
        accent = "#EB4965"

    elif final:
        badge = "FINAL"
        fg = "#53657B"
        bg = "#EEF2F6"
        border = "#D7E0E8"
        accent = "#8292A6"

    else:
        badge = "UPCOMING"
        fg = "#174DA8"
        bg = "#EAF2FF"
        border = "#C8DAFB"
        accent = "#3978E8"


    # --------------------------------------------------------
    # SCORE VALUES
    # --------------------------------------------------------

    away_score_raw = game.get(
        "away_score"
    )

    home_score_raw = game.get(
        "home_score"
    )


    def numeric_score(value):
        try:
            return float(value)
        except Exception:
            return None


    away_num = numeric_score(
        away_score_raw
    )

    home_num = numeric_score(
        home_score_raw
    )


    away_score = (
        "—"
        if away_score_raw is None
        else str(away_score_raw)
    )

    home_score = (
        "—"
        if home_score_raw is None
        else str(home_score_raw)
    )


    # --------------------------------------------------------
    # LEADER / WINNER COLORS
    #
    # Green = team currently ahead or final winner.
    # Neutral = tied / upcoming.
    # Final loser becomes muted.
    # --------------------------------------------------------

    away_leading = False
    home_leading = False

    if (
        away_num is not None
        and home_num is not None
        and away_num != home_num
    ):
        away_leading = (
            away_num > home_num
        )

        home_leading = (
            home_num > away_num
        )


    if away_leading:

        away_name_color = "#087A55"
        away_score_color = "#047857"
        away_weight = "880"

        if final:
            home_name_color = "#8795A8"
            home_score_color = "#8795A8"
        else:
            home_name_color = "#33465F"
            home_score_color = "#33465F"

        home_weight = "720"


    elif home_leading:

        home_name_color = "#087A55"
        home_score_color = "#047857"
        home_weight = "880"

        if final:
            away_name_color = "#8795A8"
            away_score_color = "#8795A8"
        else:
            away_name_color = "#33465F"
            away_score_color = "#33465F"

        away_weight = "720"


    else:

        away_name_color = "#17263B"
        home_name_color = "#17263B"

        away_score_color = "#101828"
        home_score_color = "#101828"

        away_weight = "760"
        home_weight = "760"


    # --------------------------------------------------------
    # MY TEAM BADGE
    # --------------------------------------------------------

    pin_html = ""

    if is_pinned:

        pin_html = """
        <span style="
            color:#5B3FA8;
            background:#F2ECFF;
            border:1px solid #D9C8FF;
            border-radius:999px;
            padding:5px 8px;
            font-size:10px;
            font-weight:850;
        ">
            ★ MY TEAM
        </span>
        """


    # --------------------------------------------------------
    # CARD
    # --------------------------------------------------------

    html(
        f"""
        <div style="
            position:relative;
            background:#FFFFFF;
            border:1px solid #DCE4EE;
            border-radius:18px;
            padding:18px 19px 17px 22px;
            margin-bottom:12px;
            min-height:168px;
            box-shadow:
                0 7px 20px rgba(31,48,74,.075);
        ">

            <div style="
                position:absolute;
                left:0;
                top:0;
                bottom:0;
                width:4px;
                background:{accent};
                border-radius:18px 0 0 18px;
            "></div>


            <div style="
                display:flex;
                align-items:center;
                justify-content:space-between;
                gap:8px;
                margin-bottom:13px;
            ">

                <div style="
                    display:flex;
                    gap:6px;
                    align-items:center;
                    flex-wrap:wrap;
                ">

                    <span style="
                        color:{fg};
                        background:{bg};
                        border:1px solid {border};
                        border-radius:999px;
                        padding:5px 9px;
                        font-size:11px;
                        font-weight:850;
                    ">
                        {badge}
                    </span>

                    {pin_html}

                </div>


                <span style="
                    color:#60728A;
                    font-size:14px;
                    font-weight:700;
                ">
                    {escape(
                        str(
                            game.get(
                                "status",
                                ""
                            )
                        )
                    )}
                </span>

            </div>


            <div style="
                display:grid;
                grid-template-columns:
                    minmax(0,1fr) auto;
                gap:11px 16px;
                align-items:center;
            ">


                <div style="
                    color:{away_name_color};
                    font-size:18px;
                    font-weight:{away_weight};
                    line-height:1.2;
                ">
                    {escape(
                        str(
                            game.get(
                                "away",
                                ""
                            )
                        )
                    )}
                </div>


                <div style="
                    color:{away_score_color};
                    font-size:28px;
                    font-weight:900;
                    font-variant-numeric:
                        tabular-nums;
                    line-height:1;
                ">
                    {escape(
                        away_score
                    )}
                </div>


                <div style="
                    color:{home_name_color};
                    font-size:18px;
                    font-weight:{home_weight};
                    line-height:1.2;
                ">
                    {escape(
                        str(
                            game.get(
                                "home",
                                ""
                            )
                        )
                    )}
                </div>


                <div style="
                    color:{home_score_color};
                    font-size:28px;
                    font-weight:900;
                    font-variant-numeric:
                        tabular-nums;
                    line-height:1;
                ">
                    {escape(
                        home_score
                    )}
                </div>

            </div>

        </div>
        """
    )


# ============================================================
# SCOREBOARD
# ============================================================

def _render_live_scores(
    sport,
    pinned_teams=None,
    title=None,
    limit=15,
):
    if sport not in {
        "NFL",
        "MLB",
        "NBA",
        "NHL",
        "CBB",
        "CFB",
    }:
        return

    pinned_teams = (
        pinned_teams
        or []
    )

    try:
        games = sort_games(
            get_scores(
                sport
            ),
            pinned_teams,
        )

    except Exception:
        st.warning(
            (
                "Live scores are temporarily unavailable. "
                "Research remains available below."
            )
        )
        return

    if not games:
        st.info(
            f"No {sport} games are scheduled today."
        )
        return

    if title is None:
        title = (
            "My Games"
            if pinned_teams
            else "Live & Upcoming"
        )

    live_count = sum(
        1
        for game in games
        if game.get("live")
    )

    html(
        f"""
        <div style="
            display:flex;
            align-items:center;
            gap:9px;
            margin:20px 0 12px 0;
        ">

            <div style="
                width:9px;
                height:9px;
                border-radius:50%;
                background:#EB4965;
                box-shadow:
                    0 0 0 5px rgba(235,73,101,.10);
            "></div>

            <div style="
                color:#17263B;
                font-size:28px;
                font-weight:840;
            ">
                {escape(title)}
            </div>

            {
                f'''
                <span style="
                    color:#A6293D;
                    background:#FFE9EE;
                    border:1px solid #F4BCC7;
                    border-radius:999px;
                    padding:5px 9px;
                    font-size:11px;
                    font-weight:850;
                ">
                    {live_count} LIVE
                </span>
                '''
                if live_count
                else ""
            }

        </div>
        """
    )

    shown = games[:limit]

    for start in range(
        0,
        len(shown),
        3,
    ):
        cols = st.columns(3)

        for col, game in zip(
            cols,
            shown[
                start:start + 3
            ],
        ):
            with col:
                score_card(
                    game,
                    pinned_teams,
                )

    st.caption(
        (
            "Scores refresh automatically. "
            "Betting and research feeds remain separate."
        )
    )


if hasattr(
    st,
    "fragment",
):
    render_live_scores = st.fragment(
        run_every="30s"
    )(
        _render_live_scores
    )
else:
    render_live_scores = _render_live_scores


# ============================================================
# SURVIVOR LIVE TRACKING
# ============================================================

def find_team_game(
    team,
):
    games = fetch_nfl_scores()

    for game in games:
        if game_has_team(
            game,
            team,
        ):
            return game

    return None


def score_int(value):
    try:
        return int(value)
    except Exception:
        return None


def survivor_leg_status(
    team,
    game,
):
    if not game:
        return (
            "NO GAME",
            "#65758B",
            "#EEF2F6",
        )

    if game.get(
        "live"
    ):
        return (
            "LIVE",
            "#A6293D",
            "#FFE9EE",
        )

    if not game.get(
        "final"
    ):
        return (
            "UPCOMING",
            "#174DA8",
            "#EAF2FF",
        )

    target = team_key(team)

    away_key = team_key(
        game.get(
            "away_abbr"
        )
        or game.get(
            "away"
        )
    )

    home_key = team_key(
        game.get(
            "home_abbr"
        )
        or game.get(
            "home"
        )
    )

    away_score = score_int(
        game.get(
            "away_score"
        )
    )

    home_score = score_int(
        game.get(
            "home_score"
        )
    )

    if (
        away_score is None
        or home_score is None
    ):
        return (
            "FINAL",
            "#65758B",
            "#EEF2F6",
        )

    if away_score == home_score:
        # Survivor rules treat a tie as a loss.
        return (
            "LOSS",
            "#A12B42",
            "#FFECEF",
        )

    winner = (
        away_key
        if away_score > home_score
        else home_key
    )

    if target == winner:
        return (
            "WIN",
            "#116149",
            "#EAF8F2",
        )

    return (
        "LOSS",
        "#A12B42",
        "#FFECEF",
    )


def survivor_score_line(
    game,
):
    if not game:
        return "Game not found"

    away = game.get(
        "away",
        ""
    )

    home = game.get(
        "home",
        ""
    )

    away_score = game.get(
        "away_score"
    )

    home_score = game.get(
        "home_score"
    )

    status = game.get(
        "status",
        ""
    )

    if away_score is None:
        away_score = "—"

    if home_score is None:
        home_score = "—"

    return (
        f"{away} {away_score} · "
        f"{home} {home_score} · "
        f"{status}"
    )


def _render_survivor_live_entries(
    entries,
):
    if not entries:
        return

    html(
        """
        <div style="
            color:#17263B;
            font-size:28px;
            font-weight:840;
            margin:18px 0 5px 0;
        ">
            My Survivor Games
        </div>

        <div style="
            color:#536A84;
            font-size:18px;
            font-weight:600;
            margin-bottom:12px;
        ">
            Each required team is tracked separately.
            Entries are only graded after games become final.
        </div>
        """
    )

    for entry in entries:

        key = entry.get(
            "entry_key",
            "Survivor Entry",
        )

        teams = entry.get(
            "teams",
            [],
        )

        legs = []

        for team in teams:

            game = find_team_game(
                team
            )

            status, fg, bg = (
                survivor_leg_status(
                    team,
                    game,
                )
            )

            legs.append({
                "team":
                    team,

                "game":
                    game,

                "status":
                    status,

                "fg":
                    fg,

                "bg":
                    bg,
            })

        statuses = [
            x["status"]
            for x in legs
        ]

        if "LOSS" in statuses:
            overall = "ENTRY OUT"
            overall_fg = "#A12B42"
            overall_bg = "#FFECEF"

        elif (
            statuses
            and all(
                x == "WIN"
                for x in statuses
            )
        ):
            overall = "ADVANCED"
            overall_fg = "#116149"
            overall_bg = "#EAF8F2"

        elif "LIVE" in statuses:
            overall = "IN PROGRESS"
            overall_fg = "#A6293D"
            overall_bg = "#FFE9EE"

        else:
            overall = "PENDING"
            overall_fg = "#174DA8"
            overall_bg = "#EAF2FF"

        leg_html = ""

        for leg in legs:

            leg_html += f"""
            <div style="
                padding:12px 0;
                border-top:1px solid #EEF2F6;
            ">

                <div style="
                    display:flex;
                    align-items:center;
                    justify-content:space-between;
                    gap:10px;
                    margin-bottom:5px;
                ">

                    <div style="
                        color:#17263B;
                        font-size:17px;
                        font-weight:820;
                    ">
                        {escape(str(leg["team"]))}
                    </div>

                    <span style="
                        color:{leg["fg"]};
                        background:{leg["bg"]};
                        border-radius:999px;
                        padding:6px 10px;
                        font-size:11px;
                        font-weight:850;
                    ">
                        {leg["status"]}
                    </span>

                </div>

                <div style="
                    color:#5E7188;
                    font-size:16px;
                    font-weight:600;
                ">
                    {
                        escape(
                            survivor_score_line(
                                leg["game"]
                            )
                        )
                    }
                </div>

            </div>
            """

        html(
            f"""
            <div style="
                background:#FFFFFF;
                border:1px solid #DCE4EE;
                border-radius:18px;
                padding:18px 19px;
                margin-bottom:14px;
                box-shadow:
                    0 7px 20px rgba(31,48,74,.075);
            ">

                <div style="
                    display:flex;
                    align-items:center;
                    justify-content:space-between;
                    gap:10px;
                    margin-bottom:6px;
                ">

                    <div style="
                        color:#142033;
                        font-size:20px;
                        font-weight:850;
                    ">
                        {escape(str(key))}
                    </div>

                    <span style="
                        color:{overall_fg};
                        background:{overall_bg};
                        border-radius:999px;
                        padding:6px 10px;
                        font-size:11px;
                        font-weight:850;
                    ">
                        {overall}
                    </span>

                </div>

                {leg_html}

            </div>
            """
        )


if hasattr(
    st,
    "fragment",
):
    render_survivor_live_entries = st.fragment(
        run_every="30s"
    )(
        _render_survivor_live_entries
    )
else:
    render_survivor_live_entries = (
        _render_survivor_live_entries
    )
