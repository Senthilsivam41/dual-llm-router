"""
Mutation operators for evolving agent prompts.
Each operator modifies a specific aspect of the prompt.
"""

from __future__ import annotations

import random
from typing import Dict, Optional, Tuple

# Mutation operators for Hermes prompt
HERMES_MUTATION_OPERATORS = {
    "prompt_verbosity": {
        "description": "Adjust how verbose/detailed the output is",
        "options": {
            "concise": "Be concise. Use bullet points and short explanations.",
            "medium": "Provide balanced explanations. Include key context.",
            "detailed": "Provide thorough explanations. Include edge cases and alternatives.",
            "explanatory": "Explain the 'why' behind every decision.",
        },
    },
    "few_shot_count": {
        "description": "Number of code examples included in the prompt",
        "options": {
            "minimal": "Include 2-3 focused examples.",
            "standard": "Include 5-7 diverse examples.",
            "extensive": "Include 10-15 examples covering edge cases.",
            "heavy": "Include 20+ examples for maximum coverage.",
        },
    },
    "instruction_style": {
        "description": "How instructions are formatted",
        "options": {
            "step_by_step": "Break tasks into numbered steps.",
            "imperative": "Use direct imperative language.",
            "question_based": "Frame as questions to answer.",
            "flow_based": "Follow a natural workflow pattern.",
        },
    },
    "persona_adjectives": {
        "description": "Adjectives describing the agent persona",
        "options": {
            "senior_engineer": "Senior Python Engineer with 15+ years experience.",
            "pragmatic_dev": "Pragmatic developer who ships fast.",
            "architect": "Software architect focused on clean design.",
            "mentor": "Patient mentor who explains thoroughly.",
        },
    },
    "code_example_complexity": {
        "description": "Complexity level of code examples",
        "options": {
            "simple": "Simple, straightforward implementations.",
            "medium": "Realistic with some complexity.",
            "advanced": "Production-quality with error handling.",
            "expert": "Optimized, tested, with edge case coverage.",
        },
    },
}


# Mutation operators for Laguna prompt
LAGUNA_MUTATION_OPERATORS = {
    "instruction_style": {
        "description": "How Laguna processes task specs",
        "options": {
            "sequential": "Process steps in order, one at a time.",
            "parallel_safe": "Identify parallelizable steps and execute them.",
            "iterative": "Iterate until acceptance criteria are met.",
            "greedy": "Execute all steps as fast as possible.",
        },
    },
    "code_example_count": {
        "description": "Number of code examples in Laguna's prompt",
        "options": {
            "minimal": "2-3 focused examples.",
            "standard": "5-7 diverse examples.",
            "extensive": "10-15 examples.",
            "heavy": "20+ examples.",
        },
    },
    "retry_strategy": {
        "description": "How Laguna handles failures",
        "options": {
            "fail_fast": "Stop on first error.",
            "adaptive": "Retry with modified approach on failure.",
            "exhaustive": "Try multiple approaches before giving up.",
            "escalate": "Return failure with detailed error analysis.",
        },
    },
    "output_format": {
        "description": "Format of Laguna's output",
        "options": {
            "code_only": "Only output code changes.",
            "code_with_comments": "Code with inline comments.",
            "code_with_docs": "Code with full documentation.",
            "structured": "Structured output with separate sections.",
        },
    },
    "verbosity": {
        "description": "How much Laguna explains its actions",
        "options": {
            "silent": "Only output code.",
            "brief": "Brief status updates.",
            "detailed": "Detailed step-by-step progress.",
            "explanatory": "Explain every decision.",
        },
    },
}


def _resolve_options(operator_name: str, operator_options: Dict) -> Dict[str, str]:
    """Accept either a flat options map or the nested operator registry."""
    if operator_name in operator_options and isinstance(operator_options[operator_name], dict):
        nested = operator_options[operator_name]
        if "options" in nested and isinstance(nested["options"], dict):
            return nested["options"]
    if all(isinstance(v, str) for v in operator_options.values()):
        return operator_options  # type: ignore[return-value]
    raise ValueError(f"Unknown operator: {operator_name}")


def apply_prompt_mutation(
    prompt_text: str,
    operator_name: str,
    operator_options: Dict,
    current_option: str,
    rng: Optional[random.Random] = None,
) -> Tuple[str, str]:
    """
    Apply a single mutation to a prompt.

    Returns:
        Tuple of (new_prompt, new_option)
    """
    if rng is None:
        rng = random.Random()

    options = _resolve_options(operator_name, operator_options)

    # Skip half the time to avoid over-mutating.
    if rng.random() < 0.5:
        return prompt_text, current_option

    choices = list(options.keys())
    if current_option in choices and len(choices) > 1:
        choices.remove(current_option)

    new_option = rng.choice(choices)
    guidance = options[new_option]
    marker = f"[mutation:{operator_name}]"
    # Strip a previous mutation of the same operator, then append guidance.
    lines = [ln for ln in prompt_text.splitlines() if not ln.startswith(marker)]
    base = "\n".join(lines).rstrip()
    new_prompt = f"{base}\n\n{marker} {guidance}\n"
    return new_prompt, new_option
