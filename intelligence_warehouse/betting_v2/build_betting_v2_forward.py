#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
CURRENT = OUT_DIR / "BETTING_V2_CURRENT.json"
LEDGER = OUT_DIR / "BETTING_V2_FORWARD_LEDGER.jsonl"
SUMMARY = OUT_DIR / "BETTING_V2_FORWARD_SUMMARY.json"
PUBLIC = ROOT / "commercial_web" / "public" / "betting_v2_forward.json"
DIST = ROOT / "commercial_web" / "dist" / "betting_v2_forward.json"

if str(OUT_DIR) not in sys.path:
    sys.path.insert(0, str(OUT_DIR))
import build_betting_v2 as betting

SETTLED = {"WIN", "LOSS", "PUSH"}


def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().isoformat()


def clean(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    return str(v).strip()


def num(v):
    try:
        x = float(v)
        return None if math.isnan(x) else x
    except Exception:
        return None


def norm(v):
    return re.sub(r"[^a-z0-9]+", "", clean(v).lower())


def parse_dt(v):
    try:
        d = pd.to_datetime(v, errors="coerce", utc=True)
        return None if pd.isna(d) else d.to_pydatetime()
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


def forward_key(row, model_version=None):
    version = clean(model_version or row.get("model_version"))
    sport = clean(row.get("sport")).upper()
    game = clean(row.get("game_key"))
    side = clean(row.get("side")).upper()
    selection = norm(row.get("selection"))
    identity = side if side in {"HOME", "AWAY"} else selection
    if not version or not sport or not game or not identity:
        return ""
    return f"{version}|{sport}|{game}|{identity}"


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

    version = clean(payload.get("model_version") or betting.MODEL_VERSION)
    existing = canonical()
    added = 0
    triggers = 0

    for row in payload.get("picks") or []:
        start = parse_dt(row.get("event_start"))
        if start is not None and start <= now():
            continue

        key = forward_key(row, version)
        if not key:
            continue
        prior = existing.get(key)
        monitor = clean(row.get("shadow_decision")).upper() == "SHADOW_PLAY"

        if prior is None:
            captured_at = now_iso()
            event = {
                "event_type": "ENTRY",
                "forward_key": key,
                "model_version": version,
                "captured_at": captured_at,
                "sport": clean(row.get("sport")).upper(),
                "game_key": clean(row.get("game_key")),
                "selection": clean(row.get("selection")),
                "side": clean(row.get("side")).upper() or None,
                "event_start": row.get("event_start"),
                "american_odds": num(row.get("american_odds")),
                "raw_market_probability_pct": num(
                    row.get("raw_market_implied_probability_pct")
                ),
                "market_reference_probability_pct": num(
                    row.get("market_reference_probability_pct")
                ),
                "market_reference_type": row.get("market_reference_type"),
                "devig_paired_books": int(num(row.get("devig_paired_books")) or 0),
                "v2_probability_pct": num(
                    row.get("calibrated_win_probability_pct")
                ),
                "hulk_evidence_score": num(row.get("hulk_evidence_score")),
                "old_score_status": row.get("old_score_status"),
                "historical_edge_confidence": row.get(
                    "historical_edge_confidence"
                ),
                "selection_rule_status": row.get("selection_rule_status"),
                "probability_source": row.get("probability_source"),
                "expected_value_pct": num(row.get("expected_value_pct")),
                "conservative_expected_value_pct": num(
                    row.get("conservative_expected_value_pct")
                ),
                "data_quality_grade": row.get("data_quality_grade"),
                "entry_shadow_decision": row.get("shadow_decision"),
                "monitor_selected": bool(monitor),
                "monitor_triggered_at": captured_at if monitor else None,
                "monitor_probability_pct": (
                    num(row.get("calibrated_win_probability_pct"))
                    if monitor else None
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
            added += 1
            continue

        if monitor and not bool(prior.get("monitor_selected")):
            event = {
                "event_type": "MONITOR_TRIGGER",
                "forward_key": key,
                "monitor_selected": True,
                "monitor_triggered_at": now_iso(),
                "monitor_probability_pct": num(
                    row.get("calibrated_win_probability_pct")
                ),
                "monitor_market_probability_pct": num(
                    row.get("market_reference_probability_pct")
                ),
                "monitor_american_odds": num(row.get("american_odds")),
                "live_rule_changed": False,
            }
            append_jsonl(LEDGER, event)
            existing[key] = {**prior, **event}
            triggers += 1

    return {
        "entries_added": added,
        "monitor_triggers_added": triggers,
        "model_version": version,
    }


def parse_payload(v):
    try:
        return json.loads(v or "{}")
    except Exception:
        return {}


def row_side(sport, row, payload):
    side = clean(payload.get("selection_side")).upper()
    if side in {"HOME", "AWAY"}:
        return side

    selection = clean(
        payload.get("selection_canonical")
        or payload.get("selection")
        or row.get("selection")
    ).upper()

    if sport in {"CFB", "CBB", "MLB"}:
        away = clean(payload.get("away_team")).upper()
        home = clean(payload.get("home_team")).upper()
    elif sport in {"NBA", "NHL"}:
        away = clean(payload.get("away_team_canonical")).upper()
        home = clean(payload.get("home_team_canonical")).upper()
    else:
        return None

    if selection and away and selection == away:
        return "AWAY"
    if selection and home and selection == home:
        return "HOME"
    return None


def grade_lookup():
    by_side = {}
    by_selection = {}

    for sport, path in betting.HISTORY_FILES.items():
        if not path.exists():
            continue
        d = pd.read_csv(path, low_memory=False)
        if (
            d.empty
            or "lane" not in d.columns
            or "market" not in d.columns
            or "grade" not in d.columns
        ):
            continue
        d = d[
            d["lane"].astype(str).str.upper().eq("GAME")
            & d["market"].astype(str).str.upper().eq("MONEYLINE")
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
            payload = parse_payload(row.get("payload_json"))
            game = clean(
                payload.get("game_key")
                or row.get("game_key")
                or row.get("event_id")
            )
            if not game:
                continue
            grade = clean(row.get("grade")).upper()
            selection = clean(
                payload.get("selection_canonical")
                or payload.get("selection")
                or row.get("selection")
            )
            side = row_side(sport, row, payload)
            result = {
                "grade": grade,
                "actual_value": num(row.get("actual_value")),
                "grade_snapshot_at": clean(row.get("snapshot_at")),
            }
            if side in {"HOME", "AWAY"}:
                by_side[f"{sport}|{game}|{side}"] = result
            if selection:
                by_selection[
                    f"{sport}|{game}|{norm(selection)}"
                ] = result

    return by_side, by_selection


def settle():
    existing = canonical()
    by_side, by_selection = grade_lookup()
    settled_now = 0

    for key, row in existing.items():
        if clean(row.get("grade")).upper() in SETTLED:
            continue
        sport = clean(row.get("sport")).upper()
        game = clean(row.get("game_key"))
        side = clean(row.get("side")).upper()
        selection = norm(row.get("selection"))

        match = None
        if side in {"HOME", "AWAY"}:
            match = by_side.get(f"{sport}|{game}|{side}")
        if match is None and selection:
            match = by_selection.get(f"{sport}|{game}|{selection}")
        if match is None:
            continue

        event = {
            "event_type": "SETTLED",
            "forward_key": key,
            "status": "SETTLED",
            "grade": match["grade"],
            "actual_value": match.get("actual_value"),
            "settled_at": now_iso(),
            "grade_snapshot_at": match.get("grade_snapshot_at"),
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


def independent_block(row):
    return f"{clean(row.get('sport')).upper()}|{clean(row.get('game_key'))}"


def mean(values):
    vals = [float(v) for v in values if v is not None]
    return None if not vals else round(sum(vals) / len(vals), 5)


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


def summarize(rows, monitor_only=False):
    cohort = [
        row for row in rows
        if not monitor_only or bool(row.get("monitor_selected"))
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
    brier_pairs = []
    ll_pairs = []
    units = []
    unit_pairs = []

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
            brier_pairs.append((block, mb - vb))
        if ml is not None and vl is not None:
            ll_pairs.append((block, ml - vl))

        odds = (
            row.get("monitor_american_odds")
            if monitor_only
            else row.get("american_odds")
        )
        profit = american_profit(odds)
        if profit is not None:
            unit = profit if outcome else -1.0
            units.append(unit)
            unit_pairs.append((block, unit))

    market_brier_mean = mean(market_brier)
    v2_brier_mean = mean(v2_brier)
    market_ll_mean = mean(market_ll)
    v2_ll_mean = mean(v2_ll)
    brier_adv = mean([v for _, v in brier_pairs])
    ll_adv = mean([v for _, v in ll_pairs])
    independent_blocks, brier_lcb90 = grouped_lcb90(brier_pairs)
    _, ll_lcb90 = grouped_lcb90(ll_pairs)
    priced_blocks, profit_lcb90 = grouped_lcb90(unit_pairs)

    priced_settled = len(units)
    unit_total = round(sum(units), 4) if units else None
    roi = (
        round(100 * unit_total / priced_settled, 2)
        if unit_total is not None and priced_settled
        else None
    )
    roi_lcb90 = (
        None if profit_lcb90 is None else round(100 * profit_lcb90, 2)
    )

    enough = decisions >= 50 and independent_blocks >= 30
    if not enough:
        proof = "BUILDING_FORWARD_SAMPLE"
    elif (
        brier_adv is not None
        and ll_adv is not None
        and brier_adv > 0
        and ll_adv > 0
        and brier_lcb90 is not None
        and ll_lcb90 is not None
        and brier_lcb90 > 0
        and ll_lcb90 > 0
    ):
        proof = "PROBABILITY_REVIEW_CANDIDATE"
    elif (
        brier_adv is not None
        and ll_adv is not None
        and brier_adv > 0
        and ll_adv > 0
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
        "paired_brier_advantage": brier_adv,
        "paired_brier_advantage_lcb90": brier_lcb90,
        "paired_logloss_advantage": ll_adv,
        "paired_logloss_advantage_lcb90": ll_lcb90,
        "independent_blocks": independent_blocks,
        "priced_settled": priced_settled,
        "priced_blocks": priced_blocks,
        "units": unit_total,
        "roi_pct": roi,
        "roi_lcb90_pct": roi_lcb90,
        "proof_status": proof,
        "proof_requirements": {
            "minimum_decisions": 50,
            "minimum_independent_blocks": 30,
            "paired_brier_lcb90_must_be_positive": True,
            "paired_logloss_lcb90_must_be_positive": True,
        },
        "live_rule_changed": False,
    }


def promotion_dossier(all_stats, monitor_stats):
    probability_gate = (
        all_stats.get("proof_status") == "PROBABILITY_REVIEW_CANDIDATE"
    )
    selection_gate = (
        monitor_stats.get("proof_status") == "PROBABILITY_REVIEW_CANDIDATE"
    )
    priced_sample = (
        int(monitor_stats.get("priced_settled") or 0) >= 50
        and int(monitor_stats.get("priced_blocks") or 0) >= 30
    )
    economics_gate = bool(
        priced_sample
        and monitor_stats.get("roi_lcb90_pct") is not None
        and float(monitor_stats["roi_lcb90_pct"]) > 0
    )

    if not probability_gate:
        recommendation = "HOLD_PROBABILITY_PROOF_REQUIRED"
    elif not selection_gate:
        recommendation = "BUILDING_SELECTION_PROOF"
    elif not priced_sample:
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
            "passed": selection_gate,
            "status": monitor_stats.get("proof_status"),
        },
        "economics_gate": {
            "passed": economics_gate,
            "status": (
                "PROFIT_CONFIDENCE_PROVEN"
                if economics_gate else "BUILDING_OR_UNPROVEN"
            ),
        },
        "required_before_play": (
            "Historical edge confidence + forward probability proof + "
            "forward selection proof + priced ROI confidence; manual review only."
        ),
    }


def build_summary(capture_result, settled_now):
    rows = list(canonical().values())
    current_version = capture_result.get("model_version") or betting.MODEL_VERSION
    version_rows = [
        r for r in rows if clean(r.get("model_version")) == current_version
    ]
    by_sport = {}
    for sport in betting.SPORTS:
        sport_rows = [r for r in version_rows if r.get("sport") == sport]
        all_stats = summarize(sport_rows, monitor_only=False)
        monitor_stats = summarize(sport_rows, monitor_only=True)
        by_sport[sport] = {
            "all_predictions": all_stats,
            "monitor_selection": monitor_stats,
            "promotion": promotion_dossier(all_stats, monitor_stats),
        }

    all_stats = summarize(version_rows, monitor_only=False)
    monitor_stats = summarize(version_rows, monitor_only=True)
    payload = {
        "generated_at": now_iso(),
        "status": "READY",
        "mode": "FORWARD_SHADOW",
        "model_version": current_version,
        "capture": capture_result,
        "settled_now": settled_now,
        "all_predictions": all_stats,
        "monitor_selection": monitor_stats,
        "promotion": promotion_dossier(all_stats, monitor_stats),
        "by_sport": by_sport,
        "ledger_total_versions": len(
            set(clean(r.get("model_version")) for r in rows if r.get("model_version"))
        ),
        "rules": [
            "Each model version freezes its own pregame predictions; older frozen V2 entries are never rewritten.",
            "The first pregame probability for a model version is permanent.",
            "Shadow-play selection is frozen separately if a candidate later crosses the selection rule before game start.",
            "Outcomes are matched only to settled GAME moneyline results.",
            "Probability proof compares frozen V2 probability against the frozen fair/reference market.",
            "Promotion requires at least 50 decisions, 30 independent games, positive lower-confidence Brier and log-loss improvement, and separate profitable selection proof.",
            "No forward result can automatically promote a live Best Bet.",
        ],
    }
    return payload


def main():
    capture_result = capture()
    settled_now = settle()
    payload = build_summary(capture_result, settled_now)
    write_json(SUMMARY, payload)
    write_json(PUBLIC, payload)
    if DIST.exists():
        write_json(DIST, payload)
    print(json.dumps({
        "status": payload["status"],
        "model_version": payload["model_version"],
        "capture": payload["capture"],
        "settled_now": payload["settled_now"],
        "all_predictions": payload["all_predictions"],
        "monitor_selection": payload["monitor_selection"],
        "promotion": payload["promotion"],
        "by_sport": {
            k: {
                "all": v["all_predictions"],
                "monitor": v["monitor_selection"],
                "promotion": v["promotion"],
            }
            for k, v in payload["by_sport"].items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
