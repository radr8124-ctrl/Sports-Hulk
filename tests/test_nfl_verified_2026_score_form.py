"""Source verified prior-2026 NFL points forms, not played-week outcome leakage."""
from __future__ import annotations
import copy,hashlib,json,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
import pandas as pd
from intelligence_warehouse.historical_recovery.nfl_verified_2026_score_form import (
    verify_completed_nfl_weeks,
    freeze_nfl_current_team_context,
    append_first_source_rows,
    verified_prior_nfl_game_form,
    completed_full_week_numbers,
)

CLOCK=datetime(2026,10,9,1,30,tzinfo=timezone.utc)
FUTURE=datetime(2026,10,11,17,tzinfo=timezone.utc)
YEAR=2026
def fixture(game='2026_01_CIN_MIA',espn=401555001,week=1,home='MIA',away='CIN',hscore=24,ascore=17,
            gameday='2026-09-13',status=True):
    return {
        'game_id':game,'espn':espn,'season':YEAR,'week':week,'game_type':'REG',
        'gameday':gameday,'home_team':home,'away_team':away,
        'home_score':hscore if status else None,'away_score':ascore if status else None,
        'home_rest':7,'away_rest':7,'location':'Home','stadium':'Hard Rock Stadium',
    }

def event(fix,home_abbr=None,away_abbr=None,home_score=None,away_score=None,final=True):
    home=home_abbr or fix['home_team']
    away=away_abbr or fix['away_team']
    ids={'MIA':'15','CIN':'4','LAR':'14','LA':'14','WAS':'28','WSH':'28','NYJ':'20'}
    return {
        'id':str(fix['espn']),'date':'2026-09-13T17:00Z',
        'season':{'year':2026,'type':2},
        'week':{'number':fix['week']},
        'status':{'type':{'name':'STATUS_FINAL' if final else 'STATUS_IN_PROGRESS','completed':final}},
        'competitions':[{
            'competitors':[
               {'homeAway':'home','team':{'abbreviation':home,'id':ids.get(home,'99')},'score':str(fix['home_score'] if home_score is None else home_score)},
               {'homeAway':'away','team':{'abbreviation':away,'id':ids.get(away,'99')},'score':str(fix['away_score'] if away_score is None else away_score)},
            ]
        }],
    }

def payload(fix):
    return {'events':[event(fix)],'week':{'number':fix['week']},'season':{'year':2026}}

def original_future(game_id='401872982',home='MIA',away='CIN',when=FUTURE,week=5):
    return {
        'schema':'SPORTS_NHL_NFL_PREGAME_SOURCE_V1',
        'official_game_id':game_id,
        'captured_at_utc':'2026-10-09T00:40:37Z',
        'scheduled_start_utc':when.isoformat(),
        'fixture':{
            'home_team':home,'away_team':away,
            'home_espn_team_id':'15','away_espn_team_id':'4',
            'home_espn_team_name':'Miami Dolphins','away_espn_team_name':'Cincinnati Bengals',
            'season_year':2026,'week':week,'game_state_asof':'STATUS_SCHEDULED',
            'actual_stadium_roof_state':'UNKNOWN_NOT_OBSERVED','venue_indoor_attribute':False,
        },
        'model_pick_approved':False,
        'starter_confirmed':False,
        'bankroll_or_sportsbook_action':False,
    }

def future_schedule():
    return pd.DataFrame([fixture(
        game='2026_05_CIN_MIA',espn=401872982,week=5,
        status=False,gameday='2026-10-11'
    )])

