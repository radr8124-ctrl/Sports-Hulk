#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
POOL=ROOT/"nfl_live/survivor_pool/derived"
SCHEDULE=ROOT/"nfl_live/derived/NFLVERSE_2026_SCHEDULE.csv"
FIELD=POOL/"WEEK3_OFFICIAL_PICKS.csv"
OUT=POOL/"WEEK3_FINAL_RESULTS.csv"
SUMMARY=POOL/"LATEST_OFFICIAL_POOL.json"
WEEK3_SUMMARY=POOL/"WEEK3_OFFICIAL_SUMMARY.json"

TEAM_LABEL={
"ARI":"CARDINALS","ATL":"FALCONS","BAL":"RAVENS","BUF":"BILLS",
"CAR":"PANTHERS","CHI":"BEARS","CIN":"BENGALS","CLE":"BROWNS",
"DAL":"COWBOYS","DEN":"BRONCOS","DET":"LIONS","GB":"PACKERS",
"HOU":"TEXANS","IND":"COLTS","JAX":"JAGUARS","KC":"CHIEFS",
"LV":"RAIDERS","LAC":"CHARGERS","LA":"RAMS","MIA":"DOLPHINS",
"MIN":"VIKINGS","NE":"PATRIOTS","NO":"SAINTS","NYG":"GIANTS",
"NYJ":"JETS","PHI":"EAGLES","PIT":"STEELERS","SF":"49ERS",
"SEA":"SEAHAWKS","TB":"BUCCANEERS","TEN":"TITANS","WAS":"COMMANDERS",
}

field=pd.read_csv(FIELD,low_memory=False)
sched=pd.read_csv(SCHEDULE,low_memory=False)
week=sched[(sched["season"]==2026)&(sched["week"]==3)&(sched["game_type"]=="REG")].copy()
winners=set()
losers=set()
for _,g in week.iterrows():
    hs=pd.to_numeric(g.get("home_score"),errors="coerce")
    aws=pd.to_numeric(g.get("away_score"),errors="coerce")
    if pd.isna(hs) or pd.isna(aws):
        continue
    if hs>aws:
        win,lose=g["home_team"],g["away_team"]
    elif aws>hs:
        win,lose=g["away_team"],g["home_team"]
    else:
        # Survivor treats ties as losses for both sides.
        losers.add(TEAM_LABEL.get(str(g["home_team"]),str(g["home_team"])))
        losers.add(TEAM_LABEL.get(str(g["away_team"]),str(g["away_team"])))
        continue
    winners.add(TEAM_LABEL.get(str(win),str(win)))
    losers.add(TEAM_LABEL.get(str(lose),str(lose)))

rows=[]
for r in field.to_dict("records"):
    before=str(r.get("week3_status_before_sunday") or "").strip()
    reuse=str(r.get("reuse_flag") or "").strip()
    if reuse.lower()=="nan":
        reuse=""
    p1=str(r.get("week3_pick1_team") or "").strip()
    p2=str(r.get("week3_pick2_team") or "").strip()

    if before=="ELIMINATED_THURSDAY":
        final="ELIMINATED_THURSDAY"
    elif reuse:
        final="ELIMINATED_REUSE"
    elif p1 in winners and p2 in winners:
        final="SURVIVED_WEEK3"
    elif p1 in losers or p2 in losers:
        final="ELIMINATED_WEEK3"
    else:
        final="UNRESOLVED"

    out=dict(r)
    out["week3_final_status"]=final
    out["week3_pick1_result"]=(
        "WIN" if p1 in winners else "LOSS" if p1 in losers else "UNKNOWN"
    )
    out["week3_pick2_result"]=(
        "WIN" if p2 in winners else "LOSS" if p2 in losers else "NOT_APPLICABLE"
        if not p2 else "UNKNOWN"
    )
    rows.append(out)

result=pd.DataFrame(rows)
result.to_csv(OUT,index=False)
counts=result["week3_final_status"].value_counts().astype(int).to_dict()
survivors=int(counts.get("SURVIVED_WEEK3",0))
summary=json.loads(SUMMARY.read_text()) if SUMMARY.exists() else {}
week3_summary=json.loads(WEEK3_SUMMARY.read_text()) if WEEK3_SUMMARY.exists() else {}
summary.update({
    "pool_week":4,
    "previous_pool_week":3,
    "week3_double_pick_week":bool(week3_summary.get("double_pick_week") is True),
    "double_pick_week":None,
    "current_week_required_picks":None,
    "current_week_rule_status":"AWAITING_OFFICIAL_WEEK4_SHEET",
    "week3_finalized":True,
    "week3_finalized_at":datetime.now(timezone.utc).isoformat(),
    "week3_final_status_counts":counts,
    "week3_survivors_final":survivors,
    "week4_entries_entering":survivors,
    "lost_total_through_week3":int(len(result)-survivors),
})
SUMMARY.write_text(json.dumps(summary,indent=2))

print("WEEK3 FINAL:",counts)
print("WEEK4 ENTERING:",survivors)
print("ANNIE:")
print(result[result["entry_name"].eq("ANNIE G")][[
    "entry_key","week3_pick1_team","week3_pick1_result",
    "week3_pick2_team","week3_pick2_result","week3_final_status"
]].to_string(index=False))
print("RESULT: SURVIVOR_POOL_STATUS_READY")
