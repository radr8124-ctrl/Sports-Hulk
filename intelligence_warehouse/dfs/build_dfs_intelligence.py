#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import html
import json
import re
import time

import pandas as pd
import requests

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "dfs"
RAW = OUT / "raw"
OUT.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

PROJECTIONS_OUT = OUT / "DFS_CONTEST_PROJECTIONS_CURRENT.csv"
VALUE_OUT = OUT / "DFS_VALUE_SIGNALS_CURRENT.csv"
TIMELINE_OUT = OUT / "DFS_SALARY_TIMELINE.csv"
SOURCE_OUT = OUT / "DFS_SOURCE_CATALOG.csv"
RECEIPT_OUT = OUT / "DFS_INTELLIGENCE_RECEIPT.json"

FANDUEL_GRAPHQL = "https://www.fanduel.com/research/api/graphql"
FP_DK_URL = "https://www.fantasypros.com/daily-fantasy/nfl/draftkings-salary-changes.php"
SHARKSNIP_DK_URL = "https://sharksnip.com/picks/dfs/nfl"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "text/html,application/json,*/*"}
NOW = datetime.now(timezone.utc)
FD_SPORTS = {
    "NFL": {
        "page": "https://www.fanduel.com/research/nfl/fantasy/dfs-projections/flex",
        "positions": ["NFL_SKILL", "NFL_KICKER", "NFL_D_ST"],
    },
    "MLB": {
        "page": "https://www.fanduel.com/research/mlb/fantasy/dfs-projections",
        "positions": ["MLB_BATTER", "MLB_PITCHER"],
    },
    "NBA": {
        "page": "https://www.fanduel.com/research/nba/fantasy/dfs-projections",
        "positions": ["NBA_PLAYER"],
    },
    "NHL": {
        "page": "https://www.fanduel.com/research/nhl/fantasy/dfs-projections",
        "positions": ["NHL_SKATER", "NHL_GOALIE"],
    },
}

def clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "nat", "<na>"} else text

def norm(value):
    text = clean(value).lower()
    return re.sub(r"[^a-z0-9]+", "", text)

def num(value):
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except Exception:
        return None

def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()
GRAPHQL_QUERY = """
query GetProjections($input: ProjectionsInput!) {
  getProjections(input: $input) {
    __typename
    ... on NflSkill {
      player { numberFireId name position }
      team { numberFireId name abbreviation }
      gameInfo { homeTeam { name abbreviation } awayTeam { name abbreviation } gameTime }
      salary value fantasy
    }
    ... on NflKicker {
      player { numberFireId name position }
      team { numberFireId name abbreviation }
      gameInfo { homeTeam { name abbreviation } awayTeam { name abbreviation } gameTime }
      salary value fantasy
    }
    ... on NflDefenseSt {
      player { numberFireId name position }
      team { numberFireId name abbreviation }
      gameInfo { homeTeam { name abbreviation } awayTeam { name abbreviation } gameTime }
      salary value fantasy
    }
    ... on MlbBatter {
      player { numberFireId name position }
      team { numberFireId name abbreviation }
      gameInfo { homeTeam { name abbreviation } awayTeam { name abbreviation } gameTime }
      salary value fantasy
    }
    ... on MlbPitcher {
      player { numberFireId name position }
      team { numberFireId name abbreviation }
      gameInfo { homeTeam { name abbreviation } awayTeam { name abbreviation } gameTime }
      salary value fantasy
    }
    ... on NbaPlayer {
      player { numberFireId name position }
      team { numberFireId name abbreviation }
      gameInfo { homeTeam { name abbreviation } awayTeam { name abbreviation } gameTime }
      salary value fantasy
    }
    ... on NhlSkater {
      player { numberFireId name position }
      team { numberFireId name abbreviation }
      gameInfo { homeTeam { name abbreviation } awayTeam { name abbreviation } gameTime }
      salary value fantasy
    }
    ... on NhlGoalie {
      player { numberFireId name position }
      team { numberFireId name abbreviation }
      gameInfo { homeTeam { name abbreviation } awayTeam { name abbreviation } gameTime }
      salary value fantasy
    }
  }
}
"""

def fetch_text(url, timeout=12, attempts=2):
    last_error = None
    for attempt in range(max(1, attempts)):
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
            text = response.text
            if text:
                return text
            last_error = ValueError("empty response body")
        except Exception as exc:
            last_error = exc
        if attempt + 1 < max(1, attempts):
            time.sleep(0.75)
    raise last_error or RuntimeError("fetch failed")

