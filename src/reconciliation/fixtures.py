"""Versioned synthetic scenarios with independently specified expected rows."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import asdict, dataclass
from typing import Any

FAMILIES = ("aggregation", "duplicates", "links_and_currency", "mixed")
INVOICE_COLUMNS = ("invoice_id", "currency", "amount")
PAYMENT_COLUMNS = ("payment_id", "invoice_id", "currency", "amount")


@dataclass(frozen=True)
class Probe:
    invoices: str
    payments: str
    expected: dict[str, Any]


@dataclass(frozen=True)
class Scenario:
    id: str
    family: str
    diagnostic: Probe
    private: tuple[Probe, ...]


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fixture_hash(scenarios: tuple[Scenario, ...]) -> str:
    return sha256(json.dumps([asdict(case) for case in scenarios], sort_keys=True))


def _csv(columns: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return stream.getvalue()


def _amount(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def _probe(
    invoices: list[tuple[str, str, int]],
    payments: list[tuple[str, str, str, int]],
    summaries: list[tuple[str, str, int, int, str]],
    exceptions: list[tuple[int, str, str]],
) -> Probe:
    return Probe(
        _csv(INVOICE_COLUMNS, [(key, currency, _amount(cents)) for key, currency, cents in invoices]),
        _csv(PAYMENT_COLUMNS, [
            (key, invoice, currency, _amount(cents)) for key, invoice, currency, cents in payments
        ]),
        {
            "invoices": [
                dict(invoice_id=key, currency=currency, invoiced_cents=due, paid_cents=paid, status=status)
                for key, currency, due, paid, status in sorted(summaries)
            ],
            "exceptions": [
                dict(row=row, payment_id=key, reason=reason)
                for row, key, reason in exceptions
            ],
        },
    )


def _case(family: str, seed: int) -> Probe:
    a, b, c, d = (f"INV-{seed:04d}-{letter}" for letter in "ABCD")
    p, q, r, s, t = (f"PMT-{seed:04d}-{letter}" for letter in "PQRST")
    amount = 997 + 13 * seed
    other = 238 + 7 * seed
    if family == "aggregation":
        if seed % 5 == 0:
            return _probe([(a, "EUR", amount)], [], [(a, "EUR", amount, 0, "unpaid")], [])
        return _probe(
            [(d, "USD", 49), (b, "EUR", other), (c, "USD", 250), (a, "USD", amount)],
            [(r, b, "EUR", 1), (q, a, "USD", amount - 13), (p, a, "USD", 13), (s, d, "USD", 54)],
            [(a, "USD", amount, amount, "paid"), (b, "EUR", other, 1, "partial"),
             (c, "USD", 250, 0, "unpaid"), (d, "USD", 49, 54, "overpaid")],
            [],
        )
    if family == "duplicates":
        if seed % 2 == 0:
            return _probe(
                [(b, "EUR", other), (a, "USD", amount)],
                [(p, a, "USD", amount), (q, b, "EUR", other), (p, c, "EUR", 9), (p, b, "EUR", 19)],
                [(a, "USD", amount, 0, "unpaid"), (b, "EUR", other, other, "paid")],
                [(1, p, "duplicate_payment_id"), (3, p, "duplicate_payment_id"),
                 (4, p, "duplicate_payment_id")],
            )
        return _probe(
            [(a, "USD", amount)],
            [(p, b, "EUR", amount), (p, a, "USD", amount), (q, a, "USD", 13), (q, a, "USD", 13)],
            [(a, "USD", amount, 0, "unpaid")],
            [(1, p, "duplicate_payment_id"), (2, p, "duplicate_payment_id"),
             (3, q, "duplicate_payment_id"), (4, q, "duplicate_payment_id")],
        )
    if family == "links_and_currency":
        if seed % 5 == 0:
            return _probe([], [(p, a, "EUR", 1)], [], [(1, p, "unknown_invoice")])
        return _probe(
            [(b, "EUR", other), (a, "USD", amount)],
            [(p, c, "EUR", 13), (q, a, "EUR", amount), (r, b, "EUR", other), (s, b, "USD", 11)],
            [(a, "USD", amount, 0, "unpaid"), (b, "EUR", other, other, "paid")],
            [(1, p, "unknown_invoice"), (2, q, "currency_mismatch"), (4, s, "currency_mismatch")],
        )
    return _probe(
        [(b, "EUR", amount), (a, "USD", 30)],
        [(q, b, "USD", 33), (r, a, "USD", 10), (p, b, "EUR", amount - 1), (s, a, "USD", 20),
         (t, c, "EUR", 5), (q, b, "EUR", 33)],
        [(a, "USD", 30, 30, "paid"), (b, "EUR", amount, amount - 1, "partial")],
        [(1, q, "duplicate_payment_id"), (5, t, "unknown_invoice"), (6, q, "duplicate_payment_id")],
    )


def scenarios(split: str) -> tuple[Scenario, ...]:
    if split not in {"development", "holdout"}:
        raise ValueError(f"Unknown split {split}")
    count = 3 if split == "development" else 8
    offset = 1 if split == "development" else 1001
    return tuple(
        Scenario(
            f"{split}-{family}-{index + 1:02d}",
            family,
            _case(family, seed),
            (_case(family, seed + 100), _case(FAMILIES[(group + index + 1) % len(FAMILIES)], seed + 200)),
        )
        for group, family in enumerate(FAMILIES)
        for index in range(count)
        for seed in (offset + 10 * group + index,)
    )
