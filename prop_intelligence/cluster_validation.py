"""Cluster-aware validation helpers for Sports HULK.

Sports props from the same game/slate are correlated. These helpers evaluate
probability improvements by independent clusters instead of pretending every
prop is a separate independent experiment.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable
import math
import random


def _number(value: Any) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(value) else value


def brier_loss(outcome: Any, probability: Any) -> float | None:
    y = _number(outcome)
    p = _number(probability)
    if y is None or p is None or y not in (0.0, 1.0):
        return None
    p = min(1.0, max(0.0, p))
    return (p - y) ** 2


def log_loss(outcome: Any, probability: Any) -> float | None:
    y = _number(outcome)
    p = _number(probability)
    if y is None or p is None or y not in (0.0, 1.0):
        return None
    p = min(1.0 - 1e-12, max(1e-12, p))
    return -(y * math.log(p) + (1.0 - y) * math.log(1.0 - p))


def cluster_metric_delta(
    rows: Iterable[dict[str, Any]],
    *,
    cluster_key: str,
    outcome_key: str,
    model_probability_key: str,
    baseline_probability_key: str,
    metric: str = "brier",
) -> dict[str, Any]:
    """Compare V2 to baseline after averaging loss within each event cluster.

    Negative delta means the model beats the baseline because lower probability
    loss is better.
    """
    loss_fn = brier_loss if metric == "brier" else log_loss
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)

    for row in rows:
        cluster = str(row.get(cluster_key) or "").strip()
        if not cluster:
            continue
        model_loss = loss_fn(row.get(outcome_key), row.get(model_probability_key))
        base_loss = loss_fn(row.get(outcome_key), row.get(baseline_probability_key))
        if model_loss is None or base_loss is None:
            continue
        grouped[cluster].append((model_loss, base_loss))

    deltas = []
    for cluster, losses in grouped.items():
        model_mean = sum(item[0] for item in losses) / len(losses)
        base_mean = sum(item[1] for item in losses) / len(losses)
        deltas.append({
            "cluster": cluster,
            "observations": len(losses),
            "model_loss": model_mean,
            "baseline_loss": base_mean,
            "delta": model_mean - base_mean,
        })

    if not deltas:
        return {
            "metric": metric,
            "clusters": 0,
            "observations": 0,
            "mean_cluster_delta": None,
            "model_better_cluster_pct": None,
            "cluster_details": [],
        }

    return {
        "metric": metric,
        "clusters": len(deltas),
        "observations": sum(item["observations"] for item in deltas),
        "mean_cluster_delta": sum(item["delta"] for item in deltas) / len(deltas),
        "model_better_cluster_pct": (
            100.0 * sum(item["delta"] < 0 for item in deltas) / len(deltas)
        ),
        "cluster_details": deltas,
    }


def cluster_bootstrap_delta(
    rows: Iterable[dict[str, Any]],
    *,
    cluster_key: str,
    outcome_key: str,
    model_probability_key: str,
    baseline_probability_key: str,
    metric: str = "brier",
    iterations: int = 5000,
    seed: int = 20261005,
) -> dict[str, Any]:
    """Bootstrap whole clusters and return a confidence interval for loss delta."""
    base = cluster_metric_delta(
        rows,
        cluster_key=cluster_key,
        outcome_key=outcome_key,
        model_probability_key=model_probability_key,
        baseline_probability_key=baseline_probability_key,
        metric=metric,
    )
    details = base["cluster_details"]
    if len(details) < 2:
        return {
            **base,
            "iterations": 0,
            "ci_95_low": None,
            "ci_95_high": None,
            "probability_model_beats_baseline": None,
            "proof_status": "INSUFFICIENT_CLUSTERS",
        }

    rng = random.Random(seed)
    deltas = [item["delta"] for item in details]
    n = len(deltas)
    boot = []
    for _ in range(iterations):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        boot.append(sum(sample) / n)
    boot.sort()

    low_index = max(0, int(iterations * 0.025) - 1)
    high_index = min(iterations - 1, int(iterations * 0.975))
    low = boot[low_index]
    high = boot[high_index]
    p_better = sum(value < 0 for value in boot) / iterations

    if n < 30:
        status = "BUILDING_CLUSTER_SAMPLE"
    elif high < 0 and p_better >= 0.975:
        status = "CLUSTER_VALIDATED_CANDIDATE"
    elif low > 0:
        status = "MODEL_WORSE_THAN_BASELINE"
    else:
        status = "NOT_YET_DISTINGUISHABLE"

    return {
        **base,
        "iterations": iterations,
        "ci_95_low": low,
        "ci_95_high": high,
        "probability_model_beats_baseline": p_better,
        "proof_status": status,
    }


def promotion_gate(
    *,
    independent_clusters: int,
    forward_settled: int,
    brier_ci_high: float | None,
    logloss_ci_high: float | None,
    positive_clv_rate_pct: float | None,
    roi_ci_low_pct: float | None,
) -> str:
    """Conservative PASS -> monitor -> shadow-play -> limited-live ladder."""
    if independent_clusters < 30 or forward_settled < 50:
        return "PASS_BUILDING_SAMPLE"

    probability_proven = (
        brier_ci_high is not None
        and logloss_ci_high is not None
        and brier_ci_high < 0
        and logloss_ci_high < 0
    )
    if not probability_proven:
        return "SHADOW_MONITOR"

    if independent_clusters < 100 or forward_settled < 150:
        return "SHADOW_MONITOR"

    if positive_clv_rate_pct is None or positive_clv_rate_pct < 52.5:
        return "SHADOW_MONITOR"

    if independent_clusters < 200 or forward_settled < 300:
        return "SHADOW_PLAY"

    if roi_ci_low_pct is None or roi_ci_low_pct <= 0:
        return "SHADOW_PLAY"

    return "LIMITED_LIVE_REVIEW_REQUIRED"
