# TICKET-1002: Late fee not charged on L-1007

**Reported by:** Branch 03 South
**Reported at:** 2026-09-30 11:05
**Priority:** P3

> Customer CUST-0007 (loan L-1007) has not paid the installment due on 20 Sep, but the system
> has not charged any late fee. Is the late-fee function broken?

## Investigation log

| Step | Query | Result file | What it showed |
|---|---|---|---|
| 1 | `queries/01_installment_status.sql` | `results/01_installment_status.tsv` | Installment 33 due 20 Sep is unpaid, 10 days overdue on 30 Sep, no late fee |
| 2 | `queries/02_late_fee_rule.sql` | `results/02_late_fee_rule.tsv` | HL-FIX: grace period 15 days, fee 500 |
| 3 | `queries/03_rule_working_elsewhere.sql` | `results/03_rule_working_elsewhere.tsv` | L-1003, 20 days overdue, was charged 500 on 26 Sep, so the rule works |
| 4 | `queries/04_eod_late_fee_step.sql` | `results/04_eod_late_fee_step.tsv` | LATE_FEE ran every day except 30 Sep (skipped because of TICKET-1001) |

## Outputs

- `RCA.md`: not a defect; the system is applying the configured grace period
- `USER_REPLY.md`: reply to the branch
