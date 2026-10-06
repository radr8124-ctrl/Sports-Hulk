#!/usr/bin/env python3
from collections import Counter
import pandas as pd

CONFIG = {
    "FANDUEL": {
        "cap": 60000,
        "slots": ["QB","RB","RB","WR","WR","WR","TE","FLEX","D"],
        "min_games": 1,
        "pool_limits": {"QB":20,"RB":40,"WR":55,"TE":30,"FLEX":80,"D":20},
    },
    "DRAFTKINGS": {
        "cap": 50000,
        "slots": ["QB","RB","RB","WR","WR","WR","TE","FLEX","DST"],
        "min_games": 2,
        "pool_limits": {"QB":26,"RB":46,"WR":60,"TE":32,"FLEX":78,"DST":24},
    },
}

BEAM = 1400


def ownership_columns(frame):
    return [
        col for col in [
            "projected_ownership_pct",
            "modelled_ownership_pct",
        ]
        if col in frame.columns
    ]


def has_ownership_data(frame):
    for col in ownership_columns(frame):
        if pd.to_numeric(frame[col], errors="coerce").notna().any():
            return True
    return False


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
        return None if pd.isna(x) else x
    except Exception:
        return None


def normalize_pos(v):
    p = clean(v).upper().replace("D/ST", "DST")
    if p == "DEF":
        p = "DST"
    return p


def eligible(slot, pos, platform):
    p = normalize_pos(pos)
    if slot == "FLEX":
        return p in {"RB","WR","TE"}
    if slot in {"D","DST"}:
        return p in {"D","DST"}
    return p == slot


def opponent_of(row):
    direct = clean(row.get("opponent")).upper()
    if direct:
        return direct

    team = clean(row.get("team")).upper()
    home = clean(row.get("home_team")).upper()
    away = clean(row.get("away_team")).upper()

    if team and team == home:
        return away
    if team and team == away:
        return home
    return ""


def game_key(row):
    team = clean(row.get("team")).upper()
    opp = opponent_of(row)
    if not team or not opp:
        return ""
    return "|".join(sorted([team, opp]))


def context_bonus(row):
    ctx = clean(row.get("context_signal"))
    arch = clean(row.get("contest_archetype"))
    bonus = 0.0
    if ctx == "CONFIRMED_STARTER_VALUE":
        bonus += 1.8
    elif ctx == "VALUE_PLUS_ROLE_UP":
        bonus += 1.4
    elif ctx == "CONFIRMED_STARTER_CONTEXT":
        bonus += 0.8
    elif ctx == "ROLE_DOWN_CONTEXT":
        bonus -= 1.4
    if arch == "CASH_CORE":
        bonus += 0.8
    elif arch == "GPP_CEILING":
        bonus += 1.2
    elif arch == "VALUE_PUNT":
        bonus += 0.7
    elif arch == "STARTER_VALUE":
        bonus += 0.6
    elif arch == "AVOID_AVAILABILITY_RISK":
        bonus -= 10
    return bonus


def objective(row, strategy):
    proj = num(row.get("projected_fantasy_points")) or 0.0
    value_pct = num(row.get("value_percentile")) or 50.0
    proj_pct = num(row.get("projection_percentile")) or 50.0
    own = num(row.get("projected_ownership_pct"))
    if own is None:
        own = num(row.get("modelled_ownership_pct"))

    arch = clean(row.get("contest_archetype"))
    availability = clean(row.get("availability_status")).upper()
    role = clean(row.get("role_signal")).upper()
    base = proj + context_bonus(row)

    if strategy == "Max Projection":
        return proj + 0.15 * context_bonus(row)

    if strategy == "Value":
        return base + 0.045 * value_pct

    if strategy == "Cash Safe":
        score = base + 0.018 * value_pct + 0.012 * proj_pct
        if arch == "CASH_CORE":
            score += 1.8
        if arch in {"STARTER_VALUE", "VALUE_PUNT"}:
            score += 0.5
        if availability in {"QUESTIONABLE", "DOUBTFUL", "OUT", "INACTIVE"}:
            score -= 4.0 if availability == "QUESTIONABLE" else 8.0
        if role in {"ROLE_DOWN", "ROLE_DOWN_CONTEXT"}:
            score -= 2.0
        return score

    if strategy == "GPP":
        score = base + 0.02 * value_pct + 0.01 * proj_pct
        if own is not None:
            score += max(0.0, 22.0 - own) * 0.055
        if arch == "GPP_CEILING":
            score += 1.4
        return score

    if strategy == "Contrarian":
        score = base + 0.015 * value_pct + 0.012 * proj_pct
        if arch == "GPP_CEILING":
            score += 1.8
        if own is not None:
            score += max(0.0, 25.0 - own) * 0.08
        return score

    return base + 0.018 * value_pct + 0.008 * proj_pct