def fanduel_metadata(sport, spec):
    text = fetch_text(spec["page"])
    path = RAW / f"fanduel_{sport.lower()}_page.html"
    path.write_text(text)
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        text,
        re.S,
    )
    if not match:
        raise ValueError("FanDuel __NEXT_DATA__ missing")
    payload = json.loads(html.unescape(match.group(1)))
    info = payload["props"]["pageProps"]["projectionInfo"]
    slates = info.get("slatesFilter") or []
    main = next((x for x in slates if clean(x.get("label")).lower() == "main"), None)
    return info, main
def fanduel_rows(sport, slate_id, position_type):
    variables = {
        "input": {
            "type": "DAILY",
            "position": position_type,
            "sport": sport,
            "slateId": str(slate_id),
        }
    }
    response = requests.post(
        FANDUEL_GRAPHQL,
        headers={
            **HEADERS,
            "Content-Type": "application/json",
            "Referer": FD_SPORTS[sport]["page"],
        },
        json={
            "query": GRAPHQL_QUERY,
            "variables": variables,
            "operationName": "GetProjections",
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise ValueError(str(payload["errors"])[:1000])
    raw_path = RAW / f"fanduel_{sport.lower()}_{slate_id}_{position_type.lower()}.json"
    raw_path.write_text(json.dumps(payload, separators=(",", ":")))
    return payload.get("data", {}).get("getProjections") or []

def flatten_fd(sport, slate_id, slate_label, row, projection_type):
    player = row.get("player") or {}
    team = row.get("team") or {}
    game = row.get("gameInfo") or {}
    home = game.get("homeTeam") or {}
    away = game.get("awayTeam") or {}
    salary = num(row.get("salary"))
    fantasy = num(row.get("fantasy"))
    provider_value = num(row.get("value"))
    audit_value = round(fantasy / (salary / 1000.0), 3) if salary and fantasy is not None else None
    return {
        "sport": sport,
        "platform": "FANDUEL",
        "slate_id": str(slate_id),
        "slate_label": slate_label,
        "projection_type": projection_type,
        "source_player_id": clean(player.get("numberFireId")),
        "player": clean(player.get("name")),
        "player_key": norm(player.get("name")),
        "position": clean(player.get("position")),
        "team": clean(team.get("abbreviation")),
        "team_name": clean(team.get("name")),
        "home_team": clean(home.get("abbreviation")),
        "away_team": clean(away.get("abbreviation")),
        "game_time": clean(game.get("gameTime")),
        "salary": int(salary) if salary is not None else None,
        "prior_salary": None,
        "salary_change": None,
        "projected_fantasy_points": fantasy,
        "provider_value_per_1000": provider_value,
        "audit_value_per_1000": audit_value,
        "projection_source": "FANDUEL_RESEARCH",
        "salary_source": "FANDUEL_RESEARCH",
        "retrieved_at": NOW.isoformat(),
    }

def parse_money(text):
    value = clean(text).replace("$", "").replace(",", "").replace("+", "")
    if not value or value == "-":
        return None
    try:
        return int(float(value))
    except Exception:
        return None

def parse_fantasypros_dk():
    text = fetch_text(FP_DK_URL)
    (RAW / "fantasypros_dk_salary_changes.html").write_text(text)
    rows = []
    for tr in re.findall(r"<tr\b[^>]*>(.*?)</tr>", text, re.S | re.I):
        match = re.search(
            r'<a[^>]+class="fp-player-link[^>]*fp-player-name="([^"]+)"[^>]*>.*?</a>'
            r'\s*<small>\(([^)]+)\)</small>',
            tr,
            re.S | re.I,
        )
        if not match:
            continue
        name = html.unescape(match.group(1)).strip()
        team_pos = html.unescape(match.group(2)).strip()
        parsed = re.match(r"(.+?)\s*-\s*(QB|RB|WR|TE|K|DST|D/ST)$", team_pos)
        if not parsed:
            continue
        team, position = parsed.group(1).strip(), parsed.group(2).replace("D/ST", "DST")
        cells = re.findall(r"<td\b([^>]*)>(.*?)</td>", tr, re.S | re.I)
        values = []
        attrs = []
        for attr, body in cells:
            text_value = re.sub(r"<[^>]+>", " ", body)
            text_value = html.unescape(re.sub(r"\s+", " ", text_value)).strip()
            values.append(text_value)
            attrs.append(attr)
        if len(values) < 7:
            continue

        current_salary = parse_money(values[4])
        prior_salary = parse_money(values[5])
        salary_change = parse_money(values[6])
        if current_salary is None:
            continue
        if values[6].startswith("-") and salary_change is not None:
            salary_change = -abs(salary_change)

        kickoff_epoch = None
        kickoff_match = re.search(r'data-sort="(\d{9,12})"', attrs[2]) if len(attrs) > 2 else None
        if kickoff_match:
            try:
                kickoff_epoch = int(kickoff_match.group(1))
            except Exception:
                kickoff_epoch = None

        rows.append({
            "sport": "NFL",
            "platform": "DRAFTKINGS",
            "slate_id": "CURRENT_WEEK_ALL",
            "slate_label": "Current Week All",
            "projection_type": "DK_SALARY",
            "source_player_id": "",
            "player": name,
            "player_key": norm(name),
            "position": position,
            "team": team,
            "team_name": "",
            "home_team": "",
            "away_team": "",
            "game_time": (
                datetime.fromtimestamp(kickoff_epoch, tz=timezone.utc).isoformat()
                if kickoff_epoch else ""
            ),
            "salary": current_salary,
            "prior_salary": prior_salary,
            "salary_change": salary_change,
            "projected_fantasy_points": None,
            "provider_value_per_1000": None,
            "audit_value_per_1000": None,
            "projection_source": "",
            "salary_source": "FANTASYPROS_PUBLIC_DK_SALARY_CHANGES",
            "retrieved_at": NOW.isoformat(),
        })
    return rows

def parse_sharksnip_dk():
    text = fetch_text(SHARKSNIP_DK_URL)
    (RAW / "sharksnip_nfl_dk_main.html").write_text(text)

    meta = {
        "total_rows": 0,
        "projected_rows": 0,
        "draft_group": "",
        "slate_label": "NFL Main",
    }

    title_match = re.search(
        r"DFS projections \((\d+) players\s*·\s*slate\s*([^\)]+)\)",
        text,
        re.I,
    )
    if title_match:
        meta["total_rows"] = int(title_match.group(1))
        meta["slate_label"] = clean(title_match.group(2)) or "NFL Main"

    coverage_match = re.search(
        r"(\d+)\s+of\s+(\d+)\s+projected",
        text,
        re.I,
    )
    if coverage_match:
        meta["projected_rows"] = int(coverage_match.group(1))
        if not meta["total_rows"]:
            meta["total_rows"] = int(coverage_match.group(2))

    group_match = re.search(
        r"draft group\s+(\d+)",
        text,
        re.I,
    )
    if group_match:
        meta["draft_group"] = group_match.group(1)

    table_match = re.search(
        r'<table\b[^>]*\bdata-testid=["\']picks-dfs-table["\'][^>]*>.*?<tbody[^>]*>(.*?)</tbody>',
        text,
        re.S | re.I,
    )
    if not table_match:
        raise ValueError("Shark Snip DFS table missing")

    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table_match.group(1), re.S | re.I):
        values = []
        for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I):
            value = re.sub(r"<[^>]+>", " ", td)
            value = html.unescape(re.sub(r"\s+", " ", value)).strip()
            values.append(value)

        if len(values) < 8:
            continue

        name, position, team, opponent = values[:4]
        salary = parse_money(values[4])
        projection = num(values[5])
        provider_value = num(values[6])
        modelled_own = num(values[7].replace("%", ""))
        if salary is None or not name:
            continue

        audit_value = (
            round(projection / (salary / 1000.0), 3)
            if salary and projection is not None
            else None
        )
        position = position.replace("D/ST", "DST")
        if position == "DST":
            projection_type = "NFL_D_ST"
        elif position == "K":
            projection_type = "NFL_KICKER"
        else:
            projection_type = "NFL_SKILL"

        rows.append({
            "sport": "NFL",
            "platform": "DRAFTKINGS",
            "slate_id": (
                "DK_" + meta["draft_group"]
                if meta["draft_group"]
                else "DK_MAIN"
            ),
            "slate_label": meta["slate_label"],
            "projection_type": projection_type,
            "source_player_id": "",
            "player": name,
            "player_key": norm(name),
            "position": position,
            "team": team,
            "team_name": "",
            "home_team": "",
            "away_team": "",
            "opponent": opponent,
            "game_time": "",
            "salary": salary,
            "prior_salary": None,
            "salary_change": None,
            "projected_fantasy_points": projection,
            "provider_value_per_1000": provider_value,
            "audit_value_per_1000": audit_value,
            "projection_source": "SHARKSNIP_PUBLIC_MODEL",
            "salary_source": "SHARKSNIP_DRAFTKINGS",
            "modelled_ownership_pct": modelled_own,
            "modelled_ownership_source": "SHARKSNIP_HEURISTIC",
            "verified_ownership_pct": None,
            "verified_ownership_source": "",
            "retrieved_at": NOW.isoformat(),
        })

    if meta["total_rows"] and len(rows) != meta["total_rows"]:
        raise ValueError(
            f"Shark Snip row count mismatch: expected {meta['total_rows']} got {len(rows)}"
        )

    if not meta["projected_rows"]:
        meta["projected_rows"] = sum(
            1
            for row in rows
            if row.get("projected_fantasy_points") is not None
        )

    return rows, meta

