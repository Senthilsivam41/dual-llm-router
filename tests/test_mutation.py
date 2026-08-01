import random

from evals.mutation import HERMES_MUTATION_OPERATORS, apply_prompt_mutation


def test_apply_prompt_mutation_appends_guidance():
    rng = random.Random(0)
    # Force a mutation by retrying until the prompt changes.
    base = "You are Hermes 4.\n"
    prompt, option = base, "medium"
    for seed in range(20):
        prompt, option = apply_prompt_mutation(
            base,
            "prompt_verbosity",
            HERMES_MUTATION_OPERATORS,
            "medium",
            random.Random(seed),
        )
        if prompt != base:
            break
    assert "[mutation:prompt_verbosity]" in prompt
    assert option in HERMES_MUTATION_OPERATORS["prompt_verbosity"]["options"]


def test_apply_prompt_mutation_unknown_operator():
    try:
        apply_prompt_mutation("x", "not_an_operator", HERMES_MUTATION_OPERATORS, "medium")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Unknown operator" in str(exc)
