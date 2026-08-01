from evals.ab_test import ABTestManager
from evals.alerts import detect_significant_improvement, emit_alerts


def test_ab_test_reaches_significance(tmp_path):
    mgr = ABTestManager(min_samples=5, confidence=0.95)
    mgr.start_test(
        "t1",
        [{"variant_id": "hermes_v1"}, {"variant_id": "hermes_v2"}],
    )
    for _ in range(5):
        mgr.record_result("t1", "hermes_v1", {"status": "success"})
        mgr.record_result("t1", "hermes_v2", {"status": "failure"})

    result = mgr.check_significance("t1")
    assert result is not None
    assert result["winner"] == "hermes_v1"
    assert mgr.ab_tests[0]["status"] == "completed"


def test_detect_and_emit_alerts(tmp_path):
    alerts = detect_significant_improvement(
        {
            "current_hermes": {"composite": 0.40},
            "current_laguna": {"composite": 0.50},
        },
        {
            "hermes": {"variant_id": "hermes_v2", "score": 0.55},
            "laguna": {"variant_id": "laguna_v1", "score": 0.51},
        },
        min_delta=0.05,
    )
    assert len(alerts) == 1
    assert alerts[0]["agent"] == "hermes"
    assert alerts[0]["delta"] == 0.15

    log_path = tmp_path / "alerts.jsonl"
    emit_alerts(alerts, log_path=log_path)
    assert log_path.exists()
    assert "significant_improvement" in log_path.read_text(encoding="utf-8")
