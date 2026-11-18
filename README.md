# Banking Support Workflow Kit

A small, runnable kit showing how I investigate production issues on a lending system: read-only and logged SQL, a root-cause analysis that keeps confirmed facts apart from guesses, and data fixes that are only ever proposed, never run directly.

It is based on how I work in application support for core banking and loan management systems. **All data here is invented.** The kit contains no employer code, data, table names, vendor names or system details.

## Why this exists

Production support on a lending system has three risks I care about:

1. **Changing data by accident** while investigating.
2. **Reporting a guess as a fact** to a vendor or a manager.
3. **Running a data fix that cannot be undone.**

The kit puts a guard on each one, and the same guards apply when an AI assistant helps with the investigation (see [`AGENT_RULES.md`](AGENT_RULES.md)).

| Risk | Guard |
|---|---|
| Accidental writes | `tools/safe_sql.py` refuses write statements **and** opens the database read-only, so a write fails even if the check misses it. Every run is logged with its purpose. |
| Guess reported as fact | `templates/RCA.md` has separate **Confirmed**, **Inference** and **Ruled out** sections. Each confirmed line points to a result file. |
| Irreversible fix | `tools/csv_to_sql_changes.py` turns reviewed corrections into a `PROPOSED_FIX.sql` with backup, change, guard (expected row count) and rollback sections. It never runs anything. |

## Quick start

Needs Python 3.9 or newer. No packages to install.

```bash
python tools/make_sample_db.py                     # builds sample/bank_lms.db (invented data)
python -m unittest discover -s tests -v            # 24 tests

# run one of the example investigation queries
python tools/safe_sql.py --db sample/bank_lms.db \
    --file examples/TICKET-1001/queries/02_rejected_accounts.sql \
    --purpose "TICKET-1001: which accounts did EOD reject"

# try to run a write: it is refused and the attempt is logged
python tools/safe_sql.py --db sample/bank_lms.db \
    --file examples/TICKET-1001/PROPOSED_FIX.sql --purpose "TICKET-1001: demo"
```

Logs go to `logs/sql_YYYY-MM.log`.

## The two example tickets

### TICKET-1001: EOD stopped at interest accrual (software defect)

End of day on 30 Sep failed with "Negative accrual amount; 3 accounts rejected".

Four read-only queries show the following:

- The three rejected installments are all on the variable-rate product.
- In each one, the stored interest equals the rate-change delta (11.5% − 14.0%) instead of interest at the new 11.5%.
- The rate change was approved, and the GL mappings are valid.

So configuration is ruled out and the defect is in the repricing recalculation.

Outputs:

- [RCA](examples/TICKET-1001/RCA.md)
- [vendor defect report](examples/TICKET-1001/VENDOR_REPORT.md)
- an interim [PROPOSED_FIX.sql](examples/TICKET-1001/PROPOSED_FIX.sql), generated from [corrections.csv](examples/TICKET-1001/corrections.csv)
- a [change log](examples/TICKET-1001/CHANGE_LOG.md) with the approvals still blank

### TICKET-1002: "Late fee not charged" (not a defect)

A branch reports an overdue installment with no late fee.

The queries show the following:

- The product has a 15-day grace period, and the installment is 10 days overdue.
- Another loan on the same product, 20 days overdue, was charged on time.
- The EOD failure from TICKET-1001 is ruled out: it skipped the late-fee step on 30 Sep, but no fee was due on this loan yet.

Outputs: [RCA](examples/TICKET-1002/RCA.md) and a plain-language [reply to the branch](examples/TICKET-1002/USER_REPLY.md) with the date the fee will apply.

## Layout

```
AGENT_RULES.md            rules for an AI assistant helping with a ticket
tools/
  safe_sql.py             read-only, logged query runner
  make_sample_db.py       builds the invented sample database
  csv_to_sql_changes.py   CSV of corrections -> PROPOSED_FIX.sql (never executed)
templates/                TICKET, RCA, VENDOR_REPORT, USER_REPLY, PROPOSED_FIX, CHANGE_LOG
examples/TICKET-1001/     defect: queries, results, RCA, vendor report, proposed fix
examples/TICKET-1002/     misunderstanding: queries, results, RCA, user reply
tests/                    unit tests (standard library only)
```

## How a ticket goes through the kit

1. Copy `templates/TICKET.md` into a new `examples/TICKET-xxxx/` folder (or your own tickets folder).
2. Write each query as a numbered `.sql` file and run it with `safe_sql.py`, using `--out results/...tsv`.
3. Fill in `RCA.md`: confirmed facts with evidence, inferences with how to confirm them, causes ruled out.
4. Defect: write `VENDOR_REPORT.md`. Misunderstanding: write `USER_REPLY.md`.
5. If data must change, put the reviewed values in a CSV and generate `PROPOSED_FIX.sql`. Test it and its rollback on a copy, record approval in `CHANGE_LOG.md`, then a person runs it.

## Limits

- The sample database is SQLite so it runs anywhere. In production I work with SQL Server and Oracle. For those, the read-only guard should also be a database login that only has read permission.
- The write check is a keyword filter. It is the second line of defence; the read-only connection is the first.
- `PROPOSED_FIX.sql` uses plain SQL that runs on SQLite. On another database, review the syntax before use.

## How it was built

I designed the workflow, the rules, the example tickets and the acceptance tests. The code was written with AI coding tools from that specification and is checked by the tests in `tests/`.

## License

MIT. See [LICENSE](LICENSE).