def percentile(series, ascending=True):
    numeric = pd.to_numeric(series, errors="coerce")
    return (numeric.rank(pct=True, method="average", ascending=ascending) * 100).round(1)

source_rows = []
projection_rows = []
errors = []

for sport, spec in FD_SPORTS.items():
    try:
        info, main = fanduel_metadata(sport, spec)
        if not main:
            source_rows.append({
                "sport": sport,
                "platform": "FANDUEL",
                "source": "FANDUEL_RESEARCH",
                "status": "NO_CURRENT_SLATE",
                "slate_id": "",
                "slate_label": "",
                "rows": 0,
                "projected_ownership_available": False,
                "source_url": spec["page"],
                "generated_at": NOW.isoformat(),
            })
            continue
        sport_count = 0
        for position_type in spec["positions"]:
            raw_rows = fanduel_rows(sport, main["value"], position_type)
            for row in raw_rows:
                projection_rows.append(
                    flatten_fd(
                        sport,
                        main["value"],
                        clean(main.get("label")) or "Main",
                        row,
                        position_type,
                    )
                )
            sport_count += len(raw_rows)
        source_rows.append({
            "sport": sport,
            "platform": "FANDUEL",
            "source": "FANDUEL_RESEARCH",
            "status": "LIVE_MAIN_SLATE",
            "slate_id": str(main["value"]),
            "slate_label": clean(main.get("label")) or "Main",
            "rows": sport_count,
            "projected_ownership_available": False,
            "source_url": spec["page"],
            "generated_at": NOW.isoformat(),
        })
    except Exception as exc:
        errors.append({"source": "FANDUEL_RESEARCH", "sport": sport, "error": repr(exc)})
