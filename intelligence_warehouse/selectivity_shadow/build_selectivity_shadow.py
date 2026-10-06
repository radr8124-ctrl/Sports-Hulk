#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "selectivity_shadow"
OUT_DIR.mkdir(parents=True, exist_ok=True)

POLICY_PATH = OUT_DIR / "SELECTIVITY_SHADOW_POLICY.json"
LEDGER_PATH = OUT_DIR / "SELECTIVITY_SHADOW_LEDGER.jsonl"
SUMMARY_PATH = OUT_DIR / "SELECTIVITY_SHADOW_SUMMARY.json"
ANALYSIS_PATH = ROOT / "intelligence_warehouse" / "brain_performance" / "SELECTIVITY_ANALYSIS.json"
PUBLIC_PATH = ROOT / "commercial_web" / "public" / "selectivity_shadow.json"
DIST_PATH = ROOT / "commercial_web" / "dist" / "selectivity_shadow.json"

SETTLED = {"WIN", "LOSS", "PUSH"}

CURRENT_FILES = {
    "CFB": ROOT / "cfb_live" / "decision" / "CFB_GAME_FINALISTS.csv",
}

GRADE_FILES = {
    "CFB": ROOT / "cfb_live" / "decision" / "history" / "CFB_GRADED_RECOMMENDATIONS.csv",
}


def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().isoformat()


def parse_dt(value):
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def num(value):
    try:
        x = float(value)
        return None if math.isnan(x) else x
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


def read_ledger():
    if not LEDGER_PATH.exists():
        return []
    rows = []
    for line in LEDGER_PATH.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def append_event(event):
    with LEDGER_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")


def canonical_ledger():
    latest = {}
    for event in read_ledger():
        pick_id = str(event.get("pick_id") or "")
        if not pick_id:
            continue
        latest[pick_id] = {**latest.get(pick_id, {}), **event}
    return list(latest.values())


def initial_policy():
    analysis = read_json(ANALYSIS_PATH, {})
    validated = [
        row for row in analysis.get("actionable") or []
        if str(row.get("status") or "").startswith("VALIDATED")
        and row.get("candidate", {}).get("minimum_score") is not None
    ]

    if not validated:
        return {
            "policy_version": 1,
            "created_at": now_iso(),
            "experiments": [],
            "automatic_live_changes": False,
        }

    row = validated[0]
    threshold = float(row["candidate"]["minimum_score"])
    experiment_id = (
        f"{str(row.get('sport')).lower()}_"
        f"{str(row.get('lane')).lower()}_"
        f"{str(row.get('market')).lower()}_"
        f"score_{str(threshold).replace('.', '_')}_v1"
    )
    return {
        "policy_version": 1,
        "created_at": now_iso(),
        "automatic_live_changes": False,
        "rules": [
            "Shadow experiments never suppress or promote live user-facing picks.",
            "Experiment thresholds are frozen at experiment start.",
            "Only picks captured before event start enter the forward shadow record.",
            "Prices are frozen at capture time for price-aware unit tracking.",
            "A future live threshold change requires a separate explicit review.",
        ],
        "experiments": [{
            "experiment_id": experiment_id,
            "status": "SHADOW_RUNNING",
            "started_at": now_iso(),
            "sport": str(row.get("sport") or "").upper(),
            "lane": str(row.get("lane") or "").upper(),
            "market": str(row.get("market") or "").upper(),
            "candidate_min_score": threshold,
            "baseline_rule": "ALL_CURRENT_QUALIFIED_RESEARCH",
            "candidate_rule": f"EVIDENCE_SCORE_GTE_{threshold}",
            "source_analysis_generated_at": analysis.get("generated_at"),
            "source_training": row.get("train_baseline"),
            "source_holdout": row.get("holdout_baseline"),
            "candidate_training": row.get("candidate", {}).get("train"),
            "candidate_holdout": row.get("candidate", {}).get("holdout"),
            "price_aware_profitability_validated_at_start": False,
        }],
    }


def ensure_policy():
    if not POLICY_PATH.exists():
        write_json(POLICY_PATH, initial_policy())
    return read_json(POLICY_PATH, {"experiments": []})


def current_rows(experiment):
    sport = experiment.get("sport")
    path = CURRENT_FILES.get(sport)
    if path is None or not path.exists():
        return pd.DataFrame()

    d = pd.read_csv(path, low_memory=False)
    if d.empty:
        return d

    rename = {
        "market_canonical": "market",
        "selection_canonical": "selection",
        "evidence_score": "score",
        "start_dt": "start",
        "median_price_american": "american_odds",
        "sportsbook_count": "book_count",
    }
    d = d.rename(columns={k: v for k, v in rename.items() if k in d.columns})

    for col in ["market", "selection", "decision", "game_key"]:
        if col not in d.columns:
            d[col] = ""
    if "score" not in d.columns:
        d["score"] = None
    if "start" not in d.columns:
        d["start"] = None
    if "american_odds" not in d.columns:
        d["american_odds"] = None

    d["market"] = d["market"].astype(str).str.upper()
    d["decision"] = d["decision"].astype(str).str.upper()
    d["score"] = pd.to_numeric(d["score"], errors="coerce")
    d["american_odds"] = pd.to_numeric(d["american_odds"], errors="coerce")
    d["_start"] = pd.to_datetime(d["start"], errors="coerce", utc=True)

    return d[
        d["market"].eq(str(experiment.get("market") or "").upper())
        & d["decision"].eq("QUALIFIED_RESEARCH")
    ].copy()


