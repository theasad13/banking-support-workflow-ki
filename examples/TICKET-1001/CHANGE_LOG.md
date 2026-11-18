# Change log: TICKET-1001

A data change is run only when every line in **Before running** is filled in.

## Change

| Field | Value |
|---|---|
| Script | `PROPOSED_FIX.sql` |
| Generated from | `corrections.csv` by `tools/csv_to_sql_changes.py` |
| Table | installments |
| Rows expected to change | 3 |
| Backup table | bak_TICKET_1001_installments |

## Before running

| Check | Done by | Date | Result |
|---|---|---|---|
| Script reviewed line by line | | | |
| Run on a test copy; guard returned 3 | | | |
| Rollback tested on the test copy | | | |
| Vendor agreed with the interim correction | | | |
| Approved for production | | | |

## Execution

| Step | Done by | Date / time | Result |
|---|---|---|---|
| Backup section run; backup count = 3 | | | |
| Change section run | | | |
| Guard returned 3 | | | |
| Committed | | | |
| EOD for 30 Sep re-run | | | |

_Example status: prepared, not run. Waiting on review and approval._