fp_rows = []
dk_rows = []
dk_projection_meta = {}
dk_salary_crosscheck_matched = 0
dk_salary_crosscheck_exact = 0
dk_primary_source = ""

try:
    fp_rows = parse_fantasypros_dk()
    source_rows.append({
        "sport": "NFL",
        "platform": "DRAFTKINGS",
        "source": "FANTASYPROS_PUBLIC_DK_SALARY_CHANGES",
        "status": "LIVE_CURRENT_WEEK_ENRICHMENT",
        "slate_id": "CURRENT_WEEK_ALL",
        "slate_label": "Current Week All",
        "rows": len(fp_rows),
        "projected_ownership_available": False,
        "modelled_ownership_available": False,
        "source_url": FP_DK_URL,
        "generated_at": NOW.isoformat(),
    })
except Exception as exc:
    errors.append({
        "source": "FANTASYPROS_PUBLIC_DK_SALARY_CHANGES",
        "sport": "NFL",
        "error": repr(exc),
    })

try:
    dk_rows, dk_projection_meta = parse_sharksnip_dk()

    fp_map = {
        clean(row.get("player_key")): row
        for row in fp_rows
        if clean(row.get("player_key"))
    }

    for row in dk_rows:
        prior = fp_map.get(clean(row.get("player_key")))
        if not prior:
            continue
        dk_salary_crosscheck_matched += 1
        if num(prior.get("salary")) == num(row.get("salary")):
            dk_salary_crosscheck_exact += 1
        row["prior_salary"] = prior.get("prior_salary")
        row["salary_change"] = prior.get("salary_change")
        row["salary_change_source"] = "FANTASYPROS_PUBLIC_DK_SALARY_CHANGES"

    projection_rows.extend(dk_rows)
    dk_primary_source = "SHARKSNIP_PUBLIC_MODEL"

    source_rows.append({
        "sport": "NFL",
        "platform": "DRAFTKINGS",
        "source": "SHARKSNIP_PUBLIC_MODEL",
        "status": "LIVE_MAIN_SLATE_WITH_PROJECTIONS",
        "slate_id": (
            "DK_" + clean(dk_projection_meta.get("draft_group"))
            if clean(dk_projection_meta.get("draft_group"))
            else "DK_MAIN"
        ),
        "slate_label": clean(dk_projection_meta.get("slate_label")) or "NFL Main",
        "rows": len(dk_rows),
        "projected_rows": int(dk_projection_meta.get("projected_rows") or 0),
        "projected_ownership_available": False,
        "modelled_ownership_available": True,
        "source_url": SHARKSNIP_DK_URL,
        "generated_at": NOW.isoformat(),
    })
