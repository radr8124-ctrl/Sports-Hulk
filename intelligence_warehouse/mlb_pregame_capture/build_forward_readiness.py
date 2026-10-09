"""Official schedule/source-readiness watchdog for prospective MLB research.

Read-only to every model, market, official game master, grade, and prediction.
Caches only publicly available MLB StatsAPI schedule evidence; no new API
provider credits, no data inferred from missing starters or odds.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "intelligence_warehouse/mlb_pregame_capture"
MASTER = ROOT / "baseball_vault/derived/MLB_GAME_MASTER.csv"
EVIDENCE = BASE / "MLB_PREGAME_SOURCE_EVIDENCE.jsonl"
V2 = BASE / "MLB_RESEARCH_ASOF_FEATURE_FREEZE_V2.jsonl"
V3 = BASE / "MLB_V3_PROBABLE_PITCHER_PRIOR_PARK_RESEARCH.jsonl"
V4 = BASE / "MLB_V4_TEAM_PARK_HITTER_16FEATURE_ASOF_CONTEXT.jsonl"
FORECAST = BASE / "MLB_V4_SIXTEEN_FEATURE_ACTUAL_FORWARD_SHADOW.jsonl"
GRADED = BASE / "MLB_V4_FULL16_SAME_NEW_QUOTE_OFFICIAL_THREEWAY_SCORES.jsonl"
CACHE = BASE / "MLB_OFFICIAL_FUTURE_SCHEDULE_CACHE.json"
SUMMARY = BASE / "MLB_NEXT_GAME_SOURCE_READINESS.json"
OFFICIAL_URL = "https://statsapi.mlb.com/api/v1/schedule"
SCHEMA = "MLB_OFFICIAL_NEXT_GAME_RESEARCH_READINESS_V1"


def moment(text: object) -> datetime | None:
    try:
        x = datetime.fromisoformat(str(text).replace("Z","+00:00"))
        return x.astimezone(timezone.utc) if x.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def jsonl(path: Path) -> list[dict]:
    if not path.exists(): return []
    with path.open("r",encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def counts(records: list[dict], idfield: str) -> dict[int,int]:
    c=Counter()
    for x in records:
        try: c[int(x[idfield])] += 1
        except (ValueError, KeyError, TypeError): continue
    return dict(c)


def verified_lineup(source: dict | None, official_start: datetime) -> bool:
    if not source: return False
    timestamp=moment(source.get("captured_at_utc"))
    reported=moment(source.get("first_pitch_utc"))
    if timestamp is None or reported is None or not (timestamp < official_start):
        return False
    if abs((reported-official_start).total_seconds())>180:
        return False
    lineup=source.get("lineups") or {}
    if lineup.get("status")!="OFFICIAL_BATTING_ORDER_VISIBLE_BEFORE_KICKOFF":
        return False
    for side in ("home","away"):
        r=lineup.get(side) or {}
        ids=r.get("player_ids") or []
        if r.get("confirmed_asof_capture") is not True or len(ids)!=9 or len(set(str(x) for x in ids))!=9:
            return False
    return True


def official_fixtures(schedule: dict) -> dict[int, dict]:
    out={}
    for day in schedule.get("dates",[]):
        for g in day.get("games",[]):
            try: pk=int(g["gamePk"])
            except (ValueError,TypeError,KeyError):continue
            if pk in out:raise ValueError(f"DUPLICATE_OFFICIAL_GAME_PK:{pk}")
            teams=g.get("teams") or {}
            out[pk] = {
                "pk":pk,"start":moment(g.get("gameDate")),
                "status":str((g.get("status") or {}).get("detailedState") or ""),
                "home":(teams.get("home") or {}).get("team") or {},
                "away":(teams.get("away") or {}).get("team") or {},
                "type":str(g.get("gameType") or ""),
            }
    return out


def _not_placeholder(name: str) -> bool:
    value=str(name).strip().lower()
    return bool(value) and not any(v in value for v in ("higher seed","lower seed","winner","tbd","/"))


def audit(schedule: dict, master: pd.DataFrame, evidence: list[dict], *ledgers: list[dict], now: datetime, window_hours: int=72) -> dict:
    if now.tzinfo is None:raise ValueError("AUDIT_CLOCK_MUST_HAVE_UTC_OFFSET")
    src=official_fixtures(schedule)
    if not src:raise ValueError("EMPTY_OFFICIAL_SCHEDULE_NOT_SAFE_FOR_QUARANTINE")
    future=master.copy()
    future["utc_start"]=pd.to_datetime(future.gameDate,utc=True,errors="coerce")
    future=future[future.utc_start.ge(pd.Timestamp(now))
                  & future.utc_start.le(pd.Timestamp(now+timedelta(hours=window_hours)))].copy()
    future=future[future.status.astype(str).str.lower().isin(("scheduled","pre-game","preview","warmup"))]
    ids=Counter(int(x) for x in future.gamePk)
    if any(n>1 for n in ids.values()):raise ValueError("DUPLICATED_ORIGINAL_MASTER_GAME_PK")
    original={int(r["gamePk"]):r for r in future.to_dict("records")}
    official_ids={pk:x for pk,x in src.items() if x["start"] is not None
         and now < x["start"] <= now+timedelta(hours=window_hours)
         and x["status"].lower() in ("scheduled","pre-game","preview","warmup")}
    latest={}
    for x in evidence:
        try: pk=int(x["game_pk"])
        except (TypeError,ValueError,KeyError):continue
        captured=moment(x.get("captured_at_utc"))
        if captured is None or captured > now:continue
        # Newer source may be unconfirmed; old original evidence is immutable.
        if pk not in latest or captured>moment(latest[pk]["captured_at_utc"]):
            latest[pk]=x
    all_keys=sorted(set(original)|set(official_ids))
    stage=[counts(rows,ident) for rows,ident in zip(ledgers,("game_pk","official_game_pk","game_pk","official_game_pk","official_game_pk"))]
    output=[]
    for pk in all_keys:
        old=original.get(pk)
        new=src.get(pk)
        if new is None:
            status="MASTER_GAME_NOT_ON_CURRENT_OFFICIAL_SCHEDULE"
        elif new["start"] is None or new["status"].lower() not in ("scheduled","pre-game","preview","warmup"):
            status="OFFICIAL_GAME_NOT_CURRENTLY_SCHEDULED"
        elif old is None:
            status="OFFICIAL_GAME_MISSING_FROM_MASTER_WINDOW"
        else:
            old_start=moment(old.get("gameDate"))
            home_name=str(new["home"].get("name") or "")
            away_name=str(new["away"].get("name") or "")
            if not all(_not_placeholder(n) for n in (old.get("home_team"),old.get("away_team"),home_name,away_name)):
                status="PARTICIPANTS_NOT_RESOLVED"
            elif not new["home"].get("id") or not new["away"].get("id"):
                status="OFFICIAL_TEAMS_MISSING"
            elif int(old["home_team_id"])!=int(new["home"]["id"]) or int(old["away_team_id"])!=int(new["away"]["id"]):
                status="OFFICIAL_TEAM_IDS_CONFLICT"
            elif old_start is None or abs((old_start-new["start"]).total_seconds())>180:
                status="OFFICIAL_START_MISMATCH_REQUIRES_SOURCE_REPAIR"
            else:
                status="EXACT_SOURCE_FIXTURE_MATCH"
        source=latest.get(pk)
        lineup_ok=bool(new and new["start"] and verified_lineup(source,new["start"]))
        start=new["start"] if new else moment(old.get("gameDate") if old else None)
        mins=round((start-now).total_seconds()/60,2) if start else None
        output.append({
            "game_pk":pk,
            "status":status,
            "source_eligible_for_new_model_research": status=="EXACT_SOURCE_FIXTURE_MATCH" and lineup_ok,
            "master_start":str(old.get("gameDate")) if old else None,
            "official_start":start.isoformat() if new and start else None,
            "lead_minutes":mins,
            "home":new["home"].get("name") if new else str(old.get("home_team")),
            "away":new["away"].get("name") if new else str(old.get("away_team")),
            "official_lineup_verified":lineup_ok,
            "latest_lineup_status":(source.get("lineups") or {}).get("status") if source else "NO_PRIOR_SOURCE_CAPTURE",
            "source_captured_at_utc":source.get("captured_at_utc") if source else None,
            "v2_players_frozen":stage[0].get(pk,0),
            "v3_players_frozen":stage[1].get(pk,0),
            "v4_context_players_frozen":stage[2].get(pk,0),
            "v4_model_forecasts_frozen":stage[3].get(pk,0),
            "v4_official_model_grades":stage[4].get(pk,0),
            "model_automatically_promoted":False,
        })
    return {
        "schema":SCHEMA,
        "at_utc":now.isoformat(),
        "scope":"RESEARCH_READINESS_MONITOR_ONLY_DOES_NOT_REWRITE_OFFICIAL_MASTER_OR_MODEL",
        "master_scheduled_game_count":len(original),
        "official_scheduled_game_count":len(official_ids),
        "fixture_status_counts":dict(sorted(Counter(x["status"] for x in output).items())),
        "source_verified_ready_game_count":sum(x["source_eligible_for_new_model_research"] for x in output),
        "original_frozen_model_total_games":len(stage[3]),
        "original_frozen_model_forecast_rows":sum(stage[3].values()),
        "actual_official_model_grade_game_count":len(stage[4]),
        "actual_official_model_grade_rows":sum(stage[4].values()),
        "next_games":output,
        "paid_bets_or_model_changes":False,
    }


def fetch_with_cache(now:datetime, *, force: bool=False)->tuple[dict,dict]:
    if CACHE.exists() and not force:
        try:
            saved=json.loads(CACHE.read_text())
            previous=moment(saved["captured_at_utc"])
            if previous and now>=previous and now-previous<timedelta(minutes=50):
                raw=json.dumps(saved["schedule"],sort_keys=True,separators=(",",":")).encode()
                if sha(raw)==saved["canonical_payload_sha256"]:
                    return saved["schedule"],{"status":"VERIFIED_RECENT_CACHED_OFFICIAL_SCHEDULE","captured_at_utc":saved["captured_at_utc"],"source_sha256":saved["canonical_payload_sha256"]}
        except (KeyError, ValueError, TypeError, json.JSONDecodeError): pass
    response=requests.get(OFFICIAL_URL,params={
        "sportId":1,
        "startDate":now.date().isoformat(),
        "endDate":(now+timedelta(days=4)).date().isoformat(),
    },timeout=(3,9),headers={"Accept":"application/json","User-Agent":"Zenith-Research-Readiness/1.0"})
    response.raise_for_status()
    if len(response.content)>250000:raise ValueError("OFFICIAL_RESPONSE_TOO_LARGE")
    schedule=response.json()
    official_fixtures(schedule) # validates nonduplicate fixture identities
    if not schedule.get("dates"):raise ValueError("OFFICIAL_SCHEDULE_EMPTY")
    raw=json.dumps(schedule,sort_keys=True,separators=(",",":")).encode()
    receipt={
        "captured_at_utc":now.isoformat(),
        "canonical_payload_sha256":sha(raw),
        "source_url":OFFICIAL_URL,
        "schedule":schedule,
    }
    temp=CACHE.with_suffix(".tmp")
    with temp.open("w") as f:
        json.dump(receipt,f,sort_keys=True)
        f.flush();os.fsync(f.fileno())
    os.replace(temp,CACHE)
    return schedule,{"status":"FRESH_OFFICIAL_SCHEDULE_HTTP_200","captured_at_utc":now.isoformat(),"source_sha256":receipt["canonical_payload_sha256"]}


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--no-network",action="store_true")
    args=parser.parse_args()
    now=datetime.now(timezone.utc)
    if args.no_network:
        if not CACHE.exists():raise SystemExit("NO_OFFICIAL_CACHE")
        receipt=json.loads(CACHE.read_text())
        schedule=receipt["schedule"]
        original_meta={"status":"OFFLINE_CACHE_REPLAY","captured_at_utc":receipt["captured_at_utc"],"source_sha256":receipt["canonical_payload_sha256"]}
    else:
        schedule,original_meta=fetch_with_cache(now)
    master=pd.read_csv(MASTER,low_memory=False)
    ledger_paths=(V2,V3,V4,FORECAST,GRADED)
    review=audit(schedule,master,jsonl(EVIDENCE),*(jsonl(x) for x in ledger_paths),now=now)
    review["official_schedule_source_receipt"]=original_meta
    review["official_historical_master_sha256"]=hashlib.sha256(MASTER.read_bytes()).hexdigest()
    SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    tmp=SUMMARY.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(review,f,indent=2,sort_keys=True)
        f.write("\n")
        f.flush();os.fsync(f.fileno())
    os.replace(tmp,SUMMARY)
    print("MLB_FORWARD_OFFICIAL_READINESS",json.dumps(review,sort_keys=True))


if __name__=="__main__":
    main()
