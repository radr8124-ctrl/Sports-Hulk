"""Safely archive the next official MLB postseason schedule/status snapshot.

Runs at most once per UTC day, after MLB's overnight results. Only the
public MLB StatsAPI schedule is read (no sportsbook/API account). Earlier
raw captures are never rewritten, and a failed capture keeps old proof.
"""
from __future__ import annotations

from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import requests

ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/"intelligence_warehouse/sport_cohorts/sources"
URL="https://statsapi.mlb.com/api/v1/schedule"
PARAMS={"sportId":1,"startDate":"2026-10-04","endDate":"2026-11-15"}
SERIES_TYPES={"W","D","L","F"}


def verify_response(raw:bytes)->dict:
    if len(raw)<512 or len(raw)>4_000_000:raise ValueError("Unreasonable MLB schedule payload")
    parsed=json.loads(raw)
    dates=parsed.get("dates")
    if not isinstance(dates,list) or not dates:
        raise ValueError("No original MLB schedule dates")
    ids=set()
    count=0
    for day in dates:
        for game in day.get("games") or []:
            gid=game.get("gamePk")
            if type(gid) is not int or gid in ids:
                raise ValueError("Duplicate or malformed official MLB game ID")
            ids.add(gid)
            t=game.get("gameType")
            if t not in SERIES_TYPES:
                raise ValueError("Unexpected non-postseason game type in postseason-only capture")
            if not game.get("gameDate") or not (game.get("teams") or {}).get("home") or not (game.get("teams") or {}).get("away"):
                raise ValueError("Missing original MLB teams/start")
            count+=1
    if count<10:raise ValueError("Incomplete postseason schedule; original evidence preserved")
    return {"schedule_games":count,"unique_game_ids":len(ids),
            "source_game_types":sorted({game.get("gameType") for date in dates for game in date["games"]})}


def archive_once(*, root=ROOT, now=None,session=None)->dict:
    at=now or datetime.now(timezone.utc)
    if not at.tzinfo:raise ValueError("UTC offset required")
    dest=root/"intelligence_warehouse/sport_cohorts/sources"/(
        "MLB_STATSAPI_POSTSEASON_SCHEDULE_"+at.astimezone(timezone.utc).strftime("%Y%m%d")+".raw.json")
    if dest.exists():
        raw=dest.read_bytes()
        stats=verify_response(raw)
        return {"status":"EXISTING_SOURCE_UNCHANGED","path":str(dest.relative_to(root)),
                "sha256":hashlib.sha256(raw).hexdigest(),**stats}
    http=session or requests
    response=http.get(URL,params=PARAMS,timeout=14)
    response.raise_for_status()
    raw=response.content
    stats=verify_response(raw)
    dest.parent.mkdir(parents=True,exist_ok=True)
    # Never replace a same-day file from a different worker/process; a prior
    # snapshot is still valid evidence even if its result status is older.
    try:
        fd=os.open(dest,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o644)
    except FileExistsError:
        return archive_once(root=root,now=at,session=session)
    try:
        with os.fdopen(fd,"wb") as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    return {"status":"NEW_ORIGINAL_SOURCE_ARCHIVED","path":str(dest.relative_to(root)),
            "sha256":hashlib.sha256(raw).hexdigest(),**stats}


if __name__=="__main__":
    print(json.dumps(archive_once(),indent=2))
