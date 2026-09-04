from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json, urllib.parse, urllib.request
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
HISTORY=HERE/"history"
HISTORY.mkdir(parents=True,exist_ok=True)
TZ=ZoneInfo("America/New_York")
BASE="https://statsapi.mlb.com/api/v1/schedule"

def get_json(params):
    url=BASE+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"Sports-HULK-Baseball/1.0"})
    with urllib.request.urlopen(req,timeout=90) as r:
        return json.loads(r.read().decode())

def flatten(d):
    rows=[]
    for day in d.get("dates",[]):
        for g in day.get("games",[]):
            t=g.get("teams",{})
            h=t.get("home",{}); a=t.get("away",{})
            rows.append({
                "gamePk":g.get("gamePk"),
                "officialDate":g.get("officialDate") or day.get("date"),
                "home_team":h.get("team",{}).get("name"),
                "away_team":a.get("team",{}).get("name"),
                "home_score":h.get("score"),
                "away_score":a.get("score"),
                "status":g.get("status",{}).get("detailedState"),
            })
    return rows

def main():
    today=datetime.now(TZ).date()
    start=today-timedelta(days=3)
    end=today
    d=get_json({"sportId":1,"startDate":start.isoformat(),"endDate":end.isoformat(),"hydrate":"team"})
    new=pd.DataFrame(flatten(d))
    out=HISTORY/"MLB_RESULTS_HISTORY.csv"
    if out.exists():
        old=pd.read_csv(out,low_memory=False)
        all_=pd.concat([old,new],ignore_index=True,sort=False)
    else:
        all_=new
    if not all_.empty:
        all_["gamePk"]=pd.to_numeric(all_["gamePk"],errors="coerce").astype("Int64")
        all_=all_.sort_values(["gamePk","officialDate"]).drop_duplicates("gamePk",keep="last")
    all_.to_csv(out,index=False)
    finals=(pd.to_numeric(all_.get("home_score"),errors="coerce").notna() &
            pd.to_numeric(all_.get("away_score"),errors="coerce").notna()).sum() if len(all_) else 0
    print(f"Results history rows: {len(all_):,}")
    print(f"Rows with scores: {int(finals):,}")
    print("SPORTS HULK MLB RESULT REFRESH: DONE")

if __name__=="__main__":
    main()
