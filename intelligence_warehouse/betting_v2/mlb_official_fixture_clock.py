"""Strict, non-invented MLB gamePk/competition identity for public prop research.

A sportsbook UUID is not an MLB gamePk. Uniquely crosswalk original provider
player/team/start against the official MLB StatsAPI schedule, with a 3-minute
start tolerance. If the provider timestamps disagree, quarantine that *row*
without revising source odds, source history, or original frozen research.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
import math
import re
import unicodedata

POSTSEASON = {
    'W': 'POSTSEASON_WILD_CARD',
    'D': 'POSTSEASON_DIVISION_SERIES',
    'L': 'POSTSEASON_LEAGUE_CHAMPIONSHIP',
    'F': 'POSTSEASON_WORLD_SERIES',
}
OTHER = {
    'R': 'REGULAR_SEASON',
    'S': 'SPRING_TRAINING',
    'E': 'EXHIBITION',
    'A': 'ALL_STAR',
}
ALL_TYPES = {**POSTSEASON, **OTHER}
CLOCK_TOLERANCE_SECONDS = 180


def normalized(value):
    text = unicodedata.normalize('NFKD',str(value or ''))
    return re.sub(r'[^a-z0-9]','',text.encode('ascii','ignore').decode('ascii').lower())


def utc_datetime(value):
    if isinstance(value,datetime):
        dt=value
    else:
        try:
            dt=datetime.fromisoformat(str(value or '').strip().replace('Z','+00:00'))
        except (TypeError,ValueError,OverflowError):
            return None
    return dt.astimezone(timezone.utc) if dt.tzinfo else None


def int_pk(value):
    if isinstance(value,bool):return None
    try:
        n=float(value)
        return int(n) if math.isfinite(n) and n.is_integer() and 100000<=n<=9999999 else None
    except (ValueError,TypeError,OverflowError):
        return None


def schedule_index(frame):
    """Convert one official schedule CSV snapshot to stable lookup by teams."""
    result=defaultdict(list)
    mandatory=('gamePk','gameType','gameDate','away_team','home_team')
    if frame is None or not set(mandatory).issubset(frame.columns):
        return {}
    for row in frame.to_dict('records'):
        pk=int_pk(row.get('gamePk'))
        date=utc_datetime(row.get('gameDate'))
        away=normalized(row.get('away_team'))
        home=normalized(row.get('home_team'))
        kind=str(row.get('gameType') or '').upper().strip()
        if pk is None or date is None or not away or not home or away==home or kind not in ALL_TYPES:
            continue
        entry={
            'mlb_official_gamePk':str(pk),
            'mlb_official_game_type':kind,
            'competition_regime':ALL_TYPES[kind],
            'mlb_official_original_start':date.isoformat(),
            'mlb_official_away_team':str(row['away_team']),
            'mlb_official_home_team':str(row['home_team']),
            'mlb_schedule_source':'MLB_STATSAPI_OFFICIAL_SCHEDULE',
        }
        result[(away,home)].append(entry)
    return dict(result)


def crosswalk(original_identity, schedule):
    """Return evidence only when exact club pair and uniquely matching tip exist.

    Retain source event UUID separately: it is NOT an official fixture ID.
    A row with an otherwise valid club pair but 3-hour wrong provider start
    is held from CURRENT public research until the source itself corrects it.
    """
    if not original_identity:
        return None
    if original_identity.get('mlb_source_identity_provenance')!='MLB_DECISION_EXPLICIT_PLAYER_ID_TEAM':
        return None
    club_a=normalized(original_identity.get('mlb_source_away_team'))
    club_h=normalized(original_identity.get('mlb_source_home_team'))
    player_team=normalized(original_identity.get('mlb_source_player_team'))
    original_start=utc_datetime(original_identity.get('mlb_source_original_start'))
    if not all((club_a,club_h,player_team,original_start)) or player_team not in (club_a,club_h):
        return None
    matches=[]
    for event in schedule.get((club_a,club_h),()):
        official_start=utc_datetime(event.get('mlb_official_original_start'))
        if official_start is not None and abs((official_start-original_start).total_seconds())<=CLOCK_TOLERANCE_SECONDS:
            matches.append(event)
    if len(matches)!=1:
        return None
    validated=matches[0].copy()
    validated['mlb_official_fixture_verified']=True
    validated['mlb_provider_start_delta_seconds']=round((original_start-utc_datetime(validated['mlb_official_original_start'])).total_seconds())
    validated['mlb_roster_membership_officially_verified_for_this_game']=False
    validated['mlb_original_source_market_offer_executable_verified']=False
    return validated
