#!/usr/bin/env python3
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timezone
import json
import math
import time
import pandas as pd
import requests

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "cbb_efficiency"
TEAM_SOURCE = ROOT / "cbb_live/derived/CBB_ELO_CURRENT.csv"
GAME_HISTORY = ROOT / "cbb_live/history/CBB_GAME_HISTORY.csv"
TEAM_HISTORY = ROOT / "cbb_live/history/CBB_TEAM_GAME_HISTORY.csv"

RAW_PRIOR = OUT / "CBB_PRIOR_SEASON_TEAM_STATS_RAW.csv"
BASELINE = OUT / "CBB_PRIOR_SEASON_EFFICIENCY.csv"
GAME_STATS = OUT / "CBB_POSSESSION_GAME_HISTORY.csv"
CURRENT = OUT / "CBB_EFFICIENCY_CURRENT.csv"
CATALOG = OUT / "CBB_EFFICIENCY_DATA_CATALOG.csv"
RECEIPT = OUT / "CBB_EFFICIENCY_RECEIPT.json"

PRIOR_SEASON = 2026
CURRENT_SEASON = 2027
NOW = datetime.now(timezone.utc).isoformat()

HEADERS = {
    "User-Agent":"Sports-HULK/1.0",
    "Accept":"application/json",
}

STAT_NAMES = [
    "gamesPlayed","points","fieldGoalsMade","fieldGoalsAttempted",
    "threePointFieldGoalsMade","threePointFieldGoalsAttempted",
    "freeThrowsMade","freeThrowsAttempted","offensiveRebounds",
    "defensiveRebounds","totalRebounds","assists","turnovers",
    "totalTurnovers","estimatedPossessions","avgEstimatedPossessions",
    "pointsPerEstimatedPossessions","offensiveReboundPct",
    "shootingEfficiency","scoringEfficiency",
]

def read(path):
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()

def number(v):
    try:
        x=float(v)
        return None if math.isnan(x) else x
    except Exception:
        return None

def append_csv(path, rows):
    if not rows:
        return
    d = pd.DataFrame(rows)
    exists = path.exists() and path.stat().st_size > 0
    d.to_csv(path,index=False,mode="a" if exists else "w",header=not exists)

def parse_stats(payload):
    vals = {}
    for cat in payload.get("splits",{}).get("categories",[]):
        for stat in cat.get("stats",[]):
            name = stat.get("name")
            if name in STAT_NAMES:
                vals[name] = number(stat.get("value"))
    return vals

def get_json(url, timeout=10):
    r = requests.get(url,headers=HEADERS,timeout=timeout)
    if r.status_code != 200:
        return None, r.status_code
    try:
        return r.json(), r.status_code
    except Exception:
        return None, r.status_code

def prior_url(team_id):
    return (
        "https://sports.core.api.espn.com/v2/sports/basketball/"
        f"leagues/mens-college-basketball/seasons/{PRIOR_SEASON}/"
        f"types/0/teams/{int(team_id)}/statistics"
    )

def game_url(event_id, team_id):
    return (
        "https://sports.core.api.espn.com/v2/sports/basketball/"
        "leagues/mens-college-basketball/"
        f"events/{int(event_id)}/competitions/{int(event_id)}/"
        f"competitors/{int(team_id)}/statistics"
    )

def fetch_prior(row):
    payload, status = get_json(prior_url(row.team_id))
    vals = parse_stats(payload or {})
    return {
        "team_id":int(row.team_id),
        "team":row.team,
        "team_name":row.team_name,
        "season":PRIOR_SEASON,
        "http_status":status,
        "retrieved_at":NOW,
        **vals,
    }

def refresh_prior_raw():
    teams = read(TEAM_SOURCE)
    if teams.empty:
        return 0
    existing = read(RAW_PRIOR)
    done = set(
        pd.to_numeric(existing.get("team_id"),errors="coerce")
        .dropna().astype(int).tolist()
    ) if not existing.empty else set()
    todo = teams[~teams.team_id.astype(int).isin(done)].copy()
    if todo.empty:
        return 0
    rows = []
    fetched = 0
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = [ex.submit(fetch_prior,r) for _,r in todo.iterrows()]
        for fut in as_completed(futs):
            try:
                row = fut.result()
            except Exception:
                continue
            rows.append(row)
            fetched += 1
            if len(rows) >= 50:
                append_csv(RAW_PRIOR,rows)
                rows = []
    append_csv(RAW_PRIOR,rows)
    return fetched

