#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import re
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
ENTRIES=ROOT/"nfl_live/derived/SURVIVOR_ENTRIES.json"
SCHEDULE=ROOT/"nfl_live/derived/NFLVERSE_2026_SCHEDULE.csv"

TEAM_TO_ABBR={
"Arizona Cardinals":"ARI","Atlanta Falcons":"ATL","Baltimore Ravens":"BAL",
"Buffalo Bills":"BUF","Carolina Panthers":"CAR","Chicago Bears":"CHI",
"Cincinnati Bengals":"CIN","Cleveland Browns":"CLE","Dallas Cowboys":"DAL",
"Denver Broncos":"DEN","Detroit Lions":"DET","Green Bay Packers":"GB",
"Houston Texans":"HOU","Indianapolis Colts":"IND","Jacksonville Jaguars":"JAX",
"Kansas City Chiefs":"KC","Las Vegas Raiders":"LV","Los Angeles Chargers":"LAC",
"Los Angeles Rams":"LA","Miami Dolphins":"MIA","Minnesota Vikings":"MIN",
"New England Patriots":"NE","New Orleans Saints":"NO","New York Giants":"NYG",
"New York Jets":"NYJ","Philadelphia Eagles":"PHI","Pittsburgh Steelers":"PIT",
"San Francisco 49ers":"SF","Seattle Seahawks":"SEA","Tampa Bay Buccaneers":"TB",
"Tennessee Titans":"TEN","Washington Commanders":"WAS",
}

def game_for(team_name,week,schedule):
    abbr=TEAM_TO_ABBR.get(str(team_name))
    if not abbr:
        return None
    hit=schedule[
        (schedule["week"]==week)
        & (schedule["game_type"]=="REG")
        & ((schedule["home_team"]==abbr)|(schedule["away_team"]==abbr))
    ]
    if hit.empty:
        return None
    return hit.iloc[-1]

def leg_result(team_name,week,schedule):
    g=game_for(team_name,week,schedule)
    if g is None:
        return "PENDING","Game not found"
    hs=pd.to_numeric(g.get("home_score"),errors="coerce")
    aws=pd.to_numeric(g.get("away_score"),errors="coerce")
    if pd.isna(hs) or pd.isna(aws):
        return "PENDING","Game not final"
    abbr=TEAM_TO_ABBR.get(str(team_name))
    if hs==aws:
        result="LOSS"
    elif g["home_team"]==abbr:
        result="WIN" if hs>aws else "LOSS"
    else:
        result="WIN" if aws>hs else "LOSS"
    detail=f"FINAL: {g['away_team']} {int(aws)} - {g['home_team']} {int(hs)}"
    return result,detail

data=json.loads(ENTRIES.read_text())
schedule=pd.read_csv(SCHEDULE,low_memory=False)
schedule=schedule[schedule["season"]==2026].copy()
now=datetime.now(timezone.utc).isoformat()
updated=0

for entry_name,e in (data.get("entries") or {}).items():
    week_keys=[]
    for key in e.keys():
        m=re.fullmatch(r"week_(\d+)",str(key))
        if m:
            week_keys.append((int(m.group(1)),key))
    week_keys.sort()

    latest_resolved_week=0
    for week,key in week_keys:
        block=e.get(key) or {}
        picks=block.get("picks") or []
        if not picks:
            continue

        required=int(block.get("required_picks") or len(picks) or 1)
        results=[]
        used=e.setdefault("used_teams",[])

        for leg in picks:
            team=leg.get("team")
            result,detail=leg_result(team,week,schedule)

            # A current-week pick is not a burned/used team until its
            # game is resolved. Keeping pending picks out of used_teams
            # prevents the saved choice from disappearing from the
            # current strategy board and from inflating the used count.
            if (
                team
                and result in {"WIN", "LOSS"}
                and team not in used
            ):
                used.append(team)

            if leg.get("result")!=result or leg.get("game_status")!=detail:
                updated+=1
            leg["result"]=result
            leg["game_status"]=detail
            results.append(result)

        if "LOSS" in results:
            block["entry_result"]="LOSS"
            e["status"]="ELIMINATED"
            e["current_pick_status"]="ELIMINATED"
            latest_resolved_week=max(latest_resolved_week,week)
        elif len(results)>=required and all(x=="WIN" for x in results[:required]):
            block["entry_result"]="WIN"
            if str(e.get("status","")).upper()!="ELIMINATED":
                e["status"]="ALIVE"
            latest_resolved_week=max(latest_resolved_week,week)
        else:
            block["entry_result"]="PENDING"

        block["last_checked_at"]=now
        e[key]=block

    if str(e.get("status","")).upper()=="ALIVE" and latest_resolved_week:
        next_week=latest_resolved_week+1
        if int(e.get("current_week") or 0) <= latest_resolved_week:
            e["current_week"]=next_week
            e["current_picks"]=[]
            e["current_pick"]=None
            e["backup_pick"]=None
            e["current_pick_status"]="OPEN"
        next_key=f"week_{next_week}"
        if next_key not in e:
            e[next_key]={
                "required_picks":None,
                "rule_status":"AWAITING_OFFICIAL_POOL_SHEET",
                "picks":[],
                "entry_result":"OPEN",
                "opened_at":now,
            }

data["last_result_refresh_at"]=now
ENTRIES.write_text(json.dumps(data,indent=2))

print("UPDATED LEGS:",updated)
for name in ["ANNIE G 01","ANNIE G 03"]:
    e=(data.get("entries") or {}).get(name,{})
    print(
        name,
        "status=",e.get("status"),
        "current_week=",e.get("current_week"),
        "pick_status=",e.get("current_pick_status"),
    )
print("RESULT: SURVIVOR_ENTRY_RESULTS_READY")
