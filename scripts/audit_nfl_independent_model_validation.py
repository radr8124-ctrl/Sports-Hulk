#!/usr/bin/env python3
"""Read-only integrity gate for existing NFL historical holdout evidence."""
import datetime,hashlib,json,pathlib
ROOT=pathlib.Path('/home/ubuntu/sports-hulk')
SOURCE=ROOT/'reports/NFL_2016_2024_SCORE_FORM_HOLDOUT_2025_CHECKPOINT_20261009.json'
DEST=ROOT/'nfl_live/prediction_markets/nfl_independent_model_validation_latest.json'
def evaluate(e):
    metrics=e['evaluations']
    model=metrics['historical_prior_week_score_form_ridge']
    market=metrics['raw_compiled_market_home_no_vig']
    brier=float(market['brier'])-float(model['brier'])
    logloss=float(market['log_loss'])-float(model['log_loss'])
    ci=e.get('paired_week_block_95ci_market_minus_advanced_model')
    gates={
      'sufficient_historical_games':int(e.get('game_count',0))>=200,
      'brier_improvement_vs_market':brier>0,
      'logloss_improvement_vs_market':logloss>0,
      'paired_confidence_interval_positive':isinstance(ci,list) and len(ci)==2 and all(isinstance(x,(int,float)) for x in ci) and ci[0]>0,
      'pristine_unseen_forward_holdout':not bool(e.get('historical_2025_seen_diagnostic_not_pristine_future',True))
    }
    return {'schema':'zenith.nfl.model_validation_gate.v1','model_version':e.get('model_version'),'holdout_games':e.get('game_count'),'market_baseline':market,'candidate_model':model,'brier_improvement_market_minus_model':round(brier,9),'logloss_improvement_market_minus_model':round(logloss,9),'paired_week_block_95ci':ci,'gates':gates,'validated_independent_edge':all(gates.values()),'kalshi_picks_approved':0,'note':'Historical diagnostics only; market advantage and pristine forward proof not established'}
def main():
    source_bytes=SOURCE.read_bytes()
    evidence=json.loads(source_bytes)
    report=evaluate(evidence)
    report['source_sha256']=hashlib.sha256(source_bytes).hexdigest()
    report['checked_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    DEST.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'holdout_games':report['holdout_games'],'brier_improvement':report['brier_improvement_market_minus_model'],'logloss_improvement':report['logloss_improvement_market_minus_model'],'gates':report['gates'],'validated_independent_edge':report['validated_independent_edge']}))
if __name__=='__main__':main()