def ownership_value(row):
    own = num(row.get("projected_ownership_pct"))
    if own is None:
        own = num(row.get("modelled_ownership_pct"))
    return own


def player_reason(row, strategy, locked=False):
    if locked:
        return "Locked by you"
    bits = []
    arch = clean(row.get("contest_archetype"))
    ctx = clean(row.get("context_signal"))
    if arch:
        bits.append(arch.replace("_", " ").title())
    if ctx and ctx not in {"NEUTRAL", "NONE"}:
        bits.append(ctx.replace("_", " ").title())
    value = num(row.get("audit_value_per_1000"))
    if value is not None:
        bits.append(f"{value:.2f} pts/$1K")
    if strategy in {"GPP", "Contrarian"}:
        own = num(row.get("projected_ownership_pct"))
        if own is None:
            own = num(row.get("modelled_ownership_pct"))
        if own is not None:
            bits.append(f"{own:.1f}% projected own")
    return " · ".join(bits[:3]) or "Projection/value fit"


def prepare_pool(source, platform, slate_id=None):
    d = source.copy()
    d = d[
        d["sport"].astype(str).str.upper().eq("NFL")
        & d["platform"].astype(str).str.upper().eq(platform)
    ].copy()

    if slate_id is not None and "slate_id" in d.columns:
        d = d[
            d["slate_id"].astype(str).eq(str(slate_id))
        ].copy()

    d["salary"] = pd.to_numeric(d["salary"], errors="coerce")
    d["projected_fantasy_points"] = pd.to_numeric(
        d["projected_fantasy_points"], errors="coerce"
    )
    d = d[
        d["salary"].notna()
        & d["projected_fantasy_points"].notna()
    ].copy()

    if "availability_status" in d.columns:
        hard_unavailable = {
            "OUT", "INACTIVE", "INJURED_RESERVE", "INJURED RESERVE",
            "IR", "SUSPENDED", "PUP", "NFI",
        }
        d = d[
            ~d["availability_status"].astype(str).str.upper().isin(hard_unavailable)
        ].copy()

    # AVOID_AVAILABILITY_RISK is a strong scoring penalty, not a blanket removal.
    # Keeping questionable/risky players available lets the optimizer still
    # produce a legal roster when the provider marks a large share of the slate.
    d["_pos"] = d["position"].map(normalize_pos)
    d["_key"] = d["player_key"].astype(str)
    d["opponent"] = d.apply(opponent_of, axis=1)
    return d


def _locked_assignments(locked_rows, slots, platform, cap):
    locked = locked_rows.to_dict("records")
    results = []

    def rec(i, used_slots, assigned, salary):
        if salary > cap:
            return
        if i >= len(locked):
            results.append((dict(assigned), salary))
            return

        row = locked[i]
        choices = []
        seen_labels = set()
        for idx, slot in enumerate(slots):
            if idx in used_slots:
                continue
            if not eligible(slot, row.get("position"), platform):
                continue
            # Identical repeated slots are symmetric; try only the first open one.
            if slot in seen_labels:
                continue
            seen_labels.add(slot)
            choices.append(idx)

        for idx in choices:
            rec(
                i + 1,
                used_slots | {idx},
                {**assigned, idx: row},
                salary + (num(row.get("salary")) or 0),
            )

    rec(0, set(), {}, 0.0)
    return results


def _stack_bonus(players):
    qbs = [p for slot, p in players if slot == "QB"]
    if not qbs:
        return 0.0, "NO_QB_STACK"

    qb = qbs[0]
    team = clean(qb.get("team")).upper()
    opp = opponent_of(qb)

    catchers = [
        p for slot, p in players
        if clean(p.get("team")).upper() == team
        and normalize_pos(p.get("position")) in {"WR","TE"}
    ]
    bringbacks = [
        p for slot, p in players
        if clean(p.get("team")).upper() == opp
        and normalize_pos(p.get("position")) in {"RB","WR","TE"}
    ]

    bonus = 0.0
    label = "NAKED_QB"
    if len(catchers) >= 2:
        bonus += 4.0
        label = "QB_DOUBLE_STACK"
    elif len(catchers) == 1:
        bonus += 2.4
        label = "QB_STACK"

    if bringbacks:
        bonus += 1.4
        label += "_BRINGBACK"

    return bonus, label


