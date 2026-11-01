"""Invoice totals.

`invoice_total` charges a fixed coupon and an optional tax rate.
`tax_rate` is a fraction such as "0.08" for 8%. Totals are in dollars.
"""

from decimal import Decimal, ROUND_HALF_UP

_CENT = Decimal("0.01")


def invoice_total(line_items: list[str], coupon: str = "0", tax_rate: str = "0.08") -> str:
    rounded_lines = [
        Decimal(item).quantize(_CENT, rounding=ROUND_HALF_UP) for item in line_items
    ]
    subtotal = sum(rounded_lines, Decimal("0"))
    taxed = (subtotal * (Decimal("1") + Decimal(tax_rate))).quantize(
        _CENT, rounding=ROUND_HALF_UP
    )
    total = taxed - Decimal(coupon)
    if total < 0:
        total = Decimal("0.00")
    return format(total.quantize(_CENT, rounding=ROUND_HALF_UP), "f")
