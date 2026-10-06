#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time

import pandas as pd
import requests

ROOT=Path("/home/ubuntu/sports-hulk")
OUT=ROOT/"intelligence_warehouse"/"mlb_player_history"
RAW=OUT/"raw"
OUT.mkdir(parents=True,exist_ok=True)
RAW.mkdir(parents=True,exist_ok=True)

HISTORY_OUT=OUT/"MLB_PLAYER_GAME_HISTORY.csv"
INDEX_OUT=OUT/"MLB_COMPLETED_GAME_INDEX.csv"
SOURCE_OUT=OUT/"MLB_PLAYER_HISTORY_SOURCE_CATALOG.csv"
FEATURE_OUT=OUT/"MLB_PLAYER_HISTORY_FEATURE_CATALOG.csv"
RECEIPT_OUT=OUT/"MLB_PLAYER_HISTORY_RECEIPT.json"

NOW=datetime.now(timezone.utc)
HEADERS={"User-Agent":"Sports-HULK/1.0 mlb-player-history"}
SEASONS=[2024,2025,2026]
GAME_TYPES={"R","F","D","L","W"}

FIELDS=(
    "teams,away,home,team,id,name,abbreviation,players,person,fullName,"
    "position,battingOrder,stats,batting,pitching,gamesPlayed,runs,doubles,"
    "triples,homeRuns,strikeOuts,baseOnBalls,intentionalWalks,hits,hitByPitch,"
    "atBats,caughtStealing,stolenBases,groundIntoDoublePlay,plateAppearances,"
    "totalBases,rbi,leftOnBase,sacBunts,sacFlies,gamesStarted,numberOfPitches,"
    "inningsPitched,wins,losses,saves,saveOpportunities,holds,blownSaves,"
    "earnedRuns,battersFaced,outs,pitchesThrown,balls,strikes,hitBatsmen,balks,"
    "wildPitches,pickoffs,gamesFinished,inheritedRunners,inheritedRunnersScored,"
    "batters,pitchers"
)
def clean(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    s=str(v).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        return s[:-2]
    return s

def num(v):
    try:
        return float(v)
    except Exception:
        return None

def schedule_index():
    rows=[]
    errors=[]
    for season in SEASONS:
        url=(
            "https://statsapi.mlb.com/api/v1/schedule?"
            f"sportId=1&season={season}&gameTypes=R,F,D,L,W"
        )
        try:
            x=requests.get(url,headers=HEADERS,timeout=30)
            x.raise_for_status()
            d=x.json()
        except Exception as exc:
            errors.append({"season":season,"error":repr(exc)})
            continue
        for day in d.get("dates",[]):
            for g in day.get("games",[]):
                st=g.get("status") or {}
                if st.get("abstractGameState")!="Final":
                    continue
                detailed=clean(st.get("detailedState"))
                if detailed in {"Cancelled","Postponed"}:
                    continue
                gt=clean(g.get("gameType"))
                if gt not in GAME_TYPES:
                    continue
                teams=g.get("teams") or {}
                away=(teams.get("away") or {}).get("team") or {}
                home=(teams.get("home") or {}).get("team") or {}
                rows.append({
                    "game_pk":clean(g.get("gamePk")),
                    "season":season,
                    "official_date":clean(g.get("officialDate")),
                    "game_date":clean(g.get("gameDate")),
                    "game_type":gt,
                    "status":clean(st.get("detailedState") or st.get("abstractGameState")),
                    "away_team_id":clean(away.get("id")),
                    "away_team":clean(away.get("name")),
                    "home_team_id":clean(home.get("id")),
                    "home_team":clean(home.get("name")),
                })
    out=pd.DataFrame(rows).drop_duplicates(["game_pk"]).sort_values(["season","official_date","game_pk"])
    return out,errors

def boxscore(game_pk):
    url=f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
    x=requests.get(
        url,
        params={"fields":FIELDS},
        headers=HEADERS,
        timeout=20,
    )
    x.raise_for_status()
    return x.json()
def extract_game(meta,payload):
    rows=[]
    teams=payload.get("teams") or {}
    for side in ["away","home"]:
        block=teams.get(side) or {}
        team=block.get("team") or {}
        opp_block=teams.get("home" if side=="away" else "away") or {}
        opp=opp_block.get("team") or {}
        players=block.get("players") or {}
        batter_ids={clean(x) for x in block.get("batters") or []}
        pitcher_ids={clean(x) for x in block.get("pitchers") or []}

        for key,p in players.items():
            person=p.get("person") or {}
            pid=clean(person.get("id")) or clean(key).replace("ID","")
            name=clean(person.get("fullName"))
            pos=clean((p.get("position") or {}).get("abbreviation"))
            batting_order=clean(p.get("battingOrder"))
            stats=p.get("stats") or {}

            if pid in batter_ids:
                b=stats.get("batting") or {}
                b_games=num(b.get("gamesPlayed")) or 0.0
                pa=num(b.get("plateAppearances"))
                tb=num(b.get("totalBases")) or 0.0
                bb=num(b.get("baseOnBalls")) or 0.0
                if b_games > 0:
                    rows.append({
                    **meta,
                    "side":side.upper(),
                    "team_id":clean(team.get("id")),
                    "team":clean(team.get("name")),
                    "team_abbr":clean(team.get("abbreviation")),
                    "opponent_id":clean(opp.get("id")),
                    "opponent":clean(opp.get("name")),
                    "opponent_abbr":clean(opp.get("abbreviation")),
                    "player_id":pid,
                    "player":name,
                    "position":pos,
                    "batting_order":batting_order,
                    "group":"HITTING",
                    "role_metric":"total_bases_plus_walks",
                    "role_value":tb+bb,
                    "games_played":b_games,
                    "plate_appearances":pa,
                    "at_bats":num(b.get("atBats")),
                    "hits":num(b.get("hits")),
                    "doubles":num(b.get("doubles")),
                    "triples":num(b.get("triples")),
                    "home_runs":num(b.get("homeRuns")),
                    "walks":num(b.get("baseOnBalls")),
                    "intentional_walks":num(b.get("intentionalWalks")),
                    "hit_by_pitch":num(b.get("hitByPitch")),
                    "strikeouts":num(b.get("strikeOuts")),
                    "total_bases":num(b.get("totalBases")),
                    "runs":num(b.get("runs")),
                    "rbi":num(b.get("rbi")),
                    "stolen_bases":num(b.get("stolenBases")),
                    "caught_stealing":num(b.get("caughtStealing")),
                    "ground_into_double_play":num(b.get("groundIntoDoublePlay")),
                    "sac_bunts":num(b.get("sacBunts")),
                    "sac_flies":num(b.get("sacFlies")),
                })

            if pid in pitcher_ids:
                q=stats.get("pitching") or {}
                q_games=num(q.get("gamesPlayed")) or 0.0
                outs=num(q.get("outs")) or 0.0
                ks=num(q.get("strikeOuts")) or 0.0
                if q_games > 0:
                    rows.append({
                    **meta,
                    "side":side.upper(),
                    "team_id":clean(team.get("id")),
                    "team":clean(team.get("name")),
                    "team_abbr":clean(team.get("abbreviation")),
                    "opponent_id":clean(opp.get("id")),
                    "opponent":clean(opp.get("name")),
                    "opponent_abbr":clean(opp.get("abbreviation")),
                    "player_id":pid,
                    "player":name,
                    "position":pos or "P",
                    "batting_order":batting_order,
                    "group":"PITCHING",
                    "role_metric":"pitching_workload_plus_ks",
                    "role_value":ks+(outs/3.0),
                    "games_played":q_games,
                    "games_started":num(q.get("gamesStarted")),
                    "innings_pitched":clean(q.get("inningsPitched")),
                    "outs":num(q.get("outs")),
                    "pitches":num(q.get("pitchesThrown") or q.get("numberOfPitches")),
                    "batters_faced":num(q.get("battersFaced")),
                    "hits_allowed":num(q.get("hits")),
                    "runs_allowed":num(q.get("runs")),
                    "earned_runs":num(q.get("earnedRuns")),
                    "walks_allowed":num(q.get("baseOnBalls")),
                    "strikeouts":num(q.get("strikeOuts")),
                    "home_runs_allowed":num(q.get("homeRuns")),
                    "hit_batters":num(q.get("hitBatsmen")),
                    "wild_pitches":num(q.get("wildPitches")),
                    "wins":num(q.get("wins")),
                    "losses":num(q.get("losses")),
                    "saves":num(q.get("saves")),
                    "holds":num(q.get("holds")),
                    "blown_saves":num(q.get("blownSaves")),
                    "inherited_runners":num(q.get("inheritedRunners")),
                    "inherited_runners_scored":num(q.get("inheritedRunnersScored")),
                })
    return rows
index, schedule_errors=schedule_index()
index.to_csv(INDEX_OUT,index=False)

if HISTORY_OUT.exists():
    try:
        existing=pd.read_csv(HISTORY_OUT,low_memory=False)
    except Exception:
        existing=pd.DataFrame()
else:
    existing=pd.DataFrame()

done_games=set(existing["game_pk"].astype(str)) if not existing.empty and "game_pk" in existing.columns else set()
pending=index[~index["game_pk"].astype(str).isin(done_games)].copy()

meta_by_game={
    clean(r["game_pk"]):{
        "game_pk":clean(r["game_pk"]),
        "season":int(r["season"]),
        "official_date":clean(r["official_date"]),
        "game_date":clean(r["game_date"]),
        "game_type":clean(r["game_type"]),
        "status":clean(r["status"]),
    }
    for r in index.to_dict("records")
}

fetched_rows=[]
fetch_errors=[]
start=time.time()

def fetch_one(game_pk):
    payload=boxscore(game_pk)
    return game_pk,extract_game(meta_by_game[game_pk],payload)

if len(pending):
    workers=min(32,max(4,len(pending)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(fetch_one,clean(g)):clean(g) for g in pending["game_pk"].astype(str)}
        for i,f in enumerate(as_completed(futures),1):
            game_pk=futures[f]
            try:
                _,rows=f.result()
                fetched_rows.extend(rows)
            except Exception as exc:
                fetch_errors.append({"game_pk":game_pk,"error":repr(exc)})
            if i%250==0:
                print(f"PROGRESS games={i}/{len(futures)} rows={len(fetched_rows)} errors={len(fetch_errors)}",flush=True)

new=pd.DataFrame(fetched_rows)
if existing.empty:
    history=new.copy()
elif new.empty:
    history=existing.copy()
else:
    history=pd.concat([existing,new],ignore_index=True,sort=False)

if not history.empty:
    # Boxscore arrays can contain rostered pitchers/batters who never entered
    # the game. Exclude those zero-appearance placeholders from calibration.
    history=history[pd.to_numeric(history["games_played"],errors="coerce").fillna(0)>0].copy()
    history["game_pk"]=history["game_pk"].astype(str).str.replace(r"\.0$","",regex=True)
    history["player_id"]=history["player_id"].astype(str).str.replace(r"\.0$","",regex=True)
    history["history_identity_key"]=(
        history["game_pk"].astype(str)+"|"+
        history["player_id"].astype(str)+"|"+
        history["group"].astype(str)
    )
    history=(
        history.sort_values(["season","official_date","game_pk","team","group","player"])
        .drop_duplicates(["history_identity_key"],keep="last")
        .reset_index(drop=True)
    )
    history["source"]="MLB_STATSAPI_OFFICIAL_BOXSCORE"
    history["source_tier"]="OFFICIAL_LEAGUE_FEED"
    history["generated_at"]=NOW.isoformat()
    history["automatic_model_adjustment"]=False
    history["score_is_probability"]=False

history.to_csv(HISTORY_OUT,index=False)
sources=pd.DataFrame([
    {
        "source":"MLB StatsAPI schedule",
        "purpose":"authoritative completed regular/postseason game index for 2024-2026",
        "status":"ACTIVE",
    },
    {
        "source":"MLB StatsAPI game boxscore",
        "purpose":"official game-level batter and pitcher outcomes",
        "status":"ACTIVE",
    },
])
sources["generated_at"]=NOW.isoformat()
sources.to_csv(SOURCE_OUT,index=False)

features=pd.DataFrame([
    {
        "feature":"role_value",
        "group":"HITTING",
        "definition":"totalBases + baseOnBalls; exact per-game equivalent of the live MLB hitting role metric.",
    },
    {
        "feature":"role_value",
        "group":"PITCHING",
        "definition":"strikeOuts + outs / 3; exact per-game equivalent of the live MLB pitching role metric.",
    },
    {
        "feature":"history_identity_key",
        "group":"ALL",
        "definition":"game_pk | player_id | group; collision-safe player-game identity.",
    },
    {
        "feature":"official_boxscore_stats",
        "group":"ALL",
        "definition":"raw game-level batting or pitching statistics from the official MLB boxscore endpoint.",
    },
])
features["generated_at"]=NOW.isoformat()
features["automatic_model_adjustment"]=False
features["score_is_probability"]=False
features.to_csv(FEATURE_OUT,index=False)

games_in_history=history["game_pk"].nunique() if not history.empty else 0
hitting_rows=int((history["group"]=="HITTING").sum()) if not history.empty else 0
pitching_rows=int((history["group"]=="PITCHING").sum()) if not history.empty else 0

receipt={
    "generated_at":NOW.isoformat(),
    "indexed_completed_games":int(len(index)),
    "indexed_by_season":index["season"].value_counts().sort_index().astype(int).to_dict(),
    "existing_games_before_run":int(len(done_games)),
    "pending_games_requested":int(len(pending)),
    "new_player_game_rows":int(len(new)),
    "history_rows":int(len(history)),
    "history_games":int(games_in_history),
    "hitting_rows":hitting_rows,
    "pitching_rows":pitching_rows,
    "history_rows_by_season":history["season"].value_counts().sort_index().astype(int).to_dict() if not history.empty else {},
    "schedule_errors":schedule_errors,
    "boxscore_error_count":int(len(fetch_errors)),
    "boxscore_errors":fetch_errors[:100],
    "identity_duplicates":int(history.duplicated(["history_identity_key"]).sum()) if not history.empty else 0,
    "elapsed_seconds":round(time.time()-start,2),
    "automatic_model_adjustment":False,
    "score_is_probability":False,
    "paid_provider_required":False,
    "explicit_gaps":[
        "Spring training, exhibitions, and All-Star games are excluded from the governed history.",
        "The first backfill depends on MLB StatsAPI availability; failed game IDs remain resumable on the next run.",
        "Historical role calibration is not applied automatically by this builder; it only creates the governed player-game source.",
    ],
}
RECEIPT_OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True))

print("INDEXED GAMES:",len(index))
print("PENDING REQUESTED:",len(pending))
print("NEW ROWS:",len(new))
print("HISTORY ROWS:",len(history))
print("HISTORY GAMES:",games_in_history)
print("HITTING:",hitting_rows,"PITCHING:",pitching_rows)
print("BOXSCORE ERRORS:",len(fetch_errors))
print("DUPS:",receipt["identity_duplicates"])
print("ELAPSED:",receipt["elapsed_seconds"])
print("RESULT: MLB_PLAYER_HISTORY_READY")
