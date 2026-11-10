"""Decimal parsing shared by check validation and assertion matching."""

from __future__ import annotations

import re
from decimal import Decimal

_DECIMAL_TEXT = re.compile(r"^-?\d+(?:\.\d+)?$")


def parse_decimal_string(value: str) -> Decimal:
    """Parse a decimal string such as '97.20' or '-1.5'.

    Currency symbols, thousands separators, and scientific notation are rejected
    so a planner cannot smuggle a non-numeric token into a check.
    """
    text = str(value).strip()
    if not _DECIMAL_TEXT.fullmatch(text):
        raise ValueError(f"expected a decimal string, got {value!r}")
    return Decimal(text)


def decimals_equal(left: str, right: str) -> bool:
    return parse_decimal_string(left) == parse_decimal_string(right)
