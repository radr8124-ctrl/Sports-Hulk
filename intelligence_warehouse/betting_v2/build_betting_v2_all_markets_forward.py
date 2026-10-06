#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
CURRENT = OUT_DIR / "BETTING_V2_ALL_MARKETS_CURRENT.json"
LEDGER = OUT_DIR / "BETTING_V2_ALL_MARKETS_FORWARD_LEDGER.jsonl"
PRICE_LEDGER = OUT_DIR / "BETTING_V2_ALL_MARKETS_PRICE_TIMELINE.jsonl"
SUMMARY = OUT_DIR / "BETTING_V2_ALL_MARKETS_FORWARD_SUMMARY.json"
PUBLIC = ROOT / "commercial_web" / "public" / "betting_v2_all_markets_forward.json"
DIST = ROOT / "commercial_web" / "dist" / "betting_v2_all_markets_forward.json"

SPORTS = ("NFL", "CFB", "CBB", "MLB", "NBA", "NHL")
MARKETS = ("MONEYLINE", "SPREAD", "TOTAL")
SETTLED = {"WIN", "LOSS", "PUSH"}
HISTORY_FILES = {
    sport: ROOT / f"{sport.lower()}_live" / "decision" / "history" /
    f"{sport}_GRADED_RECOMMENDATIONS.csv"
    for sport in SPORTS
}


def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().isoformat()


def clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def norm(value):
    return re.sub(r"[^a-z0-9]+", "", clean(value).lower())


def num(value):
    try:
        x = float(value)
        return None if math.isnan(x) else x
    except Exception:
        return None


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


def line_text(value):
    x = num(value)
    return "" if x is None else f"{x:.4f}"


def identity(row):
    return "|".join([
        clean(row.get("sport")).upper(),
        clean(row.get("game_key")),
        clean(row.get("market")).upper(),
        clean(row.get("selection_key")).upper(),
        line_text(row.get("line")),
    ])


def forward_key(version, row):
    return f"{clean(version)}|{identity(row)}"


def canonical():
    latest = {}
    for event in read_jsonl(LEDGER):
        key = event.get("forward_key")
        if key:
            latest[key] = {
                **latest.get(key, {}),
                **event,
            }
    return latest


def price_history():
    out = {}
    for row in read_jsonl(PRICE_LEDGER):
        key = clean(row.get("market_key"))
        if key:
            out.setdefault(key, []).append(row)
    for rows in out.values():
        rows.sort(key=lambda x: x.get("captured_at") or "")
    return out


def snapshot_prices(payload):
    captured_at = now_iso()
    existing = read_jsonl(PRICE_LEDGER)
    latest = {}
    for row in existing:
        key = clean(row.get("market_key"))
        if key:
            latest[key] = (
                row.get("american_odds"),
                row.get("market_reference_probability_pct"),
                row.get("book_count"),
            )

    added = 0
    for row in payload.get("picks") or []:
        start = parse_dt(row.get("event_start"))
        if start is not None and start <= now():
            continue
        key = identity(row)
        if not key:
            continue
        sig = (
            num(row.get("american_odds")),
            num(row.get("market_reference_probability_pct")),
            int(num(row.get("book_count")) or 0),
        )
        if latest.get(key) == sig:
            continue
        event = {
            "event_type": "MARKET_PRICE",
            "captured_at": captured_at,
            "market_key": key,
            "sport": clean(row.get("sport")).upper(),
            "game_key": clean(row.get("game_key")),
            "market": clean(row.get("market")).upper(),
            "selection": clean(row.get("selection")),
            "selection_key": clean(row.get("selection_key")).upper(),
            "line": num(row.get("line")),
            "event_start": row.get("event_start"),
            "american_odds": num(row.get("american_odds")),
            "market_reference_probability_pct": num(
                row.get("market_reference_probability_pct")
            ),
            "market_reference_type": row.get("market_reference_type"),
            "book_count": int(num(row.get("book_count")) or 0),
        }
        append_jsonl(PRICE_LEDGER, event)
        latest[key] = sig
        added += 1
    return added