def optimize_nfl(
    source,
    platform,
    locked_keys=None,
    excluded_keys=None,
    strategy="Balanced",
    alternatives=5,
    slate_id=None,
    reference_lineups=None,
    max_overlap=None,
):
    platform = clean(platform).upper()
    if platform not in CONFIG:
        raise ValueError(f"Unsupported platform: {platform}")

    cfg = CONFIG[platform]
    slots = cfg["slots"]
    cap = cfg["cap"]
    locked_keys = {str(x) for x in (locked_keys or []) if str(x)}
    excluded_keys = {str(x) for x in (excluded_keys or []) if str(x)}

    if locked_keys & excluded_keys:
        raise ValueError("A player cannot be both locked and excluded.")

    pool = prepare_pool(source, platform, slate_id=slate_id)
    if pool.empty:
        return []

    ownership_ready = has_ownership_data(pool)
    if strategy == "Contrarian" and not ownership_ready:
        return []

    missing = locked_keys - set(pool["_key"])
    if missing:
        raise ValueError(
            "Locked player(s) are not in the current projected pool: "
            + ", ".join(sorted(missing))
        )

    pool = pool[~pool["_key"].isin(excluded_keys)].copy()
    if pool.empty:
        return []
    pool["_objective"] = [
        objective(row, strategy)
        for _, row in pool.iterrows()
    ]

    locked_rows = pool[pool["_key"].isin(locked_keys)].copy()
    assignments = _locked_assignments(
        locked_rows,
        slots,
        platform,
        cap,
    )
    if locked_keys and not assignments:
        raise ValueError(
            "Those locked players cannot fit together under the roster rules."
        )
    if not assignments:
        assignments = [({}, 0.0)]

    pools = {}
    for slot in set(slots):
        x = pool[
            pool.apply(
                lambda r: eligible(slot, r.get("position"), platform),
                axis=1,
            )
        ].copy()
        x = x.sort_values(
            ["_objective", "projected_fantasy_points"],
            ascending=False,
        )
        limit = cfg["pool_limits"][slot]
        pools[slot] = x.head(limit).to_dict("records")

    min_salary = {
        slot: min((num(r.get("salary")) or 0) for r in pools[slot])
        for slot in set(slots)
        if pools[slot]
    }

    states = []
    for assignment, salary in assignments:
        used = {
            clean(row.get("player_key"))
            for row in assignment.values()
        }
        proj = sum(
            num(row.get("projected_fantasy_points")) or 0
            for row in assignment.values()
        )
        obj = sum(
            num(row.get("_objective")) or 0
            for row in assignment.values()
        )
        states.append(
            {
                "assigned": dict(assignment),
                "used": used,
                "salary": salary,
                "proj": proj,
                "objective": obj,
            }
        )

    open_indices = [
        idx for idx in range(len(slots))
        if not all(idx in state["assigned"] for state in states)
    ]

    for open_pos, idx in enumerate(open_indices):
        slot = slots[idx]

        next_states = []
        future_indices = open_indices[open_pos + 1:]

        for state in states:
            future_floor = sum(
                min_salary.get(slots[j], 0)
                for j in future_indices
                if j not in state["assigned"]
            )
            if idx in state["assigned"]:
                next_states.append(state)
                continue

            for row in pools[slot]:
                key = clean(row.get("player_key"))
                if not key or key in state["used"]:
                    continue

                salary = num(row.get("salary")) or 0
                new_salary = state["salary"] + salary
                if new_salary > cap or new_salary + future_floor > cap:
                    continue

                next_states.append(
                    {
                        "assigned": {**state["assigned"], idx: row},
                        "used": state["used"] | {key},
                        "salary": new_salary,
                        "proj": state["proj"] + (
                            num(row.get("projected_fantasy_points")) or 0
                        ),
                        "objective": state["objective"] + (
                            num(row.get("_objective")) or 0
                        ),
                    }
                )

        # Remove symmetric RB/WR permutations before the beam cutoff.
        # A state with the same player set and same filled slot indexes has
        # the same future choices, so keep only its strongest representation.
        deduped = {}
        for candidate in next_states:
            signature = (
                tuple(sorted(candidate["used"])),
                tuple(sorted(candidate["assigned"].keys())),
            )
            prior = deduped.get(signature)
            if (
                prior is None
                or (candidate["objective"], candidate["proj"])
                > (prior["objective"], prior["proj"])
            ):
                deduped[signature] = candidate

        next_states = list(deduped.values())
        next_states.sort(
            key=lambda s: (s["objective"], s["proj"]),
            reverse=True,
        )
        states = next_states[:BEAM]
        if not states:
            break

    results = []
    seen = set()

    for state in states:
        if len(state["assigned"]) != len(slots):
            continue

        players = [(slots[i], state["assigned"][i]) for i in range(len(slots))]
        keys = tuple(sorted(clean(p.get("player_key")) for _, p in players))
        if keys in seen:
            continue

        games = {game_key(p) for _, p in players if game_key(p)}
        if len(games) < cfg["min_games"]:
            continue

        defense = next(
            (p for slot, p in players if slot in {"D","DST"}),
            None,
        )
        defense_conflicts = 0
        if defense:
            defense_opp = opponent_of(defense)
            defense_conflicts = sum(
                1
                for slot, p in players
                if slot not in {"D","DST"}
                and clean(p.get("team")).upper() == defense_opp
            )

        stack_bonus, stack_label = _stack_bonus(players)

        # Tournament modes must actually behave like tournament modes.
        # A naked QB can be valid in cash/balanced builds, but GPP/Contrarian
        # research requires at least one QB pass-catcher stack.
        if strategy in {"GPP", "Contrarian"} and stack_label == "NAKED_QB":
            continue

        ownership_values = [
            ownership_value(p)
            for slot, p in players
            if slot not in {"D", "DST"}
        ]
        ownership_known = [v for v in ownership_values if v is not None]
        if strategy == "Contrarian" and len(ownership_known) < 6:
            continue
        lineup_ownership_sum = (
            round(sum(ownership_known), 3)
            if ownership_known
            else None
        )

        final_score = state["objective"]
        if strategy in {"Balanced", "GPP", "Contrarian"}:
            final_score += stack_bonus

        # Offense against your own D/ST is legal, but usually undesirable.
        # Penalize it instead of making it an impossible hard constraint.
        final_score -= defense_conflicts * 3.0

        seen.add(keys)
        results.append(
            {
                "players": players,
                "salary_used": int(state["salary"]),
                "salary_cap": cap,
                "salary_remaining": int(cap - state["salary"]),
                "projected_points": round(state["proj"], 3),
                "optimizer_score": round(final_score, 3),
                "stack_pattern": stack_label,
                "games_used": len(games),
                "ownership_available": ownership_ready,
                "ownership_player_count": len(ownership_known),
                "projected_ownership_sum": lineup_ownership_sum,
                "strategy_constraints": {
                    "qb_stack_required": strategy in {"GPP", "Contrarian"},
                    "ownership_required": strategy == "Contrarian",
                    "minimum_known_ownership_players": 6 if strategy == "Contrarian" else 0,
                },
            }
        )

    results.sort(
        key=lambda r: (r["optimizer_score"], r["projected_points"]),
        reverse=True,
    )

    if reference_lineups and max_overlap is not None:
        references = [
            {str(key) for key in ref if str(key)}
            for ref in reference_lineups
            if ref
        ]
        if references:
            filtered = []
            for result in results:
                keys = {
                    clean(player.get("player_key"))
                    for _, player in result["players"]
                    if clean(player.get("player_key"))
                }
                if all(
                    len(keys & ref) <= int(max_overlap)
                    for ref in references
                ):
                    filtered.append(result)
            results = filtered

    return results[:max(1, alternatives)]


def lineup_frame(result, strategy, locked_keys=None):
    locked_keys = {str(x) for x in (locked_keys or [])}
    rows = []
    for slot, player in result["players"]:
        key = clean(player.get("player_key"))
        rows.append(
            {
                "Slot": slot,
                "Player": clean(player.get("player")),
                "Team": clean(player.get("team")),
                "Opp": opponent_of(player),
                "Salary": int(num(player.get("salary")) or 0),
                "Projection": round(
                    num(player.get("projected_fantasy_points")) or 0,
                    2,
                ),
                "Value/$1K": round(
                    num(player.get("audit_value_per_1000")) or 0,
                    2,
                ),
                "Why": player_reason(
                    player,
                    strategy,
                    locked=key in locked_keys,
                ),
                "Locked": key in locked_keys,
            }
        )
    return pd.DataFrame(rows)
