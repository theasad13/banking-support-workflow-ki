# Defect report: negative installment interest after repricing

**Our reference:** TICKET-1001
**Severity:** High. EOD cannot complete without a data correction.
**Module:** Loan repricing / installment recalculation
**Found in:** Production, EOD run 2026-09-30

## What happens

After the HL-VAR base rate was changed from 14.0% to 11.5% on 2026-09-01, the next installment for each repriced loan was saved with a negative interest amount. The INTEREST_ACCRUAL step of EOD then rejects these accounts and stops.

## Expected

Installment interest = opening principal × 11.5 / 1200.

## Actual

Installment interest = opening principal × (11.5 − 14.0) / 1200. The rate change is applied as a delta instead of as the new rate.

| Loan | Inst | Opening principal | Stored interest | Expected at 11.5% | Delta formula |
|---|---|---|---|---|---|
| L-1004 | 33 | 1,733,333.44 | −3,611.11 | 16,611.11 | −3,611.11 |
| L-1006 | 33 | 3,120,000.00 | −6,500.00 | 29,900.00 | −6,500.00 |
| L-1008 | 33 | 1,300,000.00 | −2,708.33 | 12,458.33 | −2,708.33 |

## Steps to reproduce

1. Variable-rate product with active loans and BASE_RATE 14.0.
2. Change BASE_RATE to 11.5 through the normal maker/checker screen.
3. Let the repricing job run. Check the next installment of any repriced loan.

## Already checked on our side

- Rate change was approved through maker/checker (audit record attached).
- GL mappings for the product are valid.
- Fixed-rate loans are not affected.

## What we need from you

1. Confirmation of the cause, and a fix for the recalculation.
2. Your agreement with our interim correction (attached `PROPOSED_FIX.sql`) so EOD for 30 Sep can complete, or a correction script from your side.
3. Whether other installments or loans could be affected, and a query to find them.

**Attachments:** query results 01 to 04 (TSV), `PROPOSED_FIX.sql`
