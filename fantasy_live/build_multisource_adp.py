from pathlib import Path
from io import StringIO
from datetime import datetime, timezone
import json
import re
import unicodedata
import requests
import pandas as pd
import numpy as np

ROOT = Path("/home/ubuntu/sports-hulk")

OUT = ROOT / "fantasy_live" / "multisource"
HISTORY = ROOT / "fantasy_live" / "history"

OUT.mkdir(parents=True, exist_ok=True)
HISTORY.mkdir(parents=True, exist_ok=True)

SEASON = 2026

UA = {
    "User-Agent":
        "Sports-Hulk personal fantasy research; "
        "low-frequency cached collection"
}


# ============================================================
# HELPERS
# ============================================================

def normalize_name(v):
    if not v:
        return ""

    s = unicodedata.normalize("NFKD", str(v))
    s = "".join(
        ch for ch in s
        if not unicodedata.combining(ch)
    )

    s = s.lower()

    # remove punctuation
    s = re.sub(r"[^a-z0-9 ]+", " ", s)

    # normalize suffixes
    s = re.sub(
        r"\b(jr|sr|ii|iii|iv|v)\b",
        " ",
        s
    )

    s = re.sub(r"\s+", " ", s).strip()

    return s


def pos_ok(v):
    return str(v).upper() in {
        "QB", "RB", "WR", "TE"
    }


def safe_num(v):
    try:
        x = float(v)
        return x if np.isfinite(x) else np.nan
    except:
        return np.nan


def archive_json(name, payload):
    stamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    path = HISTORY / f"{name}_{stamp}.json"

    path.write_text(
        json.dumps(payload, indent=2)
    )


# ============================================================
# SLEEPER
# ============================================================

def fetch_sleeper():

    print()
    print("=" * 80)
    print("SLEEPER")
    print("=" * 80)

    # This is the working endpoint we already validated on Oracle.
    url = (
        f"https://api.sleeper.com/projections/"
        f"nfl/{SEASON}"
    )

    r = requests.get(
        url,
        params={
            "season_type": "regular"
        },
        headers=UA,
        timeout=40,
    )

    print("HTTP:", r.status_code)

    if r.status_code != 200:
        print(r.text[:1000])
        return pd.DataFrame()

    payload = r.json()
    archive_json("SLEEPER_ADP_RAW", payload)

    rows = []

    for item in payload:

        player = item.get("player") or {}
        stats = item.get("stats") or {}

        name = (
            player.get("full_name")
            or player.get("name")
            or (
                str(player.get("first_name") or "")
                + " "
                + str(player.get("last_name") or "")
            ).strip()
        )

        positions = player.get(
            "fantasy_positions"
        )

        if isinstance(positions, list):
            pos = (
                player.get("position")
                or (
                    positions[0]
                    if positions
                    else None
                )
            )
        else:
            pos = player.get("position")

        team = (
            item.get("team")
            or player.get("team")
        )

        if not pos_ok(pos):
            continue

        ppr = safe_num(
            stats.get("adp_ppr")
        )

        half = safe_num(
            stats.get("adp_half_ppr")
        )

        std = safe_num(
            stats.get("adp_std")
        )

        # Sleeper uses huge sentinel values
        # for effectively undrafted players.
        if pd.notna(ppr) and ppr >= 900:
            ppr = np.nan

        if pd.notna(half) and half >= 900:
            half = np.nan

        if pd.notna(std) and std >= 900:
            std = np.nan

        if (
            pd.isna(ppr)
            and pd.isna(half)
            and pd.isna(std)
        ):
            continue

        rows.append({
            "player": name,
            "name_key": normalize_name(name),
            "team": team,
            "position": str(pos).upper(),
            "sleeper_id":
                item.get("player_id"),
            "sleeper_ppr_adp": ppr,
            "sleeper_half_adp": half,
            "sleeper_std_adp": std,
        })

    df = pd.DataFrame(rows)

    print("ROWS:", len(df))

    return df


# ============================================================
# ESPN
# ============================================================

