#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
import sys
import requests
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
CURRENT = OUT_DIR / "PROP_V2_CURRENT.json"
LEDGER = OUT_DIR / "PROP_V2_FORWARD_LEDGER.jsonl"
SUMMARY = OUT_DIR / "PROP_V2_FORWARD_SUMMARY.json"
PUBLIC = ROOT / "commercial_web" / "public" / "prop_v2_forward.json"
NHL_BOX_RECEIPT = OUT_DIR / "NHL_OFFICIAL_BOX_FORWARD_RECEIPT.json"
MLB_BOX_RECEIPT = OUT_DIR / "MLB_OFFICIAL_BOX_FORWARD_RECEIPT.json"
DIST = ROOT / "commercial_web" / "dist" / "prop_v2_forward.json"

if str(OUT_DIR) not in sys.path:
    sys.path.insert(0, str(OUT_DIR))
import build_prop_v2 as prop_v2
try:
    from .forward_result_evidence import register_evidence, trusted_result
except ImportError:
    from forward_result_evidence import register_evidence, trusted_result

SETTLED = {"WIN", "LOSS", "PUSH"}


def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().isoformat()


def num(value):
    try:
        x = float(value)
        return None if math.isnan(x) else x
    except Exception:
        return None


def clean(value):
    return str(value or "").strip()


def key_text(value):
    return re.sub(r"[^a-z0-9]+", "", clean(value).lower())


def line_text(value):
    value = num(value)
    return "" if value is None else f"{value:.4f}".rstrip("0").rstrip(".")


def parse_dt(value):
    if not value:
        return None
    try:
        d = pd.to_datetime(value, errors="coerce", utc=True)
        if pd.isna(d):
            return None
        return d.to_pydatetime()
    except Exception:
        return None


