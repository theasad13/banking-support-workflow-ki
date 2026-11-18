"""Run a saved SQL file against a database, read-only, with an audit log.

Why: during incident investigation an analyst (or an AI assistant working for one)
must never change production data by accident, and every query must be traceable.

Guards (all three must pass):
  1. The query must be a saved .sql file (no ad-hoc inline SQL), with a --purpose.
  2. A statement check refuses anything that writes: INSERT, UPDATE, DELETE, MERGE,
     REPLACE, UPSERT, CREATE (except TEMP), DROP, ALTER, TRUNCATE, ATTACH, DETACH,
     VACUUM, REINDEX, GRANT, REVOKE, writing PRAGMAs, and EXEC/EXECUTE.
  3. The database is opened read-only by the driver (SQLite URI mode=ro), so even a
     statement the check misses cannot write.

Every run, including refused ones, is appended to logs/sql_YYYY-MM.log.

Exit codes: 0 ok, 2 refused by a guard, 1 database error.

Usage:
  python tools/safe_sql.py --db sample/bank_lms.db --file examples/.../01_x.sql --purpose "TICKET-1001: why"
  add --out result.tsv to save the result as tab-separated values.
"""
from __future__ import annotations

import argparse
import datetime as dt
import getpass
import os
import re
import sqlite3
import sys
from pathlib import Path

WRITE_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "MERGE", "REPLACE", "UPSERT", "DROP", "ALTER",
    "TRUNCATE", "ATTACH", "DETACH", "VACUUM", "REINDEX", "GRANT", "REVOKE",
    "EXEC", "EXECUTE",
)


def strip_comments_and_strings(sql: str) -> str:
    """Remove comments and quoted text so keywords inside them are ignored."""
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"'(?:''|[^'])*'", "''", sql)
    sql = re.sub(r'"(?:""|[^"])*"', '""', sql)
    return sql


def find_write(sql: str) -> str | None:
    """Return the first reason this SQL would write, or None if it looks read-only."""
    clean = strip_comments_and_strings(sql).upper()
    for kw in WRITE_KEYWORDS:
        if re.search(rf"\b{kw}\b", clean):
            return f"write keyword {kw}"
    for m in re.finditer(r"\bCREATE\s+(\w+)", clean):
        if m.group(1) not in ("TEMP", "TEMPORARY"):
            return f"CREATE {m.group(1)} (only CREATE TEMP is allowed)"
    if re.search(r"\bPRAGMA\s+\w+\s*=", clean):
        return "PRAGMA assignment"
    return None


def log_run(log_dir: Path, *, db: str, sql_file: str, purpose: str, sql: str, result: str) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now()
    path = log_dir / f"sql_{now:%Y-%m}.log"
    entry = (
        f"=== {now:%Y-%m-%d %H:%M:%S} | user={getpass.getuser()} | db={db}\n"
        f"file={sql_file}\npurpose={purpose}\nresult={result}\n---\n{sql.strip()}\n\n"
    )
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)


def run(db: str, sql_file: str, purpose: str, out: str | None, log_dir: Path) -> int:
    sql_path = Path(sql_file)
    if not purpose.strip():
        print("REFUSED: --purpose is required", file=sys.stderr)
        log_run(log_dir, db=db, sql_file=sql_file, purpose=purpose, sql="", result="REFUSED: no purpose")
        return 2
    if sql_path.suffix.lower() != ".sql" or not sql_path.is_file():
        print("REFUSED: query must be an existing .sql file", file=sys.stderr)
        log_run(log_dir, db=db, sql_file=sql_file, purpose=purpose, sql="", result="REFUSED: not a .sql file")
        return 2
    sql = sql_path.read_text(encoding="utf-8")
    reason = find_write(sql)
    if reason:
        print(f"REFUSED: {reason}. Write a PROPOSED_FIX file for human review instead.", file=sys.stderr)
        log_run(log_dir, db=db, sql_file=sql_file, purpose=purpose, sql=sql, result=f"REFUSED: {reason}")
        return 2

    if not Path(db).is_file():
        print(f"DB ERROR: database file not found: {db}", file=sys.stderr)
        log_run(log_dir, db=db, sql_file=sql_file, purpose=purpose, sql=sql, result="ERROR: db not found")
        return 1
    uri = Path(db).resolve().as_uri() + "?mode=ro"  # file:///... works on Windows and Linux
    try:
        con = sqlite3.connect(uri, uri=True)
        try:
            cur = con.execute(sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall() if cols else []
        finally:
            con.close()
    except sqlite3.Error as e:
        print(f"DB ERROR: {e}", file=sys.stderr)
        log_run(log_dir, db=db, sql_file=sql_file, purpose=purpose, sql=sql, result=f"ERROR: {e}")
        return 1

    lines = ["\t".join(cols)] + ["\t".join("" if v is None else str(v) for v in r) for r in rows]
    text = "\n".join(lines) + "\n"
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text, encoding="utf-8")
    print(text, end="")
    log_run(log_dir, db=db, sql_file=sql_file, purpose=purpose, sql=sql, result=f"OK: {len(rows)} rows")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read-only, logged SQL runner")
    ap.add_argument("--db", required=True)
    ap.add_argument("--file", required=True, help="saved .sql file to run")
    ap.add_argument("--purpose", required=True, help="ticket and reason, written to the log")
    ap.add_argument("--out", help="optional TSV output path")
    ap.add_argument("--log-dir", default=os.environ.get("SAFE_SQL_LOG_DIR", "logs"))
    a = ap.parse_args(argv)
    return run(a.db, a.file, a.purpose, a.out, Path(a.log_dir))


if __name__ == "__main__":
    sys.exit(main())