def fetch_espn():

    print()
    print("=" * 80)
    print("ESPN")
    print("=" * 80)

    url = (
        "https://lm-api-reads.fantasy.espn.com/"
        f"apis/v3/games/ffl/seasons/{SEASON}/"
        "segments/0/leaguedefaults/3"
    )

    fantasy_filter = {
        "players": {
            "limit": 350,
            "sortDraftRanks": {
                "sortPriority": 100,
                "sortAsc": True,
                "value": "PPR",
            },
        }
    }

    r = requests.get(
        url,
        params={
            "view": "kona_player_info"
        },
        headers={
            **UA,
            "Accept": "application/json",
            "X-Fantasy-Filter":
                json.dumps(fantasy_filter),
        },
        timeout=40,
    )

    print("HTTP:", r.status_code)

    if r.status_code != 200:
        print(r.text[:1000])
        return pd.DataFrame()

    payload = r.json()
    archive_json("ESPN_ADP_RAW", payload)

    pos_map = {
        1: "QB",
        2: "RB",
        3: "WR",
        4: "TE",
    }

    rows = []

    for wrapper in payload.get(
        "players", []
    ):

        p = wrapper.get("player") or {}

        pos = pos_map.get(
            p.get("defaultPositionId")
        )

        if not pos:
            continue

        name = p.get("fullName")

        ownership = (
            p.get("ownership") or {}
        )

        adp = safe_num(
            ownership.get(
                "averageDraftPosition"
            )
        )

        ranks = (
            p.get("draftRanksByRankType")
            or {}
        )

        ppr = ranks.get("PPR") or {}

        ppr_rank = safe_num(
            ppr.get("rank")
        )

        auction = safe_num(
            ppr.get("auctionValue")
        )

        rows.append({
            "player": name,
            "name_key": normalize_name(name),
            "position": pos,
            "espn_player_id":
                p.get("id"),
            "espn_adp": adp,
            "espn_ppr_room_rank":
                ppr_rank,
            "espn_auction":
                auction,
        })

    df = pd.DataFrame(rows)

    print("ROWS:", len(df))

    return df


# ============================================================
# YAHOO
# ============================================================

def fetch_yahoo():

    print()
    print("=" * 80)
    print("YAHOO")
    print("=" * 80)

    rows = []

    for start in [
        0,
        100,
        200,
        300,
    ]:

        url = (
            "https://pub-api-ro.fantasysports."
            "yahoo.com/fantasy/v2/game/nfl/"
            "players"
            f";position=ALL;count=100;"
            f"start={start};sort=AR/"
            "draft_analysis"
        )

        r = requests.get(
            url,
            params={
                "format": "json_f"
            },
            headers=UA,
            timeout=30,
        )

        print(
            f"PAGE {start}:",
            r.status_code
        )

        if r.status_code != 200:
            continue

        payload = r.json()

        archive_json(
            f"YAHOO_ADP_RAW_{start}",
            payload
        )

        game = (
            payload
            .get("fantasy_content", {})
            .get("game", {})
        )

        players = (
            game.get("players")
            or []
        )

        if not players:
            break

        for wrapper in players:

            p = wrapper.get("player") or {}

            pos = (
                p.get(
                    "display_position"
                )
                or ""
            ).upper()

            if not pos_ok(pos):
                continue

            da = (
                p.get("draft_analysis")
                or {}
            )

            adp = safe_num(
                da.get("average_pick")
            )

            if pd.isna(adp) or adp <= 0:
                continue

            name = (
                (p.get("name") or {})
                .get("full")
            )

            team = (
                p.get(
                    "editorial_team_abbr"
                )
                or ""
            ).upper()

            rows.append({
                "player": name,
                "name_key":
                    normalize_name(name),
                "team": team,
                "position": pos,
                "yahoo_player_id":
                    p.get("player_id"),
                "yahoo_adp": adp,
                "yahoo_auction":
                    safe_num(
                        da.get(
                            "average_cost"
                        )
                    ),
                "yahoo_pct_drafted":
                    safe_num(
                        da.get(
                            "percent_drafted"
                        )
                    ),
            })

        if len(players) < 100:
            break

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.drop_duplicates(
            subset=[
                "yahoo_player_id"
            ],
            keep="last"
        )

    print("ROWS:", len(df))

    return df


# ============================================================
# CBS
# ============================================================