def read_json(path, fallback=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {} if fallback is None else fallback


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def read_jsonl(path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def identity_parts(row):
    return {
        "model_version": clean(row.get("model_version")) or "LEGACY_PROP_V2",
        "sport": clean(row.get("sport")).upper(),
        "lane": clean(row.get("lane")).upper(),
        "event_id": clean(row.get("event_id")),
        "game_key": clean(row.get("game_key")),
        "event_start": clean(row.get("event_start")),
        "player_key": clean(row.get("player_key")) or key_text(row.get("player")),
        # Current picks expose market_subtype; captured ledger ENTRY events
        # freeze it as "market". Both must round-trip to the same identity.
        "market": clean(row.get("market_subtype") or row.get("market")).upper(),
        "side": clean(row.get("side")).upper(),
        "line": line_text(row.get("line")),
    }


def identity_keys(row):
    p = identity_parts(row)
    tail = "|".join([
        p["player_key"],
        p["market"],
        p["side"],
        p["line"],
    ])
    keys = []
    if p["event_id"]:
        keys.append(f"event|{p['sport']}|{p['lane']}|{p['event_id']}|{tail}")
    if p["game_key"]:
        keys.append(f"game|{p['sport']}|{p['lane']}|{p['game_key']}|{tail}")
    start = parse_dt(p["event_start"])
    if start is not None:
        keys.append(
            f"date|{p['sport']}|{p['lane']}|{start.date().isoformat()}|{tail}"
        )
    return keys


def primary_key(row):
    keys = identity_keys(row)
    if not keys:
        return ""
    version = clean(row.get("model_version")) or "LEGACY_PROP_V2"
    return f"{version}|{keys[0]}"


def canonical():
    latest = {}
    for event in read_jsonl(LEDGER):
        key = event.get("forward_key")
        if not key:
            continue
        latest[key] = {**latest.get(key, {}), **event}
    return latest


def capture():
    payload = read_json(CURRENT, {})
    if payload.get("status") != "READY":
        return {"entries_added": 0, "monitor_triggers_added": 0}

    existing = canonical()
    entries_added = 0
    monitor_added = 0

    for row in payload.get("picks") or []:
        start = parse_dt(row.get("event_start"))
        if start is not None and start <= now():
            continue

        key = primary_key(row)
        if not key:
            continue

        prior = existing.get(key)
        monitor = row.get("shadow_decision") == "SHADOW_MONITOR"

        if prior is None:
            captured_at = now_iso()
            event = {
                "event_type": "ENTRY",
                "forward_key": key,
                "captured_at": captured_at,
                **identity_parts(row),
                "lane_key": row.get("lane_key"),
                "old_hulk_score": num(row.get("old_hulk_score")),
                "old_score_status": row.get("old_score_status"),
                "market_raw_probability_pct": num(row.get("market_raw_probability_pct")),
                "market_reference_probability_pct": num(
                    row.get("market_reference_probability_pct")
                ),
                "market_reference_type": row.get("market_reference_type"),
                "devig_paired_books": int(num(row.get("devig_paired_books")) or 0),
                "v2_probability_pct": num(row.get("v2_probability_pct")),
                "conservative_probability_pct": num(
                    row.get("conservative_probability_pct")
                ),
                "edge_pct_points": num(row.get("edge_pct_points")),
                "conservative_edge_pct_points": num(
                    row.get("conservative_edge_pct_points")
                ),
                "american_odds": num(row.get("american_odds")),
                "expected_value_pct": num(row.get("expected_value_pct")),
                "conservative_expected_value_pct": num(
                    row.get("conservative_expected_value_pct")
                ),
                "data_quality_grade": row.get("data_quality_grade"),
                "probability_source": row.get("probability_source"),
                "selection_rule_status": row.get("selection_rule_status"),
                "entry_shadow_decision": row.get("shadow_decision"),
                "monitor_selected": bool(monitor),
                "monitor_triggered_at": captured_at if monitor else None,
                "monitor_probability_pct": (
                    num(row.get("v2_probability_pct")) if monitor else None
                ),
                "monitor_market_probability_pct": (
                    num(row.get("market_reference_probability_pct"))
                    if monitor else None
                ),
                "monitor_american_odds": (
                    num(row.get("american_odds")) if monitor else None
                ),
                "status": "PENDING",
                "grade": "PENDING",
                "live_rule_changed": False,
            }
            append_jsonl(LEDGER, event)
            existing[key] = event
            entries_added += 1
            continue

        if monitor and not bool(prior.get("monitor_selected")):
            event = {
                "event_type": "MONITOR_TRIGGER",
                "forward_key": key,
                "monitor_selected": True,
                "monitor_triggered_at": now_iso(),
                "monitor_probability_pct": num(row.get("v2_probability_pct")),
                "monitor_market_probability_pct": num(
                    row.get("market_reference_probability_pct")
                ),
                "monitor_american_odds": num(row.get("american_odds")),
                "monitor_conservative_probability_pct": num(
                    row.get("conservative_probability_pct")
                ),
                "monitor_conservative_edge_pct_points": num(
                    row.get("conservative_edge_pct_points")
                ),
                "monitor_conservative_ev_pct": num(
                    row.get("conservative_expected_value_pct")
                ),
                "live_rule_changed": False,
            }
            append_jsonl(LEDGER, event)
            existing[key] = {**prior, **event}
            monitor_added += 1

    return {
        "entries_added": entries_added,
        "monitor_triggers_added": monitor_added,
    }


def payload_value(row, payload, key):
    value = row.get(key)
    if value is not None and not (
        isinstance(value, float) and math.isnan(value)
    ):
        return value
    return payload.get(key)


def history_identity(row, payload, sport, lane):
    start = (
        payload_value(row, payload, "start")
        or payload_value(row, payload, "start_dt")
    )
    return {
        "sport": sport,
        "lane": lane,
        "event_id": clean(payload_value(row, payload, "event_id")),
        "game_key": clean(payload_value(row, payload, "game_key")),
        "event_start": clean(start),
        "player_key": (
            clean(payload_value(row, payload, "player_key"))
            or key_text(payload_value(row, payload, "player"))
        ),
        "market_subtype": clean(
            payload_value(row, payload, "market_subtype")
            or payload_value(row, payload, "market")
        ).upper(),
        "side": clean(payload_value(row, payload, "side")).upper(),
        "line": num(payload_value(row, payload, "line")),
    }


def grade_lookup():
    lookup = {}
    for lane_key, cfg in prop_v2.LANES.items():
        path = cfg["history"]
        if not path.exists():
            continue
        d = pd.read_csv(path, low_memory=False)
        if d.empty or "grade" not in d.columns or "lane" not in d.columns:
            continue
        d = d[
            d["lane"].astype(str).str.upper().eq(cfg["lane"])
            & d["grade"].astype(str).str.upper().isin(SETTLED)
        ].copy()
        if d.empty:
            continue

        if "snapshot_at" in d.columns:
            d["_snapshot"] = pd.to_datetime(
                d["snapshot_at"], errors="coerce", utc=True
            )
            d = d.sort_values("_snapshot")

        for _, row in d.iterrows():
            payload = {}
            try:
                payload = json.loads(row.get("payload_json") or "{}")
            except Exception:
                pass
            identity = history_identity(
                row, payload, cfg["sport"], cfg["lane"]
            )
            grade_row = {
                **identity,
                "grade": clean(row.get("grade")).upper(),
                "actual_value": num(row.get("actual_value")),
                "grade_snapshot_at": (
                    clean(row.get("snapshot_at"))
                    if "snapshot_at" in row.index
                    else None
                ),
                "source_event_id": identity.get("event_id"),
            }
            for key in identity_keys(grade_row):
                register_evidence(lookup, key, grade_row)
    return lookup


def settle():
    existing = canonical()
    lookup = grade_lookup()
    settled_now = 0

    for key, row in existing.items():
        if clean(row.get("grade")).upper() in SETTLED:
            continue

        match = None
        matched_by = None
        # Exact frozen event ID is the strongest evidence. A game-key fallback
        # is allowed only when a source lacks event ID, not when two IDs
        # disagree. Date-only identity cannot settle a bet (doubleheaders).
        for identity_key in identity_keys(row):
            kind = identity_key.split("|", 1)[0]
            if kind not in {"event", "game"}:
                continue
            evidence = lookup.get(identity_key)
            if evidence is None:
                continue
            if evidence.get("ambiguous"):
                match = None
                matched_by = None
                break
            if kind == "game" and clean(row.get("event_id")) and clean(evidence.get("source_event_id")):
                if clean(row.get("event_id")) != clean(evidence.get("source_event_id")):
                    continue
            if kind == "event" and clean(row.get("game_key")) and clean(evidence.get("game_key")):
                if clean(row.get("game_key")) != clean(evidence.get("game_key")):
                    continue
            if trusted_result(evidence):
                match = evidence
                matched_by = kind
                break
        if not trusted_result(match):
            continue

        event = {
            "event_type": "SETTLED",
            "forward_key": key,
            "status": "SETTLED",
            "grade": match["grade"],
            "actual_value": match.get("actual_value"),
            "settled_at": now_iso(),
            "grade_snapshot_at": match.get("grade_snapshot_at"),
            "settlement_match_type": matched_by,
            "settlement_source_event_id": match.get("source_event_id"),
        }
        append_jsonl(LEDGER, event)
        settled_now += 1

    return settled_now


def brier_term(prob_pct, outcome):
    p = num(prob_pct)
    if p is None:
        return None
    p = min(0.999999, max(0.000001, p / 100.0))
    return (p - outcome) ** 2


def logloss_term(prob_pct, outcome):
    p = num(prob_pct)
    if p is None:
        return None
    p = min(0.999999, max(0.000001, p / 100.0))
    return -(outcome * math.log(p) + (1 - outcome) * math.log(1 - p))


def american_profit(odds):
    odds = num(odds)
    if odds is None or abs(odds) < 100:
        return None
    return odds / 100.0 if odds > 0 else 100.0 / abs(odds)


def mean(values):
    vals = [float(v) for v in values if v is not None]
    return None if not vals else round(sum(vals) / len(vals), 5)


def independent_block(row):
    sport = clean(row.get("sport")).upper()
    lane = clean(row.get("lane")).upper()
    game = clean(row.get("game_key"))
    event = clean(row.get("event_id"))
    start = parse_dt(row.get("event_start"))
    if game:
        anchor = f"game|{game}"
    elif event:
        anchor = f"event|{event}"
    elif start is not None:
        anchor = f"date|{start.date().isoformat()}"
    else:
        anchor = f"row|{clean(row.get('forward_key'))}"
    return f"{sport}|{lane}|{anchor}"


def grouped_lcb90(pairs):
    grouped = {}
    for block, value in pairs:
        if value is None:
            continue
        grouped.setdefault(block, []).append(float(value))
    block_means = [sum(vals) / len(vals) for vals in grouped.values() if vals]
    n = len(block_means)
    if n < 2:
        return len(grouped), None
    avg = sum(block_means) / n
    variance = sum((v - avg) ** 2 for v in block_means) / (n - 1)
    se = math.sqrt(max(0.0, variance) / n)
    return n, round(avg - 1.645 * se, 5)


def grouped_lcb95(pairs):
    grouped = {}
    for block, value in pairs:
        if value is None:
            continue
        grouped.setdefault(block, []).append(float(value))
    block_means = [sum(vals) / len(vals) for vals in grouped.values() if vals]
    n = len(block_means)
    if n < 2:
        return len(grouped), None
    avg = sum(block_means) / n
    variance = sum((v - avg) ** 2 for v in block_means) / (n - 1)
    se = math.sqrt(max(0.0, variance) / n)
    return n, round(avg - 1.96 * se, 5)


def summarize(rows, monitor_only=False):
    cohort = [
        row for row in rows
        if (not monitor_only or bool(row.get("monitor_selected")))
    ]
    settled = [
        row for row in cohort
        if clean(row.get("grade")).upper() in SETTLED
    ]

    wins = sum(clean(r.get("grade")).upper() == "WIN" for r in settled)
    losses = sum(clean(r.get("grade")).upper() == "LOSS" for r in settled)
    pushes = sum(clean(r.get("grade")).upper() == "PUSH" for r in settled)
    decisions = wins + losses

    market_brier = []
    v2_brier = []
    market_ll = []
    v2_ll = []
    units = []
    priced_settled = 0

    for row in settled:
        grade = clean(row.get("grade")).upper()
        if grade == "PUSH":
            continue
        outcome = 1 if grade == "WIN" else 0

        market_p = (
            row.get("monitor_market_probability_pct")
            if monitor_only
            else row.get("market_reference_probability_pct")
        )
        v2_p = (
            row.get("monitor_probability_pct")
            if monitor_only
            else row.get("v2_probability_pct")
        )
        mb = brier_term(market_p, outcome)
        vb = brier_term(v2_p, outcome)
        ml = logloss_term(market_p, outcome)
        vl = logloss_term(v2_p, outcome)
        if mb is not None:
            market_brier.append(mb)
        if vb is not None:
            v2_brier.append(vb)
        if ml is not None:
            market_ll.append(ml)
        if vl is not None:
            v2_ll.append(vl)

        odds = (
            row.get("monitor_american_odds")
            if monitor_only
            else row.get("american_odds")
        )
        profit = american_profit(odds)
        if profit is not None:
            priced_settled += 1
            units.append(profit if outcome else -1.0)

    market_brier_mean = mean(market_brier)
    v2_brier_mean = mean(v2_brier)
    market_ll_mean = mean(market_ll)
    v2_ll_mean = mean(v2_ll)
    unit_total = round(sum(units), 4) if units else None
    roi = (
        round(100 * unit_total / priced_settled, 2)
        if unit_total is not None and priced_settled
        else None
    )

    if decisions < 20:
        proof = "BUILDING_FORWARD_SAMPLE"
    elif (
        v2_brier_mean is not None
        and market_brier_mean is not None
        and v2_brier_mean <= market_brier_mean - 0.005
    ):
        proof = "REVIEW_CANDIDATE"
    else:
        proof = "NOT_PROVEN"

    return {
        "tracked": len(cohort),
        "pending": len(cohort) - len(settled),
        "settled": len(settled),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate_pct": (
            None if decisions == 0 else round(100 * wins / decisions, 1)
        ),
        "market_brier": market_brier_mean,
        "v2_brier": v2_brier_mean,
        "v2_minus_market_brier": (
            None
            if market_brier_mean is None or v2_brier_mean is None
            else round(v2_brier_mean - market_brier_mean, 5)
        ),
        "market_log_loss": market_ll_mean,
        "v2_log_loss": v2_ll_mean,
        "v2_minus_market_log_loss": (
            None
            if market_ll_mean is None or v2_ll_mean is None
            else round(v2_ll_mean - market_ll_mean, 5)
        ),
        "priced_settled": priced_settled,
        "units": unit_total,
        "roi_pct": roi,
        "proof_status": proof,
        "live_rule_changed": False,
    }


def summarize_v2(rows, monitor_only=False):
    cohort = [
        row for row in rows
        if (not monitor_only or bool(row.get("monitor_selected")))
    ]
    settled = [
        row for row in cohort
        if clean(row.get("grade")).upper() in SETTLED
    ]

    wins = sum(clean(r.get("grade")).upper() == "WIN" for r in settled)
    losses = sum(clean(r.get("grade")).upper() == "LOSS" for r in settled)
    pushes = sum(clean(r.get("grade")).upper() == "PUSH" for r in settled)
    decisions = wins + losses

    market_brier = []
    v2_brier = []
    market_ll = []
    v2_ll = []
    brier_advantage = []
    logloss_advantage = []
    brier_pairs = []
    logloss_pairs = []
    unit_pairs = []
    units = []
    priced_settled = 0

    for row in settled:
        grade = clean(row.get("grade")).upper()
        if grade == "PUSH":
            continue
        outcome = 1 if grade == "WIN" else 0
        block = independent_block(row)

        market_p = (
            row.get("monitor_market_probability_pct")
            if monitor_only
            else row.get("market_reference_probability_pct")
        )
        v2_p = (
            row.get("monitor_probability_pct")
            if monitor_only
            else row.get("v2_probability_pct")
        )
        mb = brier_term(market_p, outcome)
        vb = brier_term(v2_p, outcome)
        ml = logloss_term(market_p, outcome)
        vl = logloss_term(v2_p, outcome)

        if mb is not None:
            market_brier.append(mb)
        if vb is not None:
            v2_brier.append(vb)
        if ml is not None:
            market_ll.append(ml)
        if vl is not None:
            v2_ll.append(vl)
        if mb is not None and vb is not None:
            advantage = mb - vb
            brier_advantage.append(advantage)
            brier_pairs.append((block, advantage))
        if ml is not None and vl is not None:
            advantage = ml - vl
            logloss_advantage.append(advantage)
            logloss_pairs.append((block, advantage))

        odds = (
            row.get("monitor_american_odds")
            if monitor_only
            else row.get("american_odds")
        )
        profit = american_profit(odds)
        if profit is not None:
            priced_settled += 1
            unit = profit if outcome else -1.0
            units.append(unit)
            unit_pairs.append((block, unit))

    market_brier_mean = mean(market_brier)
    v2_brier_mean = mean(v2_brier)
    market_ll_mean = mean(market_ll)
    v2_ll_mean = mean(v2_ll)
    brier_adv_mean = mean(brier_advantage)
    logloss_adv_mean = mean(logloss_advantage)
    independent_blocks, brier_lcb90 = grouped_lcb90(brier_pairs)
    _, brier_lcb95 = grouped_lcb95(brier_pairs)
    logloss_blocks, logloss_lcb90 = grouped_lcb90(logloss_pairs)
    _, logloss_lcb95 = grouped_lcb95(logloss_pairs)
    priced_blocks, profit_lcb90 = grouped_lcb90(unit_pairs)
    _, profit_lcb95 = grouped_lcb95(unit_pairs)

    unit_total = round(sum(units), 4) if units else None
    roi = (
        round(100 * unit_total / priced_settled, 2)
        if unit_total is not None and priced_settled
        else None
    )
    roi_lcb90 = (
        None if profit_lcb90 is None else round(100 * profit_lcb90, 2)
    )
    roi_lcb95 = (
        None if profit_lcb95 is None else round(100 * profit_lcb95, 2)
    )

    enough_probability_sample = decisions >= 50 and independent_blocks >= 30
    if not enough_probability_sample:
        proof = "BUILDING_FORWARD_SAMPLE"
    elif (
        brier_adv_mean is not None
        and logloss_adv_mean is not None
        and brier_adv_mean > 0
        and logloss_adv_mean > 0
        and brier_lcb95 is not None
        and logloss_lcb95 is not None
        and brier_lcb95 > 0
        and logloss_lcb95 > 0
    ):
        proof = "PROBABILITY_REVIEW_CANDIDATE"
    elif (
        brier_adv_mean is not None
        and logloss_adv_mean is not None
        and brier_adv_mean > 0
        and logloss_adv_mean > 0
    ):
        proof = "PROMISING_NOT_PROVEN"
    else:
        proof = "NOT_PROVEN"

    return {
        "tracked": len(cohort),
        "pending": len(cohort) - len(settled),
        "settled": len(settled),
        "decisions": decisions,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate_pct": (
            None if decisions == 0 else round(100 * wins / decisions, 1)
        ),
        "market_brier": market_brier_mean,
        "v2_brier": v2_brier_mean,
        "v2_minus_market_brier": (
            None
            if market_brier_mean is None or v2_brier_mean is None
            else round(v2_brier_mean - market_brier_mean, 5)
        ),
        "market_log_loss": market_ll_mean,
        "v2_log_loss": v2_ll_mean,
        "v2_minus_market_log_loss": (
            None
            if market_ll_mean is None or v2_ll_mean is None
            else round(v2_ll_mean - market_ll_mean, 5)
        ),
        "paired_brier_advantage": brier_adv_mean,
        "paired_brier_advantage_lcb90": brier_lcb90,
        "paired_brier_advantage_lcb95": brier_lcb95,
        "paired_logloss_advantage": logloss_adv_mean,
        "paired_logloss_advantage_lcb90": logloss_lcb90,
        "paired_logloss_advantage_lcb95": logloss_lcb95,
        "independent_blocks": independent_blocks,
        "logloss_blocks": logloss_blocks,
        "priced_settled": priced_settled,
        "priced_blocks": priced_blocks,
        "units": unit_total,
        "roi_pct": roi,
        "roi_lcb90_pct": roi_lcb90,
        "roi_lcb95_pct": roi_lcb95,
        "proof_status": proof,
        "proof_requirements": {
            "minimum_decisions": 50,
            "minimum_independent_blocks": 30,
            "paired_brier_lcb95_must_be_positive": True,
            "paired_logloss_lcb95_must_be_positive": True,
        },
        "live_rule_changed": False,
    }