def make_pick_id(experiment_id, row):
    body = "|".join([
        str(experiment_id),
        str(row.get("game_key") or ""),
        str(row.get("market") or ""),
        str(row.get("selection") or ""),
        str(row.get("start") or ""),
    ])
    return hashlib.sha256(body.encode()).hexdigest()


def capture(policy):
    existing_rows = {row.get("pick_id"): row for row in canonical_ledger()}
    captured = 0
    candidate_triggers = 0
    details = []

    for exp in policy.get("experiments") or []:
        if exp.get("status") != "SHADOW_RUNNING":
            continue

        rows = current_rows(exp)
        baseline_seen = 0
        candidate_seen = 0
        for _, row in rows.iterrows():
            start = row.get("_start")
            if pd.isna(start) or start.to_pydatetime() <= now():
                continue

            score = num(row.get("score"))
            if score is None:
                continue

            baseline_seen += 1
            candidate = score >= float(exp.get("candidate_min_score"))
            candidate_seen += int(candidate)

            pick_id = make_pick_id(exp["experiment_id"], row)
            odds = num(row.get("american_odds"))
            prior = existing_rows.get(pick_id)

            if prior is not None:
                if candidate and not bool(prior.get("candidate_selected")):
                    append_event({
                        "event_type": "CANDIDATE_TRIGGERED",
                        "pick_id": pick_id,
                        "candidate_selected": True,
                        "candidate_captured_at": now_iso(),
                        "candidate_score": score,
                        "candidate_american_odds": odds,
                        "candidate_book_count": int(num(row.get("book_count")) or 0),
                        "automatic_live_change": False,
                    })
                    existing_rows[pick_id] = {
                        **prior,
                        "candidate_selected": True,
                        "candidate_captured_at": now_iso(),
                        "candidate_score": score,
                        "candidate_american_odds": odds,
                    }
                    candidate_triggers += 1
                continue

            captured_at = now_iso()
            event = {
                "event_type": "CAPTURED",
                "pick_id": pick_id,
                "experiment_id": exp["experiment_id"],
                "captured_at": captured_at,
                "sport": exp.get("sport"),
                "lane": exp.get("lane"),
                "market": exp.get("market"),
                "game_key": str(row.get("game_key") or ""),
                "selection": str(row.get("selection") or ""),
                "event_start": str(row.get("start") or ""),
                "score": score,
                "candidate_min_score": float(exp.get("candidate_min_score")),
                "baseline_selected": True,
                "candidate_selected": bool(candidate),
                "american_odds": odds,
                "book_count": int(num(row.get("book_count")) or 0),
                "candidate_captured_at": captured_at if candidate else None,
                "candidate_score": score if candidate else None,
                "candidate_american_odds": odds if candidate else None,
                "candidate_book_count": int(num(row.get("book_count")) or 0) if candidate else None,
                "grade": "PENDING",
                "unit_result": None,
                "candidate_unit_result": None,
                "automatic_live_change": False,
            }
            append_event(event)
            existing_rows[pick_id] = event
            captured += 1

        details.append({
            "experiment_id": exp.get("experiment_id"),
            "current_baseline_qualified": baseline_seen,
            "current_candidate_qualified": candidate_seen,
        })

    return {
        "captured_now": captured,
        "candidate_triggers_now": candidate_triggers,
        "current": details,
    }


def settled_grade_lookup(sport):
    path = GRADE_FILES.get(sport)
    if path is None or not path.exists():
        return {}

    d = pd.read_csv(path, low_memory=False)
    if d.empty or "grade" not in d.columns:
        return {}

    for col in ["game_key", "market", "selection"]:
        if col not in d.columns:
            d[col] = ""
        d[col] = d[col].fillna("").astype(str)

    d["grade"] = d["grade"].astype(str).str.upper()
    d = d[d["grade"].isin(SETTLED)].copy()
    if "snapshot_at" in d.columns:
        d["_snapshot"] = pd.to_datetime(d["snapshot_at"], errors="coerce", utc=True)
        d = d.sort_values("_snapshot")

    lookup = {}
    for _, row in d.iterrows():
        key = (
            str(row.get("game_key") or ""),
            str(row.get("market") or "").upper(),
            str(row.get("selection") or "").upper(),
        )
        lookup[key] = row
    return lookup


def american_profit(odds):
    odds = num(odds)
    if odds is None or odds == 0:
        return None
    return odds / 100 if odds > 0 else 100 / abs(odds)


