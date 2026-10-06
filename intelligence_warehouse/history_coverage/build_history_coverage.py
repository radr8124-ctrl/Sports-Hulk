#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
OUTDIR=ROOT/"intelligence_warehouse"/"history_coverage"
OUT=OUTDIR/"CROSS_SPORT_HISTORY_COVERAGE.csv"
RECEIPT=OUTDIR/"CROSS_SPORT_HISTORY_COVERAGE_RECEIPT.json"
NOW=datetime.now(timezone.utc)

SPECS={
"CFB":{
 "game":"cfb_live/history/CFB_GAME_HISTORY.csv",
 "team":"cfb_live/history/CFB_TEAM_GAME_HISTORY.csv",
 "player":None,
 "special":None,
 "summary":"cfb_live/decision/history/CFB_LEARNING_SUMMARY.json"},
"CBB":{
 "game":"cbb_live/history/CBB_GAME_HISTORY.csv",
 "team":"cbb_live/history/CBB_TEAM_GAME_HISTORY.csv",
 "player":None,
 "special":None,
 "summary":"cbb_live/decision/history/CBB_LEARNING_SUMMARY.json"},
"NBA":{
 "game":"nba_live/history/NBA_GAME_HISTORY.csv",
 "team":"nba_live/history/NBA_TEAM_GAME_HISTORY.csv",
 "player":"nba_live/history/NBA_PLAYER_GAME_HISTORY.csv",
 "special":None,
 "summary":"nba_live/decision/history/NBA_LEARNING_SUMMARY.json"},
"NHL":{
 "game":"nhl_live/history/NHL_GAME_HISTORY.csv",
 "team":"nhl_live/history/NHL_TEAM_GAME_HISTORY.csv",
 "player":"nhl_live/history/NHL_PLAYER_GAME_HISTORY.csv",
 "special":"nhl_live/history/NHL_GOALIE_GAME_HISTORY.csv",
 "summary":"nhl_live/decision/history/NHL_LEARNING_SUMMARY.json"},
"MLB":{
 "game":"baseball_vault/derived/MLB_GAME_MASTER.csv",
 "team":None,
 "player":"intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_LEDGER.csv",
 "special":"intelligence_warehouse/mlb_player_history/MLB_PLAYER_PREGAME_FEATURES.csv",
 "summary":"mlb_live/decision/history/MLB_LEARNING_SUMMARY.json"},
}

def rows(rel):
    if not rel:return 0
    p=ROOT/rel
    if not p.exists():return 0
    try:return len(pd.read_csv(p,low_memory=False))
    except Exception:return 0

def main():
    records=[]
    for sport,s in SPECS.items():
        summary={}
        sp=ROOT/s["summary"]
        if sp.exists():
            try:summary=json.loads(sp.read_text())
            except Exception:summary={}
        game_rows=rows(s["game"])
        team_rows=rows(s["team"])
        player_rows=rows(s["player"])
        special_rows=rows(s["special"])
        ledger=int(summary.get("ledger_rows",0) or 0)
        graded=int(summary.get("graded_rows",0) or 0)
        settled=int(summary.get("settled",0) or 0)
        has_game=game_rows>=100
        player_required=sport in {"NBA","NHL","MLB"}
        has_player=(player_rows>=100) if player_required else True
        historical_ready=has_game and has_player
        if not historical_ready:
            state="HISTORY_GAP"
        elif settled>0:
            state="HISTORY_AND_LIVE_LEARNING"
        elif ledger>0:
            state="HISTORY_READY_CURRENT_SAMPLE_PENDING"
        else:
            state="HISTORY_READY_NO_CURRENT_LEDGER"
        records.append({
            "generated_at":NOW.isoformat(),"sport":sport,
            "game_history_rows":game_rows,"team_game_history_rows":team_rows,
            "player_game_history_rows":player_rows,"special_history_rows":special_rows,
            "recommendation_ledger_rows":ledger,"graded_rows":graded,"settled_rows":settled,
            "player_history_required":player_required,
            "historical_coverage_ready":historical_ready,
            "coverage_state":state,
            "automatic_model_adjustment":bool(summary.get("automatic_model_adjustment",False)),
        })
    out=pd.DataFrame(records)
    out.to_csv(OUT,index=False)
    receipt={
        "generated_at":NOW.isoformat(),
        "sports":len(out),
        "historical_ready":int(out["historical_coverage_ready"].sum()),
        "history_gaps":int((out["coverage_state"]=="HISTORY_GAP").sum()),
        "states":out["coverage_state"].value_counts().to_dict(),
        "automatic_model_adjustment_enabled_sports":int(out["automatic_model_adjustment"].sum()),
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True))
    print(json.dumps(receipt,indent=2,sort_keys=True))
if __name__=="__main__":main()
