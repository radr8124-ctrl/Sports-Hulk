from prop_intelligence.experiment_registry import (
    experiment_id,
    record_result,
    register_experiment,
    summarize,
)


def spec():
    return {
        "sport": "NHL",
        "lane": "PRIZEPICKS",
        "market": "shots_on_goal",
        "features": ["market_logit", "toi", "role"],
        "calibration": "platt",
        "thresholds": {"min_edge": 0.02},
        "training_window": "2025-10-01/2026-03-01",
        "validation_window": "2026-03-02/2026-04-15",
        "cluster_key": "game_id",
    }


def test_experiment_id_is_stable_for_same_spec():
    assert experiment_id(spec()) == experiment_id(spec())


def test_changed_threshold_gets_new_experiment_id():
    a = spec()
    b = spec()
    b["thresholds"] = {"min_edge": 0.03}
    assert experiment_id(a) != experiment_id(b)


def test_failed_experiment_remains_in_summary(tmp_path):
    ledger = tmp_path / "experiments.jsonl"
    exp_id = register_experiment(ledger, spec())
    record_result(
        ledger,
        exp_id,
        status="COMPLETE",
        metrics={"brier_delta": 0.012},
        decision="REJECTED",
        reason="WORSE_THAN_MARKET",
    )
    summary = summarize(ledger)
    assert summary["registered_experiments"] == 1
    assert summary["experiments_with_results"] == 1
    assert summary["decision_counts"]["REJECTED"] == 1
