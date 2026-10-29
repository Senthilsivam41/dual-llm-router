"""Find numeric literals that appear inside pytest assertion expressions."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .decimals import parse_decimal_string

_DECIMAL_TEXT = re.compile(r"^-?\d+(?:\.\d+)?$")


@dataclass(frozen=True)
class AssertionHit:
    path: str
    function_name: str
    line: int
    text: str
    value: Decimal


def _number_from_constant(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        text = value.strip()
        if re_fullmatch_decimal(text):
            return parse_decimal_string(text)
    return None


def re_fullmatch_decimal(text: str) -> bool:
    return _DECIMAL_TEXT.fullmatch(text) is not None


def _collect_decimals(node: ast.AST, found: list[Decimal]) -> None:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        number = None
        if isinstance(node.operand, ast.Constant):
            number = _number_from_constant(node.operand.value)
        if number is not None and not isinstance(node.operand.value, str):
            found.append(-number)
            return
    if isinstance(node, ast.Constant):
        number = _number_from_constant(node.value)
        if number is not None:
            found.append(number)
        return
    for child in ast.iter_child_nodes(node):
        _collect_decimals(child, found)


def assertion_hits(source: str, path: str) -> list[AssertionHit]:
    """Return numeric values that occur in the test expression of an assert.

    Values that appear only in the assertion message, or in comments, are ignored.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    lines = source.splitlines()
    hits: list[AssertionHit] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Assert):
                continue
            values: list[Decimal] = []
            _collect_decimals(child.test, values)
            text = lines[child.lineno - 1].strip() if 0 < child.lineno <= len(lines) else ""
            for value in values:
                hits.append(
                    AssertionHit(
                        path=path,
                        function_name=node.name,
                        line=child.lineno,
                        text=text,
                        value=value,
                    )
                )
    return hits


def load_test_sources(workspace: str) -> list[tuple[str, str]]:
    root = Path(workspace)
    sources: list[tuple[str, str]] = []
    if not root.exists():
        return sources
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        sources.append((str(path.relative_to(root)), path.read_text(encoding="utf-8")))
    return sources