def safe_div(a,b):
    a,b=number(a),number(b)
    if a is None or b in {None,0}:
        return None
    return a/b

def efficiency_fields(r, points_allowed=None):
    poss = number(r.get("estimatedPossessions"))
    pts = number(r.get("points"))
    fgm = number(r.get("fieldGoalsMade"))
    fga = number(r.get("fieldGoalsAttempted"))
    tpm = number(r.get("threePointFieldGoalsMade"))
    tpa = number(r.get("threePointFieldGoalsAttempted"))
    fta = number(r.get("freeThrowsAttempted"))
    tov = number(r.get("totalTurnovers")) or number(r.get("turnovers"))
    return {
        "off_rating":safe_div(pts,poss)*100 if safe_div(pts,poss) is not None else None,
        "def_rating":safe_div(points_allowed,poss)*100 if safe_div(points_allowed,poss) is not None else None,
        "efg_pct":safe_div((fgm or 0)+0.5*(tpm or 0),fga),
        "turnover_pct":safe_div(tov,poss),
        "off_rebound_pct":number(r.get("offensiveReboundPct")),
        "free_throw_rate":safe_div(fta,fga),
        "three_point_attempt_rate":safe_div(tpa,fga),
        "tempo_possessions_per_game":number(r.get("avgEstimatedPossessions")),
    }

def prior_points_allowed():
    d = read(TEAM_HISTORY)
    if d.empty:
        return {}
    d = d[pd.to_numeric(d["season"],errors="coerce").eq(PRIOR_SEASON)].copy()
    d["opponent_score"] = pd.to_numeric(d["opponent_score"],errors="coerce")
    g = d.groupby("team_id",as_index=False).agg(
        points_allowed=("opponent_score","sum"),
        history_games=("event_id","nunique"),
    )
    return {
        int(r.team_id):(number(r.points_allowed),int(r.history_games))
        for _,r in g.iterrows()
    }

def build_prior_baseline():
    raw = read(RAW_PRIOR)
    if raw.empty:
        return pd.DataFrame()
    pa = prior_points_allowed()
    rows = []
    for _,r in raw.iterrows():
        tid = int(r.team_id)
        points_allowed, hist_games = pa.get(tid,(None,0))
        metrics = efficiency_fields(r,points_allowed)
        off = metrics["off_rating"]
        deff = metrics["def_rating"]
        rows.append({
            "team_id":tid,
            "team":r.get("team"),
            "team_name":r.get("team_name"),
            "season":PRIOR_SEASON,
            "games":int(number(r.get("gamesPlayed")) or hist_games),
            "points":number(r.get("points")),
            "points_allowed":points_allowed,
            "estimated_possessions":number(r.get("estimatedPossessions")),
            **metrics,
            "net_rating":(
                off-deff if off is not None and deff is not None else None
            ),
            "shooting_efficiency":number(r.get("shootingEfficiency")),
            "scoring_efficiency":number(r.get("scoringEfficiency")),
            "source":"ESPN_CORE_SEASON_STATS+HULK_SCORE_HISTORY",
            "baseline_is_model_probability":False,
        })
    d = pd.DataFrame(rows)
    if not d.empty:
        d["net_rating_percentile"] = (
            d["net_rating"].rank(pct=True,method="average")*100
        )
        d["sample_status"] = d["games"].apply(
            lambda x:"FULL_BASELINE" if x >= 10 else "LIMITED_SAMPLE"
        )
        d["generated_at"] = NOW
    d.to_csv(BASELINE,index=False)
    return d

def existing_game_keys():
    d = read(GAME_STATS)
    if d.empty:
        return set()
    return set(
        zip(
            pd.to_numeric(d["event_id"],errors="coerce").fillna(-1).astype(int),
            pd.to_numeric(d["team_id"],errors="coerce").fillna(-1).astype(int),
        )
    )