except Exception as exc:
    errors.append({
        "source": "SHARKSNIP_PUBLIC_MODEL",
        "sport": "NFL",
        "error": repr(exc),
    })

    if fp_rows:
        projection_rows.extend(fp_rows)
        dk_rows = fp_rows
        dk_primary_source = "FANTASYPROS_PUBLIC_DK_SALARY_CHANGES"

current = pd.DataFrame(projection_rows)
sources = pd.DataFrame(source_rows)

if not current.empty:
    current = current.drop_duplicates(
        ["sport", "platform", "slate_id", "projection_type", "player_key"],
        keep="last",
    ).reset_index(drop=True)
    current["salary"] = pd.to_numeric(current["salary"], errors="coerce")
    current["prior_salary"] = pd.to_numeric(current["prior_salary"], errors="coerce")
    current["salary_change"] = pd.to_numeric(current["salary_change"], errors="coerce")
    current["projected_fantasy_points"] = pd.to_numeric(
        current["projected_fantasy_points"], errors="coerce"
    )
    current["provider_value_per_1000"] = pd.to_numeric(
        current["provider_value_per_1000"], errors="coerce"
    )
    current["audit_value_per_1000"] = pd.to_numeric(
        current["audit_value_per_1000"], errors="coerce"
    )
    current["salary_percentile"] = (
        current.groupby(["sport", "platform", "slate_id", "position"])["salary"]
        .transform(lambda x: percentile(x))
    )
    current["projection_percentile"] = (
        current.groupby(["sport", "platform", "slate_id", "position"])[
            "projected_fantasy_points"
        ].transform(lambda x: percentile(x))
    )
    current["value_percentile"] = (
        current.groupby(["sport", "platform", "slate_id", "position"])[
            "audit_value_per_1000"
        ].transform(lambda x: percentile(x))
    )
    current["score_is_probability"] = False
    current["automatic_model_adjustment"] = False

availability = read_csv(
    ROOT / "intelligence_warehouse" / "availability" / "AVAILABILITY_CURRENT.csv"
)
return_watch = read_csv(
    ROOT / "intelligence_warehouse" / "availability" / "RETURN_WATCH.csv"
)
roles = read_csv(
    ROOT / "intelligence_warehouse" / "features" / "PLAYER_ROLE_SIGNALS_CURRENT.csv"
)
fantasy_market = read_csv(
    ROOT / "intelligence_warehouse" / "fantasy_market" / "FANTASY_MARKET_CONTEXT_CURRENT.csv"
)
news_context = read_csv(
    ROOT / "intelligence_warehouse" / "news_graph" / "NEWS_PLAYER_CONTEXT_CURRENT.csv"
)
starters = read_csv(
    ROOT / "intelligence_warehouse" / "starters" / "STARTER_STATUS_CURRENT.csv"
)

def lookup_by_key(frame, value_columns):
    result = {}
    if frame.empty or "sport" not in frame.columns or "player_key" not in frame.columns:
        return result
    for row in frame.to_dict("records"):
        key = (clean(row.get("sport")).upper(), clean(row.get("player_key")))
        if not key[0] or not key[1]:
            continue
        result[key] = {column: row.get(column) for column in value_columns}
    return result
availability_map = lookup_by_key(
    availability,
    ["status_normalized", "injury_type", "return_date", "source_disagreement"],
)
return_map = lookup_by_key(
    return_watch,
    ["return_window", "stash_research_signal"],
)
role_map = lookup_by_key(
    roles,
    ["signal", "role_delta", "role_score"],
)
fantasy_map = lookup_by_key(
    fantasy_market,
    ["add_rank_24h", "adds_24h", "drop_rank_24h", "drops_24h"],
)

