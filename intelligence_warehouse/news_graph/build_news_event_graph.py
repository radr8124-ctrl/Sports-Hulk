#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import unicodedata

import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "news_graph"
OUT.mkdir(parents=True, exist_ok=True)

NEWS = ROOT / "sports_content" / "derived" / "SPORTS_NEWS_CURRENT.csv"
FACTS = ROOT / "sports_content" / "derived" / "SPORTS_FACTS_CURRENT.csv"
AVAIL = ROOT / "intelligence_warehouse" / "availability" / "AVAILABILITY_CURRENT.csv"
RETURN = ROOT / "intelligence_warehouse" / "availability" / "RETURN_WATCH.csv"
ROLES = ROOT / "intelligence_warehouse" / "features" / "PLAYER_ROLE_SIGNALS_CURRENT.csv"
FANTASY = ROOT / "intelligence_warehouse" / "fantasy_market" / "FANTASY_MARKET_CONTEXT_CURRENT.csv"

NODE_OUT = OUT / "NEWS_EVENT_NODES_CURRENT.csv"
ENTITY_OUT = OUT / "NEWS_ENTITY_LINKS_CURRENT.csv"
FACT_LINK_OUT = OUT / "NEWS_FACT_LINKS_CURRENT.csv"
PLAYER_CONTEXT_OUT = OUT / "NEWS_PLAYER_CONTEXT_CURRENT.csv"
RECEIPT = OUT / "NEWS_EVENT_GRAPH_RECEIPT.json"

