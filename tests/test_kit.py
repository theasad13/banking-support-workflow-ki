"""Tests for the kit. Run from the repo root:  python -m unittest discover -s tests -v"""
from __future__ import annotations

import csv
import io
import shutil
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import csv_to_sql_changes as gen  # noqa: E402
import make_sample_db  # noqa: E402
import safe_sql  # noqa: E402


def sections(sql: str) -> dict[str, str]:
    out, name = {}, None
    for line in sql.splitlines():
        if line.startswith("-- @section "):
            name = line.split()[-1]
            out[name] = ""
        elif name:
            out[name] += line + "\n"
    return out


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.db = make_sample_db.build(self.tmp / "bank_lms.db")
        self.logs = self.tmp / "logs"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sql_file(self, text: str, name: str = "q.sql") -> Path:
        p = self.tmp / name
        p.write_text(text, encoding="utf-8")
        return p

    def run_safe(self, path, purpose="TEST: check"):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = safe_sql.run(str(self.db), str(path), purpose, None, self.logs)
        return code, out.getvalue(), err.getvalue()

    def log_text(self) -> str:
        return "".join(p.read_text(encoding="utf-8") for p in self.logs.glob("*.log"))


class WriteDetection(unittest.TestCase):
    def test_blocks_writes(self):
        for sql in [
            "UPDATE loans SET status='X'", "delete from loans", "INSERT INTO t VALUES (1)",
            "DROP TABLE loans", "ALTER TABLE loans ADD c INT", "CREATE TABLE x (a INT)",
            "CREATE INDEX i ON loans(status)", "REPLACE INTO t VALUES (1)", "PRAGMA journal_mode = WAL",
            "ATTACH DATABASE 'x.db' AS x", "MERGE INTO t USING s ON 1=1", "TRUNCATE TABLE loans",
            "EXEC sp_who", "SELECT 1; DELETE FROM loans", "WITH x AS (SELECT 1) UPDATE loans SET status='X'",
        ]:
            with self.subTest(sql=sql):
                self.assertIsNotNone(safe_sql.find_write(sql))

    def test_allows_reads(self):
        for sql in [
            "SELECT * FROM loans", "with x as (select 1 as a) select a from x",
            "SELECT 'please update me' AS note", "SELECT 1 -- DELETE in a comment",
            "/* DROP TABLE loans */ SELECT 1", "SELECT updated_at FROM t", "CREATE TEMP TABLE t AS SELECT 1",
            "PRAGMA table_info(loans)",
        ]:
            with self.subTest(sql=sql):
                self.assertIsNone(safe_sql.find_write(sql))


class SafeSqlRunner(Base):
    def test_select_runs_and_is_logged(self):
        code, out, _ = self.run_safe(self.sql_file("SELECT COUNT(*) AS n FROM loans;"), "TICKET-1: count")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["n", "10"])
        log = self.log_text()
        self.assertIn("purpose=TICKET-1: count", log)
        self.assertIn("result=OK: 1 rows", log)

    def test_write_refused_logged_and_db_unchanged(self):
        code, _, err = self.run_safe(self.sql_file("UPDATE loans SET status = 'CLOSED';"))
        self.assertEqual(code, 2)
        self.assertIn("REFUSED", err)
        self.assertIn("result=REFUSED", self.log_text())
        con = sqlite3.connect(self.db)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM loans WHERE status='ACTIVE'").fetchone()[0], 10)
        con.close()

    def test_purpose_required(self):
        code, _, err = self.run_safe(self.sql_file("SELECT 1;"), purpose="  ")
        self.assertEqual(code, 2)
        self.assertIn("--purpose", err)

    def test_query_must_be_sql_file(self):
        code, _, _ = self.run_safe(self.sql_file("SELECT 1;", "q.txt"))
        self.assertEqual(code, 2)
        code, _, _ = self.run_safe(self.tmp / "missing.sql")
        self.assertEqual(code, 2)

    def test_driver_read_only_even_if_check_missed(self):
        con = sqlite3.connect(f"file:{self.db.as_posix()}?mode=ro", uri=True)
        with self.assertRaises(sqlite3.OperationalError):
            con.execute("UPDATE loans SET status = 'X'")
        con.close()

    def test_missing_db_is_not_created(self):
        missing = self.tmp / "nope.db"
        code, _, _ = safe_sql.run(str(missing), str(self.sql_file("SELECT 1;")), "T", None, self.logs), None, None
        self.assertEqual(code, 1)
        self.assertFalse(missing.exists())

    def test_path_with_spaces(self):
        spaced = self.tmp / "folder with space" / "bank lms.db"
        spaced.parent.mkdir()
        shutil.copy(self.db, spaced)
        self.db = spaced
        code, out, err = self.run_safe(self.sql_file("SELECT COUNT(*) AS n FROM loans;"))
        self.assertEqual(code, 0, err)

    def test_db_error_returns_1(self):
        code, _, err = self.run_safe(self.sql_file("SELECT * FROM no_such_table;"))
        self.assertEqual(code, 1)
        self.assertIn("DB ERROR", err)