def settle(policy):
    lookups = {}
    settled_now = 0

    for pick in canonical_ledger():
        if str(pick.get("grade") or "PENDING").upper() in SETTLED:
            continue

        sport = str(pick.get("sport") or "").upper()
        if sport not in lookups:
            lookups[sport] = settled_grade_lookup(sport)

        key = (
            str(pick.get("game_key") or ""),
            str(pick.get("market") or "").upper(),
            str(pick.get("selection") or "").upper(),
        )
        row = lookups[sport].get(key)
        if row is None:
            continue

        grade = str(row.get("grade") or "").upper()
        if grade not in SETTLED:
            continue

        if grade == "WIN":
            unit_result = american_profit(pick.get("american_odds"))
            candidate_unit_result = (
                american_profit(pick.get("candidate_american_odds"))
                if bool(pick.get("candidate_selected"))
                else None
            )
        elif grade == "LOSS":
            unit_result = -1.0
            candidate_unit_result = -1.0 if bool(pick.get("candidate_selected")) else None
        else:
            unit_result = 0.0
            candidate_unit_result = 0.0 if bool(pick.get("candidate_selected")) else None

        append_event({
            "event_type": "SETTLED",
            "pick_id": pick.get("pick_id"),
            "grade": grade,
            "unit_result": None if unit_result is None else round(unit_result, 4),
            "candidate_unit_result": (
                None if candidate_unit_result is None
                else round(candidate_unit_result, 4)
            ),
            "settled_at": now_iso(),
            "grade_source": str(GRADE_FILES.get(sport, "")),
        })
        settled_now += 1

    return settled_now


def cohort_summary(rows, candidate=False):
    if not rows:
        return {
            "published": 0, "settled": 0, "pending": 0,
            "wins": 0, "losses": 0, "pushes": 0,
            "hit_rate_pct": None, "units": None, "roi_pct": None,
        }

    grades = [str(row.get("grade") or "PENDING").upper() for row in rows]
    wins = grades.count("WIN")
    losses = grades.count("LOSS")
    pushes = grades.count("PUSH")
    settled = wins + losses + pushes
    pending = len(rows) - settled
    decisions = wins + losses

    unit_field = "candidate_unit_result" if candidate else "unit_result"
    unit_values = [
        num(row.get(unit_field))
        for row in rows
        if str(row.get("grade") or "").upper() in SETTLED
    ]
    unit_values = [v for v in unit_values if v is not None]
    units = round(sum(unit_values), 3) if settled and len(unit_values) == settled else None
    roi = round(100 * units / settled, 1) if units is not None and settled else None

    return {
        "published": len(rows),
        "settled": settled,
        "pending": pending,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate_pct": None if decisions == 0 else round(100 * wins / decisions, 1),
        "units": units,
        "roi_pct": roi,
    }


def build_summary(policy, capture_result, settled_now):
    canonical = canonical_ledger()
    experiments = []

    for exp in policy.get("experiments") or []:
        rows = [row for row in canonical if row.get("experiment_id") == exp.get("experiment_id")]
        baseline = cohort_summary(rows)
        candidate_rows = [row for row in rows if bool(row.get("candidate_selected"))]
        candidate = cohort_summary(candidate_rows, candidate=True)

        retention = None
        if baseline["published"]:
            retention = round(100 * candidate["published"] / baseline["published"], 1)

        experiments.append({
            **exp,
            "baseline": baseline,
            "candidate": candidate,
            "forward_retention_pct": retention,
            "captured_picks": rows[-20:],
            "promotion_status": (
                "WAITING_FOR_FORWARD_SAMPLE"
                if candidate["settled"] < 10
                else "REVIEW_REQUIRED"
            ),
            "live_threshold_changed": False,
        })

    payload = {
        "generated_at": now_iso(),
        "status": "READY",
        "automatic_live_changes": False,
        "captured_now": capture_result.get("captured_now", 0),
        "candidate_triggers_now": capture_result.get("candidate_triggers_now", 0),
        "settled_now": settled_now,
        "current_capture": capture_result.get("current", []),
        "experiments": experiments,
    }
    write_json(SUMMARY_PATH, payload)
    write_json(PUBLIC_PATH, payload)
    if DIST_PATH.parent.exists():
        write_json(DIST_PATH, payload)
    return payload


def main():
    policy = ensure_policy()
    captured = capture(policy)
    settled_now = settle(policy)
    summary = build_summary(policy, captured, settled_now)

    print(json.dumps({
        "status": summary["status"],
        "experiments": len(summary["experiments"]),
        "captured_now": summary["captured_now"],
        "candidate_triggers_now": summary.get("candidate_triggers_now", 0),
        "settled_now": summary["settled_now"],
        "experiment_summaries": [
            {
                "experiment_id": exp["experiment_id"],
                "baseline": exp["baseline"],
                "candidate": exp["candidate"],
                "retention_pct": exp["forward_retention_pct"],
            }
            for exp in summary["experiments"]
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