def capture():
    payload = read_json(CURRENT, {})
    if payload.get("status") != "READY":
        return {
            "entries_added": 0,
            "shadow_triggers_added": 0,
            "price_snapshots_added": 0,
            "model_version": None,
        }

    version = clean(
        payload.get("model_version")
        or "BETTING_V2_ALL_MARKETS_UNVERSIONED"
    )
    price_added = snapshot_prices(payload)
    existing = canonical()
    added = 0
    triggers = 0

    for row in payload.get("picks") or []:
        start = parse_dt(row.get("event_start"))
        if start is not None and start <= now():
            continue
        key = forward_key(version, row)
        prior = existing.get(key)
        shadow = clean(row.get("shadow_decision")).upper() == "SHADOW_PLAY"

        if prior is None:
            captured_at = now_iso()
            event = {
                "event_type": "ENTRY",
                "forward_key": key,
                "model_version": version,
                "captured_at": captured_at,
                "lane_key": clean(row.get("lane_key")),
                "sport": clean(row.get("sport")).upper(),
                "game_key": clean(row.get("game_key")),
                "market": clean(row.get("market")).upper(),
                "selection": clean(row.get("selection")),
                "selection_key": clean(row.get("selection_key")).upper(),
                "line": num(row.get("line")),
                "event_start": row.get("event_start"),
                "entry_american_odds": num(row.get("american_odds")),
                "entry_market_reference_probability_pct": num(
                    row.get("market_reference_probability_pct")
                ),
                "entry_v2_probability_pct": num(
                    row.get("calibrated_win_probability_pct")
                ),
                "entry_probability_source": row.get("probability_source"),
                "entry_edge_pct_points": num(row.get("edge_pct_points")),
                "entry_expected_value_pct": num(row.get("expected_value_pct")),
                "entry_conservative_ev_pct": num(
                    row.get("conservative_expected_value_pct")
                ),
                "historical_edge_confidence": row.get(
                    "historical_edge_confidence"
                ),
                "selection_rule_status": row.get("selection_rule_status"),
                "data_quality_grade": row.get("data_quality_grade"),
                "opposite_side_conflict": bool(
                    row.get("opposite_side_conflict")
                ),
                "duplicate_line_variant": bool(
                    row.get("duplicate_line_variant")
                ),
                "same_game_exposure_block": bool(
                    row.get("same_game_exposure_block")
                ),
                "entry_shadow_decision": row.get("shadow_decision"),
                "shadow_selected": bool(shadow),
                "shadow_triggered_at": captured_at if shadow else None,
                "shadow_probability_pct": (
                    num(row.get("calibrated_win_probability_pct"))
                    if shadow else None
                ),
                "shadow_market_reference_probability_pct": (
                    num(row.get("market_reference_probability_pct"))
                    if shadow else None
                ),
                "shadow_american_odds": (
                    num(row.get("american_odds")) if shadow else None
                ),
                "status": "PENDING",
                "grade": "PENDING",
                "live_rule_changed": False,
            }
            append_jsonl(LEDGER, event)
            existing[key] = event
            added += 1
            continue

        if shadow and not bool(prior.get("shadow_selected")):
            event = {
                "event_type": "SHADOW_TRIGGER",
                "forward_key": key,
                "shadow_selected": True,
                "shadow_triggered_at": now_iso(),
                "shadow_probability_pct": num(
                    row.get("calibrated_win_probability_pct")
                ),
                "shadow_market_reference_probability_pct": num(
                    row.get("market_reference_probability_pct")
                ),
                "shadow_american_odds": num(row.get("american_odds")),
                "live_rule_changed": False,
            }
            append_jsonl(LEDGER, event)
            existing[key] = {**prior, **event}
            triggers += 1

    return {
        "entries_added": added,
        "shadow_triggers_added": triggers,
        "price_snapshots_added": price_added,
        "model_version": version,
    }