def promotion_dossier(lane_key, all_stats, monitor_stats):
    lane_kind = prop_v2.LANES[lane_key]["lane"]
    probability_gate = all_stats.get("proof_status") == "PROBABILITY_REVIEW_CANDIDATE"
    selection_probability_gate = (
        monitor_stats.get("proof_status") == "PROBABILITY_REVIEW_CANDIDATE"
    )

    if lane_kind == "PRIZEPICKS":
        economics_gate = False
        economics_status = "ENTRY_LEVEL_PAYOUT_PROOF_REQUIRED"
        if not probability_gate:
            recommendation = "HOLD_PROBABILITY_PROOF_REQUIRED"
        elif not selection_probability_gate:
            recommendation = "BUILDING_LEG_SELECTION_PROOF"
        else:
            recommendation = "LEG_MODEL_REVIEW_CANDIDATE_PAYOUT_PROOF_REQUIRED"
    else:
        priced_sample_gate = (
            int(monitor_stats.get("priced_settled") or 0) >= 50
            and int(monitor_stats.get("priced_blocks") or 0) >= 30
        )
        economics_gate = (
            priced_sample_gate
            and monitor_stats.get("roi_lcb95_pct") is not None
            and float(monitor_stats["roi_lcb95_pct"]) > 0
        )
        economics_status = (
            "PROFIT_CONFIDENCE_PROVEN"
            if economics_gate
            else "BUILDING_OR_UNPROVEN"
        )
        if not probability_gate:
            recommendation = "HOLD_PROBABILITY_PROOF_REQUIRED"
        elif not selection_probability_gate:
            recommendation = "BUILDING_SELECTION_PROOF"
        elif not priced_sample_gate:
            recommendation = "BUILDING_PRICED_SAMPLE"
        elif not economics_gate:
            recommendation = "HOLD_PROFIT_NOT_PROVEN"
        else:
            recommendation = "MANUAL_REVIEW_CANDIDATE"

    return {
        "recommendation": recommendation,
        "automatic_promotion": False,
        "probability_gate": {
            "passed": probability_gate,
            "status": all_stats.get("proof_status"),
        },
        "selection_gate": {
            "passed": selection_probability_gate,
            "status": monitor_stats.get("proof_status"),
        },
        "economics_gate": {
            "passed": economics_gate,
            "status": economics_status,
        },
        "required_before_play": (
            "Probability proof + leg selection proof + entry-level payout economics."
            if lane_kind == "PRIZEPICKS"
            else "Probability proof + selection proof + priced ROI confidence; manual review only."
        ),
    }


