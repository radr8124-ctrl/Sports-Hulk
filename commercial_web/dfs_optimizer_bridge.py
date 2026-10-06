#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from premium_ui.dfs_optimizer import (
    optimize_nfl,
    lineup_frame,
    prepare_pool,
    has_ownership_data,
)

MODE_TO_STRATEGY = {
    "BEST_OVERALL": "Balanced",
    "CASH_SAFE": "Cash Safe",
    "TOURNAMENT_UPSIDE": "GPP",
    "CONTRARIAN": "Contrarian",
}


def load_rows():
    candidates = [
        ROOT / "commercial_web" / "dist" / "ask_context.json",
        ROOT / "commercial_web" / "public" / "ask_context.json",
    ]
    for path in candidates:
        if path.exists():
            payload = json.loads(path.read_text())
            return payload.get("datasets", {}).get("dfs", []), payload.get("generated_at")
    return [], None


def clean_value(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def player_payload(slot, row, reason, locked):
    keys = [
        "player", "player_key", "position", "team", "opponent", "salary",
        "projected_fantasy_points", "audit_value_per_1000",
        "contest_archetype", "context_signal", "availability_status",
        "injury_type", "projected_ownership_pct", "modelled_ownership_pct",
    ]
    out = {key: clean_value(row.get(key)) for key in keys}
    out["slot"] = slot
    out["why"] = reason
    out["locked"] = bool(locked)
    return out


def main():
    request = json.loads(sys.stdin.read() or "{}")
    platform = str(request.get("platform") or "DRAFTKINGS").upper()
    mode = str(request.get("mode") or "BEST_OVERALL").upper()
    strategy = MODE_TO_STRATEGY.get(mode)
    if not strategy:
        raise ValueError("Unsupported DFS build mode.")

    locked = [str(x) for x in request.get("locked_keys") or [] if str(x)]
    excluded = [str(x) for x in request.get("excluded_keys") or [] if str(x)]
    alternatives = max(1, min(10, int(request.get("alternatives") or 3)))

    rows, generated_at = load_rows()
    source = pd.DataFrame(rows)
    if source.empty:
        raise ValueError("The current DFS projection pool is unavailable.")

    slate_id = request.get("slate_id")
    platform_rows = source[
        source["sport"].astype(str).str.upper().eq("NFL")
        & source["platform"].astype(str).str.upper().eq(platform)
    ].copy()
    if slate_id is None and "slate_id" in platform_rows.columns and not platform_rows.empty:
        counts = platform_rows["slate_id"].astype(str).value_counts()
        if not counts.empty:
            slate_id = counts.index[0]

    prepared = prepare_pool(source, platform, slate_id=slate_id)
    ownership_available = has_ownership_data(prepared)

    if strategy == "Contrarian" and not ownership_available:
        response = {
            "status": "MODE_UNAVAILABLE",
            "reason": "Contrarian mode requires current ownership data; HULK will not fake contrarian leverage without it.",
            "platform": platform,
            "slate_id": str(slate_id) if slate_id is not None else None,
            "mode": mode,
            "strategy": strategy,
            "ownership_available": False,
            "pool_size": int(len(prepared)),
            "generated_at": generated_at,
            "lineups": [],
        }
        print(json.dumps(response, separators=(",", ":")))
        return

    reference_lineups = []
    max_overlap = None
    if strategy in {"GPP", "Contrarian"}:
        for reference_strategy in ["Balanced", "Cash Safe"]:
            reference = optimize_nfl(
                source,
                platform,
                locked_keys=locked,
                excluded_keys=excluded,
                strategy=reference_strategy,
                alternatives=1,
                slate_id=slate_id,
            )
            if reference:
                reference_lineups.append([
                    str(player.get("player_key"))
                    for _, player in reference[0]["players"]
                    if str(player.get("player_key") or "")
                ])
        max_overlap = 7 if strategy == "GPP" else 6

    results = optimize_nfl(
        source,
        platform,
        locked_keys=locked,
        excluded_keys=excluded,
        strategy=strategy,
        alternatives=alternatives,
        slate_id=slate_id,
        reference_lineups=reference_lineups,
        max_overlap=max_overlap,
    )

    lineups = []
    for result in results:
        frame = lineup_frame(result, strategy, locked_keys=locked)
        reasons = {
            str(row["Player"]): str(row["Why"])
            for _, row in frame.iterrows()
        }
        players = []
        for slot, player in result["players"]:
            players.append(
                player_payload(
                    slot,
                    player,
                    reasons.get(str(player.get("player")), "Projection/value fit"),
                    str(player.get("player_key")) in set(locked),
                )
            )
        lineups.append({
            "players": players,
            "salary_used": result["salary_used"],
            "salary_cap": result["salary_cap"],
            "salary_remaining": result["salary_remaining"],
            "projected_points": result["projected_points"],
            "optimizer_score": result["optimizer_score"],
            "stack_pattern": result["stack_pattern"],
            "games_used": result["games_used"],
            "ownership_player_count": result.get("ownership_player_count", 0),
            "projected_ownership_sum": result.get("projected_ownership_sum"),
            "strategy_constraints": result.get("strategy_constraints", {}),
        })

    if lineups:
        status = "READY"
        unavailable_reason = None
    elif strategy in {"GPP", "Contrarian"}:
        status = "MODE_UNAVAILABLE"
        unavailable_reason = (
            "No lineup satisfied the strategy's required differentiation from Balanced/Cash under the current slate constraints."
        )
    else:
        status = "NO_LEGAL_LINEUP"
        unavailable_reason = None

    response = {
        "status": status,
        "reason": unavailable_reason,
        "platform": platform,
        "slate_id": str(slate_id) if slate_id is not None else None,
        "mode": mode,
        "strategy": strategy,
        "ownership_available": ownership_available,
        "pool_size": int(len(prepared)),
        "generated_at": generated_at,
        "lineups": lineups,
    }
    print(json.dumps(response, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}))
        sys.exit(1)
