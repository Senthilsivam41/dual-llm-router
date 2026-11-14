# Invoice reconciliation

Implement a reusable, standard-library Python program in `reconcile.py`. It is the only target file. Use the patch action to create it. An independent runner executes the program.

`python reconcile.py INVOICES.csv PAYMENTS.csv` prints one JSON object with the keys `invoices` and `exceptions`. It must read the supplied paths and handle header-only files. Inputs are UTF-8 CSV with headers and valid fields. Currency is USD or EUR. Invoice IDs are unique. Amounts are positive decimal strings with at most two fractional digits.

- Invoice columns are `invoice_id,currency,amount`.
- Payment columns are `payment_id,invoice_id,currency,amount`.
- Count payment IDs across the whole payment file. Reject **every occurrence** of any duplicated ID, including its first occurrence. For remaining payments reject unknown invoice IDs, then reject currency mismatches. Use reason codes `duplicate_payment_id`, `unknown_invoice`, and `currency_mismatch`, respectively. Rejected payments never contribute to totals.
- Each invoice summary contains exactly `invoice_id`, `currency`, `invoiced_cents`, `paid_cents`, and `status`. Use exact integer cents. The status is `unpaid` for zero paid, `partial` for less than the invoiced amount, `paid` for equality, and `overpaid` for more. Include every invoice. Sort by invoice ID.
- Each exception contains exactly `row`, `payment_id`, and `reason`. Row numbers start at 1 for the first data record, excluding the header. Sort exceptions by row.