def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

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
    text = unicodedata.normalize("NFKD", clean(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", text.lower())

def stable_id(*parts):
    raw = "|".join(clean(x) for x in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]
def add_player_map(target, frame, player_col="player", team_col="team"):
    if frame.empty or "sport" not in frame.columns:
        return
    for row in frame.to_dict("records"):
        sport = clean(row.get("sport")).upper()
        name = clean(row.get(player_col))
        key = norm(name)
        if not sport or not key or not name:
            continue
        map_key = (sport, key)
        value = {
            "player": name,
            "team": clean(row.get(team_col)),
            "player_key": key,
        }
        if map_key not in target:
            target[map_key] = value

def team_names_from_file(path, sport, columns):
    frame = read_csv(path)
    rows = []
    if frame.empty:
        return rows
    for col in columns:
        if col not in frame.columns:
            continue
        for value in frame[col].dropna().astype(str).unique():
            name = clean(value)
            if name:
                rows.append((sport, norm(name), name))
    return rows

news_df = read_csv(NEWS)
facts_df = read_csv(FACTS)
availability_df = read_csv(AVAIL)
return_df = read_csv(RETURN)
role_df = read_csv(ROLES)
fantasy_df = read_csv(FANTASY)

player_map = {}
add_player_map(player_map, availability_df)
add_player_map(player_map, return_df)
add_player_map(player_map, role_df)
add_player_map(player_map, fantasy_df)

team_map = {}
team_sources = [
    (ROOT / "nfl_live" / "derived" / "NFL_ESPN_CONTEXT.csv", "NFL", ["away_team", "home_team"]),
    (ROOT / "nba_live" / "derived" / "NBA_GAMES_CURRENT.csv", "NBA", ["away_team_name", "home_team_name"]),
    (ROOT / "cfb_live" / "derived" / "CFB_GAMES_CURRENT.csv", "CFB", ["away_team_name", "home_team_name"]),
    (ROOT / "cbb_live" / "derived" / "CBB_GAMES_CURRENT.csv", "CBB", ["away_team_name", "home_team_name"]),
    (ROOT / "baseball_vault" / "latest" / "MLB_SCHEDULE.csv", "MLB", ["away_team", "home_team"]),
]
for path, sport, columns in team_sources:
    for row in team_names_from_file(path, sport, columns):
        team_map[(row[0], row[1])] = row[2]

for row in facts_df.to_dict("records") if not facts_df.empty else []:
    sport = clean(row.get("sport")).upper()
    team = clean(row.get("team"))
    if sport and team:
        team_map.setdefault((sport, norm(team)), team)
LEAGUE_LABELS = {
    "NFL": {"nfl", "nationalfootballleague"},
    "NBA": {"nba", "nationalbasketballassociation"},
    "NHL": {"nhl", "nationalhockeyleague"},
    "MLB": {"mlb", "majorleaguebaseball"},
    "CFB": {"ncaafootball", "collegefootball"},
    "CBB": {"ncaamensbasketball", "menscollegebasketball", "collegebasketball"},
}

generated_at = datetime.now(timezone.utc).isoformat()
node_rows = []
entity_rows = []

for row in news_df.to_dict("records") if not news_df.empty else []:
    sport = clean(row.get("sport")).upper()
    news_id = clean(row.get("news_id")) or stable_id("NEWS", row.get("source_url"), row.get("headline"))
    node_id = f"NEWS:{news_id}"
    node_rows.append({
        "event_node_id": node_id,
        "sport": sport,
        "event_source_type": "NEWS",
        "event_type": clean(row.get("news_type")) or "NEWS",
        "severity": "",
        "title": clean(row.get("headline")),
        "detail": clean(row.get("description")),
        "source": clean(row.get("source")),
        "source_tier": clean(row.get("source_tier")),
        "source_url": clean(row.get("source_url")),
        "published_or_effective_at": clean(row.get("published_at")),
        "verified_status": "",
        "provenance_status": clean(row.get("provenance_status")),
        "provider_type": clean(row.get("provider_type")),
        "source_record_id": clean(row.get("source_id")),
        "game_event_id": "",
        "return_date": "",
        "generated_at": generated_at,
    })

    seen_links = set()
    categories = [clean(x) for x in clean(row.get("categories")).split("|") if clean(x)]
    for category in categories:
        ckey = norm(category)
        if not ckey or ckey == "news":
            continue
        player = player_map.get((sport, ckey))
        team = team_map.get((sport, ckey))
        if player:
            link = ("PLAYER", ckey)
            if link not in seen_links:
                entity_rows.append({
                    "event_node_id": node_id,
                    "sport": sport,
                    "entity_type": "PLAYER",
                    "entity_key": ckey,
                    "entity_name": player["player"],
                    "entity_team": player["team"],
                    "link_basis": "EXACT_CATEGORY_PLAYER",
                    "generated_at": generated_at,
                })
                seen_links.add(link)
        elif team:
            link = ("TEAM", ckey)
            if link not in seen_links:
                entity_rows.append({
                    "event_node_id": node_id,
                    "sport": sport,
                    "entity_type": "TEAM",
                    "entity_key": ckey,
                    "entity_name": team,
                    "entity_team": team,
                    "link_basis": "EXACT_CATEGORY_TEAM",
                    "generated_at": generated_at,
                })
                seen_links.add(link)
        elif ckey in LEAGUE_LABELS.get(sport, set()):
            link = ("LEAGUE", ckey)
            if link not in seen_links:
                entity_rows.append({
                    "event_node_id": node_id,
                    "sport": sport,
                    "entity_type": "LEAGUE",
                    "entity_key": ckey,
                    "entity_name": category,
                    "entity_team": "",
                    "link_basis": "EXACT_CATEGORY_LEAGUE",
                    "generated_at": generated_at,
                })
                seen_links.add(link)
        elif "@" in category:
            link = ("MATCHUP", ckey)
            if link not in seen_links:
                entity_rows.append({
                    "event_node_id": node_id,
                    "sport": sport,
                    "entity_type": "MATCHUP",
                    "entity_key": ckey,
                    "entity_name": category,
                    "entity_team": "",
                    "link_basis": "STRUCTURED_MATCHUP_CATEGORY",
                    "generated_at": generated_at,
                })
                seen_links.add(link)
for row in facts_df.to_dict("records") if not facts_df.empty else []:
    sport = clean(row.get("sport")).upper()
    fact_id = clean(row.get("fact_id")) or stable_id("FACT", row.get("source_url"), row.get("fact_text"))
    node_id = f"FACT:{fact_id}"
    subject = clean(row.get("subject"))
    team = clean(row.get("team"))
    game_event_id = clean(row.get("event_id"))
    node_rows.append({
        "event_node_id": node_id,
        "sport": sport,
        "event_source_type": "FACT",
        "event_type": clean(row.get("fact_type")) or "FACT",
        "severity": clean(row.get("severity")),
        "title": subject,
        "detail": clean(row.get("fact_text")),
        "source": clean(row.get("source")),
        "source_tier": clean(row.get("source_tier")),
        "source_url": clean(row.get("source_url")),
        "published_or_effective_at": clean(row.get("effective_at")),
        "verified_status": clean(row.get("verified_status")),
        "provenance_status": "",
        "provider_type": "",
        "source_record_id": fact_id,
        "game_event_id": game_event_id,
        "return_date": clean(row.get("return_date")),
        "generated_at": generated_at,
    })

    subject_key = norm(subject)
    player = player_map.get((sport, subject_key)) if subject_key else None
    if player:
        entity_rows.append({
            "event_node_id": node_id,
            "sport": sport,
            "entity_type": "PLAYER",
            "entity_key": subject_key,
            "entity_name": player["player"],
            "entity_team": player["team"],
            "link_basis": "EXACT_FACT_SUBJECT_PLAYER",
            "generated_at": generated_at,
        })

    if team:
        entity_rows.append({
            "event_node_id": node_id,
            "sport": sport,
            "entity_type": "TEAM",
            "entity_key": norm(team),
            "entity_name": team,
            "entity_team": team,
            "link_basis": "STRUCTURED_FACT_TEAM",
            "generated_at": generated_at,
        })

    if game_event_id:
        entity_rows.append({
            "event_node_id": node_id,
            "sport": sport,
            "entity_type": "GAME",
            "entity_key": game_event_id,
            "entity_name": game_event_id,
            "entity_team": "",
            "link_basis": "STRUCTURED_FACT_EVENT_ID",
            "generated_at": generated_at,
        })

nodes_df = pd.DataFrame(node_rows)
entities_df = pd.DataFrame(entity_rows)
if not entities_df.empty:
    entities_df = entities_df.drop_duplicates(
        ["event_node_id", "entity_type", "entity_key", "link_basis"]
    ).reset_index(drop=True)

news_url_map = {}
for row in news_df.to_dict("records") if not news_df.empty else []:
    url = clean(row.get("source_url"))
    nid = clean(row.get("news_id"))
    if url and nid:
        news_url_map.setdefault(url, []).append(f"NEWS:{nid}")

fact_link_rows = []
for row in facts_df.to_dict("records") if not facts_df.empty else []:
    url = clean(row.get("source_url"))
    fid = clean(row.get("fact_id"))
    if not url or not fid:
        continue
    for news_node in news_url_map.get(url, []):
        fact_link_rows.append({
            "fact_event_node_id": f"FACT:{fid}",
            "news_event_node_id": news_node,
            "sport": clean(row.get("sport")).upper(),
            "link_basis": "EXACT_SOURCE_URL",
            "generated_at": generated_at,
        })
fact_links_df = pd.DataFrame(fact_link_rows)
def row_lookup(frame, key_col):
    out = {}
    if frame.empty or "sport" not in frame.columns or key_col not in frame.columns:
        return out
    for row in frame.to_dict("records"):
        sport = clean(row.get("sport")).upper()
        key = norm(row.get(key_col)) if key_col != "player_key" else clean(row.get(key_col))
        if sport and key:
            out[(sport, key)] = row
    return out

availability_lookup = row_lookup(availability_df, "player_key")
return_lookup = row_lookup(return_df, "player_key")
role_lookup = row_lookup(role_df, "player_key")
fantasy_lookup = row_lookup(fantasy_df, "player_key")

player_context_rows = []
player_links = (
    entities_df[entities_df["entity_type"] == "PLAYER"]
    if not entities_df.empty else pd.DataFrame()
)
for link in player_links.to_dict("records") if not player_links.empty else []:
    sport = clean(link.get("sport")).upper()
    pkey = clean(link.get("entity_key"))
    availability = availability_lookup.get((sport, pkey), {})
    return_state = return_lookup.get((sport, pkey), {})
    role = role_lookup.get((sport, pkey), {})
    fantasy = fantasy_lookup.get((sport, pkey), {})

    stash = str(return_state.get("stash_research_signal")).strip().lower() in {"true", "1", "yes"}
    add_rank = fantasy.get("add_rank_24h")
    has_add = False
    try:
        has_add = pd.notna(add_rank) and float(add_rank) > 0
    except Exception:
        has_add = False

    if stash:
        combined = "EVENT_PLUS_RETURN_WATCH"
    elif clean(role.get("signal")) == "ROLE_UP":
        combined = "EVENT_PLUS_ROLE_UP"
    elif has_add:
        combined = "EVENT_PLUS_FANTASY_ADD_ACTIVITY"
    elif availability:
        combined = "EVENT_PLUS_AVAILABILITY_CONTEXT"
    else:
        combined = "EVENT_PLAYER_LINK_ONLY"

    player_context_rows.append({
        "event_node_id": link["event_node_id"],
        "sport": sport,
        "player_key": pkey,
        "player": link["entity_name"],
        "team": link.get("entity_team", ""),
        "availability_status": availability.get("status_normalized"),
        "injury_type": availability.get("injury_type"),
        "return_date": availability.get("return_date"),
        "source_disagreement": availability.get("source_disagreement"),
        "return_window": return_state.get("return_window"),
        "stash_research_signal": return_state.get("stash_research_signal"),
        "role_signal": role.get("signal"),
        "role_delta": role.get("role_delta"),
        "fantasy_add_rank_24h": fantasy.get("add_rank_24h"),
        "fantasy_adds_24h": fantasy.get("adds_24h"),
        "fantasy_drop_rank_24h": fantasy.get("drop_rank_24h"),
        "combined_research_context": combined,
        "generated_at": generated_at,
        "automatic_model_adjustment": False,
    })

player_context_df = pd.DataFrame(player_context_rows)
nodes_df.to_csv(NODE_OUT, index=False)
entities_df.to_csv(ENTITY_OUT, index=False)
fact_links_df.to_csv(FACT_LINK_OUT, index=False)
player_context_df.to_csv(PLAYER_CONTEXT_OUT, index=False)

receipt = {
    "generated_at": generated_at,
    "news_rows": len(news_df),
    "fact_rows": len(facts_df),
    "event_nodes": len(nodes_df),
    "entity_links": len(entities_df),
    "fact_to_news_links": len(fact_links_df),
    "player_context_rows": len(player_context_df),
    "event_nodes_by_source_type": nodes_df["event_source_type"].value_counts().to_dict() if not nodes_df.empty else {},
    "event_types": nodes_df["event_type"].value_counts().head(30).to_dict() if not nodes_df.empty else {},
    "entity_types": entities_df["entity_type"].value_counts().to_dict() if not entities_df.empty else {},
    "player_context_counts": player_context_df["combined_research_context"].value_counts().to_dict() if not player_context_df.empty else {},
    "high_precision_entity_linking": True,
    "unknown_categories_not_forced_into_entities": True,
    "fact_news_link_requires_exact_source_url": True,
    "headline_text_entity_guessing_used": False,
    "source_provenance_preserved": True,
    "score_is_probability": False,
    "automatic_model_adjustment": False,
    "paid_provider_required": False,
}
RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True))

print("EVENT NODES:", len(nodes_df))
print("ENTITY LINKS:", len(entities_df), receipt["entity_types"])
print("FACT->NEWS LINKS:", len(fact_links_df))
print("PLAYER CONTEXT:", len(player_context_df), receipt["player_context_counts"])
print("RESULT: NEWS_EVENT_GRAPH_READY")