def fetch_game_team(event_id, team_id, team, team_name, opponent_id,
                    opponent, opponent_name, home_away, game_date,
                    score, opponent_score):
    payload, status = get_json(game_url(event_id,team_id))
    vals = parse_stats(payload or {})
    return {
        "event_id":int(event_id),
        "game_date":game_date,
        "season":CURRENT_SEASON,
        "team_id":int(team_id),
        "team":team,
        "team_name":team_name,
        "opponent_id":int(opponent_id),
        "opponent":opponent,
        "opponent_name":opponent_name,
        "home_away":home_away,
        "score":number(score),
        "opponent_score":number(opponent_score),
        "http_status":status,
        "retrieved_at":NOW,
        **vals,
    }

def refresh_current_game_stats():
    hist = read(TEAM_HISTORY)
    if hist.empty:
        return 0
    hist = hist[
        pd.to_numeric(hist["season"],errors="coerce").eq(CURRENT_SEASON)
    ].copy()
    hist = hist[
        pd.to_numeric(hist["score"],errors="coerce").notna() &
        pd.to_numeric(hist["opponent_score"],errors="coerce").notna()
    ]
    done = existing_game_keys()
    todo = []
    for _,r in hist.iterrows():
        key=(int(r.event_id),int(r.team_id))
        if key in done:
            continue
        todo.append(r)
    if not todo:
        return 0
    rows=[]
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs=[]
        for r in todo:
            futs.append(ex.submit(
                fetch_game_team,
                r.event_id,r.team_id,r.team,r.team_name,
                r.opponent_id,r.opponent,r.opponent_name,
                r.home_away,r.game_date,r.score,r.opponent_score
            ))
        for fut in as_completed(futs):
            try:
                rows.append(fut.result())
            except Exception:
                continue
            if len(rows) >= 50:
                append_csv(GAME_STATS,rows)
                rows=[]
    append_csv(GAME_STATS,rows)
    return len(todo)

def current_aggregate():
    d=read(GAME_STATS)
    if d.empty:
        return pd.DataFrame()
    rows=[]
    for tid,g in d.groupby("team_id"):
        sums={}
        for col in [
            "points","fieldGoalsMade","fieldGoalsAttempted",
            "threePointFieldGoalsMade","threePointFieldGoalsAttempted",
            "freeThrowsMade","freeThrowsAttempted","offensiveRebounds",
            "defensiveRebounds","totalRebounds","assists","turnovers",
            "totalTurnovers","estimatedPossessions"
        ]:
            sums[col]=pd.to_numeric(g.get(col),errors="coerce").sum()
        points_allowed=pd.to_numeric(
            g["opponent_score"],errors="coerce"
        ).sum()
        base = {
            **sums,
            "avgEstimatedPossessions":safe_div(
                sums["estimatedPossessions"],g["event_id"].nunique()
            ),
            "offensiveReboundPct":pd.to_numeric(
                g.get("offensiveReboundPct"),errors="coerce"
            ).mean(),
        }
        metrics=efficiency_fields(base,points_allowed)
        off=metrics["off_rating"]; deff=metrics["def_rating"]
        first=g.iloc[0]
        rows.append({
            "team_id":int(tid),
            "team":first.get("team"),
            "team_name":first.get("team_name"),
            "current_games":int(g["event_id"].nunique()),
            "current_points":sums["points"],
            "current_points_allowed":points_allowed,
            "current_estimated_possessions":sums["estimatedPossessions"],
            **{f"current_{k}":v for k,v in metrics.items()},
            "current_net_rating":(
                off-deff if off is not None and deff is not None else None
            ),
        })
    return pd.DataFrame(rows)