class SampleDataAndExamples(Base):
    """The example queries must find the planted issues and nothing else."""

    def rows(self, ticket, name):
        code, out, err = self.run_safe(ROOT / "examples" / ticket / "queries" / f"{name}.sql", f"{ticket}: test")
        self.assertEqual(code, 0, err)
        return list(csv.DictReader(io.StringIO(out), delimiter="\t"))

    def test_build_is_repeatable(self):
        again = make_sample_db.build(self.tmp / "again.db")
        dump = lambda p: list(sqlite3.connect(p).iterdump())  # noqa: E731
        self.assertEqual(dump(self.db), dump(again))

    def test_ticket_1001_eod_failure(self):
        steps = {r["step"]: r["status"] for r in self.rows("TICKET-1001", "01_eod_status")}
        self.assertEqual(steps["INTEREST_ACCRUAL"], "FAILED")
        self.assertEqual(steps["DAY_CLOSE"], "SKIPPED")

    def test_ticket_1001_exactly_three_variable_loans(self):
        rows = self.rows("TICKET-1001", "02_rejected_accounts")
        self.assertEqual([r["loan_id"] for r in rows], ["L-1004", "L-1006", "L-1008"])
        self.assertTrue(all(r["product_code"] == "HL-VAR" for r in rows))

    def test_ticket_1001_stored_equals_delta(self):
        rows = self.rows("TICKET-1001", "03_expected_vs_stored")
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["finding"] == "stored = delta" for r in rows))

    def test_ticket_1001_config_is_clean(self):
        results = [r["result"] for r in self.rows("TICKET-1001", "04_config_check")]
        self.assertNotIn("NOT APPROVED", results)
        self.assertNotIn("GL MISSING", results)

    def test_ticket_1002_inside_grace_period(self):
        sept = [r for r in self.rows("TICKET-1002", "01_installment_status") if r["inst_no"] == "33"][0]
        self.assertEqual(sept["days_overdue"], "10")
        self.assertEqual(float(sept["late_fee"]), 0)
        rule = {r["setting_name"]: r["setting_value"] for r in self.rows("TICKET-1002", "02_late_fee_rule")}
        self.assertEqual(rule["LATE_FEE_GRACE_DAYS"], "15")
        self.assertLess(int(sept["days_overdue"]), int(rule["LATE_FEE_GRACE_DAYS"]))

    def test_ticket_1002_rule_works_on_other_loan(self):
        l1003 = [r for r in self.rows("TICKET-1002", "03_rule_working_elsewhere") if r["loan_id"] == "L-1003"][0]
        self.assertEqual(int(l1003["days_overdue"]), 20)
        self.assertEqual(float(l1003["late_fee"]), 500)

    def test_all_example_queries_are_read_only(self):
        for f in (ROOT / "examples").glob("*/queries/*.sql"):
            with self.subTest(f=f.name):
                self.assertIsNone(safe_sql.find_write(f.read_text(encoding="utf-8")))