class NFL2026OriginalOfficialResultsStrictTests(unittest.TestCase):
    def test_exact_espn_game_id_team_scores_and_prior_week_match(self):
        f=fixture()
        rows,audit=verify_completed_nfl_weeks(
            pd.DataFrame([f]),{1:payload(f)},captured_at_utc=CLOCK,source_schedule_sha256='a'*64)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['official_espn_game_id'],'401555001')
        self.assertEqual(rows[0]['home_points'],24)
        self.assertEqual(rows[0]['away_points'],17)
        self.assertEqual(rows[0]['week'],1)
        self.assertTrue(rows[0]['official_espn_final_confirmed'])
        self.assertEqual(audit['source_disagreements'],0)

    def test_wrong_provider_score_and_team_cannot_silently_merge(self):
        f=fixture()
        altered=payload(f)
        altered['events'][0]['competitions'][0]['competitors'][0]['score']='15'
        with self.assertRaisesRegex(ValueError,'score'):
            verify_completed_nfl_weeks(pd.DataFrame([f]),{1:altered},
                captured_at_utc=CLOCK,source_schedule_sha256='a'*64)
        altered=payload(f)
        altered['events'][0]['competitions'][0]['competitors'][0]['team']['abbreviation']='NYJ'
        with self.assertRaisesRegex(ValueError,'team'):
            verify_completed_nfl_weeks(pd.DataFrame([f]),{1:altered},
                captured_at_utc=CLOCK,source_schedule_sha256='a'*64)

    def test_legitimate_Rams_LAR_to_LA_and_Washington_WSH_to_WAS_aliases(self):
        for source_abbr,canonical in [('LAR','LA'),('WSH','WAS')]:
            f=fixture(home=canonical,game=f'2026_01_CIN_{canonical}')
            payload_=payload(f)
            payload_['events'][0]['competitions'][0]['competitors'][0]['team']['abbreviation']=source_abbr
            matches,audit=verify_completed_nfl_weeks(pd.DataFrame([f]),{1:payload_},
                captured_at_utc=CLOCK,source_schedule_sha256='a'*64)
            self.assertEqual(matches[0]['home_team'],canonical)
            self.assertEqual(matches[0]['original_espn_home_abbreviation'],source_abbr)

    def test_live_nonfinal_must_not_become_verified_score(self):
        f=fixture()
        bad=payload(f)
        bad['events'][0]['status']['type']['name']='STATUS_IN_PROGRESS'
        with self.assertRaisesRegex(ValueError,'Final'):
            verify_completed_nfl_weeks(pd.DataFrame([f]),{1:bad},
                captured_at_utc=CLOCK,source_schedule_sha256='a'*64)

    def test_duplicate_independent_espn_id_and_future_game_rejected(self):
        a=fixture()
        bad=pd.DataFrame([a,a])
        with self.assertRaisesRegex(ValueError,'[Dd]uplicate'):
            verify_completed_nfl_weeks(bad,{1:payload(a)},captured_at_utc=CLOCK,source_schedule_sha256='a'*64)
        early=CLOCK-timedelta(weeks=20)
        with self.assertRaisesRegex(ValueError,'future'):
            verify_completed_nfl_weeks(pd.DataFrame([a]),{1:payload(a)},
                captured_at_utc=early,source_schedule_sha256='a'*64)

    def test_never_freeze_partial_week_when_thursday_is_final_but_sunday_unplayed(self):
        thursday=fixture(week=5,game='2026_05_TB_DAL',home='MIA',away='CIN',
                         gameday='2026-10-08',hscore=27,ascore=14)
        sunday=fixture(week=5,game='2026_05_CIN_MIA',home='MIA',away='CIN',
                        gameday='2026-10-11',status=False)
        partial=pd.DataFrame([thursday,sunday])
        self.assertEqual(completed_full_week_numbers(partial),[])
        sunday['home_score']=19
        sunday['away_score']=22
        all_final=pd.DataFrame([thursday,sunday])
        self.assertEqual(completed_full_week_numbers(all_final),[5])

    def test_feature_prior_same_season_week_never_uses_today_or_future_results(self):
        # Equal Week5 scores from the target game cannot enter target features.
        rows=[]
        for week in range(1,5):
            rows.extend([
                {'game_id':f'2026_{week:02d}_CIN_MIA','season':2026,'week':week,
                 'home_team':'MIA','away_team':'CIN','home_points':20+week,
                 'away_points':14+week,'final_observed_at_utc':'2026-10-07T01:00:00Z',
                 'source_first_pitch_utc':'2026-09-20T17:00:00Z','official_espn_final_confirmed':True},
            ])
        frame=pd.DataFrame(rows)
        expected=verified_prior_nfl_game_form(frame,'MIA',2026,5,FUTURE,asof=CLOCK)
        self.assertEqual(expected['games_available'],3)
        poison=frame.copy()
        poison.loc[len(poison)]={
            **rows[-1],'game_id':'2026_05_CIN_MIA','week':5,
            'home_points':4000,'away_points':0,
        }
        actual=verified_prior_nfl_game_form(poison,'MIA',2026,5,FUTURE,asof=CLOCK)
        self.assertEqual(actual,expected)

    def test_full_week5_context_on_independent_final_only(self):
        prev=[]
        for week in range(1,5):
            prev.append({
                'game_id':f'2026_{week:02d}_CIN_MIA','season':2026,'week':week,
                'home_team':'MIA','away_team':'CIN','home_points':20+week,
                'away_points':13+week,'official_espn_final_confirmed':True,
                'source_first_pitch_utc':'2026-09-20T17:00:00Z',
                'final_observed_at_utc':'2026-10-09T01:00:00Z',
            })
        schedule=future_schedule()
        original=original_future()
        context,meta=freeze_nfl_current_team_context(
            [original],schedule,pd.DataFrame(prev),now=CLOCK,
            official_espn_source_sha256='a'*64,
            schedule_snapshot_sha256='b'*64,
            historical_model_sha256='c'*64
        )
        self.assertEqual(len(context),1)
        self.assertEqual(context[0]['official_espn_event_id'],'401872982')
        self.assertTrue(context[0]['source_team_form_first_frozen_at_utc']<context[0]['official_first_pitch_utc'])
        self.assertEqual(context[0]['source_2026_prior_final_team_home_games'],3)
        self.assertEqual(len(context[0]['nine_features_excluding_market']),7)
        self.assertEqual(meta['unique_future_espn_games'],1)
        self.assertFalse(context[0]['actual_stadium_roof_state_confirmed'])
        self.assertFalse(context[0]['betting_play_authorized'])

    def test_immutable_future_context_never_rewrites_prior_games(self):
        prev=[{
            'game_id':'2026_04_CIN_MIA','season':2026,'week':4,
            'home_team':'MIA','away_team':'CIN','home_points':24,
            'away_points':17,'official_espn_final_confirmed':True,
            'source_first_pitch_utc':'2026-10-05T17:00:00Z',
            'final_observed_at_utc':'2026-10-09T01:00:00Z',
        }]
        first,_=freeze_nfl_current_team_context(
            [original_future()],future_schedule(),pd.DataFrame(prev),now=CLOCK,
            official_espn_source_sha256='a'*64,schedule_snapshot_sha256='b'*64,
            historical_model_sha256='c'*64)
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'CONTEXT.jsonl'
            self.assertEqual(append_first_source_rows(file,first),1)
            first_bytes=file.read_bytes()
            self.assertEqual(append_first_source_rows(file,first),0)
            rewritten=copy.deepcopy(first);rewritten[0]['nine_features_excluding_market'][0]=999
            with self.assertRaisesRegex(ValueError,'conflict'):
                append_first_source_rows(file,rewritten)
            self.assertEqual(file.read_bytes(),first_bytes)

if __name__=='__main__':
    unittest.main()
