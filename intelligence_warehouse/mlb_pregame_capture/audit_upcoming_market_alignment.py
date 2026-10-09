"""Read-only original bookmaker fixture/price-pair quality before MLB Full16.

The public official schedule and previously accepted source-time game master
must agree. The source's capture timestamp is NOT independently established
as the named sportsbook's executable quote update. This audit never fits or
changes a model, freezes a prediction, or publishes a bet.
"""
from __future__ import annotations

from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import pandas as pd

from .build_forward_readiness import BASE,MASTER,SUMMARY as READINESS,CACHE,moment

ROOT=Path(__file__).resolve().parents[2]
MARKET=ROOT/"mlb_live/markets/current/MLB_PLAYER_PROP_MARKET.csv"
OUT=BASE/"MLB_PRETIPOFF_BOOK_FIXTURE_ALIGNMENT_AUDIT.json"
SCHEMA="MLB_ORIGINAL_SOURCE_0_5_HITS_BOOK_FIXTURE_ALIGNMENT_RESEARCH_V1"
REQUIRED={
    "provider","sportsbook","event_id","start","away_team","home_team",
    "market","market_subtype","selection","side","line",
    "price_american","player_id","player","captured_at",
}


def digest(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()


def implied(value):
    try:
        odds=float(value)
        if not math.isfinite(odds) or not(100<=abs(odds)<=10000):
            return None
        return 100/(100+odds) if odds>0 else (-odds)/(100-odds)
    except (ValueError,TypeError,OverflowError):
        return None


def source_proof(readiness:dict,original_cache:dict,master:pd.DataFrame,now:datetime):
    """Return accepted exact official future games, or refuse stale/mismatched source."""
    if not now.tzinfo:raise ValueError("SOURCE_AUDIT_CLOCK_WITHOUT_OFFSET")
    receipt=readiness.get("official_schedule_source_receipt") or {}
    at=moment(readiness.get("at_utc"))
    source_at=moment(receipt.get("captured_at_utc"))
    cache_at=moment(original_cache.get("captured_at_utc"))
    if not all((at,source_at,cache_at)):
        raise ValueError("MISSING_INDEPENDENT_OFFICIAL_SOURCE_TIMESTAMPS")
    if any(t>now or now-t>timedelta(minutes=75) for t in (at,source_at,cache_at)):
        raise ValueError("STALE_OR_FUTURE_OFFICIAL_SCHEDULE_VALIDATION")
    original=original_cache.get("schedule")
    if not isinstance(original,dict):
        raise ValueError("MISSING_PUBLIC_SCHEDULE_ORIGINAL_PAYLOAD")
    canonical=json.dumps(original,sort_keys=True,separators=(",",":")).encode()
    if (digest(canonical)!=original_cache.get("canonical_payload_sha256")
        or digest(canonical)!=receipt.get("source_sha256")):
        raise ValueError("SOURCE_ORIGINAL_SCHEDULE_CACHE_OR_AUDIT_HASH_CHANGED")
    official={}
    for day in original.get("dates",[]):
        for game in day.get("games",[]):
            pk=int(game["gamePk"])
            if pk in official:raise ValueError("DUPLICATE_PUBLIC_OFFICIAL_MLB_GAME")
            official[pk]=game
    if master.gamePk.isna().any() or master.gamePk.duplicated().any():
        raise ValueError("DUPLICATED_SOURCE_MASTER_GAME")
    master_ix=master.set_index("gamePk",drop=False)
    result={}
    for r in readiness.get("next_games",[]):
        if r.get("status")!="EXACT_SOURCE_FIXTURE_MATCH":continue
        pk=int(r["game_pk"])
        if pk in result:raise ValueError("DUPLICATE_ACCEPTED_MLB_GAME")
        g=official.get(pk)
        if not g or pk not in master_ix.index:raise ValueError("MISSING_ORIGINAL_GAME_KEY")
        if g.get("startTimeTBD") is True or (g.get("status") or {}).get("startTimeTBD") is True:
            continue  # Never treat an unresolved source kickoff as a matched price.
        m=master_ix.loc[pk]
        teams=g.get("teams") or {}
        home=(teams.get("home") or {}).get("team") or {}
        away=(teams.get("away") or {}).get("team") or {}
        venue=g.get("venue") or {}
        start=moment(g.get("gameDate"))
        startmaster=moment(m.get("gameDate"))
        startreceipt=moment(r.get("official_start"))
        if not start or not(start==startmaster==startreceipt) or not now<start:continue
        if (str((g.get("status") or {}).get("detailedState")).lower() not in
              ("scheduled","pre-game","preview","warmup")):continue
        if (str(home.get("name"))!=str(m.home_team)
            or str(away.get("name"))!=str(m.away_team)
            or str(home.get("id"))!=str(m.home_team_id)
            or str(away.get("id"))!=str(m.away_team_id)
            or str(venue.get("id"))!=str(m.venue_id)
            or home.get("placeholder") is True or away.get("placeholder") is True):
            continue
        result[pk]={"pk":pk,"start":start,"home":str(m.home_team),
                    "away":str(m.away_team),"lineup_confirmed":r.get("official_lineup_verified") is True}
    return result


def audit_quotes(raw:pd.DataFrame,fixtures:dict,now:datetime)->dict:
    if not now.tzinfo:raise ValueError("NEED_ORIGINAL_TIMESTAMPED_AUDIT")
    if not REQUIRED.issubset(raw.columns):
        raise ValueError("PROVIDER_MARKET_FILE_MISSING_REQUIRED_IDENTITY_COLUMNS")
    if len(raw)>250_000:raise ValueError("UNBOUNDED_PROVIDER_PRICE_SOURCE")
    reasons=Counter()
    pairgroups=defaultdict(list)
    events=defaultdict(set)
    for r in raw.itertuples(index=False):
        x=r._asdict()
        if str(x["market"])!="PLAYER_TOTAL" or str(x["market_subtype"])!="PLAYER_TOTAL_HITS" or str(x["side"]).upper() not in ("OVER","UNDER"):
            reasons["NOT_EXACT_TWO_SIDED_PLAYER_TOTAL_HITS"]+=1
            continue
        if pd.isna(x["line"]) or abs(float(x["line"])-0.5)>1e-9:
            reasons["NOT_EXACT_HITS_0_5_LINE"]+=1
            continue
        # MLB playoff series can have consecutive days with the SAME two teams.
        # A name-only join would be ambiguous; require original event kickoff.
        by_name=[f for f in fixtures.values() if x["home_team"]==f["home"] and x["away_team"]==f["away"]]
        if not by_name:
            reasons["NOT_UNIQUE_OR_OFFICIAL_FIXTURE"]+=1
            continue
        bookstart=moment(x["start"])
        matches=[f for f in by_name if bookstart is not None and
                 abs((bookstart-f["start"]).total_seconds())<=180]
        if not matches:
            reasons["STALE_PROVIDER_FIXTURE_START"]+=1
            continue
        if len(matches)!=1:
            reasons["SAME_TEAM_MULTIPLE_OFFICIAL_GAME_STARTS_AMBIGUOUS"]+=1
            continue
        f=matches[0]
        captured=moment(x["captured_at"])
        if captured is None or captured>now or captured>=f["start"] or now-captured>timedelta(minutes=30):
            reasons["SOURCE_CAPTURE_NOT_RECENT_PREGAME"]+=1
            continue
        if not str(x["provider"]) or not str(x["sportsbook"]) or not str(x["event_id"]) or not str(x["player_id"]):
            reasons["MISSING_EXACT_PROVIDER_PRICE_OR_PLAYER_UUID"]+=1
            continue
        price=implied(x["price_american"])
        if price is None:
            reasons["INVALID_ORIGINAL_BOOK_AMERICAN_ODDS"]+=1
            continue
        events[(str(x["provider"]),str(x["event_id"]))].add(f["pk"])
        key=(
            f["pk"],str(x["provider"]),str(x["event_id"]),
            str(x["sportsbook"]),str(x["player_id"]),str(x["player"]),
            str(x["captured_at"]),str(x["start"]),0.5,
        )
        pairgroups[key].append((str(x["side"]).upper(),float(x["price_american"]),price))
    counted=Counter(); books=defaultdict(set);players=defaultdict(set)
    for key,legs in pairgroups.items():
        pk,provider,event,book,playeruuid,player,at,start,line=key
        if len(events[(provider,event)])!=1:
            reasons["PROVIDER_EVENT_ID_MAPPED_TO_MULTIPLE_OFFICIAL_GAMES"]+=len(legs)
            continue
        if len(legs)!=2 or {x[0] for x in legs}!={"OVER","UNDER"}:
            reasons["MISSING_UNIQUE_SAME_BOOK_PAIR"]+=len(legs)
            continue
        vig=sum(z[2] for z in legs)
        if not 1.000001<vig<=1.25:
            reasons["INVALID_SAME_BOOK_PROBABILITY_VIG"]+=2
            continue
        counted[pk]+=1
        books[pk].add(book)
        players[pk].add(playeruuid)
    games=[]
    for pk,f in sorted(fixtures.items()):
        games.append({
            "official_game_pk":pk,
            "official_first_pitch_utc":f["start"].isoformat(),
            "home_team":f["home"],"away_team":f["away"],
            "two_sided_source_book_hits_over_under_half_pairs":counted[pk],
            "source_bookmakers_with_identity_matched_pairs":sorted(books[pk]),
            "unique_provider_player_uuids_quoted":len(players[pk]),
            "full18_official_lineups_confirmed":f["lineup_confirmed"],
            "can_freeze_new_full16_prediction_now":False,
            "source_book_website_executability_verified":False,
            "source_provider_player_uuid_matches_MLBAM_id_verified_here":False,
        })
    return {
        "research_only":True,
        "source_rows":len(raw),"eligible_exact_half_line_side_group_count":len(pairgroups),
        "book_player_exact_same_source_time_pairs_accepted":sum(counted.values()),
        "rejected_source_row_reasons":dict(sorted(reasons.items())),
        "official_game_blocks":[x["official_game_pk"] for x in games],
        "per_official_game":games,
        "model_retrained_or_wagers_created":False,
        "priced_edge_proven":False,
    }


def run(*,clock=None,market=MARKET,master=MASTER,readiness=READINESS,cache=CACHE):
    now=clock or datetime.now(timezone.utc)
    if not now.tzinfo:raise ValueError("RESEARCH_CLOCK_MUST_HAVE_UTC_OFFSET")
    source_bytes=market.read_bytes()
    public=json.loads(cache.read_text())
    last=json.loads(readiness.read_text())
    fixture_master=pd.read_csv(master,low_memory=False)
    fixtures=source_proof(last,public,fixture_master,now)
    quotes=pd.read_csv(market,low_memory=False)
    stats=audit_quotes(quotes,fixtures,now)
    return {
        "schema":SCHEMA,"audited_at_utc":now.isoformat(),
        "official_source_age_minutes":round((now-moment(last["at_utc"])).total_seconds()/60,2),
        "source_market_file_sha256":digest(source_bytes),
        "source_master_file_sha256":digest(master.read_bytes()),
        "source_schedule_original_sha256":public["canonical_payload_sha256"],
        "official_exact_fixture_count":len(fixtures),
        "source_market_captured_at_is_aggregator_observation_not_book_update_time":True,
        "model_play_or_postgame_status_not_changed":True,
        **stats,
    }


def main():
    result=run()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    tmp=OUT.with_suffix(".tmp")
    with tmp.open("w",encoding="utf8") as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write("\n");f.flush();os.fsync(f.fileno())
    os.replace(tmp,OUT)
    print("MLB_CURRENT_FUTURE_PRICE_IDENTITY_AUDIT",json.dumps(result,sort_keys=True))


if __name__=="__main__":main()
