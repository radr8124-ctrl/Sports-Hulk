#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    from .forward_result_evidence import register_evidence, trusted_result
except ImportError:
    from forward_result_evidence import register_evidence, trusted_result

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
CURRENT = OUT_DIR / "PARLAY_V2_CURRENT.json"
LEDGER = OUT_DIR / "PARLAY_V2_FORWARD_LEDGER.jsonl"
SUMMARY = OUT_DIR / "PARLAY_V2_FORWARD_SUMMARY.json"
PUBLIC = ROOT / "commercial_web" / "public" / "parlay_v2_forward.json"
DIST = ROOT / "commercial_web" / "dist" / "parlay_v2_forward.json"

SPORTS = ("NFL", "CFB", "CBB", "MLB", "NBA", "NHL")
SETTLED = {"WIN", "LOSS", "PUSH"}
HISTORY_FILES = {
    sport: ROOT / f"{sport.lower()}_live" / "decision" / "history" /
    f"{sport}_GRADED_RECOMMENDATIONS.csv"
    for sport in SPORTS
}

if str(OUT_DIR) not in sys.path:
    sys.path.insert(0, str(OUT_DIR))
import build_parlay_v2 as pv2


def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().isoformat()


def clean(value):
    return pv2.clean(value)


def num(value):
    return pv2.num(value)


def parse_dt(value):
    try:
        d = pd.to_datetime(value, errors="coerce", utc=True)
        return None if pd.isna(d) else d.to_pydatetime()
    except Exception:
        return None


