"""Predeclared correction hypotheses from inspected 2025 NFL model misses.

Never used for live picks. The 2025 cohort was previously inspected and
historical sportsbook prices lack individual original capture timestamps.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from intelligence_warehouse.historical_recovery.nfl_prior_score_form_model import (
    _fit_ridge,_sigmoid,_loss,historical_prior_scoring_matrix,HISTORICAL,MODEL
)

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/"reports/NFL_ERROR_RECOVERY_SHADOW_DIAGNOSTIC_20261010.json"
YEARS=(2022,2023,2024,2025)
METHODS=("original_model","low_form_market_fallback","winner_disagreement_market_fallback","both_guards_market_fallback")

def score(pred,y):
    return {"brier":round(float(np.mean((pred-y)**2)),9),
            "log_loss":_loss(pred,y)["log_loss"],
            "winner_accuracy_pct":round(float(np.mean((pred>=.5)==y)*100),3)}

def variants(model,book,home_games,away_games):
    low=(home_games<3)|(away_games<3)
    disagree=(model>=.5)!=(book>=.5)
    return {
      "original_model":model,
      "low_form_market_fallback":np.where(low,book,model),
      "winner_disagreement_market_fallback":np.where(disagree,book,model),
      "both_guards_market_fallback":np.where(low|disagree,book,model),
    },low,disagree

def analyze(matrix,source_model):
    if {r["season"] for r in matrix}!=set(range(2016,2026)):
        raise ValueError("Unexpected historical seasons or future result")
    if len(matrix)!=len({r["game_id"] for r in matrix}):
        raise ValueError("Duplicate source game identity")
    if source_model.get("model_version")!="NFL_PREQUOTE_SCORE_FORM_9COL_2016_2024_RIDGE20_RESEARCH_V1":
        raise ValueError("Original frozen NFL model mismatched")
    if source_model.get("training_2025_outcomes_used") is not False:
        raise ValueError("Original model leaked 2025 outcomes")
    folds=[];misses=[]
    for season in YEARS:
        train=[r for r in matrix if r["season"]<season]
        test=[r for r in matrix if r["season"]==season]
        if not test or min(r["season"] for r in train)!=2016 or max(r["season"] for r in train)!=season-1:
            raise ValueError("Invalid expanding-year split")
        if {r["game_id"] for r in train}&{r["game_id"] for r in test}:
            raise ValueError("Train/test overlap")
        if any(not r["prior_week_team_stats_only_not_same_game_result"] for r in train+test):
            raise ValueError("Future result in historical features")
        x=np.asarray([r["features"] for r in train],float)
        y_tr=np.asarray([r["observed_home_win"] for r in train],float)
        xx=np.asarray([r["features"] for r in test],float)
        y=np.asarray([r["observed_home_win"] for r in test],float)
        if x.shape[1]!=9 or xx.shape[1]!=9:
            raise ValueError("Wrong model feature dimension")
        beta=_fit_ridge(x,y_tr,20.0)
        if season==2025 and not np.allclose(beta,source_model["coefficients"],rtol=0,atol=1e-8):
            raise ValueError("Original 2025-frozen model could not be reproduced")
        model=np.asarray(_sigmoid(xx@beta),float)
        book=np.asarray([r["raw_market_home_win_prob"] for r in test],float)
        hg=np.asarray([r["prior_home_games_available"] for r in test],int)
        ag=np.asarray([r["prior_away_games_available"] for r in test],int)
        p,low,disagree=variants(model,book,hg,ag)
        results={name:score(vec,y) for name,vec in p.items()}
        results["market_original"]=score(book,y)
        byweek=defaultdict(list)
        for i,r in enumerate(test):byweek[int(r["week"])].append(i)
        random=np.random.default_rng(20261010+season)
        ci={}
        for name,pred in p.items():
            delta=(book-y)**2-(pred-y)**2
            keys=sorted(byweek)
            samples=[]
            for _ in range(400):
                weeks=random.choice(keys,len(keys),replace=True)
                ids=[i for w in weeks for i in byweek[int(w)]]
                samples.append(float(np.mean(delta[ids])))
            ci[name]=[round(float(v),8) for v in np.quantile(samples,[.025,.975])]
        folds.append({
          "season":season,"train_seasons":list(range(2016,season)),
          "train_independent_games":len(train),"test_independent_games":len(test),
          "missing_prior3_games":int(np.sum(low)),
          "model_disagreed_with_market_winner_games":int(np.sum(disagree)),
          "disagreement_model_wrong_book_right":int(np.sum(disagree & ((model>=.5)!=y) & ((book>=.5)==y))),
          "disagreement_model_right_book_wrong":int(np.sum(disagree & ((model>=.5)==y) & ((book>=.5)!=y))),
          "results":results,
          "week_block_bootstrap95_market_minus_candidate_brier":ci,
          "no_same_game_or_same_season_train_test_overlap":True,
        })
        if season==2025:
            harm=(model-y)**2-(book-y)**2
            for idx in np.argsort(-harm)[:10]:
                i=int(idx);r=test[i]
                contributions=[{"feature":source_model["features"][j],
                  "logit_contribution":round(float(xx[i,j]*beta[j]),4)} for j in range(2,9)]
                contributions.sort(key=lambda z:abs(z["logit_contribution"]),reverse=True)
                misses.append({
                  "game_id":r["game_id"],"home_team":r["home_team"],"away_team":r["away_team"],
                  "actual_winner":r["home_team"] if y[i] else r["away_team"],
                  "market_favorite":r["home_team"] if book[i]>=.5 else r["away_team"],
                  "model_favorite":r["home_team"] if model[i]>=.5 else r["away_team"],
                  "book_home_probability_pct":round(float(book[i])*100,2),
                  "model_home_probability_pct":round(float(model[i])*100,2),
                  "model_minus_book_brier":round(float(harm[i]),6),
                  "missing_reliable_prior3":bool(low[i]),"model_flipped_market_favorite":bool(disagree[i]),
                  "home_prior_games":int(hg[i]),"away_prior_games":int(ag[i]),
                  "largest_score_form_terms":contributions[:3],
                  "feature_terms_are_logit_arithmetic_not_causal_explanations":True,
                  "injury_weather_or_coaching_cause_verified":False,
                })
    n=sum(x["test_independent_games"] for x in folds)
    pooled={}
    for name in ("market_original",*METHODS):
        pooled[name]={metric:round(sum(f["test_independent_games"]*f["results"][name][metric]
            for f in folds)/n,7) for metric in ("brier","log_loss","winner_accuracy_pct")}
    for name in METHODS:
        pooled[name]["market_minus_candidate_brier"]=round(
          pooled["market_original"]["brier"]-pooled[name]["brier"],7)
    return {
      "schema":"ZENITH_NFL_ERROR_RECOVERY_SHADOW_V1",
      "study_status":"EXPLORATORY_RETROSPECTIVE_ALREADY_INSPECTED_NOT_PROSPECTIVE",
      "decision":"KEEP_EXISTING_MODEL_NO_AUTOMATIC_PROMOTION",
      "design_based_on_inspected_2025_errors":True,
      "source_quotes_originally_timestamped":False,
      "fixed_hypotheses":[
        "With fewer than 3 prior same-season games for either team, use no-vig market.",
        "If model winner disagrees with bookmaker favorite, use no-vig market.",
        "Apply both fixed gates."
      ],
      "years":list(YEARS),"independent_test_games":n,
      "folds":folds,"pooled":pooled,"historical_error_examples_2025":misses,
      "candidate_live_model_deployed":False,"original_frozen_2026_predictions_modified":False,
      "independent_positive_EV_proven":False,"new_future_frozen_predictions_required":True,
      "causal_attribution_not_proven_from_prediction_contribution":True,
    }

def main():
    raw=HISTORICAL.read_bytes()
    frozen=MODEL.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    frozen_sha=hashlib.sha256(frozen).hexdigest()
    matrix,_=historical_prior_scoring_matrix(pd.read_csv(HISTORICAL,low_memory=False))
    result=analyze(matrix,json.loads(frozen))
    result.update({
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "historical_source_sha256":sha,"original_frozen_model_sha256":frozen_sha,
      "source_unique_games":len(matrix),
    })
    if sha!=hashlib.sha256(HISTORICAL.read_bytes()).hexdigest() or frozen_sha!=hashlib.sha256(MODEL.read_bytes()).hexdigest():
        raise RuntimeError("Source changed while studying error")
    OUTPUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"test_games":result["independent_test_games"],"pooled":result["pooled"],
      "folds":[{"season":f["season"],"n":f["test_independent_games"],
        "low_form":f["missing_prior3_games"],"flips":f["model_disagreed_with_market_winner_games"],
        "briers":{k:v["brier"] for k,v in f["results"].items()}}
       for f in result["folds"]],"deployed":result["candidate_live_model_deployed"]},indent=2))

if __name__=="__main__":main()
