# RCA: TICKET-1001, EOD failure on 30 Sep 2026

## Summary

EOD stopped at INTEREST_ACCRUAL because three variable-rate installments due on 30 Sep had a negative interest amount. For each of them the system stored the difference between the new and old rate, applied to the outstanding principal, instead of interest at the new rate. The rate change itself was approved and configured correctly. This points to a defect in how installments are recalculated after a repricing, and it has been reported to the vendor.

## Impact

- Day close for 30 Sep did not run. LATE_FEE and GL_POSTING were skipped for every loan, not only the three affected ones.
- Affected installments: L-1004, L-1006 and L-1008, installment 33, all product HL-VAR.
- Fixed-rate loans (HL-FIX) are not affected.

## Confirmed (from query results)

| # | Fact | Evidence |
|---|---|---|
| C1 | INTEREST_ACCRUAL failed with "Negative accrual amount; 3 accounts rejected". Later steps were skipped | `results/01_eod_status.tsv` |
| C2 | Exactly 3 installments due 30 Sep have interest below zero, all HL-VAR | `results/02_rejected_accounts.tsv` |
| C3 | Stored interest equals principal × (11.5 − 14.0) / 1200 in all 3 cases. Interest at 11.5% would be 16,611.11, 29,900.00 and 12,458.33 | `results/03_expected_vs_stored.tsv` |
| C4 | BASE_RATE for HL-VAR changed 14.0 to 11.5 on 2026-09-01 09:12, approved | `results/04_config_check.tsv` |
| C5 | INTEREST_GL and PRINCIPAL_GL for HL-VAR point to GL accounts that exist | `results/04_config_check.tsv` |

## Inference (not yet confirmed)

| # | Inference | Based on | How to confirm |
|---|---|---|---|
| I1 | The repricing job writes the rate delta into the installment instead of recomputing interest at the new rate | C3: exact match in 3 of 3 cases | Vendor to check the repricing recalculation code |
| I2 | Every variable-rate loan repriced on 1 Sep will hit this when its next installment falls due | All repriced HL-VAR installments in Sep show the pattern | Vendor confirmation; check October installments before their due date |

## Ruled out

- **Configuration error:** the rate change was approved and the GL mappings are valid (C4, C5).
- **Data entry on individual loans:** the pattern is identical across three loans in three different branches.

## Actions

| Action | Owner | Status |
|---|---|---|
| Report defect with evidence | Application support | Done: `VENDOR_REPORT.md` |
| Interim correction of the 3 installments so EOD can complete | Application support (prepare), Head of IT (approve) | Prepared: `PROPOSED_FIX.sql`, **not run** |
| Re-run EOD for 30 Sep after the correction | EOD operator | Waiting on approval |
| Permanent fix to repricing recalculation | Vendor | Open |
| Check October HL-VAR installments before they fall due | Application support | Open |