def build_summary(capture_result, settled_now):
    archived_rows = list(canonical().values())
    rows = [
        r for r in archived_rows
        if clean(r.get("model_version")) == prop_v2.MODEL_VERSION
    ]
    by_lane = {}
    for lane_key in prop_v2.LANES:
        lane_rows = [r for r in rows if r.get("lane_key") == lane_key]
        all_stats = summarize_v2(lane_rows, monitor_only=False)
        monitor_stats = summarize_v2(lane_rows, monitor_only=True)
        by_lane[lane_key] = {
            "all_predictions": all_stats,
            "monitor_selection": monitor_stats,
            "promotion": promotion_dossier(lane_key, all_stats, monitor_stats),
        }

    payload = {
        "generated_at": now_iso(),
        "status": "READY",
        "mode": "FORWARD_SHADOW",
        "model_version": prop_v2.MODEL_VERSION,
        "active_predictions_total": len(rows),
        "archived_predictions_total": len(archived_rows),
        "legacy_predictions_preserved": len(archived_rows) - len(rows),
        "capture": capture_result,
        "settled_now": settled_now,
        "all_predictions": summarize_v2(rows, monitor_only=False),
        "monitor_selection": summarize_v2(rows, monitor_only=True),
        "by_lane": by_lane,
        "rules": [
            "First pregame V2 probability is frozen for forward calibration.",
            "Shadow-monitor selection is frozen separately when a candidate first crosses the monitor rule.",
            "Settled outcomes never rewrite the frozen probabilities.",
            "Probability-model proof and betting-selection proof are measured separately.",
            "Correlated props from the same game count as one independent evidence block for confidence testing.",
            "Promotion review requires at least 50 decisions, 30 independent blocks, and positive 95% lower-confidence bounds for both paired Brier and log-loss improvement.",
            "Sportsbook prop promotion also requires a priced forward sample and positive lower-confidence ROI; PrizePicks requires separate entry-level payout proof.",
            "No live promotion occurs automatically from this ledger.",
        ],
    }
    return payload


