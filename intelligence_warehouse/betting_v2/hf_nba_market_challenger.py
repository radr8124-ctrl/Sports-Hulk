"""Hugging Face NBA closing-line source audit and frozen historical challenger.

Source scores are independently reconciled to ESPN completed games.
Publisher's odds DO NOT have original bookmaker timestamps or licensed
executability proof; every result is retrospective research only.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .hf_mlb_prop_asof import _fit_small_ridge_logistic, _logit, _sigmoid

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "reports/HF_ZENITH_NBA_REGULAR_SEASON_MODEL_PREREG_2026-10-09.json"
OUT = ROOT / "reports/hf_nba_closinglines_audit_20261009"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(text: object) -> str:
    v = " ".join(str(text or "").lower().strip().split())
    return {"los angeles clippers": "la clippers"}.get(v, v)


def side(v: float, positive: str, negative: str) -> str:
    return positive if v > 1e-6 else negative if v < -1e-6 else "push"


def source_verified_rows(hf: pd.DataFrame, official: pd.DataFrame) -> tuple[list[dict],dict]:
    if hf.game_id.duplicated().any():
        raise ValueError("DUPLICATE_PUBLISHER_GAME_IDS")
    hf = hf.copy()
    official = official.copy()
    official = official[
        (official.season.astype(str) == "2026")
        & official.completed.astype(str).str.lower().eq("true")
    ].copy()
    hf["start_ts"] = pd.to_datetime(hf.start_time_utc, utc=True, errors="coerce")
    official["start_ts"] = pd.to_datetime(official.start, utc=True, errors="coerce")
    hf["home_key"] = hf.home_team.map(norm)
    hf["away_key"] = hf.away_team.map(norm)
    official["home_key"] = official.home_team_name.map(norm)
    official["away_key"] = official.away_team_name.map(norm)
    hf["date_utc"] = hf.start_ts.dt.date
    official["date_utc"] = official.start_ts.dt.date
    merged = hf.merge(
        official, on=["home_key","away_key","date_utc"], how="left",
        suffixes=("_hf", "_official"), validate="many_to_many",
    )
    reasons=Counter()
    accepted=[]
    for _, g in merged.groupby("game_id",sort=True,dropna=False):
        src=g.iloc[0]
        if pd.isna(src["start_ts_hf"]):
            reasons["SOURCE_TIMESTAMP_MISSING"]+=1
            continue
        g=g[g.event_id.notna()].copy()
        if not g.empty:
            g["time_gap"]=(g.start_ts_hf-g.start_ts_official).abs().dt.total_seconds()
            g=g[g.time_gap<=180]
        if len(g)==0:
            reasons["NO_UNIQUE_OFFICIAL_MATCH"]+=1
            continue
        if len(g)>1:
            reasons["AMBIGUOUS_OFFICIAL_GAME"]+=1
            continue
        r=g.iloc[0]
        # Exclude preseason, play-in and playoffs from both training and test.
        if str(r.get("season_type_hf"))!="regular" or str(r.get("season_type_official"))!="2":
            reasons["NOT_REGULAR_SEASON"]+=1
            continue
        if int(r.home_score_hf)!=int(r.home_score_official) or int(r.away_score_hf)!=int(r.away_score_official):
            reasons["FINAL_SCORE_CONFLICT"]+=1
            continue
        margin=float(r.home_score_official)-float(r.away_score_official)
        total=float(r.home_score_official)+float(r.away_score_official)
        try:
            close_total=float(r.close_total)
            open_total=float(r.open_total)
            close_spread=float(r.close_spread_home)
            open_spread=float(r.open_spread_home)
            close_over=float(r.close_over_prob)
            close_cover=float(r.close_home_cover_prob)
            close_home=float(r.close_home_win_prob)
            open_home=float(r.open_home_win_prob)
            book_home=float(r.close_fair_home_odds)
            book_away=float(r.close_fair_away_odds)
        except (ValueError,TypeError):
            reasons["MISSING_MARKET_NUMBER"]+=1
            continue
        values=(close_total,open_total,close_spread,open_spread,close_over,close_cover,
                close_home,open_home,book_home,book_away)
        if not all(math.isfinite(v) for v in values):
            reasons["NONFINITE_MARKET"]+=1
            continue
        if not (0.01<=close_over<=0.99 and 0.01<=close_cover<=0.99 and
                0.01<=close_home<=0.99 and 0.01<=open_home<=0.99 and
                book_home>1 and book_away>1 and 80<=close_total<=450):
            reasons["IMPLAUSIBLE_MARKET"]+=1
            continue
        if abs(1/book_home-close_home)>.002 or abs(1/book_away-(1-close_home))>.002:
            reasons["SOURCE_FAIR_MONEYLINE_CONFLICT"]+=1
            continue
        y_tot=side(total-close_total,"over","under")
        y_spread=side(margin+close_spread,"home","away")
        y_ml=side(margin,"home","away")
        if (y_tot!=str(r.total_result).lower()
                or y_spread!=str(r.ats_result).lower()
                or y_ml!=str(r.moneyline_winner).lower()):
            reasons["PUBLISHER_RESULT_GRADE_CONFLICT"]+=1
            continue
        accepted.append({
            "provider_game_id":str(r.game_id),
            "official_event_id":str(int(r.event_id)),
            "start":r.start_ts_hf.isoformat(),
            "home_name":str(r.get("home_team_hf",r.get("home_team"))),
            "away_name":str(r.get("away_team_hf",r.get("away_team"))),
            "official_home_score":int(r.home_score_official),
            "official_away_score":int(r.away_score_official),
            "close_over_prob":close_over,"close_cover_prob":close_cover,
            "close_home_win_prob":close_home,"open_home_win_prob":open_home,
            "close_spread_home":close_spread,"open_spread_home":open_spread,
            "close_total":close_total,"open_total":open_total,
            "over_result":y_tot,"cover_result":y_spread,"home_win_result":y_ml,
            "season_type":"NBA_2025_26_REGULAR","book_source_verified":False,
        })
    if len(set(x["official_event_id"] for x in accepted)) != len(accepted):
        raise ValueError("OFFICIAL_GAME_REUSED_BY_DIFFERENT_PROVIDER_IDS")
    audit={
        "source_dataset_rows":len(hf),
        "official_nba_history_rows":len(official),
        "verified_regular_game_rows":len(accepted),
        "source_rejection_counts":dict(sorted(reasons.items())),
        "independently_confirmed_matchup_time_final_score_and_grade":True,
        "source_original_book_quote_timestamps_verified":False,
        "official_pregame_odds_execution_verified":False,
    }
    return sorted(accepted,key=lambda r:(r["start"],r["official_event_id"])),audit


def clip(x: np.ndarray,low: float,high: float) -> np.ndarray:
    return np.clip(x,low,high)


def matrix(rows: list[dict], market: str, augmented: bool) -> np.ndarray:
    if market=="NBA_TOTAL_REGULAR_SEASON":
        p=np.array([r["close_over_prob"] for r in rows])
        aux=[
            clip(np.array([r["close_total"]-r["open_total"] for r in rows])/8,-3,3),
            clip((np.array([r["close_total"] for r in rows])-230)/25,-3,3),
            clip(np.abs(np.array([r["close_spread_home"] for r in rows]))/12,0,3),
        ]
    elif market=="NBA_SPREAD_REGULAR_SEASON":
        p=np.array([r["close_cover_prob"] for r in rows])
        aux=[
            clip(np.array([r["close_spread_home"]-r["open_spread_home"] for r in rows])/8,-3,3),
            clip((np.array([r["close_total"] for r in rows])-230)/25,-3,3),
            clip(np.abs(np.array([r["close_spread_home"] for r in rows]))/12,0,3),
        ]
    elif market=="NBA_HOME_MONEYLINE_REGULAR_SEASON":
        p=np.array([r["close_home_win_prob"] for r in rows])
        aux=[
            clip(np.array([r["close_home_win_prob"]-r["open_home_win_prob"] for r in rows])/.15,-3,3),
            clip(np.array([r["close_spread_home"] for r in rows])/12,-3,3),
            clip((np.array([r["close_total"] for r in rows])-230)/25,-3,3),
        ]
    else:
        raise ValueError("UNREGISTERED_NBA_MARKET")
    cols=[np.ones(len(rows)),_logit(p)]
    if augmented:
        cols+=aux
    return np.column_stack(cols)


def labels(rows: list[dict], market: str) -> np.ndarray:
    key={
        "NBA_TOTAL_REGULAR_SEASON":("over_result","over"),
        "NBA_SPREAD_REGULAR_SEASON":("cover_result","home"),
        "NBA_HOME_MONEYLINE_REGULAR_SEASON":("home_win_result","home"),
    }[market]
    if any(r[key[0]]=="push" for r in rows):
        raise ValueError("PUSH_REQUIRES_SEPARATE_THREE_WAY_MARKET")
    return np.array([1 if r[key[0]]==key[1] else 0 for r in rows],dtype=float)


def scores(y:np.ndarray,p:np.ndarray)->dict:
    q=clip(p,1e-6,1-1e-6)
    return {
        "brier":round(float(np.mean((q-y)**2)),6),
        "log_loss":round(float(np.mean(-(y*np.log(q)+(1-y)*np.log(1-q)))),6),
    }


def intervals(rows:list[dict],gain:np.ndarray,reps:int,seed:int)->dict:
    rng=np.random.default_rng(seed)
    n=len(gain)
    sampled=rng.integers(0,n,size=(reps,n))
    game=np.quantile(gain[sampled].mean(axis=1),[.025,.975])
    days=defaultdict(list)
    for i,r in enumerate(rows):
        days[str(r["start"])[:10]].append(i)
    labels=sorted(days)
    days_draw=[]
    for _ in range(reps):
        chosen=rng.integers(0,len(labels),size=len(labels))
        indexes=[i for j in chosen for i in days[labels[int(j)]]]
        days_draw.append(gain[indexes].mean())
    day_ci=np.quantile(days_draw,[.025,.975])
    return {
        "one_event_per_game":True,
        "independent_games":n,
        "unique_calendar_days":len(labels),
        "market_only_minus_augmented_brier_gain":round(float(gain.mean()),6),
        "game_bootstrap_95ci":[round(float(z),6) for z in game],
        "day_cluster_95ci":[round(float(z),6) for z in day_ci],
        "statistical_advantage_proven":False,
    }


def winning_pct(rows:list[dict], y:np.ndarray,p:np.ndarray)->dict:
    picks=[i for i,v in enumerate(p) if max(float(v),1-float(v))>=.7]
    wins=sum(bool((p[i]>=.5)==(y[i]==1)) for i in picks)
    return {
        "probability_gate":.70,"selected_games":len(picks),
        "total_available_games":len(rows),
        "coverage_pct":round(100*len(picks)/len(rows),2),
        "wins":wins,"losses":len(picks)-wins,
        "hit_rate_pct":round(100*wins/len(picks),2) if picks else None,
        "source_odds_not_executable":True,
        "profit_and_roi":None,
    }


def evaluate(rows:list[dict],spec:dict)->tuple[dict,list[dict]]:
    cutoff=datetime.fromisoformat(spec["test_first_start_inclusive"])
    a=[r for r in rows if datetime.fromisoformat(r["start"])<cutoff]
    b=[r for r in rows if datetime.fromisoformat(r["start"])>=cutoff]
    if len(a)<100 or len(b)<100 or max(x["start"] for x in a)>=min(x["start"] for x in b):
        raise ValueError("INSUFFICIENT_CHRONOLOGICAL_GAME_BLOCK_SPLIT")
    if set(r["official_event_id"] for r in a)&set(r["official_event_id"] for r in b):
        raise ValueError("TRAIN_TEST_OVERLAP")
    reports={}
    predictions=[]
    for j,m in enumerate(spec["market_types"]):
        y_a=labels(a,m);y_b=labels(b,m)
        x_cal_a=matrix(a,m,False);x_full_a=matrix(a,m,True)
        model_market=_fit_small_ridge_logistic(x_cal_a,y_a,regularization=25.0)
        model_full=_fit_small_ridge_logistic(x_full_a,y_a,regularization=25.0)
        raw=np.asarray({
            "NBA_TOTAL_REGULAR_SEASON":[r["close_over_prob"] for r in b],
            "NBA_SPREAD_REGULAR_SEASON":[r["close_cover_prob"] for r in b],
            "NBA_HOME_MONEYLINE_REGULAR_SEASON":[r["close_home_win_prob"] for r in b],
        }[m])
        p_market=_sigmoid(matrix(b,m,False)@model_market)
        p_full=_sigmoid(matrix(b,m,True)@model_full)
        gains=(p_market-y_b)**2-(p_full-y_b)**2
        reports[m]={
            "research_status":"HISTORICAL_ONLY_NOT_PROSPECTIVE_PROOF",
            "train_games":len(a),"test_games":len(b),
            "train_last_start":a[-1]["start"],"test_first_start":b[0]["start"],
            "trained_market_only_coefficients":[round(float(v),9) for v in model_market],
            "trained_feature_coefficients":[round(float(v),9) for v in model_full],
            "raw_close_market":scores(y_b,raw),
            "train_calibrated_market":scores(y_b,p_market),
            "frozen_feature_challenger":scores(y_b,p_full),
            "uncertainty":intervals(b,gains,spec["bootstrap_repetitions"],spec["bootstrap_seed"]+j),
            "raw_market_high_confidence":winning_pct(b,y_b,raw),
            "calibrated_market_high_confidence":winning_pct(b,y_b,p_market),
            "feature_challenger_high_confidence":winning_pct(b,y_b,p_full),
            "model_promotion_allowed":False,
            "original_quote_timestamps":False,
        }
        for r,y,x,z,w in zip(b,y_b,raw,p_market,p_full):
            predictions.append({
                "market":m,
                "official_event_id":r["official_event_id"],
                "start":r["start"],
                "verified_result":int(y),
                "raw_market_probability":round(float(x),9),
                "market_only_prediction":round(float(z),9),
                "feature_model_prediction":round(float(w),9),
                "historical_research_only":True,
            })
    return reports,predictions


def main():
    parser=argparse.ArgumentParser(description='Strictly historical NBA Hugging Face source/market calibration research')
    parser.add_argument('--out-dir',type=Path,default=OUT)
    args=parser.parse_args()
    destination=args.out_dir.resolve()
    if (ROOT/'reports') not in destination.parents:
        raise SystemExit('Research outputs restricted to reports directory')
    if any(term in destination.parts for term in ('commercial_web','decision','public','live','latest')):
        raise SystemExit('Historical NBA sources may not enter live model folders')
    spec_digest=sha(SPEC)
    spec=json.loads(SPEC.read_text())
    if spec.get("model_form") != "RIDGE_LOGISTIC, prior beta=[0,1,0,0,0] with market-logit coefficient one; unpenalized intercept":
        raise ValueError("SPEC_MODEL_CHANGED")
    if spec.get("ridge_lambda")!=25.0 or spec.get("production_changes_allowed") is not False:
        raise ValueError("SPEC_RULE_CHANGED")
    sources={}
    for key,pathkey,hashkey in (
        ("hf","nba_hf_source_file","nba_hf_source_sha256"),
        ("official","official_nba_snapshot","official_nba_snapshot_sha256"),
    ):
        p=ROOT/spec[pathkey]
        if sha(p)!=spec[hashkey]:
            raise ValueError(f"FROZEN_{key.upper()}_DATA_CHANGED")
        sources[key]=p
    hf=pd.read_parquet(sources["hf"])
    official=pd.read_csv(sources["official"])
    verified,audit=source_verified_rows(hf,official)
    compared,preds=evaluate(verified,spec)
    if sha(SPEC)!=spec_digest:
        raise RuntimeError("PREREG_CHANGED_DURING_RUN")
    summary={
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "study_id":spec["study_id"],"spec_sha256":spec_digest,
        "status":"HISTORICAL_HF_NBA_RESEARCH_NO_BETTING_MODEL_PROMOTION",
        "data_audit":audit,"market_comparisons":compared,
        "new_forward_picks":0,"new_paid_hf_cloud_jobs":0,
        "actual_betting_placement":False,"commercial_odds_license_verified":False,
        "source_price_timestamps_verified":False,
        "cross_market_outcomes_correlated_same_games":True,
    }
    destination.mkdir(parents=True,exist_ok=True)
    for fname,payload in [("nba_hf_official_source_audit.json",audit),("nba_research_comparison_summary.json",summary),
                          ("nba_research_predictions_PRIVATE.json",preds)]:
        with (destination/fname).open("x",encoding="utf-8") as f:
            f.write(json.dumps(payload,indent=2,sort_keys=True)+"\n")
            f.flush();os.fsync(f.fileno())
    print(json.dumps(summary,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
