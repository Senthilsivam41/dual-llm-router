# Invoice total is wrong

A customer was overcharged. `invoice_total` in `billing.py` applies a fixed coupon after tax, and it rounds each line item to cents before summing. The coupon has to come off the pre-tax subtotal. Line items have to be summed exactly, and the charge rounded half up to cents once at the end.

## Case 1 — coupon applied after tax

- Line items: 100.00
- Coupon: 10.00
- Tax rate: 0.08
- Charged: 98.00
- Expected: 97.20

The $10 coupon applies to the $100 subtotal first. Tax is 8% of what remains.

## Case 2 — per-line rounding

- Line items: 1.235, 1.235
- Coupon: 0
- Tax rate: 0
- Charged: 2.48
- Expected: 2.47

Do not round each line before summing. Sum 1.235 and 1.235, then round half up to cents.