news_counts = {}
if not news_context.empty:
    for (sport, pkey), frame in news_context.groupby(["sport", "player_key"]):
        news_counts[(clean(sport).upper(), clean(pkey))] = len(frame)

starter_candidates = {}
if not starters.empty and "entity_type" in starters.columns:
    player_starters = starters[starters["entity_type"].astype(str) == "PLAYER"]
    for row in player_starters.to_dict("records"):
        key = (clean(row.get("sport")).upper(), clean(row.get("player_key")))
        if key[0] and key[1]:
            starter_candidates.setdefault(key, []).append(row)

def best_starter_context(sport, pkey, game_time):
    candidates = starter_candidates.get((sport, pkey), [])
    target = pd.to_datetime(game_time, utc=True, errors="coerce")
    if pd.isna(target):
        return {}, None
    best = None
    best_hours = None
    for item in candidates:
        start = pd.to_datetime(item.get("start"), utc=True, errors="coerce")
        if pd.isna(start):
            continue
        hours = abs((start - target).total_seconds()) / 3600.0
        if hours <= 6 and (best_hours is None or hours < best_hours):
            best = item
            best_hours = hours
    return best or {}, best_hours

signal_rows = []
for row in current.to_dict("records") if not current.empty else []:
    key = (clean(row.get("sport")).upper(), clean(row.get("player_key")))
    availability_ctx = availability_map.get(key, {})
    return_ctx = return_map.get(key, {})
    role_ctx = role_map.get(key, {})
    fantasy_ctx = fantasy_map.get(key, {})
    starter_ctx, starter_hours_delta = best_starter_context(
        key[0], key[1], row.get("game_time")
    )
    starter_phase = clean(starter_ctx.get("observation_phase"))
    starter_usable_pregame = bool(starter_ctx) and starter_phase == "PRE_GAME"

    salary_pct = num(row.get("salary_percentile"))
    projection_pct = num(row.get("projection_percentile"))
    value_pct = num(row.get("value_percentile"))
    salary_change = num(row.get("salary_change"))

    if projection_pct is not None:
        if value_pct is not None and value_pct >= 85 and projection_pct >= 40:
            value_signal = "TOP_VALUE"
        elif projection_pct >= 85:
            value_signal = "PREMIUM_PROJECTION"
        elif salary_pct is not None and salary_pct <= 35 and projection_pct >= 65:
            value_signal = "UNDERPRICED_VS_PROJECTION"
        elif salary_pct is not None and salary_pct >= 80 and projection_pct <= 50:
            value_signal = "SALARY_HEAVY_VS_PROJECTION"
        else:
            value_signal = "BALANCED"
    elif row.get("platform") == "DRAFTKINGS":
        if salary_change is None:
            value_signal = "NO_PRIOR_SALARY"
        elif salary_change >= 500:
            value_signal = "SALARY_RISER"
        elif salary_change <= -500:
            value_signal = "SALARY_FALLER"
        else:
            value_signal = "SALARY_STABLE"
    else:
        value_signal = "LIMITED_SAMPLE"
    status = clean(availability_ctx.get("status_normalized"))
    role_signal = clean(role_ctx.get("signal"))
    add_rank = num(fantasy_ctx.get("add_rank_24h"))
    if status in {"OUT", "IR", "PUP", "SUSPENDED"}:
        context_signal = "AVAILABILITY_RISK"
    elif starter_usable_pregame and clean(starter_ctx.get("state")) in {
        "CONFIRMED_OFFICIAL", "CONFIRMED_SOURCE"
    } and value_signal in {"TOP_VALUE", "UNDERPRICED_VS_PROJECTION"}:
        context_signal = "CONFIRMED_STARTER_VALUE"
    elif starter_usable_pregame and clean(starter_ctx.get("state")) == "PROBABLE_OFFICIAL":
        context_signal = "PROBABLE_STARTER_CONTEXT"
    elif starter_usable_pregame:
        context_signal = "CONFIRMED_STARTER_CONTEXT"
    elif value_signal in {"TOP_VALUE", "UNDERPRICED_VS_PROJECTION"} and role_signal == "ROLE_UP":
        context_signal = "VALUE_PLUS_ROLE_UP"
    elif value_signal in {"TOP_VALUE", "UNDERPRICED_VS_PROJECTION"} and add_rank is not None and add_rank <= 25:
        context_signal = "VALUE_PLUS_FANTASY_ADDS"
    elif role_signal == "ROLE_DOWN":
        context_signal = "ROLE_DOWN_CONTEXT"
    elif status:
        context_signal = "AVAILABILITY_CONTEXT"
    else:
        context_signal = "NO_EXTRA_CONTEXT"

    signal_rows.append({
        **row,
        "value_signal": value_signal,
        "context_signal": context_signal,
        "availability_status": availability_ctx.get("status_normalized"),
        "injury_type": availability_ctx.get("injury_type"),
        "return_date": availability_ctx.get("return_date"),
        "availability_source_disagreement": availability_ctx.get("source_disagreement"),
        "return_window": return_ctx.get("return_window"),
        "stash_research_signal": return_ctx.get("stash_research_signal"),
        "role_signal": role_ctx.get("signal"),
        "role_delta": role_ctx.get("role_delta"),
        "role_score": role_ctx.get("role_score"),
        "fantasy_add_rank_24h": fantasy_ctx.get("add_rank_24h"),
        "fantasy_adds_24h": fantasy_ctx.get("adds_24h"),
        "fantasy_drop_rank_24h": fantasy_ctx.get("drop_rank_24h"),
        "news_event_context_count": news_counts.get(key, 0),
        "starter_role": starter_ctx.get("role"),
        "starter_state": starter_ctx.get("state"),
        "starter_order_number": starter_ctx.get("order_number"),
        "starter_source": starter_ctx.get("source"),
        "starter_source_tier": starter_ctx.get("source_tier"),
        "starter_observation_phase": starter_phase or None,
        "starter_game_time_delta_hours": starter_hours_delta,
        "starter_context_usable_pregame": starter_usable_pregame,
        "projected_ownership_pct": None,
        "projected_ownership_source": "",
        "generated_at": NOW.isoformat(),
        "score_is_probability": False,
        "automatic_model_adjustment": False,
    })

