#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import re
import requests
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
DEC=ROOT/"nfl_live"/"decision"
RAW=DEC/"raw"
ALIAS=ROOT/"nfl_live"/"identity"/"team_aliases.json"
NOW=datetime.now(timezone.utc)
STAMP=NOW.strftime("%Y%m%dT%H%M%SZ")
URL="https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"

def clean(v):
    return re.sub(r"\s+"," ",str(v or "").strip())

def norm(v):
    s=clean(v).lower()
    s=re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?","",s)
    return re.sub(r"[^a-z0-9]+","",s)

aliases=json.loads(ALIAS.read_text())
team_map={}
for abbr,vals in aliases.items():
    team_map[norm(abbr)]=abbr
    for v in vals:
        team_map[norm(v)]=abbr

def canon(v):
    k=norm(v)
    return team_map.get(k,clean(v).upper())

r=requests.get(URL,timeout=20,headers={"User-Agent":"Sports-HULK/1.0"})
if r.status_code!=200:
    raise SystemExit(f"ESPN injury HTTP {r.status_code}")

payload=r.json()
rows=[]
for group in payload.get("injuries",[]) if isinstance(payload,dict) else []:
    team_obj=group.get("team",{}) if isinstance(group,dict) else {}
    team=canon(
        team_obj.get("abbreviation")
        or team_obj.get("displayName")
        or team_obj.get("name")
    )
    entries=group.get("injuries",[]) if isinstance(group,dict) else []
    for item in entries:
        if not isinstance(item,dict):
            continue
        athlete=item.get("athlete",{}) or {}
        pos=athlete.get("position",{}) or {}
        details=item.get("details",{}) or {}
        typ=item.get("type",{}) or {}
        status=item.get("status")
        if not status and isinstance(typ,dict):
            status=typ.get("description")
        if not status and isinstance(details,dict):
            status=details.get("status")
        name=athlete.get("fullName") or athlete.get("displayName")
        rows.append({
            "player":name,
            "player_key":norm(name),
            "team":team,
            "position":pos.get("abbreviation") if isinstance(pos,dict) else "",
            "status":clean(status),
            "injury_type":clean(
                details.get("type") if isinstance(details,dict) else ""
            ),
            "detail":clean(
                item.get("shortComment") or item.get("longComment")
            ),
        })

df=pd.DataFrame(rows,columns=[
    "player","player_key","team","position",
    "status","injury_type","detail"
])
RAW.mkdir(parents=True,exist_ok=True)
raw_path=RAW/f"ESPN_NFL_INJURIES_{STAMP}.json"
raw_path.write_text(json.dumps(payload,indent=2,default=str))
df.to_csv(DEC/"NFL_ESPN_INJURIES.csv",index=False)

receipt={
    "generated_at":NOW.isoformat(),
    "espn_injury_http":r.status_code,
    "espn_injury_rows":int(len(df)),
    "raw_path":str(raw_path.relative_to(ROOT)),
    "sportsbook_api_called":False,
    "recommendation_generated":False,
}
(DEC/"NFL_FREE_STATUS_RECEIPT.json").write_text(
    json.dumps(receipt,indent=2,sort_keys=True)
)
print("ESPN INJURY HTTP:",r.status_code)
print("ESPN INJURY ROWS:",len(df))
print("RESULT: NFL_FREE_STATUS_READY")
