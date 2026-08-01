from evals.scoring import calculate_fitness, get_top_variants


def _run(hermes="hermes_v1", laguna="laguna_v1", status="success", cost=0.1, quality=0.9):
    return {
        "config": {"hermes_variant": hermes, "laguna_variant": laguna},
        "task": {"expected_cost": 0.15},
        "result": {"status": status, "cost": cost, "time_seconds": 20},
        "quality_metrics": {
            "quality_score": quality,
            "code_quality_score": quality,
            "task_spec_clarity": quality,
        },
    }


def test_calculate_fitness_composite():
    runs = [_run() for _ in range(5)]
    score = calculate_fitness(runs, "hermes_v1", "laguna_v1")
    assert score["sample_size"] == 5
    assert score["success_rate"] == 1.0
    assert 0 < score["composite"] <= 1.5


def test_get_top_variants():
    runs = [_run() for _ in range(5)] + [
        _run(hermes="hermes_v2", status="failure", quality=0.1) for _ in range(5)
    ]
    top = get_top_variants(runs, top_n=2)
    assert top
    assert top[0][0][0] in {"hermes_v1", "hermes_v2"}
