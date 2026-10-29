"""Invoice totals.

`invoice_total` charges a fixed coupon and an optional tax rate.
`tax_rate` is a fraction such as "0.08" for 8%. Totals are in dollars.
"""

from decimal import Decimal, ROUND_HALF_UP

_CENT = Decimal("0.01")


def invoice_total(line_items: list[str], coupon: str = "0", tax_rate: str = "0.08") -> str:
    # Sum line items exactly; no per-line rounding.
    subtotal = sum((Decimal(item) for item in line_items), Decimal("0"))
    # Apply the coupon to the pre-tax subtotal.
    discounted = subtotal - Decimal(coupon)
    # Compute tax on the discounted subtotal.
    taxed = discounted * (Decimal("1") + Decimal(tax_rate))
    # Round half up to cents exactly once at the end.
    total = taxed.quantize(_CENT, rounding=ROUND_HALF_UP)
    return format(total, "f")
