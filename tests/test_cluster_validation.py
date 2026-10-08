from prop_intelligence.cluster_validation import (
    cluster_bootstrap_delta,
    cluster_metric_delta,
    promotion_gate,
)


def sample_rows():
    return [
        {"game": "A", "y": 1, "model": 0.70, "market": 0.55},
        {"game": "A", "y": 1, "model": 0.72, "market": 0.56},
        {"game": "A", "y": 0, "model": 0.40, "market": 0.48},
        {"game": "B", "y": 0, "model": 0.30, "market": 0.45},
        {"game": "B", "y": 1, "model": 0.65, "market": 0.52},
        {"game": "C", "y": 1, "model": 0.68, "market": 0.54},
    ]


def test_cluster_metric_counts_games_not_props_as_independent_clusters():
    result = cluster_metric_delta(
        sample_rows(),
        cluster_key="game",
        outcome_key="y",
        model_probability_key="model",
        baseline_probability_key="market",
        metric="brier",
    )
    assert result["clusters"] == 3
    assert result["observations"] == 6
    assert result["mean_cluster_delta"] < 0


def test_cluster_bootstrap_requires_more_than_one_cluster():
    result = cluster_bootstrap_delta(
        [{"game": "A", "y": 1, "model": 0.7, "market": 0.55}],
        cluster_key="game",
        outcome_key="y",
        model_probability_key="model",
        baseline_probability_key="market",
        metric="brier",
        iterations=100,
    )
    assert result["proof_status"] == "INSUFFICIENT_CLUSTERS"


def test_promotion_ladder_never_jumps_small_sample_to_live():
    assert promotion_gate(
        independent_clusters=20,
        forward_settled=100,
        brier_ci_high=-0.01,
        logloss_ci_high=-0.01,
        positive_clv_rate_pct=60,
        roi_ci_low_pct=5,
    ) == "PASS_BUILDING_SAMPLE"

    assert promotion_gate(
        independent_clusters=120,
        forward_settled=180,
        brier_ci_high=-0.01,
        logloss_ci_high=-0.01,
        positive_clv_rate_pct=55,
        roi_ci_low_pct=3,
    ) == "SHADOW_PLAY"

    assert promotion_gate(
        independent_clusters=220,
        forward_settled=320,
        brier_ci_high=-0.01,
        logloss_ci_high=-0.01,
        positive_clv_rate_pct=55,
        roi_ci_low_pct=-0.1,
    ) == "SHADOW_PLAY"

    assert promotion_gate(
        independent_clusters=220,
        forward_settled=320,
        brier_ci_high=-0.01,
        logloss_ci_high=-0.01,
        positive_clv_rate_pct=55,
        roi_ci_low_pct=0.5,
    ) == "LIMITED_LIVE_REVIEW_REQUIRED"