def settle_nhl_official_box():
    try:
        from .nhl_official_box_forward import (
            plan_nhl_settlement, file_digests,
        )
    except ImportError:
        from nhl_official_box_forward import (
            plan_nhl_settlement, file_digests,
        )

    receipt, planned = plan_nhl_settlement(ROOT, canonical())
    status = receipt.get("status")
    if status == "READY":
        # NHL core refresh may be writing a source file concurrently.
        # In that case settle nothing and retry at the next hourly pass.
        if file_digests(ROOT) != receipt.get("source_digests"):
            receipt["status"] = "SOURCE_CHANGED_BEFORE_SETTLEMENT"
        else:
            for row in planned:
                append_jsonl(LEDGER, row)
            receipt["settled_now"] = len(planned)
    else:
        receipt["settled_now"] = 0
    receipt.setdefault("settled_now", 0)
    write_json(NHL_BOX_RECEIPT, receipt)
    if receipt["status"] == "INTEGRITY_HOLD_CONTRADICTORY_SETTLEMENT":
        raise RuntimeError("NHL official box disagrees with existing forward grade; no new NHL settlements written")
    return receipt


def settle_mlb_official_box(session=None, max_events=50):
    # Bound each verified settlement pass. Subsequent runs continue from the
    # unchanged frozen ledger; default hourly refresh also uses this cap.
    if not isinstance(max_events, int) or not 1 <= max_events <= 500:
        raise ValueError("MLB verified settlement batch must contain 1 to 500 events")
    try:
        from .mlb_official_box_forward import (
            plan_mlb_settlement, archive_fingerprint,
        )
    except ImportError:
        from mlb_official_box_forward import (
            plan_mlb_settlement, archive_fingerprint,
        )

    try:
        from .mlb_verified_player_crosswalk import source_fingerprint
    except ImportError:
        from mlb_verified_player_crosswalk import source_fingerprint

    source_ledger = LEDGER
    before = (
        (source_ledger.stat().st_size, source_ledger.stat().st_mtime_ns)
        if source_ledger.exists() else None
    )
    receipt, planned = plan_mlb_settlement(
        ROOT, canonical(), session or requests.Session(),
    )
    # Two independently corroborated official-ID crosswalks are prioritized
    # over ordinary original archive IDs to resolve old missing-ID cases.
    planned = sorted(planned, key=lambda x: (
        x.get("player_id_provenance") != "TWO_STATSAPI_ID_SOURCES_EXACT_NAME_AND_TEAM",
        str(x.get("official_game_pk")), str(x.get("forward_key")),
    ))
    batch = planned[:max_events]
    receipt["batch_limit"] = max_events
    receipt["pending_verified_next_batch"] = len(planned) - len(batch)
    receipt["planned_verified_this_run"] = len(planned)
    receipt["settled_now"] = 0
    if receipt.get("status") == "READY":
        current = (
            (source_ledger.stat().st_size, source_ledger.stat().st_mtime_ns)
            if source_ledger.exists() else None
        )
        if archive_fingerprint(ROOT) != receipt.get("archive_source"):
            receipt["status"] = "ARCHIVE_CHANGED_BEFORE_APPEND"
        elif source_fingerprint(ROOT) != receipt.get("id_source_fingerprints"):
            receipt["status"] = "OFFICIAL_ID_EVIDENCE_CHANGED_BEFORE_APPEND"
        elif current != before:
            receipt["status"] = "LEDGER_CHANGED_BEFORE_APPEND"
        else:
            for event in batch:
                append_jsonl(LEDGER, event)
            receipt["settled_now"] = len(batch)
    write_json(MLB_BOX_RECEIPT, receipt)
    if receipt["status"] == "INTEGRITY_HOLD_PREVIOUS_GRADE_CONFLICT":
        raise RuntimeError("MLB official box contradicts an existing grade; no new official MLB events appended")
    return receipt