def read_json(path, fallback=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {} if fallback is None else fallback


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


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def canonical():
    out = {}
    for event in read_jsonl(LEDGER):
        key = event.get("forward_key")
        if not key:
            continue
        out[key] = {**out.get(key, {}), **event}
    return out


def leg_event_id(leg):
    return clean(
        leg.get("source_game_key")
        or leg.get("source_event_id")
        or leg.get("event")
    )


def earliest_start(legs):
    values = []
    for leg in legs:
        dt = parse_dt(leg.get("source_event_start"))
        if dt is not None:
            values.append(dt)
    return min(values) if values else None


def forward_key(version, row):
    return "|".join([
        clean(version),
        clean(row.get("sport")).upper(),
        clean(row.get("combo_signature")),
    ])


def capture():
    payload = read_json(CURRENT, {})
    if payload.get("status") != "READY":
        return {
            "model_version": None,
            "entries_added": 0,
            "monitor_triggers_added": 0,
        }

    version = clean(
        payload.get("model_version")
        or "PARLAY_V2_UNVERSIONED"
    )
    existing = canonical()
    entries = 0
    triggers = 0

    for row in payload.get("picks") or []:
        legs = row.get("legs") or []
        start = earliest_start(legs)
        if start is not None and start <= now():
            continue

        key = forward_key(version, row)
        prior = existing.get(key)
        monitor = (
            clean(row.get("shadow_decision")).upper()
            == "SHADOW_MONITOR"
        )

        if prior is None:
            captured_at = now_iso()
            event = {
                "event_type": "ENTRY",
                "forward_key": key,
                "model_version": version,
                "captured_at": captured_at,
                "sport": clean(row.get("sport")).upper(),
                "combo_signature": row.get("combo_signature"),
                "legacy_parlay_score": num(
                    row.get("legacy_parlay_score")
                ),
                "legs": legs,
                "component_events": sorted(set(
                    leg_event_id(leg)
                    for leg in legs
                    if leg_event_id(leg)
                )),
                "first_leg_start": (
                    start.isoformat() if start is not None
                    else None
                ),
                "resolved_all_legs": (
                    int(row.get("resolved_legs") or 0)
                    == int(row.get("leg_count") or 0)
                ),
                "all_source_legs_forward_proven": bool(
                    row.get(
                        "all_source_legs_forward_proven"
                    )
                ),
                "correlation_status": row.get(
                    "correlation_status"
                ),
                "joint_probability_method": row.get(
                    "joint_probability_method"
                ),
                "entry_joint_v2_probability_pct": num(
                    row.get("joint_v2_probability_pct")
                ),
                "entry_joint_reference_probability_pct": num(
                    row.get(
                        "joint_reference_probability_pct"
                    )
                ),
                "entry_joint_conservative_probability_pct": num(
                    row.get(
                        "joint_conservative_probability_pct"
                    )
                ),
                "entry_joint_edge_pct_points": num(
                    row.get("joint_edge_pct_points")
                ),
                "entry_parlay_american_odds": num(
                    row.get(
                        "captured_parlay_american_odds"
                    )
                ),
                "entry_expected_value_pct": num(
                    row.get("expected_value_pct")
                ),
                "entry_conservative_ev_pct": num(
                    row.get(
                        "conservative_expected_value_pct"
                    )
                ),
                "entry_shadow_decision": row.get(
                    "shadow_decision"
                ),
                "monitor_selected": monitor,
                "monitor_triggered_at": (
                    captured_at if monitor else None
                ),
                "monitor_joint_v2_probability_pct": (
                    num(row.get("joint_v2_probability_pct"))
                    if monitor else None
                ),
                "monitor_joint_reference_probability_pct": (
                    num(
                        row.get(
                            "joint_reference_probability_pct"
                        )
                    )
                    if monitor else None
                ),
                "monitor_parlay_american_odds": (
                    num(
                        row.get(
                            "captured_parlay_american_odds"
                        )
                    )
                    if monitor else None
                ),
                "status": "PENDING",
                "grade": "PENDING",
                "live_rule_changed": False,
            }
            append_jsonl(LEDGER, event)
            existing[key] = event
            entries += 1
            continue

        if monitor and not bool(prior.get("monitor_selected")):
            event = {
                "event_type": "MONITOR_TRIGGER",
                "forward_key": key,
                "monitor_selected": True,
                "monitor_triggered_at": now_iso(),
                "monitor_joint_v2_probability_pct": num(
                    row.get("joint_v2_probability_pct")
                ),
                "monitor_joint_reference_probability_pct": num(
                    row.get(
                        "joint_reference_probability_pct"
                    )
                ),
                "monitor_parlay_american_odds": num(
                    row.get(
                        "captured_parlay_american_odds"
                    )
                ),
                "live_rule_changed": False,
            }
            append_jsonl(LEDGER, event)
            existing[key] = {**prior, **event}
            triggers += 1

    return {
        "model_version": version,
        "entries_added": entries,
        "monitor_triggers_added": triggers,
    }


def result_lookup():
    out = {}
    for sport, path in HISTORY_FILES.items():
        if not path.exists():
            continue
        try:
            d = pd.read_csv(path, low_memory=False)
        except Exception:
            continue
        if (
            d.empty
            or "lane" not in d.columns
            or "grade" not in d.columns
        ):
            continue
        d = d[
            d["lane"].astype(str).str.upper().eq("PARLAY")
            & d["grade"].astype(str).str.upper().isin(SETTLED)
        ].copy()
        if d.empty:
            continue

        if "snapshot_at" in d.columns:
            d["_snapshot"] = pd.to_datetime(
                d["snapshot_at"],
                errors="coerce",
                utc=True,
            )
            d = d.sort_values("_snapshot")

        for _, row in d.iterrows():
            payload = pv2.parse_json(row.get("payload_json"))
            mapping = dict(payload)
            legs = [
                pv2.leg_from_mapping(mapping, 1, sport),
                pv2.leg_from_mapping(mapping, 2, sport),
            ]
            signature = pv2.combo_signature(legs)
            grade = clean(row.get("grade")).upper()
            if not signature or grade not in SETTLED:
                continue
            register_evidence(out, (sport, signature), {
                "grade": grade,
                "grade_snapshot_at": clean(row.get("snapshot_at")),
                "leg1_grade": clean(row.get("leg1_grade")).upper(),
                "leg2_grade": clean(row.get("leg2_grade")).upper(),
            })
    return out


def settle():
    entries = canonical()
    results = result_lookup()
    settled_now = 0

    for key, row in entries.items():
        if clean(row.get("grade")).upper() in SETTLED:
            continue
        sport = clean(row.get("sport")).upper()
        signature = clean(row.get("combo_signature"))
        result = results.get((sport, signature))
        if not trusted_result(result):
            continue
        event = {
            "event_type": "SETTLED",
            "forward_key": key,
            "status": "SETTLED",
            "grade": result["grade"],
            "settled_at": now_iso(),
            "grade_snapshot_at": result.get(
                "grade_snapshot_at"
            ),
            "leg1_grade": result.get("leg1_grade"),
            "leg2_grade": result.get("leg2_grade"),
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
    return -(
        outcome * math.log(p)
        + (1 - outcome) * math.log(1 - p)
    )


def american_profit(odds):
    return pv2.american_profit(odds)


def mean(values):
    vals = [float(v) for v in values if v is not None]
    return None if not vals else round(
        sum(vals) / len(vals), 5
    )


def grouped_lcb90(values):
    vals = [float(v) for v in values if v is not None]
    n = len(vals)
    if n < 2:
        return n, None
    avg = sum(vals) / n
    variance = (
        sum((v - avg) ** 2 for v in vals)
        / (n - 1)
    )
    se = math.sqrt(max(0.0, variance) / n)
    return n, round(avg - 1.645 * se, 5)


def disjoint_subset(rows):
    chosen = []
    used = set()
    for row in sorted(
        rows,
        key=lambda r: r.get("captured_at") or "",
    ):
        events = {
            clean(v)
            for v in row.get("component_events") or []
            if clean(v)
        }
        if not events:
            continue
        if events & used:
            continue
        chosen.append(row)
        used |= events
    return chosen


def summarize(rows, monitor_only=False):
    cohort = [
        row for row in rows
        if not monitor_only
        or bool(row.get("monitor_selected"))
    ]
    settled = [
        row for row in cohort
        if clean(row.get("grade")).upper()
        in SETTLED
    ]
    decisions = [
        row for row in settled
        if clean(row.get("grade")).upper()
        in {"WIN", "LOSS"}
    ]
    disjoint = disjoint_subset(decisions)

    wins = sum(
        clean(r.get("grade")).upper() == "WIN"
        for r in decisions
    )
    losses = len(decisions) - wins
    pushes = sum(
        clean(r.get("grade")).upper() == "PUSH"
        for r in settled
    )

    market_brier = []
    v2_brier = []
    market_ll = []
    v2_ll = []
    brier_adv = []
    ll_adv = []
    units = []
    priced = 0

    proof_market_brier = []
    proof_v2_brier = []
    proof_market_ll = []
    proof_v2_ll = []
    proof_brier_adv = []
    proof_ll_adv = []
    proof_units = []

    def fields(row):
        if monitor_only:
            return (
                row.get(
                    "monitor_joint_reference_probability_pct"
                ),
                row.get(
                    "monitor_joint_v2_probability_pct"
                ),
                row.get("monitor_parlay_american_odds"),
            )
        return (
            row.get(
                "entry_joint_reference_probability_pct"
            ),
            row.get("entry_joint_v2_probability_pct"),
            row.get("entry_parlay_american_odds"),
        )

    for row in decisions:
        outcome = (
            1
            if clean(row.get("grade")).upper() == "WIN"
            else 0
        )
        market_p, v2_p, odds = fields(row)
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
            brier_adv.append(mb - vb)
        if ml is not None and vl is not None:
            ll_adv.append(ml - vl)
        profit = american_profit(odds)
        if profit is not None:
            priced += 1
            units.append(profit if outcome else -1.0)

    for row in disjoint:
        outcome = (
            1
            if clean(row.get("grade")).upper() == "WIN"
            else 0
        )
        market_p, v2_p, odds = fields(row)
        mb = brier_term(market_p, outcome)
        vb = brier_term(v2_p, outcome)
        ml = logloss_term(market_p, outcome)
        vl = logloss_term(v2_p, outcome)
        if mb is not None:
            proof_market_brier.append(mb)
        if vb is not None:
            proof_v2_brier.append(vb)
        if ml is not None:
            proof_market_ll.append(ml)
        if vl is not None:
            proof_v2_ll.append(vl)
        if mb is not None and vb is not None:
            proof_brier_adv.append(mb - vb)
        if ml is not None and vl is not None:
            proof_ll_adv.append(ml - vl)
        profit = american_profit(odds)
        if profit is not None:
            proof_units.append(
                profit if outcome else -1.0
            )

    proof_n, brier_lcb = grouped_lcb90(
        proof_brier_adv
    )
    _, ll_lcb = grouped_lcb90(proof_ll_adv)
    priced_proof_n, roi_unit_lcb = grouped_lcb90(
        proof_units
    )

    unit_total = (
        round(sum(units), 4) if units else None
    )
    roi = (
        None
        if unit_total is None or priced == 0
        else round(100 * unit_total / priced, 2)
    )
    roi_lcb = (
        None
        if roi_unit_lcb is None
        else round(100 * roi_unit_lcb, 2)
    )

    brier_adv_mean = mean(proof_brier_adv)
    ll_adv_mean = mean(proof_ll_adv)

    enough_probability = (
        len(decisions) >= 50
        and proof_n >= 30
    )
    if not enough_probability:
        proof_status = "BUILDING_FORWARD_SAMPLE"
    elif (
        brier_adv_mean is not None
        and ll_adv_mean is not None
        and brier_adv_mean > 0
        and ll_adv_mean > 0
        and brier_lcb is not None
        and ll_lcb is not None
        and brier_lcb > 0
        and ll_lcb > 0
    ):
        proof_status = "PROBABILITY_REVIEW_CANDIDATE"
    elif (
        brier_adv_mean is not None
        and ll_adv_mean is not None
        and brier_adv_mean > 0
        and ll_adv_mean > 0
    ):
        proof_status = "PROMISING_NOT_PROVEN"
    else:
        proof_status = "NOT_PROVEN"

    return {
        "tracked": len(cohort),
        "pending": len(cohort) - len(settled),
        "settled": len(settled),
        "decisions": len(decisions),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate_pct": (
            None
            if not decisions
            else round(
                100 * wins / len(decisions), 1
            )
        ),
        "research_market_brier": mean(market_brier),
        "research_v2_brier": mean(v2_brier),
        "research_market_log_loss": mean(market_ll),
        "research_v2_log_loss": mean(v2_ll),
        "proof_disjoint_parlays": len(disjoint),
        "proof_market_brier": mean(
            proof_market_brier
        ),
        "proof_v2_brier": mean(proof_v2_brier),
        "proof_market_log_loss": mean(
            proof_market_ll
        ),
        "proof_v2_log_loss": mean(proof_v2_ll),
        "paired_brier_advantage": brier_adv_mean,
        "paired_brier_advantage_lcb90": brier_lcb,
        "paired_logloss_advantage": ll_adv_mean,
        "paired_logloss_advantage_lcb90": ll_lcb,
        "priced_settled": priced,
        "units": unit_total,
        "roi_pct": roi,
        "priced_disjoint_parlays": priced_proof_n,
        "roi_lcb90_pct": roi_lcb,
        "proof_status": proof_status,
        "live_rule_changed": False,
    }


def promotion(stats):
    probability_gate = (
        stats.get("proof_status")
        == "PROBABILITY_REVIEW_CANDIDATE"
    )
    priced_ready = (
        int(stats.get("priced_settled") or 0) >= 50
        and int(
            stats.get("priced_disjoint_parlays") or 0
        ) >= 30
    )
    economics_gate = (
        priced_ready
        and stats.get("roi_lcb90_pct") is not None
        and float(stats["roi_lcb90_pct"]) > 0
    )

    if not probability_gate:
        recommendation = "HOLD_PROBABILITY_PROOF_REQUIRED"
    elif not priced_ready:
        recommendation = "BUILDING_PRICED_PARLAY_SAMPLE"
    elif not economics_gate:
        recommendation = "HOLD_PROFIT_NOT_PROVEN"
    else:
        recommendation = "MANUAL_REVIEW_CANDIDATE"

    return {
        "recommendation": recommendation,
        "automatic_promotion": False,
        "probability_gate": {
            "passed": probability_gate,
            "status": stats.get("proof_status"),
        },
        "economics_gate": {
            "passed": economics_gate,
            "sample_ready": priced_ready,
            "roi_lcb90_pct": stats.get(
                "roi_lcb90_pct"
            ),
        },
        "required_before_play": (
            "All source legs forward-proven + disjoint forward "
            "parlay probability proof + captured price sample + "
            "positive lower-confidence ROI; manual review only."
        ),
    }


def build_summary(capture_result, settled_now):
    rows = list(canonical().values())
    version = clean(capture_result.get("model_version"))
    current_rows = [
        r for r in rows
        if clean(r.get("model_version")) == version
    ]

    all_stats = summarize(
        current_rows, monitor_only=False
    )
    monitor_stats = summarize(
        current_rows, monitor_only=True
    )

    by_sport = {}
    for sport in SPORTS:
        sport_rows = [
            r for r in current_rows
            if clean(r.get("sport")).upper() == sport
        ]
        sport_all = summarize(
            sport_rows, monitor_only=False
        )
        sport_monitor = summarize(
            sport_rows, monitor_only=True
        )
        by_sport[sport] = {
            "all_predictions": sport_all,
            "monitor_selection": sport_monitor,
            "promotion": promotion(sport_monitor),
        }

    versions = {}
    for row in rows:
        v = clean(row.get("model_version")) or "UNKNOWN"
        versions[v] = versions.get(v, 0) + 1

    return {
        "generated_at": now_iso(),
        "status": "READY",
        "mode": "FORWARD_SHADOW_VERSIONED",
        "current_model_version": version,
        "capture": capture_result,
        "settled_now": settled_now,
        "ledger_unique_predictions": len(rows),
        "version_counts": versions,
        "all_predictions": all_stats,
        "monitor_selection": monitor_stats,
        "promotion": promotion(monitor_stats),
        "by_sport": by_sport,
        "rules": [
            "Each Parlay V2 model version has its own immutable forward cohort.",
            "Only pregame combinations are frozen.",
            "Joint probability is tracked only for cross-game resolved combinations.",
            "The independence product is research-only until forward calibration proves it.",
            "Probability proof uses a deterministic disjoint subset so combinations sharing underlying events cannot inflate sample size.",
            "No ROI proof exists without a captured combined parlay price or platform payout.",
            "No live parlay promotion occurs automatically.",
        ],
    }


def main():
    capture_result = capture()
    settled_now = settle()
    payload = build_summary(
        capture_result, settled_now
    )
    write_json(SUMMARY, payload)
    write_json(PUBLIC, payload)
    if DIST.exists():
        write_json(DIST, payload)

    print(json.dumps({
        "status": payload["status"],
        "capture": capture_result,
        "settled_now": settled_now,
        "all_predictions": payload["all_predictions"],
        "monitor_selection": payload[
            "monitor_selection"
        ],
        "promotion": payload["promotion"],
    }, indent=2))


if __name__ == "__main__":
    main()