class ProposedFix(Base):
    ROWS = [
        {"loan_id": "L-1004", "inst_no": "33", "interest_amount": "16611.11"},
        {"loan_id": "L-1006", "inst_no": "33", "interest_amount": "29900.00"},
        {"loan_id": "L-1008", "inst_no": "33", "interest_amount": "12458.33"},
    ]

    def interest(self, con):
        return dict(con.execute(
            "SELECT loan_id, interest_amount FROM installments WHERE inst_no = 33 "
            "AND loan_id IN ('L-1004','L-1006','L-1008')").fetchall())

    def test_backup_change_guard_rollback_on_copy(self):
        sql = gen.generate(self.ROWS, "installments", ["loan_id", "inst_no"], "TICKET-1001")
        s = sections(sql)
        self.assertEqual(set(s), {"backup", "change", "guard", "rollback"})
        con = sqlite3.connect(self.db)
        before = self.interest(con)
        con.executescript(s["backup"])
        self.assertEqual(con.execute("SELECT COUNT(*) FROM bak_TICKET_1001_installments").fetchone()[0], 3)
        con.executescript(s["change"])
        self.assertEqual(con.execute(s["guard"]).fetchone()[0], 3)
        self.assertEqual(self.interest(con), {"L-1004": 16611.11, "L-1006": 29900.0, "L-1008": 12458.33})
        self.assertEqual(con.execute("SELECT COUNT(*) FROM installments WHERE interest_amount < 0").fetchone()[0], 0)
        con.executescript(s["rollback"])
        self.assertEqual(self.interest(con), before)
        con.close()

    def test_other_rows_untouched(self):
        s = sections(gen.generate(self.ROWS, "installments", ["loan_id", "inst_no"], "T-1"))
        con = sqlite3.connect(self.db)
        q = "SELECT * FROM installments WHERE NOT (inst_no = 33 AND loan_id IN ('L-1004','L-1006','L-1008')) ORDER BY 1,2"
        before = con.execute(q).fetchall()
        con.executescript(s["backup"] + s["change"])
        self.assertEqual(con.execute(q).fetchall(), before)
        con.close()

    def test_shipped_example_matches_generator(self):
        shipped = (ROOT / "examples/TICKET-1001/PROPOSED_FIX.sql").read_text(encoding="utf-8")
        with open(ROOT / "examples/TICKET-1001/corrections.csv", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        fresh = gen.generate(rows, "installments", ["loan_id", "inst_no"], "TICKET-1001")
        strip = lambda t: t.split("\n", 1)[1]  # noqa: E731  (first line holds the timestamp)
        self.assertEqual(strip(shipped), strip(fresh))

    def test_proposed_fix_is_refused_by_safe_sql(self):
        code, _, _ = self.run_safe(ROOT / "examples/TICKET-1001/PROPOSED_FIX.sql")
        self.assertEqual(code, 2)

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            gen.generate(self.ROWS, "installments; DROP TABLE loans", ["loan_id"], "T")
        with self.assertRaises(ValueError):
            gen.generate(self.ROWS, "installments", ["missing_col"], "T")
        with self.assertRaises(ValueError):
            gen.generate([{"loan_id": "L-1"}], "installments", ["loan_id"], "T")
        with self.assertRaises(ValueError):
            gen.generate(self.ROWS + [self.ROWS[0]], "installments", ["loan_id", "inst_no"], "T")
        with self.assertRaises(ValueError):
            gen.generate([], "installments", ["loan_id"], "T")

    def test_quotes_are_escaped(self):
        sql = gen.generate([{"id": "A'1", "note": "it's"}], "t", ["id"], "T")
        self.assertIn("'A''1'", sql)
        self.assertIn("'it''s'", sql)


if __name__ == "__main__":
    unittest.main()
