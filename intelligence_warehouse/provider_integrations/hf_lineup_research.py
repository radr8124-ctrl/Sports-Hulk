"""Hugging Face MLB lineup-reaction data discovery (RESEARCH ONLY).

Public Dataset Viewer read only; bounded, stratified *source inventory*,
not a random event sample, a fitted betting model, or production feed.
Original source rows remain isolated from live decisions and future ledgers.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[2]
DATASET = "SmartStake/mlb-lineup-reactions"
VIEWER = "https://datasets-server.huggingface.co"
OFFICIAL_AUDIT = ROOT / "reports/hf_mlb_expanded_20261008/official_audit.json"
RESEARCH = ROOT / "reports/hf_mlb_lineup_reactions_20261009"


def utc(value):
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    x = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if x.tzinfo is None:  # Viewer timestamps documented as UTC by publisher.
        x = x.replace(tzinfo=timezone.utc)
    return x.astimezone(timezone.utc)


def normalized(text):
    return " ".join(str(text or "").lower().split())


def candidates_by_provider_game(official_audit):
    """Only game/player combinations with validated MLB official outcomes."""
    games = defaultdict(set)
    players = defaultdict(set)
    starts = defaultdict(set)
    for r in official_audit:
        if r.get("status") != "VERIFIED_HISTORICAL":
            continue
        game = str(r.get("game_id") or "").strip()
        pk = r.get("official_game_pk")
        if not game or pk is None:
            continue
        games[game].add(str(pk))
        starts[game].add(str(r.get("official_start") or ""))
        if r.get("player"):
            players[game].add(normalized(r["player"]))
    return games, players, starts


def audit_rows(rows, official_audit):
    games, players, starts = candidates_by_provider_game(official_audit)
    result = []
    for i, row in enumerate(rows):
        source_game = str(row.get("game_id") or "")
        reason = "SOURCE_REVIEW"
        crosswalk_game = None
        try:
            event = str(row["event_id"])
            quote = utc(row["ts"])
            post = utc(row["tweet_ts"])
            offset = (quote - post).total_seconds()
            odds = float(row.get("odds"))
            recorded_offset = float(row.get("offset_sec"))
            if not event or not source_game or not str(row.get("book") or "").strip() or not str(row.get("player") or "").strip() or not str(row.get("market") or "").strip() or row.get("is_suspended") is None or row.get("is_alt") is None or not 1.01 < odds <= 1000:
                reason = "INVALID_SOURCE_FIELDS"
            elif abs(offset) > 3600 or abs(offset-recorded_offset)>2:
                reason = "SOURCE_TIME_CONTRADICTION"
            elif row["is_suspended"] is not False:
                reason = "SUSPENDED_QUOTE"
            elif row["is_alt"] is not False:
                reason = "ALTERNATE_PROP_NOT_MAIN_LINE"
            elif len(games.get(source_game, set())) != 1 or len(starts.get(source_game,set())) != 1:
                reason = "MISSING_UNIQUE_OFFICIAL_GAME_CROSSWALK"
            elif normalized(row.get("player")) not in players[source_game]:
                reason = "UNVERIFIED_OR_DIFFERENT_PLAYER"
            elif post >= utc(next(iter(starts[source_game]))) or quote >= utc(next(iter(starts[source_game]))):
                reason = "NOT_VERIFIED_PREGAME"
            elif quote < post:
                reason = "PRE_ANNOUNCEMENT_REFERENCE_ONLY"
            else:
                reason = "RESEARCH_CANDIDATE_NEEDS_LINEUP_TEAM_AND_PAIR_VERIFICATION"
                crosswalk_game = next(iter(games[source_game]))
        except (ValueError, KeyError, TypeError, OverflowError):
            reason = "INVALID_SOURCE_FIELDS_OR_TIME"
        result.append({
            "sample_index": i,
            "source_game_id": source_game,
            "provider_event_id": str(row.get("event_id") or ""),
            "status": reason,
            "official_game_pk": crosswalk_game,
            "source_row_hash": hashlib.sha256(
                json.dumps(row,sort_keys=True,separators=(",",":"),default=str).encode()
            ).hexdigest(),
        })
    return result


def fetch_bounded():
    with requests.Session() as session:
        s = session.get(VIEWER+"/size",params={"dataset":DATASET},timeout=18)
        s.raise_for_status()
        z = s.json()
        splits = z.get("size",{}).get("splits",[])
        source_size = next(int(x["num_rows"]) for x in splits if x["split"]=="train" and x["config"]=="default")
        positions = sorted({min(source_size-1,int(source_size*k/24)) for k in range(1,24,2)})
        rows=[]
        sample_slots=[]
        for offset in positions:
            r=session.get(VIEWER+"/rows",params={
                "dataset":DATASET,"config":"default","split":"train",
                "offset":offset,"length":2,
            },timeout=18)
            r.raise_for_status()
            vals=[v["row"] for v in r.json().get("rows",[])]
            if len(vals)!=2:
                raise ValueError(f"Source dataset changed: expected two rows at {offset}")
            rows.extend(vals)
            sample_slots.append({"offset":offset,"count":len(vals)})
        return {
            "source":DATASET,"viewer_base":VIEWER,"config":"default","split":"train",
            "estimated_total_source_rows":source_size,
            "sampling_rule":"12 fixed evenly spaced two-row offsets, source inventory only; NOT event-random",
            "slots":sample_slots,"rows":rows,
        }


def create_manifest(path, payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    # Never overwrite a preserved original observation.
    with path.open("x",encoding="utf-8") as f:
        f.write(json.dumps(payload,sort_keys=True,indent=2,ensure_ascii=False)+"\n")
        f.flush()
        os.fsync(f.fileno())


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",type=Path,help="replay existing on-VPS original sampled source, no network")
    ap.add_argument("--out-dir",type=Path,default=RESEARCH)
    args=ap.parse_args()
    if args.manifest:
        manifest=json.loads(args.manifest.read_text())
    else:
        manifest=fetch_bounded()
    if manifest.get("source")!=DATASET or len(manifest.get("rows",[]))>48:
        raise ValueError("Incorrect dataset or unbounded sample")
    original=json.loads(OFFICIAL_AUDIT.read_text())
    classified=audit_rows(manifest["rows"],original)
    counts=Counter(r["status"] for r in classified)
    usable=[r for r in classified if r["status"]=="RESEARCH_CANDIDATE_NEEDS_LINEUP_TEAM_AND_PAIR_VERIFICATION"]
    receipt={
        "observed_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_dataset":DATASET,
        "reference_dataset":"SmartStake/mlb-player-props",
        "source_license_card":"CC-BY-4.0 (upstream commercial odds rights not independently verified)",
        "source_status":"HISTORICAL_RESEARCH_ONLY_NOT_LIVE_FEED",
        "external_cloud_job_started":False,
        "production_model_changes":False,
        "provider_records":len(manifest["rows"]),
        "provider_events":len({r.get("event_id") for r in manifest["rows"]}),
        "provider_game_ids":len({r.get("game_id") for r in manifest["rows"]}),
        "status_counts":dict(sorted(counts.items())),
        "candidate_rows":len(usable),
        "candidate_independent_official_games":len({r["official_game_pk"] for r in usable}),
        "no_auto_betting_or_training":True,
        "source_manifest_sha256":hashlib.sha256(
            json.dumps(manifest,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
        ).hexdigest(),
        "official_audit_sha256":hashlib.sha256(OFFICIAL_AUDIT.read_bytes()).hexdigest(),
        "limitations":["lineup source team is not independently verified",
                       "no contemporaneous paired-book fair prop price computed",
                       "model improvement and current October lineup coverage unproven",
                       "offset sampling is not a representative sample of games"],
    }
    args.out_dir.mkdir(parents=True,exist_ok=True)
    if not args.manifest:
        create_manifest(args.out_dir/"original_public_sample.json",manifest)
    # Receipt paths versioned by the original sample content, safe against accidental overwrites.
    prefix=receipt["source_manifest_sha256"][:12]
    create_manifest(args.out_dir/f"research_audit_{prefix}.json",
       {"summary":receipt,"rows":classified})
    print(json.dumps(receipt,indent=2,sort_keys=True))
if __name__=="__main__":
    main()
