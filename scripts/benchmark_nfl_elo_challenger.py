#!/usr/bin/env python3
"""Previously inspected NFL history, fixed Elo; conditional diagnostics only."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from nfl_elo_challenger import CONFIG,replay
from benchmark_nfl_compact_challenger import metrics,interval,write
from audit_nfl_selective_value import select,summarize

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'nfl_live/prediction_markets'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    protocol_path=ROOT/'reports/NFL_ELO_CHALLENGER_PROTOCOL_20261011.json'
    protocol=json.loads(protocol_path.read_text())
    if any(protocol[k]!=v for k,v in CONFIG.items()) or protocol['test_seasons']!=list(range(2019,2025)) or protocol['previously_seen_diagnostic_season']!=2025 or protocol['minimum_expected_return_after_stress']!=.03 or protocol['hypothetical_cost_per_unit_stake']!=.02:
        raise ValueError('Protocol changed; new version required')
    source_path=ROOT/'data_vault/derived/NFL_GAME_MASTER.csv'
    reference_path=DATA/'nfl_opponent_epa_challenger_latest.json'
    reference=json.loads(reference_path.read_text())
    if sha(source_path)!=reference['historical_master_sha256']:
        raise ValueError('Historical source changed since comparison baseline')
    master=pd.read_csv(source_path,low_memory=False)
    if master.game_id.duplicated().any():raise ValueError('Duplicate game identity')
    played=master.dropna(subset=['home_score','away_score','gameday'])
    played=played[(played.season>=2016)&(played.season<=2025)]
    games=played.to_dict('records')
    probabilities=replay(games)
    index=master.set_index('game_id').to_dict('index')
    cohorts={};simulation={}
    for key in ('predictions','secondary_predictions'):
        rows=[dict(r,candidate=probabilities[r['game_id']]) for r in reference[key]]
        expected=protocol['test_seasons'] if key=='predictions' else [2025]
        if sorted({r['season'] for r in rows})!=expected:raise ValueError('Unexpected comparison seasons')
        cohorts[key]=rows
        simulation[key]=[select(r,index[r['game_id']],.03,.02) for r in rows]
    rolling=metrics(cohorts['predictions'])
    rolling['week_block_brier_gain_95ci']=interval(cohorts['predictions'],10000,61011)
    rolling['brier_gain_vs_market']=rolling['market']['brier']-rolling['candidate']['brier']
    rolling['logloss_gain_vs_market']=rolling['market']['log_loss']-rolling['candidate']['log_loss']
    out=dict(schema='zenith.nfl.elo_challenger_benchmark.v1',checked_at_utc=datetime.now(timezone.utc).isoformat(),
        candidate=protocol['candidate'],protocol=protocol,source_hashes=dict(protocol=sha(protocol_path),
        master=sha(source_path),reference=sha(reference_path),model_code=sha(ROOT/'scripts/nfl_elo_challenger.py')),
        rolling_summary=rolling,secondary_seen_2025=metrics(cohorts['secondary_predictions']),
        rolling_value_simulation=summarize(simulation['predictions'],10000,61011),
        secondary_value_simulation=summarize(simulation['secondary_predictions'],10000,61012),
        by_season={str(year):dict(pricing=metrics([r for r in cohorts['predictions'] if r['season']==year]),
          value=summarize([r for r in simulation['predictions'] if r['season']==year],10000,61011+year)) for year in range(2019,2025)},
        historical_data_previously_inspected=True,forward_entries_created=0,forward_games_scored=0,
        production_model_changed=False,validated_edge=False,validated_exchange_profit=False,approved_picks=0,
        limitations=['Fixed NFL-only challenger; NBA not tested',
          'Date-blocked scores-only replay; original final timestamps unavailable',
          'Previously inspected history, not untouched prospective validation',
          'Compiled historical sportsbook odds lack original quote time and book identity',
          'Value simulation includes sportsbook payout odds and a hypothetical 2% stake cost, not verified exchange fees',
          'Binary comparison cohort excludes ties; exchange-specific settlement probability unmodeled',
          'Positive retrospective ROI does not establish future profitable edge'],
        predictions=cohorts['predictions'],secondary_predictions=cohorts['secondary_predictions'],
        conditional_simulation=simulation)
    write(DATA/'nfl_elo_challenger_latest.json',out)
    public_path=ROOT/'commercial_web/public/prediction_market_nfl_evidence.json'
    public=json.loads(public_path.read_text())
    public['elo_challenger']={k:out[k] for k in ('candidate','checked_at_utc','rolling_summary','secondary_seen_2025',
        'rolling_value_simulation','secondary_value_simulation','production_model_changed','validated_edge','forward_games_scored')}
    write(public_path,public)
    print(json.dumps(public['elo_challenger']))
if __name__=='__main__':main()
