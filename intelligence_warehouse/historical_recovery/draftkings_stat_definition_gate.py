"""Gate for *potential* DraftKings or other external NFL stats before model use.

DraftKings's connected ChatGPT app returns scores/team statistics only; it is
not a sportsbook odds API and is not automatically connected to Sports Zenith.

This read-only QA helper is NOT wired into the frozen predictive pipeline.
It deliberately fails closed on unknown metric definitions / pregame clocks.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite


def utc(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        d=datetime.fromisoformat(value.strip().replace("Z","+00:00"))
    except ValueError:
        return None
    return d.astimezone(timezone.utc) if d.tzinfo else None


def scalar(value):
    if value is None or isinstance(value,bool):
        return None
    try:
        x=float(value)
    except (ValueError,TypeError):
        return None
    return x if isfinite(x) and x>=0 else None


def score_fixture_match(official, external):
    """Match team/clock/final on both sides; external ID != ESPN ID by design."""
    ao,bo=official.get("away"),external.get("away")
    ah,bh=official.get("home"),external.get("home")
    a=utc(official.get("kickoff_utc"))
    b=utc(external.get("kickoff_utc"))
    if not ao or not ah or ao!=bo or ah!=bh or ao==ah or not a or not b:
        return False
    if abs((a-b).total_seconds())>3*60:
        return False
    if official.get("final") is not True or external.get("final") is not True:
        return False
    for team in ("home","away"):
        x=scalar(official.get(team+"_points"))
        y=scalar(external.get(team+"_points"))
        if x is None or y is None or x!=y:
            return False
    return True


def check_game_yards(*, official: dict, external: dict) -> dict:
    """The 407 DK vs 399 official yards example is a definition mismatch.

    NFL official team net passing subtracts sack yards; an external summary
    may display gross passing + rushing and still label it 'Total Yards'.
    """
    if not score_fixture_match(official,external):
        return {
            "status":"QUARANTINE_UNVERIFIED_GAME_IDENTITY_OR_SCORE",
            "training_admitted":False,
            "historical_result_created":False,
        }
    official_total=scalar(official.get("away_net_yards"))
    external_total=scalar(external.get("away_total_yards"))
    external_pass=scalar(external.get("away_passing_yards"))
    external_rush=scalar(external.get("away_rushing_yards"))
    if any(x is None for x in (official_total,external_total,external_pass,external_rush)):
        return {
            "status":"QUARANTINE_MISSING_YARDAGE_DEFINITION",
            "training_admitted":False,
            "historical_result_created":False,
        }
    gross_sum=external_pass+external_rush
    if abs(gross_sum-external_total)>0.1:
        status="QUARANTINE_EXTERNAL_TOTAL_INTERNAL_INCONSISTENCY"
    elif abs(official_total-external_total)>0.1:
        status="QUARANTINE_POSSIBLE_GROSS_VS_NET_STAT_DEFINITION"
    else:
        # Identical numbers aren't evidence of identical semantic definition.
        status="SOURCE_NUMBERS_AGREE_SEMANTICS_NOT_INDEPENDENTLY_VERIFIED"
    return {
        "status":status,
        "official_net_yards":official_total,
        "external_reported_total_yards":external_total,
        "external_reported_passing_yards":external_pass,
        "external_reported_rushing_yards":external_rush,
        "external_pass_plus_rush_yards":gross_sum,
        "yardage_difference":round(external_total-official_total,2),
        "same_fixture_and_final_score":True,
        "external_stat_definition_independently_proven":False,
        "training_admitted":False,
        "historical_result_created":False,
    }


def assess_team_ppg(*, official_game_scores:list[int], external_ppg, scope=None):
    """Official scoreboard PF/game is not necessarily an external 'offense points' stat."""
    scores=[scalar(v) for v in official_game_scores]
    external=scalar(external_ppg)
    if not scores or any(v is None for v in scores) or external is None:
        return {"status":"QUARANTINE_INSUFFICIENT_OR_INVALID_SCORES",
                "training_admitted":False}
    correct=sum(scores)/len(scores)
    if scope!="SCOREBOARD_TOTAL_POINTS_PER_COMPLETED_REGULAR_SEASON_GAME":
        status="QUARANTINE_SCOPE_OR_DENOMINATOR_UNKNOWN"
    elif abs(correct-external)>0.11:
        status="QUARANTINE_OFFICIAL_SCOREBOARD_CONFLICT"
    else:
        status="SOURCE_SCOREBOARD_PPG_ARITHMETIC_MATCHES"
    return {
        "status":status,"official_completed_regular_games":len(scores),
        "official_scored_points":sum(scores),
        "official_scoreboard_ppg":round(correct,4),
        "external_reported_offensive_ppg":external,
        "scope":scope,
        "training_admitted":False,
        "needs_capture_and_phase_validation":True,
    }


def pregame_feature_admission(*, source_received_at, target_kickoff,
                            source_event_id, official_event_id, official_match_verified,
                            competition_phase, metric_semantics_verified,
                            already_completed_games, rolling_window=5):
    """Independent source candidate gate; never reads outcomes after original freeze."""
    captured=utc(source_received_at)
    kickoff=utc(target_kickoff)
    blockers=[]
    if captured is None or kickoff is None or captured>=kickoff:
        blockers.append("MISSING_OR_POSTSTART_PREGAME_CAPTURE")
    if not source_event_id or not official_event_id or official_match_verified is not True:
        blockers.append("EVENT_ID_NOT_INDEPENDENTLY_MATCHED")
    if competition_phase not in ("REGULAR","POSTSEASON","PRESEASON"):
        blockers.append("UNVERIFIED_COMPETITION_PHASE")
    if metric_semantics_verified is not True:
        blockers.append("METRIC_DEFINITION_UNKNOWN")
    if (not isinstance(already_completed_games,int) or isinstance(already_completed_games,bool)
            or already_completed_games<rolling_window or rolling_window not in (5,10,20)):
        blockers.append("INSUFFICIENT_PREVIOUS_GAMES_FOR_WINDOW")
    return {
        "status":"SOURCE_CANDIDATE_ELIGIBLE_FOR_FURTHER_ASOF_AUDIT" if not blockers
                  else "QUARANTINE_EXTERNAL_MODEL_INPUT",
        "blocking_reasons":blockers,
        "source_value_used_for_training":False,
        "final_training_admission_requires_prepared_immutable_feature_source":True,
        "independent_model_edge_proven":False,
    }
