"""Turn a CSV of reviewed corrections into a PROPOSED_FIX .sql file. Never executes anything.

The CSV holds one row per record to change: the key columns that identify the
record, plus the columns to set. The output file has four marked sections so a
reviewer (and the tests) can see exactly what each part does:

  -- @section backup    copy the affected rows into a backup table first
  -- @section change    one UPDATE per CSV row, keyed on the key columns
  -- @section guard     a count that must equal the number of CSV rows
  -- @section rollback  restores the original values from the backup table

The file is a proposal. A person reviews it, runs it on a test copy, records
approval in the change log, and only then runs it on the real database.

Usage:
  python tools/csv_to_sql_changes.py --csv fix.csv --table installments \
      --key loan_id,inst_no --ticket TICKET-1001 [--out PROPOSED_FIX.sql]
Without --out the SQL is printed (dry run).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path

IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def ident(name: str) -> str:
    if not IDENT.match(name):
        raise ValueError(f"not a safe column or table name: {name!r}")
    return name


def literal(value: str) -> str:
    v = value.strip()
    if v == "" or v.upper() == "NULL":
        return "NULL"
    if re.fullmatch(r"-?\d+(\.\d+)?", v):
        return v
    return "'" + v.replace("'", "''") + "'"


def where_for(row: dict, keys: list[str]) -> str:
    return " AND ".join(f"{k} = {literal(row[k])}" for k in keys)


def generate(rows: list[dict], table: str, keys: list[str], ticket: str, now: dt.datetime | None = None) -> str:
    table = ident(table)
    keys = [ident(k) for k in keys]
    if not rows:
        raise ValueError("CSV has no data rows")
    cols = list(rows[0].keys())
    missing = [k for k in keys if k not in cols]
    if missing:
        raise ValueError(f"CSV is missing key column(s): {', '.join(missing)}")
    set_cols = [ident(c) for c in cols if c not in keys]
    if not set_cols:
        raise ValueError("CSV has no columns to change (only key columns)")
    seen = set()
    for r in rows:
        k = tuple(r[c] for c in keys)
        if k in seen:
            raise ValueError(f"duplicate key in CSV: {k}")
        seen.add(k)

    n = len(rows)
    tag = re.sub(r"[^A-Za-z0-9]", "_", ticket)
    bak = ident(f"bak_{tag}_{table}")
    any_row = " OR ".join(f"({where_for(r, keys)})" for r in rows)
    stamp = (now or dt.datetime.now()).strftime("%Y-%m-%d %H:%M")

    out = [
        f"-- PROPOSED_FIX for {ticket}: generated {stamp}. NOT EXECUTED.",
        f"-- Table: {table}. Keys: {', '.join(keys)}. Columns changed: {', '.join(set_cols)}.",
        f"-- Expected rows changed: {n}",
        "-- Steps: review -> run on a test copy -> record approval in CHANGE_LOG.md -> run for real.",
        "",
        "-- @section backup",
        f"DROP TABLE IF EXISTS {bak};",
        f"CREATE TABLE {bak} AS SELECT * FROM {table} WHERE {any_row};",
        f"-- Check: SELECT COUNT(*) FROM {bak};  -- must be {n}",
        "",
        "-- @section change",
    ]
    for r in rows:
        sets = ", ".join(f"{c} = {literal(r[c])}" for c in set_cols)
        out.append(f"UPDATE {table} SET {sets} WHERE {where_for(r, keys)};")
    match = " OR ".join(
        "(" + where_for(r, keys) + " AND " + " AND ".join(
            f"{c} IS {literal(r[c])}" if literal(r[c]) == "NULL" else f"{c} = {literal(r[c])}" for c in set_cols
        ) + ")" for r in rows)
    out += [
        "",
        "-- @section guard",
        f"-- The result must be exactly {n}. If not, do not commit: run the rollback section.",
        f"SELECT COUNT(*) AS changed_rows FROM {table} WHERE {match};",
        "",
        "-- @section rollback",
        f"-- Restores the values saved in {bak}. Keep the backup table until the fix is signed off.",
    ]
    for c in set_cols:
        join = " AND ".join(f"b.{k} = {table}.{k}" for k in keys)
        out.append(f"UPDATE {table} SET {c} = (SELECT b.{c} FROM {bak} b WHERE {join}) "
                   f"WHERE EXISTS (SELECT 1 FROM {bak} b WHERE {join});")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CSV of corrections -> PROPOSED_FIX .sql (never executed)")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--table", required=True)
    ap.add_argument("--key", required=True, help="comma-separated key columns")
    ap.add_argument("--ticket", required=True)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    with open(a.csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    try:
        sql = generate(rows, a.table, [k.strip() for k in a.key.split(",")], a.ticket)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if a.out:
        Path(a.out).write_text(sql, encoding="utf-8")
        print(f"wrote {a.out} ({len(rows)} rows). Review it; nothing was run.")
    else:
        print(sql, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