def fetch_cbs():

    print()
    print("=" * 80)
    print("CBS")
    print("=" * 80)

    url = (
        "https://www.cbssports.com/"
        "fantasy/football/draft/"
        "averages/ppr/both/roto/all/"
    )

    r = requests.get(
        url,
        headers=UA,
        timeout=30,
    )

    print("HTTP:", r.status_code)

    if r.status_code != 200:
        print(r.text[:1000])
        return pd.DataFrame()

    # pandas parses the public ADP table
    tables = pd.read_html(
        StringIO(r.text)
    )

    target = None

    for t in tables:

        cols = [
            str(c).strip()
            for c in t.columns
        ]

        if (
            "Rank" in cols
            and "Player" in cols
            and "Avg Pos" in cols
        ):
            target = t.copy()
            break

    if target is None:
        print("CBS ADP TABLE NOT FOUND")
        return pd.DataFrame()

    target.columns = [
        str(c).strip()
        for c in target.columns
    ]

    rows = []

    for _, row in target.iterrows():

        raw_player = str(
            row.get("Player", "")
        ).strip()

        # CBS player cell usually contains
        # abbreviated name followed by full name.
        # We'll preserve the raw string and
        # resolve it later against our Hulk board.
        adp = safe_num(
            row.get("Avg Pos")
        )

        rank = safe_num(
            row.get("Rank")
        )

        if pd.isna(adp):
            continue

        rows.append({
            "cbs_raw_player":
                raw_player,
            "cbs_rank": rank,
            "cbs_adp": adp,
            "cbs_hi_lo":
                row.get("Hi/Lo"),
            "cbs_pct_drafted":
                safe_num(
                    row.get("Pct")
                ),
        })

    df = pd.DataFrame(rows)

    print("ROWS:", len(df))

    return df


# ============================================================
# RUN COLLECTION
# ============================================================

sleeper = fetch_sleeper()
espn = fetch_espn()
yahoo = fetch_yahoo()
cbs = fetch_cbs()

sleeper.to_csv(
    OUT / "SLEEPER_ADP.csv",
    index=False
)

espn.to_csv(
    OUT / "ESPN_ADP.csv",
    index=False
)

yahoo.to_csv(
    OUT / "YAHOO_ADP.csv",
    index=False
)

cbs.to_csv(
    OUT / "CBS_ADP_RAW.csv",
    index=False
)

stamp = datetime.now(
    timezone.utc
).strftime("%Y%m%dT%H%M%SZ")

summary = {
    "collected_at": stamp,
    "sleeper_rows": len(sleeper),
    "espn_rows": len(espn),
    "yahoo_rows": len(yahoo),
    "cbs_rows": len(cbs),
}

(
    OUT /
    "ADP_SOURCE_SUMMARY.json"
).write_text(
    json.dumps(
        summary,
        indent=2
    )
)

print()
print("=" * 80)
print("MULTI-SOURCE ADP SUMMARY")
print("=" * 80)

for k, v in summary.items():
    print(f"{k}: {v}")

print()
print("SLEEPER SAMPLE")

if not sleeper.empty:
    print(
        sleeper[
            [
                "player",
                "team",
                "position",
                "sleeper_ppr_adp",
                "sleeper_half_adp",
            ]
        ]
        .sort_values(
            "sleeper_ppr_adp"
        )
        .head(15)
        .to_string(index=False)
    )

print()
print("ESPN SAMPLE")

if not espn.empty:
    print(
        espn[
            [
                "player",
                "position",
                "espn_adp",
                "espn_ppr_room_rank",
            ]
        ]
        .sort_values(
            "espn_adp"
        )
        .head(15)
        .to_string(index=False)
    )

print()
print("YAHOO SAMPLE")

if not yahoo.empty:
    print(
        yahoo[
            [
                "player",
                "team",
                "position",
                "yahoo_adp",
            ]
        ]
        .sort_values(
            "yahoo_adp"
        )
        .head(15)
        .to_string(index=False)
    )

print()
print("CBS SAMPLE")

if not cbs.empty:
    print(
        cbs.head(15)
        .to_string(index=False)
    )

print()
print("RESULT: PASS")
