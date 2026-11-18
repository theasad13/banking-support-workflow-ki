# RCA: TICKET-1002, late fee not charged on L-1007

## Summary

Not a defect. Product HL-FIX has a 15-day grace period before the late fee applies. The installment due on 20 Sep was 10 days overdue on 30 Sep, so no fee was due yet. If it is still unpaid, the fee of 500 will be charged by the EOD of 6 Oct 2026.

## Confirmed (from query results)

| # | Fact | Evidence |
|---|---|---|
| C1 | L-1007 installment 33, due 2026-09-20, is unpaid and 10 days overdue on 2026-09-30. Late fee 0 | `results/01_installment_status.tsv` |
| C2 | HL-FIX: LATE_FEE_GRACE_DAYS = 15, LATE_FEE_AMOUNT = 500, unchanged since 2024-01-01 | `results/02_late_fee_rule.tsv` |
| C3 | L-1003 (same product), due 10 Sep, was charged 500 on 26 Sep, i.e. on day 16 | `results/03_rule_working_elsewhere.tsv` |
| C4 | The LATE_FEE step ran OK from 26 to 29 Sep; on 30 Sep it was skipped because EOD stopped earlier | `results/04_eod_late_fee_step.tsv` |

## Inference

| # | Inference | Based on |
|---|---|---|
| I1 | The fee is charged on the 16th day after the due date | C3 |
| I2 | For L-1007 that is 6 Oct 2026 | C1, I1 |

## Ruled out

- **Late-fee function broken:** it charged L-1003 correctly (C3).
- **EOD failure on 30 Sep (TICKET-1001):** it did skip LATE_FEE that day, but L-1007 was inside the grace period anyway, so the outcome is the same.

## Actions

| Action | Owner | Status |
|---|---|---|
| Reply to branch with the rule and the date | Application support | Done: `USER_REPLY.md` |
| Check L-1007 after EOD of 6 Oct | Application support | Open |
