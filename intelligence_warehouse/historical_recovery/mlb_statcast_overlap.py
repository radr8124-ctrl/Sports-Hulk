"""Research-only identity/velocity overlap between existing and newly recovered sources.

Contact exit velocity is batted-ball performance, never measured sprint speed.
The existing prior aggregate cannot be proven an as-of prediction feature by
this comparison. It never edits the production MLB pitcher/batter profiles.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone

import pandas as pd

from .mlb_statcast_quarantine import ROOT
from .mlb_statcast_staging import TARGET


def _source(path:Path,keys:list[str],numeric:str)->pd.DataFrame:
    df=pd.read_csv(path,low_memory=False)
    required=set(keys)|{'pitches',numeric}
    if missing:=required-set(df.columns):
        raise ValueError(f'Statcast profile lacks needed metric/identity: {sorted(missing)}')
    clean=df.dropna(subset=keys).copy()
    if clean.duplicated(keys).any():
        raise ValueError('Found ambiguous duplicate player/pitch-type identity keys')
    clean['pitches']=pd.to_numeric(clean['pitches'],errors='coerce')
    clean[numeric]=pd.to_numeric(clean[numeric],errors='coerce')
    return clean


def compare_profile_overlap(oldp:pd.DataFrame,newp:pd.DataFrame,oldb:pd.DataFrame,newb:pd.DataFrame)->dict:
    def prep(df,keys,column):
        required=set(keys)|{'pitches',column}
        if not required.issubset(df.columns):
            raise ValueError('Profile metric or identity missing')
        out=df.dropna(subset=keys).copy()
        if out.duplicated(keys).any():
            raise ValueError('Found ambiguous duplicate profile source identity')
        out['pitches']=pd.to_numeric(out['pitches'],errors='coerce')
        out[column]=pd.to_numeric(out[column],errors='coerce')
        return out
    op=prep(oldp,['pitcher','pitch_type'],'avg_velocity')
    np_=prep(newp,['pitcher','pitch_type'],'avg_velocity')
    ob=prep(oldb,['batter','pitch_type'],'avg_exit_velo')
    nb=prep(newb,['batter','pitch_type'],'avg_exit_velo')
    p=np_.merge(op,on=['pitcher','pitch_type'],how='inner',suffixes=('_sept','_stored'),validate='one_to_one')
    b=nb.merge(ob,on=['batter','pitch_type'],how='inner',suffixes=('_sept','_stored'),validate='one_to_one')
    pitchers=p[(p.pitches_sept>=30)&(p.pitches_stored>=100)&p.avg_velocity_sept.notna()&p.avg_velocity_stored.notna()]
    batters=b[(b.pitches_sept>=15)&(b.pitches_stored>=80)&b.avg_exit_velo_sept.notna()&b.avg_exit_velo_stored.notna()]
    velo_delta=(pitchers.avg_velocity_sept-pitchers.avg_velocity_stored)
    exit_delta=(batters.avg_exit_velo_sept-batters.avg_exit_velo_stored)
    return {
        'research_only':True,
        'comparison_window':'2026-09-01 through 2026-09-05',
        'source_is_newly_downloaded_not_original_archive':True,
        'existing_profiles_not_proven_exact_temporal_baseline':True,
        'pitcher_stored_profile_count':len(oldp),
        'pitcher_sep_profile_count':len(newp),
        'overlap_pitcher_pitch_types':len(p),
        'qualified_pitcher_pitch_types':len(pitchers),
        'qualified_pitcher_ids':int(pitchers.pitcher.nunique()),
        'pitcher_qualified_threshold':{'recovered_pitches_at_least':30,'existing_pitches_at_least':100},
        'qualified_pitcher_median_velocity_delta_mph':round(float(velo_delta.median()),4) if len(velo_delta) else None,
        'qualified_pitcher_velocity_delta_mph_range':[round(float(velo_delta.min()),4),round(float(velo_delta.max()),4)] if len(velo_delta) else None,
        'batter_stored_profile_count':len(oldb),
        'batter_sep_profile_count':len(newb),
        'overlap_batter_pitch_types':len(b),
        'qualified_batter_pitch_types':len(batters),
        'qualified_batter_ids':int(batters.batter.nunique()),
        'batter_qualified_threshold':{'recovered_pitches_at_least':15,'existing_pitches_at_least':80},
        'qualified_batter_median_exit_velocity_delta_mph':round(float(exit_delta.median()),4) if len(exit_delta) else None,
        'direct_batter_sprint_speed_available':False,
        'bat_speed_measurement_available':False,
        'exit_velocity_is_sprint_speed':False,
        'betting_edge_proven':False,
        'new_pitches_are_historical_not_forward_evidence':True,
        'no_live_mlb_model_or_price_changes':True,
    }


def main():
    ap=argparse.ArgumentParser(description='Research-only MLB September 2026 profile overlap')
    ap.add_argument('--output',type=Path,default=TARGET/'PROFILE_COMPARISON_RESEARCH_ONLY.json')
    args=ap.parse_args()
    if args.output.resolve()!=(TARGET/'PROFILE_COMPARISON_RESEARCH_ONLY.json').resolve():
        raise SystemExit('Refusing noncanonical or live output path')
    paths={
        'old_p':ROOT/'baseball_vault/derived/MLB_PITCHER_ARSENAL.csv',
        'new_p':TARGET/'MLB_PITCHER_ARSENAL.csv',
        'old_b':ROOT/'baseball_vault/derived/MLB_BATTER_VS_PITCH_TYPE.csv',
        'new_b':TARGET/'MLB_BATTER_VS_PITCH_TYPE.csv',
    }
    for name,p in paths.items():
        if not p.is_file():raise SystemExit(f'Missing source {name}: {p}')
    inputs={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in paths.items()}
    d=compare_profile_overlap(*[pd.read_csv(paths[x],low_memory=False) for x in ('old_p','new_p','old_b','new_b')])
    d['source_files']={name:{'path':str(p.relative_to(ROOT)),'sha256':inputs[name]} for name,p in paths.items()}
    if args.output.is_file():
        old=json.loads(args.output.read_text())
        oldcmp={k:v for k,v in old.items() if k!='generated_at_utc'}
        currentcmp={k:v for k,v in d.items()}
        if oldcmp!=currentcmp:
            raise ValueError('Existing comparison is immutable; source has changed')
    else:
        d['generated_at_utc']=datetime.now(timezone.utc).isoformat()
        args.output.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print('SOURCE_IDENTIFIED_PITCHER_BATTER_RESEARCH',json.dumps({
        k:d.get(k) for k in [
            'overlap_pitcher_pitch_types','qualified_pitcher_pitch_types','qualified_pitcher_ids',
            'overlap_batter_pitch_types','qualified_batter_pitch_types','qualified_batter_ids',
            'qualified_pitcher_median_velocity_delta_mph','qualified_batter_median_exit_velocity_delta_mph',
            'direct_batter_sprint_speed_available','betting_edge_proven'
        ]
    },sort_keys=True))

if __name__=='__main__':
    main()
