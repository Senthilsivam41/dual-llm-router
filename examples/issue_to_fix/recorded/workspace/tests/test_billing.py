from decimal import Decimal

from billing import invoice_total


def test_coupon_applied_before_tax():
    assert Decimal(invoice_total(["100.00"], coupon="10.00", tax_rate="0.08")) == Decimal("97.20")


def test_no_per_line_rounding():
    assert Decimal(invoice_total(["1.235", "1.235"], coupon="0", tax_rate="0")) == Decimal("2.47")


def test_half_cent_rounds_up():
    assert Decimal(invoice_total(["1.005"], coupon="0", tax_rate="0")) == Decimal("1.01")


def test_coupon_exceeds_subtotal():
    assert Decimal(invoice_total(["5.00"], coupon="10.00", tax_rate="0.08")) == Decimal("-5.40")