def main():
    capture_result = capture()
    generic_settled_now = settle()
    nhl_receipt = settle_nhl_official_box()
    mlb_receipt = settle_mlb_official_box()
    settled_now = (
        generic_settled_now
        + int(nhl_receipt.get("settled_now") or 0)
        + int(mlb_receipt.get("settled_now") or 0)
    )
    payload = build_summary(capture_result, settled_now)
    payload["nhl_official_box"] = {
        "status": nhl_receipt.get("status"),
        "settled_now": nhl_receipt.get("settled_now", 0),
        "existing_verified": nhl_receipt.get("existing_verified", 0),
        "conflicting_previous_grades_count": nhl_receipt.get("conflicting_previous_grades_count", 0),
        "official_result_not_platform_payout": True,
        "automatic_model_promotion": False,
    }
    payload["mlb_official_box"] = {
        "status": mlb_receipt.get("status"),
        "settled_now": mlb_receipt.get("settled_now", 0),
        "existing_verified": mlb_receipt.get("existing_verified", 0),
        "conflicting_previous_grades_count": mlb_receipt.get("conflicting_previous_grades_count", 0),
        "official_result_not_platform_payout": True,
        "automatic_model_promotion": False,
    }
    write_json(SUMMARY, payload)
    write_json(PUBLIC, payload)
    if DIST.exists():
        write_json(DIST, payload)

    print(json.dumps({
        "status": payload["status"],
        "capture": capture_result,
        "settled_now": settled_now,
        "nhl_official_box": payload["nhl_official_box"],
        "mlb_official_box": payload["mlb_official_box"],
        "all_predictions": payload["all_predictions"],
        "monitor_selection": payload["monitor_selection"],
        "by_lane": {
            key: {
                "all": value["all_predictions"],
                "monitor": value["monitor_selection"],
            }
            for key, value in payload["by_lane"].items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
