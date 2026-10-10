"""Pre-registered non-promotable NFL rolling 5/10/20 score-form diagnostic.

Expanding-year fits (2016->21 for 2022, then prior seasons for 2023-25).
Original historical prices have NO source-book capture timestamps, so even a
better retrospective Brier score would not establish executable betting value.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib,json,math
import numpy as np
import pandas as pd
from intelligence_warehouse.historical_recovery.nfl_prior_score_form_model import _fit_ridge,_sigmoid,_loss,_book_p,_logit

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"data_vault/derived/NFL_GAME_MASTER.csv"
OUTPUT=ROOT/"reports/NFL_ROLLING_5_10_20_WALK_FORWARD_DIAGNOSTIC_20261010.json"
WINDOWS=(5,10,20)
TEST_YEARS=(2022,2023,2024,2025)
RIDGE_L2=20.0
SHRINK_GAMES=3
PRIOR_POINTS=22.0


def rolling_stats(prior,width):
    observed=prior[-width:]
    n=len(observed)
    return (
        (sum(x[0] for x in observed)+SHRINK_GAMES*PRIOR_POINTS)/(n+SHRINK_GAMES),
        (sum(x[1] for x in observed)+SHRINK_GAMES*PRIOR_POINTS)/(n+SHRINK_GAMES),
        min(1.0,n/width),
    )


def source_matrix(frame):
    need={"game_id","season","week","gameday","home_team","away_team",
          "home_score","away_score","home_moneyline","away_moneyline",
          "home_rest","away_rest","location"}
    if missing:=need-set(frame.columns):
        raise ValueError("Missing game fields: "+repr(sorted(missing)))
    if frame.game_id.isna().any() or frame.duplicated(["game_id"]).any():
        raise ValueError("Duplicate original game ID")
    years=set(map(int,frame.season.unique()))
    if years!=set(range(2016,2026)):
        raise ValueError("Only the original 2016-25 historical set is allowed")
    work=frame.copy()
    work["gameday"]=pd.to_datetime(work.gameday,errors="coerce")
    if work.gameday.isna().any():raise ValueError("Unparseable game date")
    work=work.sort_values(["season","week","gameday","game_id"])
    output=[]
    quarantined=defaultdict(int)
    for season,year in work.groupby("season",sort=True):
        history=defaultdict(list)
        for week,games in year.groupby("week",sort=True):
            for row in games.itertuples(index=False):
                h,a=str(row.home_team),str(row.away_team)
                if not h or not a or h==a:raise ValueError("Broken original teams")
                p_h,p_a=_book_p(row.home_moneyline),_book_p(row.away_moneyline)
                if p_h is None or p_a is None or not 1.000001<p_h+p_a<=1.25:
                    quarantined["invalid_historical_moneyline"]+=1
                    continue
                hs,as_=float(row.home_score),float(row.away_score)
                if not all(math.isfinite(x) and 0<=x<=150 for x in (hs,as_)):
                    raise ValueError("Non-final or implausible original score")
                if hs==as_:
                    quarantined["tied_binary_outcome"]+=1
                    continue
                fair=p_h/(p_h+p_a)
                vector=[1.0,_logit(fair)]
                counts={}
                for n in WINDOWS:
                    hpf,hpa,hcount=rolling_stats(history[h],n)
                    apf,apa,acount=rolling_stats(history[a],n)
                    opponent_adjusted_home_margin=(hpf+apa-apf-hpa)/2
                    vector.extend((opponent_adjusted_home_margin/14,
                                   (hpf-apf)/14,(apa-hpa)/14,
                                   min(hcount,acount)))
                    counts[n]=(min(len(history[h]),n),min(len(history[a]),n))
                hr,ar=float(row.home_rest),float(row.away_rest)
                if not all(math.isfinite(x) for x in (hr,ar)):
                    quarantined["nonfinite_rest"]+=1
                    continue
                vector.extend(((hr-ar)/7,float(str(row.location).lower()=="neutral")))
                if len(vector)!=16 or not np.isfinite(vector).all():
                    raise ValueError("Unexpected rolling model features")
                output.append({
                    "game_id":str(row.game_id),"season":int(season),"week":int(week),
                    "home":h,"away":a,"book_home_prob":fair,
                    "features":vector,"home_win":int(hs>as_),
                    "prior_counts":counts,"current_week_outcome_not_in_inputs":True,
                })
            # Make previous results available ONLY after the entire week was frozen.
            for row in games.itertuples(index=False):
                h,a=str(row.home_team),str(row.away_team)
                history[h].append((float(row.home_score),float(row.away_score)))
                history[a].append((float(row.away_score),float(row.home_score)))
    if len(output)<2500:raise ValueError("Expected thousands of completed original games")
    return output,dict(quarantined)


def evaluate(records):
    folds=[]
    for year in TEST_YEARS:
        train=[r for r in records if r["season"]<year]
        test=[r for r in records if r["season"]==year]
        ids_train={r["game_id"] for r in train}
        ids_test={r["game_id"] for r in test}
        if not test or len(ids_test)!=len(test) or ids_train & ids_test:
            raise ValueError("Train/test leakage or duplicate games")
        if min(r["season"] for r in train)!=2016 or max(r["season"] for r in train)!=year-1:
            raise ValueError("Not strictly expanding past-season fit")
        x=np.asarray([r["features"] for r in train],dtype=float)
        y=np.asarray([r["home_win"] for r in train],dtype=float)
        target_x=np.asarray([r["features"] for r in test],dtype=float)
        target_y=np.asarray([r["home_win"] for r in test],dtype=float)
        book=np.asarray([r["book_home_prob"] for r in test],dtype=float)
        model_market=np.asarray(_sigmoid(target_x[:,:2]@_fit_ridge(x[:,:2],y,RIDGE_L2)))
        model_rolling=np.asarray(_sigmoid(target_x@_fit_ridge(x,y,RIDGE_L2)))
        metrics={
            "paired_book_no_vig":_loss(book,target_y),
            "past_train_market_only_ridge":_loss(model_market,target_y),
            "rolling_5_10_20_opponent_score_form":_loss(model_rolling,target_y),
        }
        accuracy={k:round(float(np.mean((v>=0.5)==target_y))*100,2)
                  for k,v in [("paired_book_no_vig",book),
                              ("past_train_market_only_ridge",model_market),
                              ("rolling_5_10_20_opponent_score_form",model_rolling)]}
        paired_delta=(book-target_y)**2-(model_rolling-target_y)**2
        blocks=defaultdict(list)
        for i,r in enumerate(test):blocks[r["week"]].append(i)
        weeks=sorted(blocks)
        rng=np.random.default_rng(20261010+year)
        boot=[]
        for _ in range(400):
            selected=rng.choice(weeks,len(weeks),replace=True)
            indexes=[i for w in selected for i in blocks[int(w)]]
            boot.append(float(np.mean(paired_delta[indexes])))
        folds.append({
            "year":year,
            "train_seasons":list(range(2016,year)),
            "training_games":len(train),"test_games":len(test),
            "brier_and_log_loss":metrics,
            "winner_accuracy_pct":accuracy,
            "book_brier_minus_rolling_brier":round(float(np.mean(paired_delta)),8),
            "paired_week_bootstrap95":[round(float(v),8) for v in np.quantile(boot,[.025,.975])],
            "training_and_test_game_ids_disjoint":True,
            "all_form_sources_prior_same_season_weeks_only":True,
            "source_bookmaker_prices_originally_timestamped":False,
        })
    n=sum(f["test_games"] for f in folds)
    def weighted(key):
        return sum(f["test_games"]*f["brier_and_log_loss"][key]["brier"] for f in folds)/n
    book_brier=weighted("paired_book_no_vig")
    rolling_brier=weighted("rolling_5_10_20_opponent_score_form")
    return {
        "schema":"NFL_ASOF_ROLLING_5_10_20_DIAGNOSTIC_V1",
        "data_type":"RETROSPECTIVE_COMPILED_ODDS_NOT_LIVE_EXECUTABLE_QUOTES",
        "strategy_preregistered_without_fitting_TO_future_season":True,
        "train_range_first_year":2016,
        "test_years":list(TEST_YEARS),
        "total_heldout_game_observations":n,
        "pooled_book_brier":round(book_brier,8),
        "pooled_rolling_brier":round(rolling_brier,8),
        "pooled_book_minus_rolling_brier":round(book_brier-rolling_brier,8),
        "folds_rolling_beats_book":sum(f["book_brier_minus_rolling_brier"]>0 for f in folds),
        "folds":folds,
        "cross_game_leakage_detected":False,
        "historical_prices_individual_quote_timestamps_available":False,
        "2025_has_already_been_inspected_during_prior_experiments":True,
        "new_forward_2026_holdout_required":True,
        "positive_EV_or_actual_profit_proven":False,
        "real_money_bets_created":False,
        "automatically_adjusted_production_weights":False,
        "live_model_promoted":False,
    }


def main():
    raw=SOURCE.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    records,quarantine=source_matrix(pd.read_csv(SOURCE,low_memory=False))
    report=evaluate(records)
    report.update({
        "original_source_sha256":sha,"original_path":str(SOURCE.relative_to(ROOT)),
        "original_game_rows_evaluated":len(records),"quarantined_counts":quarantine,
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
    })
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=sha:
        raise RuntimeError("Historical source changed during experiment")
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:report[k] for k in [
        "total_heldout_game_observations","pooled_book_brier","pooled_rolling_brier",
        "pooled_book_minus_rolling_brier","folds_rolling_beats_book","live_model_promoted"
    ]},indent=2))
    for fold in report["folds"]:
        print("FOLD",fold["year"],"GAMES",fold["test_games"],
              "Brier",fold["brier_and_log_loss"],
              "Winner %",fold["winner_accuracy_pct"])


if __name__=="__main__":main()
