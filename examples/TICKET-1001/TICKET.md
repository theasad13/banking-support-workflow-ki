# TICKET-1001: EOD stopped on 30 Sep 2026

**Reported by:** Operations (EOD operator)
**Reported at:** 2026-09-30 21:40
**Priority:** P1. Day close has not run, so the next business day cannot open.

> EOD for 30-Sep stopped at Interest Accrual with "Negative accrual amount; 3 accounts rejected".
> Everything after that step was skipped. Please check urgently.

## Investigation log

| Step | Query | Result file | What it showed |
|---|---|---|---|
| 1 | `queries/01_eod_status.sql` | `results/01_eod_status.tsv` | INTEREST_ACCRUAL failed; LATE_FEE, GL_POSTING and DAY_CLOSE skipped |
| 2 | `queries/02_rejected_accounts.sql` | `results/02_rejected_accounts.tsv` | 3 installments due 30 Sep have negative interest: L-1004, L-1006, L-1008, all HL-VAR |
| 3 | `queries/03_expected_vs_stored.sql` | `results/03_expected_vs_stored.tsv` | In all 3, the stored amount equals the rate-change delta (new rate minus old rate), not interest at the new rate |
| 4 | `queries/04_config_check.sql` | `results/04_config_check.tsv` | The 14.0 to 11.5 rate change was approved; HL-VAR GL mappings exist |

Every query ran through `tools/safe_sql.py` (read-only, logged). See `examples/logs/`.

## Outputs

- `RCA.md`: root cause, with confirmed facts kept apart from inference
- `VENDOR_REPORT.md`: defect report for the software vendor
- `corrections.csv` and `PROPOSED_FIX.sql`: interim data correction, **not run**, waiting for approval
- `CHANGE_LOG.md`: approvals and execution record
