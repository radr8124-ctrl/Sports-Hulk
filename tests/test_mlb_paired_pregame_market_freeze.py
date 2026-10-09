"""Only same-book time, line and officially mapped MLB player market pairs."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from intelligence_warehouse.historical_recovery.mlb_paired_pregame_market_freeze import (
    select_paired_market_sources,append_verified_paired_baselines,
    freeze_market_cycle,
)

NOW=datetime(2026,10,8,22,0,tzinfo=timezone.utc)
FIRST=datetime(2026,10,9,0,0,tzinfo=timezone.utc)
QUOTE=NOW-timedelta(minutes=8)
LINEUP=NOW-timedelta(hours=1)


def official_source():
    home=list(range(501,510));away=list(range(701,710))
    return {
        'schema':'MLB_PREGAME_SOURCE_EVIDENCE_V1',
        'evidence_id':'ORIGINAL_PRE_KICKOFF_PREVIEW_PROOF',
        'game_pk':849832,
        'captured_at_utc':LINEUP.isoformat(),
        'first_pitch_utc':FIRST.isoformat(),
        'fixture':{
            'away_team':'Cleveland Guardians',
            'home_team':'Chicago White Sox',
            'official_status_at_capture':'Pre-Game',
        },
        'lineups':{
            'status':'OFFICIAL_BATTING_ORDER_VISIBLE_BEFORE_KICKOFF',
            'home':{'player_ids':home,'player_names':['Example Hitter']+[f'Home {i}' for i in home[1:]],
                    'source':'LIVE_FEED_OFFICIAL_BATTING_ORDER_CAPTURED_PREGAME','confirmed_asof_capture':True},
            'away':{'player_ids':away,'player_names':[f'Away {i}' for i in away],
                    'source':'LIVE_FEED_OFFICIAL_BATTING_ORDER_CAPTURED_PREGAME','confirmed_asof_capture':True},
        },
    }


def official_raw_and_frozen():
    raw=json.dumps(official_source())+'\n'
    sha=hashlib.sha256(raw.encode()).hexdigest()
    row={
        'schema':'MLB_TRUE_PREGAME_RESEARCH_FEATURE_FREEZE_V2',
        'game_pk':849832,'player_id':501,
        'team_side_at_capture':'home',
        'source_evidence_id':'ORIGINAL_PRE_KICKOFF_PREVIEW_PROOF',
        'original_append_only_line_sha256':sha,
        'source_capture_at_utc':LINEUP.isoformat(),
        'feature_frozen_at_utc':(LINEUP+timedelta(minutes=3)).isoformat(),
        'scheduled_first_pitch_utc':FIRST.isoformat(),
        'source_history_revision':'OFFICIAL_FINAL_REGULAR_AND_POSTSEASON_V2',
        'source_history_verified_completed_through_date':'2026-10-07',
        'betting_prediction_written':False,'live_play_approved':False,
    }
    return raw,row


def fusion():
    return pd.DataFrame([{
        'event_id':'SPORTWIZ-MLB-MOCK',
        'start':FIRST.isoformat(),
        'away_team':'Cleveland Guardians',
        'home_team':'Chicago White Sox',
        'player_id':501,'player':'Example Hitter','team':'Chicago White Sox',
        'market_subtype':'PLAYER_TOTAL_HITS',
    }])


def quotes(*,book='draftkings',when=QUOTE,over=110,under=-130):
    return pd.DataFrame([
        {
            'provider':'sportwizzard','sportsbook':book,
            'event_id':'SPORTWIZ-MLB-MOCK','start':FIRST.isoformat(),
            'away_team':'Cleveland Guardians','home_team':'Chicago White Sox',
            'market':'PLAYER_TOTAL','market_subtype':'PLAYER_TOTAL_HITS',
            'selection':f'Example Hitter {side} 0.5',
            'side':side,'line':0.5,'price_american':price,
            'player_id':'provider-opaque-uuid-1',
            'player':'Example Hitter','captured_at':when.isoformat()
        } for side,price in [('OVER',over),('UNDER',under)]
    ])


class MLBTwoSidedBookPriceTruthTests(unittest.TestCase):
    def test_source_player_id_from_official_lineup_and_exact_two_side_price(self):
        _,v2=official_raw_and_frozen()
        raw=official_source()
        rows,summary=select_paired_market_sources(raw,[v2],fusion(),quotes(),now=NOW,source_file_sha256='a'*64,fusion_file_sha256='b'*64)
        self.assertEqual(len(rows),1)
        x=rows[0]
        self.assertEqual(x['mlbam_player_id'],501)
        self.assertEqual(x['player_name_official'],'Example Hitter')
        self.assertEqual(x['provider_player_id'],'provider-opaque-uuid-1')
        self.assertEqual(x['market_metric'],'hits')
        self.assertEqual(x['line'],0.5)
        self.assertAlmostEqual(x['market_fair_probability_over']+x['market_fair_probability_under'],1,places=10)
        self.assertGreater(x['book_overround'],1)
        self.assertLess(x['book_overround'],1.25)
        self.assertEqual(x['price_over_american'],110)
        self.assertEqual(x['price_under_american'],-130)
        self.assertFalse(x['model_prediction_created'])
        self.assertFalse(x['betting_selection_approved'])
        self.assertFalse(x['commercial_market_redistribution_approved'])
        self.assertEqual(summary['independent_games_with_qualifying_source_pairs'],1)

    def test_never_de_vig_across_different_books_or_mismatched_line(self):
        _,v2=official_raw_and_frozen()
        diff=quotes()
        diff.loc[1,'sportsbook']='fanduel'
        out,_=select_paired_market_sources(official_source(),[v2],fusion(),diff,now=NOW,source_file_sha256='a'*64,fusion_file_sha256='b'*64)
        self.assertEqual(out,[])
        changed=quotes();changed.loc[1,'line']=1.5
        out,_=select_paired_market_sources(official_source(),[v2],fusion(),changed,now=NOW,source_file_sha256='a'*64,fusion_file_sha256='b'*64)
        self.assertEqual(out,[])

    def test_wrong_name_team_event_id_and_wrong_player_uuid_fail_closed(self):
        _,v2=official_raw_and_frozen()
        for change in ('player','team','event_id'):
            other=fusion()
            other.loc[0,change]={'player':'Other Name','team':'Cleveland Guardians','event_id':'DIFFERENT'}[change]
            with self.subTest(change=change):
                output,_=select_paired_market_sources(official_source(),[v2],other,quotes(),now=NOW,source_file_sha256='a'*64,fusion_file_sha256='b'*64)
                self.assertEqual(output,[])
        raw=quotes()
        raw.loc[1,'player_id']='DIFFERENT_PLAYER_UUID'
        output,_=select_paired_market_sources(official_source(),[v2],fusion(),raw,now=NOW,source_file_sha256='a'*64,fusion_file_sha256='b'*64)
        self.assertEqual(output,[])

    def test_overside_only_and_odds_capture_after_first_pitch_are_ineligible(self):
        _,v2=official_raw_and_frozen()
        output,_=select_paired_market_sources(official_source(),[v2],fusion(),quotes().iloc[:1],now=NOW,source_file_sha256='a'*64,fusion_file_sha256='b'*64)
        self.assertEqual(output,[])
        after=quotes(when=FIRST+timedelta(minutes=3))
        output,_=select_paired_market_sources(official_source(),[v2],fusion(),after,now=NOW,source_file_sha256='a'*64,fusion_file_sha256='b'*64)
        self.assertEqual(output,[])
        stale=quotes(when=NOW-timedelta(minutes=95))
        output,_=select_paired_market_sources(official_source(),[v2],fusion(),stale,now=NOW,source_file_sha256='a'*64,fusion_file_sha256='b'*64)
        self.assertEqual(output,[])

    def test_duplicate_side_or_impossible_vig_refuses_to_freeze(self):
        _,v2=official_raw_and_frozen()
        rows=quotes()
        duplicate=pd.concat([rows,rows.iloc[:1]],ignore_index=True)
        with self.assertRaisesRegex(ValueError,'[Dd]uplicate'):
            select_paired_market_sources(official_source(),[v2],fusion(),duplicate,now=NOW,source_file_sha256='a'*64,fusion_file_sha256='b'*64)
        odd=quotes(over=1000,under=1000)
        found,_=select_paired_market_sources(official_source(),[v2],fusion(),odd,now=NOW,source_file_sha256='a'*64,fusion_file_sha256='b'*64)
        self.assertEqual(found,[])

    def test_immutable_first_qualifying_quote_never_silently_replaced(self):
        _,v2=official_raw_and_frozen()
        sample,_=select_paired_market_sources(official_source(),[v2],fusion(),quotes(),now=NOW,source_file_sha256='a'*64,fusion_file_sha256='b'*64)
        with tempfile.TemporaryDirectory() as temp:
            ledger=Path(temp)/'MARKET_BASELINE.jsonl'
            self.assertEqual(append_verified_paired_baselines(ledger,sample),1)
            preserved=ledger.read_bytes()
            self.assertEqual(append_verified_paired_baselines(ledger,sample),0)
            self.assertEqual(ledger.read_bytes(),preserved)
            changed,_=select_paired_market_sources(official_source(),[v2],fusion(),quotes(over=105,under=-132),now=NOW,source_file_sha256='c'*64,fusion_file_sha256='b'*64)
            self.assertEqual(append_verified_paired_baselines(ledger,changed),0)
            self.assertEqual(ledger.read_bytes(),preserved)

    def test_real_cycle_is_explicitly_not_betting_model_and_has_original_lineup_digest(self):
        original,v2=official_raw_and_frozen()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source=root/'MLB_ORIGINAL_PREGAME.jsonl'
            frozen=root/'V2_FROZEN.jsonl'
            fused=root/'PLAYER_FUSION.csv'
            markets=root/'MLB_PLAYER_PROP_MARKET_20261008T215200Z.csv'
            target=root/'OUT.jsonl'
            source.write_text(original)
            frozen.write_text(json.dumps(v2)+'\n')
            fusion().to_csv(fused,index=False)
            quotes().to_csv(markets,index=False)
            result=freeze_market_cycle(source,frozen,fused,markets,target,now=NOW)
            self.assertEqual(result['market_baseline_pairs_frozen'],1)
            self.assertEqual(result['independent_game_ids'],1)
            self.assertFalse(result['paid_bets_approved'])
            self.assertFalse(result['model_fitted_or_promoted'])
            self.assertEqual(len(target.read_text().splitlines()),1)
            record=json.loads(target.read_text())
            self.assertEqual(record['original_lineup_source_line_sha256'],hashlib.sha256(original.encode()).hexdigest())
            again=freeze_market_cycle(source,frozen,fused,markets,target,now=NOW)
            self.assertEqual(again['market_baseline_pairs_frozen'],0)

if __name__=='__main__':
    unittest.main()
