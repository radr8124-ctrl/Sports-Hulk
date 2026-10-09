"""Only derive analytic historical grades from official MLB stats when vendor is blank.

No assertion of sportsbook/DFS platform settlement; this is retrospective
research outcome verification, with strict identity and participation checks.
"""
from __future__ import annotations

import pandas as pd

from .hf_mlb_prop_pilot import (MARKETS, clean_player_name,
    fair_grade_from_stat,market_implied_probability,safe_number)


def derive_missing_vendor_outcomes(audit: list[dict], official_history: pd.DataFrame) -> list[dict]:
    """Fail-closed official analytic outcome recovery; never rescue a conflict.

    Only accepts a row ALREADY uniquely matched to MLB game and player by
    earlier `audit_rows`, with no source grade/result. Current-game stats are
    used as *outcome only*, and never as pre-kickoff predictive features.
    """
    candidates={int(row['official_game_pk']) for row in audit
        if row.get('status')=='MISSING_VENDOR_OUTCOME'
        and row.get('official_game_pk') is not None}
    if not candidates:
        return [dict(row) for row in audit]
    required={'game_pk','player','group','plate_appearances','outs','game_date'}
    if not required.issubset(official_history.columns):
        raise ValueError('Missing required official participation/identity evidence')
    h=official_history[official_history.game_pk.isin(candidates)].copy()
    h['_name']=h.player.map(clean_player_name)
    keyed={(int(pk),name,str(group).upper()):group_frame
        for (pk,name,group),group_frame in h.groupby(['game_pk','_name','group'],dropna=False,sort=False)}
    out=[]
    for record in audit:
        row=dict(record)
        if row.get('status')!='MISSING_VENDOR_OUTCOME':
            out.append(row);continue
        if row.get('won') is not None or row.get('result') is not None:
            row['status']='PARTIAL_VENDOR_OUTCOME_NOT_DERIVABLE'
            out.append(row);continue
        if not row.get('timestamp_before_official_start'):
            row['status']='NOT_PREGAME_OFFICIAL_QUOTE'
            out.append(row);continue
        try:pk=int(row['official_game_pk'])
        except (TypeError,ValueError):
            row['status']='NO_UNIQUE_OFFICIAL_PLAYER_STAT'
            out.append(row);continue
        key=(pk,clean_player_name(row.get('player')),str(row.get('official_group') or '').upper())
        matches=keyed.get(key)
        if matches is None or len(matches)!=1:
            row['status']='NO_UNIQUE_OFFICIAL_PLAYER_STAT'
            out.append(row);continue
        actual=matches.iloc[0]
        if str(actual['group']).upper()=='HITTING':
            pa=safe_number(actual.get('plate_appearances'))
            eligible=pa is not None and pa>=1
        elif str(actual['group']).upper()=='PITCHING':
            outs=safe_number(actual.get('outs'))
            eligible=outs is not None and outs>=1
        else:
            eligible=False
        if not eligible:
            row['status']='NO_OFFICIALLY_VERIFIED_PARTICIPATION'
            out.append(row);continue
        market=str(row.get('market') or '').lower()
        field=MARKETS.get(market)
        official_stat=safe_number(actual.get(field)) if field else None
        if official_stat is None:
            row['status']='MISSING_OFFICIAL_PROP_STAT'
            out.append(row);continue
        grade=fair_grade_from_stat(row.get('side'),row.get('line'),official_stat)
        if grade is None:
            row['status']='OFFICIAL_PUSH_OR_UNDETERMINED_NOT_WINLOSS'
            out.append(row);continue
        implied=market_implied_probability(row.get('odds'))
        if implied is None:
            row['status']='INVALID_ORIGINAL_ODDS'
            out.append(row);continue
        row.update({
            'status':'OFFICIAL_DERIVED_HISTORICAL',
            'verified_win':grade,
            'official_stat':official_stat,
            'official_stat_name':field,
            'market_implied_probability':implied,
            'source_graded':False,
            'provider_grade_state':'UNAVAILABLE_NOT_SETTLED_BY_VENDOR',
            'grade_source':'OFFICIAL_MLB_STATSAPI_BOXSCORE_ANALYTIC_ONLY',
            'platform_settlement_claim':False,
            'historical_scope':'EXTERNAL_RETROSPECTIVE_WITH_OFFICIAL_OUTCOME',
        })
        out.append(row)
    return out
