"""Source-preserving model-error diagnosis. No deployed betting-model changes."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import isfinite, log, sqrt

VERSION = "ZENITH_ASOF_MARKET_RESIDUAL_SHADOW_V1"
VALID_GRADES = {"WIN", "LOSS", "PUSH"}
MIN_TRAIN_GAMES = 30
MIN_TRAIN_ROWS = 50
MIN_BUCKET_GAMES = 10
MIN_HOLDOUT_GAMES = 30
MIN_HOLDOUT_ROWS = 50


def when(v):
    if not isinstance(v, str) or not v.strip():
        return None
    try:
        d = datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except ValueError:
        return None


def num(v):
    if v is None or v == "":
        return None
    try:
        x = float(v)
        return x if isfinite(x) else None
    except (TypeError, ValueError):
        return None


def block(row):
    return str(row.get("sport") or "") + "|" + str(row.get("game_key") or "")


def scored_grade(row):
    """Independent arithmetic recomputation against the frozen market side/line."""
    h, a = num(row.get("home_score")), num(row.get("away_score"))
    line = num(row.get("line"))
    side = str(row.get("selection_key") or row.get("side") or "").upper()
    m = str(row.get("market") or "").upper()
    if h is None or a is None or h < 0 or a < 0:
        return None
    if m in {"MONEYLINE", "SPREAD"}:
        if side not in {"HOME", "AWAY"}:
            return None
        margin = (h-a) if side == "HOME" else (a-h)
        if m == "SPREAD":
            if line is None:
                return None
            margin += line
    elif m == "TOTAL":
        if side not in {"OVER", "UNDER"} or line is None:
            return None
        margin = (h+a-line) * (1 if side == "OVER" else -1)
    else:
        return None
    return "WIN" if margin > 1e-7 else "LOSS" if margin < -1e-7 else "PUSH"


def diagnosis(row):
    """Observable outcome mechanics, never guessed injury/weather cause."""
    if row.get("grade") != "LOSS":
        return "NOT_LOST", "This selection did not lose."
    h, a = num(row.get("home_score")), num(row.get("away_score"))
    side = str(row.get("selection_key") or row.get("side") or "").upper()
    m = row.get("market")
    line = num(row.get("line"))
    if h is None or a is None:
        return "NO_SCORE", "Final-score evidence is missing."
    if m == "MONEYLINE":
        return "OUTRIGHT_WINNER_DIFFERENT", "The selected side did not win. An upset is not proof that one specific feature was wrong."
    if m == "SPREAD":
        margin = (h-a) if side == "HOME" else (a-h)
        if margin > 0 and line is not None and line < 0:
            return "WINNER_DID_NOT_COVER", "Team won outright but not by enough to cover. Winning probability is not a predicted margin-of-victory distribution."
        if margin < 0 and line is not None and line > 0:
            return "UNDERDOG_LOST_OUTSIDE_SPREAD", "The underdog lost by more than the point cushion. Specific causal factors remain unverified."
        return "SPREAD_MARGIN_MISS", "Predicted side failed to cover. Need a properly tested margin model."
    if m == "TOTAL":
        return ("TOTAL_BELOW_LINE" if side == "OVER" else "TOTAL_ABOVE_LINE"), (
            f"Recorded combined score was {h+a:g} against a {line:g} point total. "
            "Cannot infer the cause from the final score alone."
        )
    return "UNCLASSIFIED", "No verified causal information."


def canonical(events):
    """First frozen ENTRY + later SETTLED; quarantine contradictions or invalid clocks."""
    table, poisoned, why = {}, set(), Counter()
    for r in events:
        key = r.get("forward_key")
        if not isinstance(key, str) or not key:
            why["MISSING_KEY"] += 1
            continue
        typ = r.get("event_type")
        if typ == "ENTRY":
            if key not in table:
                table[key] = {"original": r, "result": None}
            elif table[key]["original"] != r:
                poisoned.add(key)
                why["CONFLICTING_ENTRY"] += 1
        elif typ == "SETTLED":
            if key not in table:
                poisoned.add(key)
                why["ORPHAN_SETTLEMENT"] += 1
            elif table[key]["result"] is not None and table[key]["result"] != r:
                poisoned.add(key)
                why["CONFLICTING_SETTLEMENT"] += 1
            else:
                table[key]["result"] = r
        elif typ != "SHADOW_TRIGGER":
            why["UNRECOGNIZED_EVENT"] += 1

    rows = []
    for key, pair in table.items():
        if key in poisoned:
            why["QUARANTINED_CONFLICT"] += 1
            continue
        e, r = pair["original"], pair["result"]
        capture, kickoff = when(e.get("captured_at")), when(e.get("event_start"))
        p, market = num(e.get("entry_v2_probability_pct")), num(e.get("entry_market_reference_probability_pct"))
        if not capture or not kickoff or capture >= kickoff:
            why["INVALID_PREGAME_CLOCK"] += 1
            continue
        if p is None or market is None or not (0 < p < 100 and 0 < market < 100):
            why["NO_FINITE_PROBABILITY"] += 1
            continue
        if not e.get("sport") or not e.get("game_key"):
            why["NO_SPORT_GAME_BLOCK"] += 1
            continue
        row = dict(e)
        row.update({"model_probability_pct": p, "market_probability_pct": market,
                    "original_capture_utc": capture.isoformat(),
                    "original_start_utc": kickoff.isoformat(), "grade": "PENDING"})
        if r is None:
            rows.append(row)
            continue
        settled = when(r.get("settled_at"))
        if r.get("grade") not in VALID_GRADES or settled is None or settled <= kickoff:
            why["INVALID_SETTLED_EVENT_CLOCK"] += 1
            continue
        row.update({k:v for k,v in r.items() if k not in {"event_type","forward_key",
            "market","sport","game_key","captured_at","event_start","line",
            "selection_key","model_version"}})
        row["settled_at_utc"] = settled.isoformat()
        expected = scored_grade(row)
        if expected is None:
            why["FINAL_SCORE_NOT_RECOMPUTABLE"] += 1
            continue
        if expected != r["grade"]:
            why["RECORDED_FINAL_CONFLICTS_WITH_GRADE"] += 1
            continue
        snapshot = when(r.get("grade_snapshot_at"))
        row["grade_snapshot_is_original_pregame_time"] = bool(snapshot and snapshot < kickoff)
        row["result_source_identity_recorded"] = bool(r.get("settlement_source_event_id"))
        row["independent_official_boxscore_double_checked"] = False
        rows.append(row)
    return rows, why


def lane_rollup(rows):
    lanes = defaultdict(list)
    for r in rows:
        if r.get("grade") in VALID_GRADES:
            lanes[str(r.get("lane_key") or r["sport"]+"_"+r["market"])].append(r)
    output=[]
    for lane, group in sorted(lanes.items()):
        valid = [r for r in group if r["grade"] != "PUSH"]
        blocks = defaultdict(list)
        for r in valid:
            outcome = int(r["grade"]=="WIN")
            blocks[block(r)].append((
                (r["market_probability_pct"]/100-outcome)**2,
                (r["model_probability_pct"]/100-outcome)**2,
            ))
        baseline = sum(sum(a for a,b in v)/len(v) for v in blocks.values())/len(blocks) if blocks else None
        model = sum(sum(b for a,b in v)/len(v) for v in blocks.values())/len(blocks) if blocks else None
        output.append({
            "lane": lane, "graded_rows":len(group), "independent_game_blocks":len(blocks),
            "wins":sum(r["grade"]=="WIN" for r in group),
            "losses":sum(r["grade"]=="LOSS" for r in group),
            "pushes":sum(r["grade"]=="PUSH" for r in group),
            "model_equal_to_market_probability_rows":sum(abs(r["model_probability_pct"]-r["market_probability_pct"])<1e-7 for r in valid),
            "market_brier_equal_game_weighted":round(baseline,5) if baseline is not None else None,
            "model_brier_equal_game_weighted":round(model,5) if model is not None else None,
            "independently_proven_predictive_advantage":False,
        })
    return output


def phase(row):
    """Do not blend NBA preseason and regular season calibration histories."""
    value = str(row.get("competition_regime") or row.get("season_type") or "UNKNOWN").upper().strip()
    return value if value in {"PRESEASON","REGULAR","POSTSEASON"} else "UNKNOWN"


def asof_training(frozen, records):
    """No target-game leak; only labels already SETTLED before original freeze."""
    captured = when(frozen.get("original_capture_utc"))
    if captured is None:
        return []
    return [r for r in records
            if r.get("grade") in {"WIN","LOSS"}
            and r.get("sport")==frozen.get("sport") and r.get("market")==frozen.get("market")
            and phase(r)==phase(frozen)
            and block(r)!=block(frozen) and r.get("result_source_identity_recorded")
            and when(r.get("settled_at_utc")) is not None
            and when(r["settled_at_utc"]) < captured
            and when(r.get("original_start_utc")) < when(r["settled_at_utc"])]


def shadow_calibration(frozen, records):
    """Conservative pre-registered residual adjustment, not a real new bet."""
    samples = asof_training(frozen, records)
    grouped = defaultdict(list)
    for r in samples:
        grouped[block(r)].append(r)
    baseline = frozen["market_probability_pct"]/100
    band = min(4,int(baseline*5))
    by_band={}
    for key, game in grouped.items():
        matching=[r for r in game if min(4,int(r["market_probability_pct"]/100*5))==band]
        if matching:
            by_band[key]=sum(int(r["grade"]=="WIN")-r["market_probability_pct"]/100 for r in matching)/len(matching)
    counts={"training_rows":len(samples),"training_independent_games":len(grouped),
            "same_probability_band_games":len(by_band)}
    if len(samples)<MIN_TRAIN_ROWS or len(grouped)<MIN_TRAIN_GAMES or len(by_band)<MIN_BUCKET_GAMES:
        return {"status":"WAIT_FOR_SOURCE_VALID_OUT_OF_TIME_GAMES",
            **counts,"required_training_rows":MIN_TRAIN_ROWS,
            "required_training_games":MIN_TRAIN_GAMES,
            "required_same_probability_band_games":MIN_BUCKET_GAMES,
            "model_version":VERSION,"automatic_live_adjustment_allowed":False}
    residual=sum(by_band.values())/len(by_band)
    shrinkage=min(.25,len(by_band)/(len(by_band)+50))
    offset=max(-.05,min(.05,shrinkage*residual))
    return {
        "status":"ASOF_SHADOW_RESEARCH_ONLY","model_version":VERSION,
        "original_forward_key":frozen["forward_key"],
        "original_capture_utc":frozen["original_capture_utc"],
        "game_start_utc":frozen["original_start_utc"],
        "sport":frozen["sport"],"market":frozen["market"],"game_key":frozen["game_key"],
        "competition_regime":phase(frozen),
        "baseline_market_probability_pct":round(baseline*100,4),
        "shadow_probability_pct":round(min(.99,max(.01,baseline+offset))*100,4),
        "market_only_residual_adjustment_pp":round(offset*100,4),
        "max_adjustment_pp":5,
        **counts,
        "latest_training_result_available_utc":max(r["settled_at_utc"] for r in samples),
        "independent_model_advantage_proven":False,
        "bet_or_automatic_production_change_created":False,
    }


def shadow_metrics(records, shadows):
    original = {r["forward_key"]:r for r in records}
    grouped=defaultdict(list)
    n=0
    for candidate in shadows:
        r=original.get(candidate.get("original_forward_key"))
        if (candidate.get("status")!="ASOF_SHADOW_RESEARCH_ONLY" or not r
            or r.get("grade") not in {"WIN","LOSS"}):
            continue
        freeze=when(candidate.get("frozen_at_utc"))
        kickoff=when(r.get("original_start_utc"))
        p=num(candidate.get("shadow_probability_pct"))
        if not freeze or not kickoff or freeze>=kickoff or p is None or not 0<p<100:
            continue
        if candidate.get("game_start_utc")!=r.get("original_start_utc"):
            continue
        y=int(r["grade"]=="WIN")
        diff=(r["market_probability_pct"]/100-y)**2-(p/100-y)**2
        grouped[block(r)].append(diff)
        n+=1
    points=[sum(v)/len(v) for v in grouped.values()]
    games=len(points)
    m=sum(points)/games if games else None
    lcb=None
    if games>=2:
        var=sum((x-m)**2 for x in points)/(games-1)
        lcb=m-1.645*sqrt(var/games)
    review=bool(n>=MIN_HOLDOUT_ROWS and games>=MIN_HOLDOUT_GAMES
        and lcb is not None and lcb>0)
    return {
        "graded_frozen_shadow_rows":n,"independent_shadow_game_blocks":games,
        "mean_game_block_brier_advantage":round(m,6) if m is not None else None,
        "advantage_90pct_lower_bound":round(lcb,6) if lcb is not None else None,
        "review_eligible":review,
        "mode":"MANUAL_MODEL_REVIEW_ONLY" if review else "UNPROVEN_FORWARD_SHADOW",
        "required_shadow_rows":MIN_HOLDOUT_ROWS,
        "required_independent_shadow_games":MIN_HOLDOUT_GAMES,
        "automated_live_model_adjustment_allowed":False,
        "verified_positive_expected_value_betting_proven":False,
    }