signals = pd.DataFrame(signal_rows)
def comparable(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if isinstance(value, float):
        return round(value, 4)
    return clean(value)

timeline = read_csv(TIMELINE_OUT)
timeline_rows = timeline.to_dict("records") if not timeline.empty else []
latest_by_key = {}

for row in timeline_rows:
    identity = (
        clean(row.get("sport")),
        clean(row.get("platform")),
        clean(row.get("slate_id")),
        clean(row.get("projection_type")),
        clean(row.get("player_key")),
    )
    latest_by_key[identity] = row

for row in current.to_dict("records") if not current.empty else []:
    identity = (
        clean(row.get("sport")),
        clean(row.get("platform")),
        clean(row.get("slate_id")),
        clean(row.get("projection_type")),
        clean(row.get("player_key")),
    )
    previous = latest_by_key.get(identity)
    watched = [
        "salary",
        "prior_salary",
        "salary_change",
        "projected_fantasy_points",
        "provider_value_per_1000",
    ]
    changed = previous is None or any(
        comparable(previous.get(column)) != comparable(row.get(column))
        for column in watched
    )
    if not changed:
        continue
    entry = {
        "observed_at": NOW.isoformat(),
        "sport": row.get("sport"),
        "platform": row.get("platform"),
        "slate_id": row.get("slate_id"),
        "slate_label": row.get("slate_label"),
        "projection_type": row.get("projection_type"),
        "player": row.get("player"),
        "player_key": row.get("player_key"),
        "position": row.get("position"),
        "team": row.get("team"),
        "salary": row.get("salary"),
        "prior_salary": row.get("prior_salary"),
        "salary_change": row.get("salary_change"),
        "projected_fantasy_points": row.get("projected_fantasy_points"),
        "provider_value_per_1000": row.get("provider_value_per_1000"),
        "salary_source": row.get("salary_source"),
        "projection_source": row.get("projection_source"),
    }
    timeline_rows.append(entry)
    latest_by_key[identity] = entry

timeline_df = pd.DataFrame(timeline_rows)
current.to_csv(PROJECTIONS_OUT, index=False)
signals.to_csv(VALUE_OUT, index=False)
timeline_df.to_csv(TIMELINE_OUT, index=False)
sources.to_csv(SOURCE_OUT, index=False)

source_status = {}
if not sources.empty:
    for row in sources.to_dict("records"):
        source_status[f"{row['platform']}:{row['sport']}"] = row["status"]

dk_current = (
    current[
        current["platform"].astype(str).eq("DRAFTKINGS")
        & current["sport"].astype(str).eq("NFL")
    ].copy()
    if not current.empty
    else pd.DataFrame()
)
dk_projected_rows = (
    int(
        pd.to_numeric(
            dk_current.get(
                "projected_fantasy_points",
                pd.Series(dtype=float),
            ),
            errors="coerce",
        ).notna().sum()
    )
    if not dk_current.empty
    else 0
)
dk_modelled_ownership_rows = (
    int(
        pd.to_numeric(
            dk_current.get(
                "modelled_ownership_pct",
                pd.Series(dtype=float),
            ),
            errors="coerce",
        ).notna().sum()
    )
    if not dk_current.empty
    else 0
)
dk_projection_coverage_rate = (
    dk_projected_rows / len(dk_current)
    if len(dk_current)
    else 0.0
)

receipt = {
    "generated_at": NOW.isoformat(),
    "current_rows": len(current),
    "value_signal_rows": len(signals),
    "timeline_rows": len(timeline_df),
    "current_rows_by_platform": (
        current["platform"].value_counts().to_dict() if not current.empty else {}
    ),
    "current_rows_by_sport": (
        current["sport"].value_counts().to_dict() if not current.empty else {}
    ),
    "value_signal_counts": (
        signals["value_signal"].value_counts().to_dict() if not signals.empty else {}
    ),
    "context_signal_counts": (
        signals["context_signal"].value_counts().to_dict() if not signals.empty else {}
    ),
    "starter_context_matches": (
        int(signals["starter_role"].notna().sum())
        if not signals.empty and "starter_role" in signals.columns else 0
    ),
    "pregame_starter_context_matches": (
        int(signals["starter_context_usable_pregame"].fillna(False).astype(bool).sum())
        if not signals.empty and "starter_context_usable_pregame" in signals.columns else 0
    ),
    "source_status": source_status,
    "projected_ownership_available": False,
    "modelled_ownership_available": dk_modelled_ownership_rows > 0,
    "modelled_ownership_rows": dk_modelled_ownership_rows,
    "modelled_ownership_source": (
        "SHARKSNIP_HEURISTIC"
        if dk_modelled_ownership_rows
        else ""
    ),
    "ownership_gap": "VERIFIED_PRELOCK_OWNERSHIP_FULL_SLATE",
    "ownership_gap_reason": (
        "No verified observed full-slate pre-lock ownership feed was found. "
        "Shark Snip modelled ownership is stored separately and is not promoted "
        "to verified ownership or automatic model adjustment."
    ),
    "draftkings_projection_available": dk_projected_rows > 0,
    "draftkings_projection_rows": dk_projected_rows,
    "draftkings_slate_rows": int(len(dk_current)),
    "draftkings_projection_coverage_rate": round(
        dk_projection_coverage_rate,
        4,
    ),
    "draftkings_projection_source": dk_primary_source,
    "draftkings_salary_source_is_official_dk": False,
    "draftkings_salary_source": (
        "SHARKSNIP_DRAFTKINGS_CROSSCHECKED_WITH_FANTASYPROS"
        if dk_primary_source == "SHARKSNIP_PUBLIC_MODEL"
        else "FANTASYPROS_PUBLIC_DK_SALARY_CHANGES"
    ),
    "draftkings_salary_crosscheck_matched": dk_salary_crosscheck_matched,
    "draftkings_salary_crosscheck_exact": dk_salary_crosscheck_exact,
    "fanduel_projection_source": "FANDUEL_RESEARCH",
    "cross_platform_scoring_blended": False,
    "score_is_probability": False,
    "automatic_model_adjustment": False,
    "paid_provider_required": False,
    "errors": errors,
}
RECEIPT_OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True))
print("CURRENT ROWS:", len(current))
print("BY PLATFORM:", receipt["current_rows_by_platform"])
print("BY SPORT:", receipt["current_rows_by_sport"])
print("VALUE SIGNALS:", receipt["value_signal_counts"])
print("CONTEXT SIGNALS:", receipt["context_signal_counts"])
print("SOURCE STATUS:", source_status)
print("TIMELINE ROWS:", len(timeline_df))
print("OWNERSHIP:", "EXPLICIT_GAP")
print("ERRORS:", len(errors))
print("RESULT: DFS_INTELLIGENCE_READY")
