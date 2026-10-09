"""Future ONLY: corroborate replacement of a previously fictional NL bracket fixture.

Never infer teams from brackets, odds, standings or a single quote. A real,
timestamped original pregame MLB schedule capture + separately archived raw
public StatsAPI response + freshly refetched current official fixture must
match exactly before the future historical MASTER can be reconciled.

This is *schedule identity* only, not batting order, starter, bet or projection.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime,timezone,timedelta
from pathlib import Path

RAW_DIRECTORY="intelligence_warehouse/mlb_pregame_capture/official_future_schedule_raw"
SCHEMA="MLB_RESEARCH_FUTURE_OFFICIAL_SCHEDULE_SECOND_RAW_V1"
ALLOWED_ORIGINAL={
    ("NL Higher Seed","5517","NL Lower Seed","5525","NL Stadium","3833",
     "NL Championship Series","L","1"),
}


def instant(v):
    try:
        x=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return x.astimezone(timezone.utc) if x.tzinfo else None
    except (TypeError,ValueError,OverflowError):
        return None


def identity(v):
    x=str(v or "").strip()
    return x[:-2] if x.endswith(".0") and x[:-2].isdigit() else x


def resolved(name):
    x=str(name or "").strip()
    return bool(x) and not any(t in x.lower() for t in
              ("tbd","winner","higher seed","lower seed","/","pending"))


def load_archived_original_responses(root):
    """Verify the original bytes of each archived HTTP 200 schedule response."""
    folder=Path(root)/RAW_DIRECTORY
    if not folder.is_dir():return []
    result=[]
    for metadata in sorted(folder.glob("*_RECEIPT.json")):
        j=json.loads(metadata.read_text())
        if j.get("schema")!=SCHEMA or j.get("response_status")!=200:
            raise ValueError("UNVERIFIED_ORIGINAL_MLB_SCHEDULE_RECEIPT")
        source=Path(j.get("source_filename") or "")
        if source.parent!=Path(RAW_DIRECTORY) or source.name!=metadata.name.replace("_RECEIPT.json",".json"):
            raise ValueError("ORIGINAL_SCHEDULE_RAW_FILENAME_MISMATCH")
        b=(Path(root)/source).read_bytes()
        if len(b)>180000 or hashlib.sha256(b).hexdigest()!=j.get("response_sha256"):
            raise ValueError("TAMPERED_OR_UNBOUNDED_ORIGINAL_MLB_SCHEDULE_RESPONSE")
        if not str(j.get("source_uri") or "").startswith("https://statsapi.mlb.com/api/v1/schedule?"):
            raise ValueError("NOT_OFFICIAL_MLB_SOURCE_URL")
        raw=json.loads(b)
        source_game=[x for day in raw.get("dates",[]) for x in day.get("games",[])
                     if identity(x.get("gamePk"))==str(j.get("official_game_pk"))]
        if len(source_game)!=1:
            raise ValueError("ORIGINAL_MLB_SOURCE_GAME_NOT_UNIQUE")
        g=source_game[0]
        away=(g.get("teams",{}).get("away") or {}).get("team") or {}
        home=(g.get("teams",{}).get("home") or {}).get("team") or {}
        venue=g.get("venue") or {}
        if (g.get("gameDate")!=j.get("official_game_utc")
            or g.get("officialDate")!=j.get("official_date")
            or g.get("gameType")!=j.get("official_game_type")
            or (g.get("status") or {}).get("detailedState")!="Scheduled"
            or identity(venue.get("id"))!=identity(j.get("venue_id"))
            or venue.get("name")!=j.get("venue_name")
            or any(identity(team.get("id"))!=identity(j.get(side+"_team_id"))
                   or str(team.get("name"))!=j.get(side+"_team_name")
                   or team.get("placeholder") is True
                   or identity((team.get("league") or {}).get("id"))!="104"
                   for side,team in (("away",away),("home",home)))):
            raise ValueError("ORIGINAL_MLB_SCHEDULE_RECEIPT_FIELDS_NOT_IN_RAW_SOURCE")
        result.append({"receipt":j,"raw":g})
    return result


def verified_nl_placeholder_overrides(master,official,observations,archived,*,clock):
    if clock.tzinfo is None:raise ValueError("MLB_RECONCILIATION_CLOCK_MUST_BE_AWARE")
    now=clock.astimezone(timezone.utc)
    if "gamePk" not in master or master.gamePk.duplicated().any():
        raise ValueError("DUPLICATED_MLB_MASTER_GAME")
    previous={identity(x["gamePk"]):x for _,x in master.iterrows()}
    out={}
    for gamepk,new in official.items():
        old=previous.get(str(gamepk))
        if old is None:continue
        oldtuple=(str(old.get("home_team")),identity(old.get("home_team_id")),
                  str(old.get("away_team")),identity(old.get("away_team_id")),
                  str(old.get("venue")),identity(old.get("venue_id")),
                  str(old.get("seriesDescription")),str(old.get("gameType")),
                  identity(old.get("gameNumber")))
        if oldtuple not in ALLOWED_ORIGINAL:continue
        if str(old.get("status"))!="Scheduled" or new.get("status")!="Scheduled":continue
        oldstart=instant(old.get("gameDate"));newstart=instant(new.get("gameDate"))
        if (not oldstart or not newstart or not
            now+timedelta(minutes=30)<oldstart<newstart
            or (newstart-oldstart)>timedelta(hours=36)
            or str(old.get("officialDate"))!=new.get("officialDate")
            or str(old.get("gameType"))!=new.get("gameType")
            or identity(old.get("gameNumber"))!=identity(new.get("gameNumber"))):
            continue
        if (not all(resolved(new.get(s+"_team")) for s in ("home","away"))
            or any(not identity(new.get(s+"_team_id")).isdigit()
                   or int(identity(new.get(s+"_team_id")))>1000 for s in ("home","away"))):
            continue
        primary=[]
        for original in observations:
            if original.get("schema")!="MLB_PREGAME_SOURCE_EVIDENCE_V1" or identity(original.get("game_pk"))!=str(gamepk):
                continue
            at=instant(original.get("captured_at_utc"))
            fx=original.get("fixture") or {}
            if (not at or not at<oldstart or not at<=now
                or instant(original.get("first_pitch_utc"))!=newstart
                or original.get("lineups",{}).get("status")=="OFFICIAL_BATTING_ORDER_VISIBLE_BEFORE_KICKOFF"
                or fx.get("official_game_type")!=new.get("gameType")
                or fx.get("official_date")!=new.get("officialDate")
                or fx.get("official_status_at_capture")!="Scheduled"
                or identity(fx.get("venue_id"))!=identity(new.get("venue_id"))
                or any(identity(fx.get(s+"_team_id"))!=identity(new.get(s+"_team_id"))
                       or str(fx.get(s+"_team"))!=str(new.get(s+"_team")) for s in ("home","away"))):
                continue
            if not original.get("evidence_id") or not original.get("_raw_source_line_sha256"):
                continue
            primary.append((at,original))
        for capture in archived:
            j=capture["receipt"]
            if identity(j.get("official_game_pk"))!=str(gamepk):continue
            later=instant(j.get("independent_received_at_utc"))
            if not later or not later<oldstart or later>now:continue
            x=capture["raw"]
            venue=x.get("venue") or {}
            home=(x.get("teams",{}).get("home") or {}).get("team") or {}
            away=(x.get("teams",{}).get("away") or {}).get("team") or {}
            if (x.get("gameDate")!=new.get("gameDate")
                or x.get("officialDate")!=new.get("officialDate")
                or x.get("gameType")!=new.get("gameType")
                or identity(x.get("gameNumber"))!=identity(new.get("gameNumber"))
                or identity(venue.get("id"))!=identity(new.get("venue_id"))
                or not resolved(venue.get("name"))
                or any(identity(team.get("id"))!=identity(new.get(s+"_team_id"))
                       or team.get("name")!=new.get(s+"_team")
                       or identity((team.get("league") or {}).get("id"))!="104"
                       for s,team in (("home",home),("away",away)))):
                continue
            for earlier,original in primary:
                if later-earlier<timedelta(minutes=15):continue
                if original.get("evidence_id")!=j.get("original_earlier_evidence_id"):
                    continue
                if original["_raw_source_line_sha256"]!=j.get("original_earlier_line_sha256"):
                    continue
                out[str(gamepk)]={
                    "proof_type":"NL_FUTURE_PLACEHOLDER_REPLACEMENT_FROM_TWO_ORIGINAL_OFFICIAL_SOURCE_CAPTURES",
                    "gamePk":str(gamepk),
                    "original_old_start":str(old.get("gameDate")),
                    "verified_real_start":str(new["gameDate"]),
                    "original_placeholder_game_type":str(old.get("gameType")),
                    "official_date":str(new["officialDate"]),
                    "original_placeholder_home":str(old.get("home_team")),
                    "original_placeholder_away":str(old.get("away_team")),
                    "resolved_home_team_id":identity(new.get("home_team_id")),
                    "resolved_away_team_id":identity(new.get("away_team_id")),
                    "resolved_home_team_name":str(new.get("home_team")),
                    "resolved_away_team_name":str(new.get("away_team")),
                    "resolved_venue_id":identity(new.get("venue_id")),
                    "resolved_venue_name":venue["name"],
                    "original_pregame_evidence_id":original["evidence_id"],
                    "original_pregame_line_sha256":original["_raw_source_line_sha256"],
                    "second_original_schedule_response_sha256":j["response_sha256"],
                    "first_source_captured_utc":earlier.isoformat(),
                    "second_source_captured_utc":later.isoformat(),
                    "independent_original_captures":2,
                    "source_payloads_held_private":True,
                    "original_batting_orders_or_starters_verified":False,
                    "original_bets_or_model_predictions_changed":False,
                }
                break
            if str(gamepk) in out:break
    return out
