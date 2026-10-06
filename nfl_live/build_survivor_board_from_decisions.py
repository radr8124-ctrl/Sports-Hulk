#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
SRC=ROOT/"nfl_live/decision/NFL_GAME_FINALISTS.csv"
OUT=ROOT/"nfl_live/derived"

ABBR_TO_NAME={
"ARI":"Arizona Cardinals","ATL":"Atlanta Falcons","BAL":"Baltimore Ravens",
"BUF":"Buffalo Bills","CAR":"Carolina Panthers","CHI":"Chicago Bears",
"CIN":"Cincinnati Bengals","CLE":"Cleveland Browns","DAL":"Dallas Cowboys",
"DEN":"Denver Broncos","DET":"Detroit Lions","GB":"Green Bay Packers",
"HOU":"Houston Texans","IND":"Indianapolis Colts","JAX":"Jacksonville Jaguars",
"KC":"Kansas City Chiefs","LV":"Las Vegas Raiders","LAC":"Los Angeles Chargers",
"LAR":"Los Angeles Rams","LA":"Los Angeles Rams","MIA":"Miami Dolphins",
"MIN":"Minnesota Vikings","NE":"New England Patriots","NO":"New Orleans Saints",
"NYG":"New York Giants","NYJ":"New York Jets","PHI":"Philadelphia Eagles",
"PIT":"Pittsburgh Steelers","SF":"San Francisco 49ers","SEA":"Seattle Seahawks",
"TB":"Tampa Bay Buccaneers","TEN":"Tennessee Titans","WAS":"Washington Commanders",
}

df=pd.read_csv(SRC,low_memory=False)
ml=df[df["market"].astype(str).eq("MONEYLINE")].copy()
sp=df[df["market"].astype(str).eq("SPREAD")].copy()

spread_lookup={}
for _,r in sp.iterrows():
    spread_lookup[str(r.get("game_key"))]=r.to_dict()

rows=[]
for _,r in ml.iterrows():
    game_key=str(r.get("game_key") or "")
    if "@" not in game_key:
        continue
    away_abbr,home_abbr=game_key.split("@",1)
    away=ABBR_TO_NAME.get(away_abbr,away_abbr)
    home=ABBR_TO_NAME.get(home_abbr,home_abbr)
    survivor=str(r.get("selection") or "")
    prob=pd.to_numeric(r.get("market_implied_safety"),errors="coerce")
    prob=(float(prob)/100.0) if pd.notna(prob) else None
    spread_row=spread_lookup.get(game_key,{})
    spread_line=pd.to_numeric(spread_row.get("line"),errors="coerce")
    if spread_row and str(spread_row.get("selection"))!=survivor:
        spread_line=-spread_line if pd.notna(spread_line) else spread_line

    if prob is None:
        grade="NO GRADE"
    elif prob>=0.80:
        grade="A+"
    elif prob>=0.75:
        grade="A"
    elif prob>=0.70:
        grade="B+"
    elif prob>=0.65:
        grade="B"
    elif prob>=0.60:
        grade="C"
    else:
        grade="AVOID"

    rows.append({
        "start":r.get("start"),
        "away_team":away,
        "home_team":home,
        "survivor_team":survivor,
        "survivor_win_prob":prob,
        "survivor_spread":spread_line,
        "survivor_grade":grade,
        "sportsbooks":r.get("sw_books"),
        "market_source":"NFL_GAME_FINALISTS",
        "market_status":"GOVERNED_CURRENT",
        "collected_at":datetime.now(timezone.utc).isoformat(),
        "game_key":game_key,
        "market_data_quality":r.get("market_data_quality"),
        "provider_agreement":r.get("provider_agreement"),
        "game_decision":r.get("decision"),
        "hulk_market_score":r.get("hulk_market_score"),
    })

board=pd.DataFrame(rows)
board["start"]=pd.to_datetime(board["start"],errors="coerce",utc=True)
board=board.sort_values(["survivor_win_prob","start"],ascending=[False,True])

board.to_csv(OUT/"NFL_SURVIVOR_BOARD.csv",index=False)
board.to_parquet(OUT/"NFL_SURVIVOR_BOARD.parquet",index=False)

print("SURVIVOR BOARD ROWS:",len(board))
print(board[[
    "survivor_team","away_team","home_team","survivor_win_prob",
    "survivor_spread","survivor_grade","sportsbooks","market_data_quality"
]].head(16).to_string(index=False))
print("RESULT: GOVERNED_SURVIVOR_BOARD_READY")
