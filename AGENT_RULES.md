# Rules for an AI assistant working in this kit

Give this file to any AI coding or chat assistant before it helps with a support ticket.
The rules come from production support on lending systems, where one wrong UPDATE can
change customer balances and one pasted screenshot can leak customer data.

## 1. Database access is read-only

- Run every query through `tools/safe_sql.py`. Never connect to the database any other way.
- Save each query as a numbered file in the ticket folder (`queries/01_name.sql`) before running it.
  No inline SQL.
- Give every run a `--purpose` that starts with the ticket number and says what the query is for.
- If `safe_sql.py` refuses a query, do not try to get around it. A refusal means the query
  writes, and writes are not your job (see rule 3).

## 2. Keep facts and guesses apart

- The RCA has two tables: **Confirmed** (each line points to a result file) and **Inference**
  (each line says what it is based on and how to confirm it).
- Do not move a line from Inference to Confirmed without a query result that proves it.
- Always fill in **Ruled out**: the causes you checked and why you excluded them.
- Decide which of four it is: software defect, configuration, data, or user misunderstanding.
  Defect goes to `VENDOR_REPORT.md`; misunderstanding goes to `USER_REPLY.md`.

## 3. Data changes are proposals, never actions

- To change data, put the reviewed values in a CSV and generate `PROPOSED_FIX.sql` with
  `tools/csv_to_sql_changes.py`. It always has backup, change, guard and rollback sections.
- Never run a PROPOSED_FIX yourself. A person reviews it, tests it on a copy, records the
  approval in `CHANGE_LOG.md`, and runs it.
- State the expected row count. If the guard count differs, the change is rolled back.

## 4. No customer data leaves the ticket folder

- Use loan IDs and customer reference numbers, never names, CNIC or ID numbers, phone
  numbers or addresses.
- Do not paste query results into outside tools, chats or websites.
- Vendor reports contain only the rows needed to prove the defect.

## 5. Stop and ask a person when

- The evidence points two ways and more queries will not settle it.
- The fix needs a configuration change or a change to more rows than the ticket names.
- You would need access you do not have (production server, vendor system, another database).
- Anything would be sent outside the team.

## 6. Write so the reader can act

- Users get plain words: what happened, why, what happens next, and the date if there is one.
- Vendors get: expected, actual, the values that prove it, steps to reproduce, and what we need.
- No blame, no guessing presented as fact.