def history_lookup():
    lookup = {}
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
            or "market" not in d.columns
        ):
            continue
        d = d[
            d["lane"].astype(str).str.upper().eq("GAME")
            & d["market"].astype(str).str.upper().isin(MARKETS)
            & d["grade"].astype(str).str.upper().isin(SETTLED)
        ].copy()
        if "snapshot_at" in d.columns:
            d["_snapshot"] = pd.to_datetime(
                d["snapshot_at"], errors="coerce", utc=True
            )
            d = d.sort_values("_snapshot")

        for _, row in d.iterrows():
            market = clean(row.get("market")).upper()
            game_key = clean(row.get("game_key"))
            selection = clean(row.get("selection"))
            line = None if market == "MONEYLINE" else num(row.get("line"))
            if not game_key or not selection:
                continue
            key = "|".join([
                sport,
                game_key,
                market,
                norm(selection),
                line_text(line),
            ])
            lookup[key] = {
                "grade": clean(row.get("grade")).upper(),
                "grade_snapshot_at": clean(row.get("snapshot_at")),
                "away_score": num(row.get("away_score")),
                "home_score": num(row.get("home_score")),
            }
    return lookup


def settle():
    lookup = history_lookup()
    existing = canonical()
    settled_now = 0

    for key, row in existing.items():
        if clean(row.get("grade")).upper() in SETTLED:
            continue
        result_key = "|".join([
            clean(row.get("sport")).upper(),
            clean(row.get("game_key")),
            clean(row.get("market")).upper(),
            norm(row.get("selection")),
            line_text(row.get("line")),
        ])
        result = lookup.get(result_key)
        if not result:
            continue
        event = {
            "event_type": "SETTLED",
            "forward_key": key,
            "status": "SETTLED",
            "grade": result["grade"],
            "settled_at": now_iso(),
            "grade_snapshot_at": result.get("grade_snapshot_at"),
            "away_score": result.get("away_score"),
            "home_score": result.get("home_score"),
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
    odds = num(odds)
    if odds is None or abs(odds) < 100:
        return None
    return odds / 100.0 if odds > 0 else 100.0 / abs(odds)


def mean(values):
    vals = [float(v) for v in values if v is not None]
    return None if not vals else round(sum(vals) / len(vals), 5)


def grouped_lcb90(pairs):
    grouped = {}
    for block, value in pairs:
        if value is not None:
            grouped.setdefault(block, []).append(float(value))
    means = [
        sum(values) / len(values)
        for values in grouped.values()
        if values
    ]
    n = len(means)
    if n < 2:
        return n, None
    avg = sum(means) / n
    var = sum((x - avg) ** 2 for x in means) / (n - 1)
    se = math.sqrt(max(0.0, var) / n)
    return n, round(avg - 1.645 * se, 5)


def closing_reference(row, prices):
    key = identity(row)
    start = parse_dt(row.get("event_start"))
    captured_at = parse_dt(row.get("captured_at"))
    if not key or start is None or captured_at is None:
        return None
    candidates = []
    for quote in prices.get(key, []):
        qtime = parse_dt(quote.get("captured_at"))
        if qtime is None:
            continue
        if qtime < captured_at or qtime > start:
            continue
        candidates.append(quote)
    if not candidates:
        return None
    close = candidates[-1]
    probability = num(close.get("market_reference_probability_pct"))
    if probability is None:
        return None
    return {
        "captured_at": close.get("captured_at"),
        "probability_pct": probability,
    }


def summarize(rows, shadow_only=False, prices=None):
    cohort = [
        row for row in rows
        if not shadow_only or bool(row.get("shadow_selected"))
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
    clv = []
    clv_pairs = []
    priced = 0

    for row in settled:
        grade = clean(row.get("grade")).upper()
        if grade == "PUSH":
            continue
        outcome = 1 if grade == "WIN" else 0
        block = f"{clean(row.get('sport')).upper()}|{clean(row.get('game_key'))}"

        if shadow_only:
            market_p = row.get("shadow_market_reference_probability_pct")
            v2_p = row.get("shadow_probability_pct")
            odds = row.get("shadow_american_odds")
        else:
            market_p = row.get("entry_market_reference_probability_pct")
            v2_p = row.get("entry_v2_probability_pct")
            odds = row.get("entry_american_odds")

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

        profit = american_profit(odds)
        if profit is not None:
            priced += 1
            unit = profit if outcome else -1.0
            units.append(unit)
            unit_pairs.append((block, unit))

        if prices is not None:
            close = closing_reference(row, prices)
            if close is not None:
                entry_ref = num(market_p)
                close_ref = num(close.get("probability_pct"))
                if entry_ref is not None and close_ref is not None:
                    value = close_ref - entry_ref
                    clv.append(value)
                    clv_pairs.append((block, value))

    market_b = mean(market_brier)
    v2_b = mean(v2_brier)
    market_l = mean(market_ll)
    v2_l = mean(v2_ll)
    brier_adv = mean([v for _, v in brier_pairs])
    ll_adv = mean([v for _, v in ll_pairs])
    blocks, brier_lcb = grouped_lcb90(brier_pairs)
    ll_blocks, ll_lcb = grouped_lcb90(ll_pairs)
    priced_blocks, profit_lcb = grouped_lcb90(unit_pairs)
    clv_blocks, clv_lcb = grouped_lcb90(clv_pairs)

    total_units = round(sum(units), 4) if units else None
    roi = (
        round(100 * total_units / priced, 2)
        if total_units is not None and priced
        else None
    )
    roi_lcb = (
        None if profit_lcb is None
        else round(100 * profit_lcb, 2)
    )

    if decisions < 50 or blocks < 30:
        proof = "BUILDING_FORWARD_SAMPLE"
    elif (
        brier_adv is not None
        and ll_adv is not None
        and brier_adv > 0
        and ll_adv > 0
        and brier_lcb is not None
        and ll_lcb is not None
        and brier_lcb > 0
        and ll_lcb > 0
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
            None if decisions == 0
            else round(100 * wins / decisions, 1)
        ),
        "market_brier": market_b,
        "v2_brier": v2_b,
        "v2_minus_market_brier": (
            None if market_b is None or v2_b is None
            else round(v2_b - market_b, 5)
        ),
        "market_log_loss": market_l,
        "v2_log_loss": v2_l,
        "v2_minus_market_log_loss": (
            None if market_l is None or v2_l is None
            else round(v2_l - market_l, 5)
        ),
        "paired_brier_advantage": brier_adv,
        "paired_brier_advantage_lcb90": brier_lcb,
        "paired_logloss_advantage": ll_adv,
        "paired_logloss_advantage_lcb90": ll_lcb,
        "independent_blocks": blocks,
        "logloss_blocks": ll_blocks,
        "priced_settled": priced,
        "priced_blocks": priced_blocks,
        "units": total_units,
        "roi_pct": roi,
        "roi_lcb90_pct": roi_lcb,
        "closing_quotes": len(clv),
        "closing_blocks": clv_blocks,
        "avg_clv_probability_pp": mean(clv),
        "clv_lcb90_probability_pp": clv_lcb,
        "proof_status": proof,
        "live_rule_changed": False,
    }


def promotion(all_stats, shadow_stats):
    probability = (
        all_stats.get("proof_status")
        == "PROBABILITY_REVIEW_CANDIDATE"
    )
    selection = (
        shadow_stats.get("proof_status")
        == "PROBABILITY_REVIEW_CANDIDATE"
    )
    priced_ready = (
        int(shadow_stats.get("priced_settled") or 0) >= 50
        and int(shadow_stats.get("priced_blocks") or 0) >= 30
    )
    economics = (
        priced_ready
        and shadow_stats.get("roi_lcb90_pct") is not None
        and float(shadow_stats["roi_lcb90_pct"]) > 0
    )
    clv_ready = (
        int(shadow_stats.get("closing_quotes") or 0) >= 30
        and int(shadow_stats.get("closing_blocks") or 0) >= 25
    )
    clv = (
        clv_ready
        and shadow_stats.get("clv_lcb90_probability_pp") is not None
        and float(shadow_stats["clv_lcb90_probability_pp"]) > 0
    )

    if not probability:
        rec = "HOLD_PROBABILITY_PROOF_REQUIRED"
    elif not selection:
        rec = "BUILDING_SELECTION_PROOF"
    elif not priced_ready:
        rec = "BUILDING_PRICED_SAMPLE"
    elif not economics:
        rec = "HOLD_PROFIT_NOT_PROVEN"
    elif not clv_ready:
        rec = "BUILDING_CLV_SAMPLE"
    elif not clv:
        rec = "HOLD_CLV_NOT_PROVEN"
    else:
        rec = "MANUAL_REVIEW_CANDIDATE"

    return {
        "recommendation": rec,
        "automatic_promotion": False,
        "probability_gate": {
            "passed": probability,
            "status": all_stats.get("proof_status"),
        },
        "selection_gate": {
            "passed": selection,
            "status": shadow_stats.get("proof_status"),
        },
        "economics_gate": {
            "passed": economics,
            "sample_ready": priced_ready,
            "roi_lcb90_pct": shadow_stats.get("roi_lcb90_pct"),
        },
        "clv_gate": {
            "passed": clv,
            "sample_ready": clv_ready,
            "clv_lcb90_probability_pp": shadow_stats.get(
                "clv_lcb90_probability_pp"
            ),
        },
    }


def main():
    capture_result = capture()
    settled_now = settle()
    rows = list(canonical().values())
    version = clean(capture_result.get("model_version"))
    rows = [
        r for r in rows
        if clean(r.get("model_version")) == version
    ]
    prices = price_history()

    lane_keys = sorted({
        clean(r.get("lane_key"))
        for r in rows
        if clean(r.get("lane_key"))
    })
    by_lane = {}
    for lane in lane_keys:
        cohort = [
            r for r in rows
            if clean(r.get("lane_key")) == lane
        ]
        all_stats = summarize(
            cohort, shadow_only=False, prices=prices
        )
        shadow_stats = summarize(
            cohort, shadow_only=True, prices=prices
        )
        by_lane[lane] = {
            "all_predictions": all_stats,
            "shadow_selection": shadow_stats,
            "promotion": promotion(all_stats, shadow_stats),
        }

    payload = {
        "generated_at": now_iso(),
        "status": "READY",
        "mode": "FORWARD_SHADOW_VERSIONED",
        "current_model_version": version,
        "capture": capture_result,
        "settled_now": settled_now,
        "all_predictions": summarize(
            rows, shadow_only=False, prices=prices
        ),
        "shadow_selection": summarize(
            rows, shadow_only=True, prices=prices
        ),
        "by_lane": by_lane,
        "rules": [
            "Each sport/market lane has its own immutable forward cohort.",
            "Same-game results share one confidence block.",
            "First pregame probability and price are frozen and never rewritten.",
            "SHADOW_PLAY triggers are frozen separately.",
            "Probability, ROI and CLV proof are independent promotion gates.",
            "Missing real closing quotes receive no CLV credit.",
            "No automatic PLAY promotion is allowed.",
        ],
    }

    write_json(SUMMARY, payload)
    write_json(PUBLIC, payload)
    if DIST.exists():
        write_json(DIST, payload)

    print(json.dumps({
        "status": "READY",
        "capture": capture_result,
        "settled_now": settled_now,
        "all_predictions": payload["all_predictions"],
        "shadow_selection": payload["shadow_selection"],
        "lanes": {
            k: {
                "all": v["all_predictions"],
                "shadow": v["shadow_selection"],
                "promotion": v["promotion"],
            }
            for k, v in by_lane.items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