def build_current_view(baseline):
    cur=current_aggregate()
    if baseline.empty:
        return cur
    b=baseline.copy()
    keep=[
        "team_id","team","team_name","games","off_rating","def_rating",
        "net_rating","efg_pct","turnover_pct","off_rebound_pct",
        "free_throw_rate","three_point_attempt_rate",
        "tempo_possessions_per_game","net_rating_percentile","sample_status"
    ]
    b=b[keep].rename(columns={
        c:f"prior_{c}" for c in keep if c not in {"team_id","team","team_name"}
    })
    if cur.empty:
        out=b.copy()
        out["current_games"]=0
        out["context_stage"]="PRESEASON_BASELINE"
    else:
        out=b.merge(cur,on=["team_id","team","team_name"],how="outer")
        out["current_games"]=pd.to_numeric(
            out["current_games"],errors="coerce"
        ).fillna(0).astype(int)
        out["context_stage"]=out["current_games"].apply(
            lambda x:"CURRENT_ESTABLISHED" if x >= 10 else
                     "CURRENT_EMERGING" if x >= 3 else
                     "PRESEASON_BASELINE"
        )
    out["automatic_model_adjustment"]=False
    out["efficiency_score_is_probability"]=False
    out["generated_at"]=NOW
    out.to_csv(CURRENT,index=False)
    return out

def build_catalog():
    rows=[
        {
            "capability":"prior_season_possession_efficiency",
            "status":"LIVE",
            "source":"ESPN Core all-season team statistics",
            "rights_status":"REVIEW_BEFORE_COMMERCIAL_REDISTRIBUTION"
        },
        {
            "capability":"current_season_game_possessions",
            "status":"LIVE_WHEN_GAMES_COMPLETE",
            "source":"ESPN Core event competitor statistics",
            "rights_status":"REVIEW_BEFORE_COMMERCIAL_REDISTRIBUTION"
        },
        {
            "capability":"four_factors_offense",
            "status":"LIVE",
            "source":"Derived from FGM/FGA/3PM/FTA/TO/ORB/possessions",
            "rights_status":"DERIVED_RESEARCH_FEATURE"
        },
        {
            "capability":"defensive_efficiency",
            "status":"LIVE",
            "source":"Opponent points + estimated possessions",
            "rights_status":"DERIVED_RESEARCH_FEATURE"
        },
        {
            "capability":"official_NET_rankings",
            "status":"NOT_AVAILABLE_PRESEASON",
            "source":"Official NCAA source when published",
            "rights_status":"SOURCE_REQUIRED"
        },
        {
            "capability":"proprietary_KenPom_metrics",
            "status":"NOT_INGESTED",
            "source":"Proprietary external model",
            "rights_status":"LICENSE_REQUIRED"
        },
    ]
    d=pd.DataFrame(rows)
    d["generated_at"]=NOW
    d.to_csv(CATALOG,index=False)
    return d

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    fetched_prior=refresh_prior_raw()
    baseline=build_prior_baseline()
    fetched_games=refresh_current_game_stats()
    current=build_current_view(baseline)
    catalog=build_catalog()

    raw=read(RAW_PRIOR)
    game_stats=read(GAME_STATS)
    receipt={
        "generated_at":NOW,
        "prior_season":PRIOR_SEASON,
        "current_season":CURRENT_SEASON,
        "prior_team_rows":int(len(raw)),
        "prior_team_http_200":int(
            pd.to_numeric(raw.get("http_status"),errors="coerce").eq(200).sum()
        ) if not raw.empty else 0,
        "new_prior_teams_fetched":int(fetched_prior),
        "baseline_rows":int(len(baseline)),
        "full_baseline_rows":int(
            baseline.get("sample_status",pd.Series(dtype=str))
            .eq("FULL_BASELINE").sum()
        ),
        "current_game_stat_rows":int(len(game_stats)),
        "new_current_team_games_fetched":int(fetched_games),
        "current_view_rows":int(len(current)),
        "context_stage_counts":(
            current.get("context_stage",pd.Series(dtype=str))
            .value_counts().astype(int).to_dict()
            if len(current) else {}
        ),
        "catalog_rows":int(len(catalog)),
        "official_net_status":"NOT_AVAILABLE_PRESEASON",
        "proprietary_kenpom_ingested":False,
        "automatic_model_adjustment":False,
        "efficiency_score_is_probability":False,
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True))

    print("PRIOR TEAM STATS:",len(raw),"new",fetched_prior)
    print("BASELINE:",len(baseline),"full",receipt["full_baseline_rows"])
    print("CURRENT GAME STATS:",len(game_stats),"new",fetched_games)
    print("CURRENT VIEW:",len(current),receipt["context_stage_counts"])
    print("RESULT: CBB_EFFICIENCY_READY")

if __name__ == "__main__":
    main()
