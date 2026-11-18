"""Build the invented sample database used by the examples and tests.

Everything here is made up: a tiny generic lending system with two products,
ten loans, three months of installments and an end-of-day (EOD) process log.
No real institution, vendor, customer or system is represented.

Two problems are planted on purpose so the example tickets have something to find:
  TICKET-1001  EOD on 2026-09-30 fails at INTEREST_ACCRUAL. The three variable-rate
               loans repriced on 2026-09-01 have a negative interest amount on their
               30 Sep installment: the system stored the rate-change delta instead of
               the interest at the new rate. Configuration is correct, so it is a
               software defect to report to the vendor.
  TICKET-1002  A branch says loan L-1007 is overdue but no late fee was charged.
               The product has a 15-day grace period and the installment is only
               10 days overdue, so the system is behaving as configured.

Usage:  python tools/make_sample_db.py [--out sample/bank_lms.db]
"""
from __future__ import annotations

import argparse
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

RUN_DATE = "2026-09-30"
OLD_VAR_RATE = Decimal("14.0")
NEW_VAR_RATE = Decimal("11.5")

SCHEMA = """
CREATE TABLE branches (branch_code TEXT PRIMARY KEY, name TEXT NOT NULL, city TEXT NOT NULL);
CREATE TABLE products (product_code TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE product_settings (
    product_code TEXT NOT NULL REFERENCES products(product_code),
    setting_name TEXT NOT NULL, setting_value TEXT NOT NULL, effective_from TEXT NOT NULL,
    PRIMARY KEY (product_code, setting_name));
CREATE TABLE gl_accounts (gl_code TEXT PRIMARY KEY, description TEXT NOT NULL);
CREATE TABLE loans (
    loan_id TEXT PRIMARY KEY, branch_code TEXT NOT NULL REFERENCES branches(branch_code),
    product_code TEXT NOT NULL REFERENCES products(product_code), customer_ref TEXT NOT NULL,
    principal NUMERIC NOT NULL, rate_pct NUMERIC NOT NULL, start_date TEXT NOT NULL,
    due_day INTEGER NOT NULL, status TEXT NOT NULL);
CREATE TABLE installments (
    loan_id TEXT NOT NULL REFERENCES loans(loan_id), inst_no INTEGER NOT NULL,
    due_date TEXT NOT NULL, opening_principal NUMERIC NOT NULL,
    principal_amount NUMERIC NOT NULL, interest_amount NUMERIC NOT NULL,
    paid_date TEXT, late_fee NUMERIC NOT NULL DEFAULT 0, late_fee_date TEXT,
    PRIMARY KEY (loan_id, inst_no));
CREATE TABLE eod_process_log (
    run_date TEXT NOT NULL, seq INTEGER NOT NULL, step TEXT NOT NULL,
    status TEXT NOT NULL, message TEXT, PRIMARY KEY (run_date, seq));
CREATE TABLE settings_audit (
    changed_at TEXT NOT NULL, product_code TEXT NOT NULL, setting_name TEXT NOT NULL,
    old_value TEXT, new_value TEXT, changed_by TEXT NOT NULL, approved_by TEXT);
"""

BRANCHES = [("B01", "Branch 01 North", "Sample City"),
            ("B02", "Branch 02 Central", "Sample City"),
            ("B03", "Branch 03 South", "Example Town")]
PRODUCTS = [("HL-FIX", "Home loan, fixed rate"), ("HL-VAR", "Home loan, variable rate")]
SETTINGS = [
    ("HL-FIX", "RATE_TYPE", "FIXED", "2024-01-01"),
    ("HL-FIX", "LATE_FEE_GRACE_DAYS", "15", "2024-01-01"),
    ("HL-FIX", "LATE_FEE_AMOUNT", "500", "2024-01-01"),
    ("HL-FIX", "INTEREST_GL", "4100-01", "2024-01-01"),
    ("HL-FIX", "PRINCIPAL_GL", "1300-01", "2024-01-01"),
    ("HL-VAR", "RATE_TYPE", "VARIABLE", "2024-01-01"),
    ("HL-VAR", "BASE_RATE", str(NEW_VAR_RATE), "2026-09-01"),
    ("HL-VAR", "LATE_FEE_GRACE_DAYS", "15", "2024-01-01"),
    ("HL-VAR", "LATE_FEE_AMOUNT", "500", "2024-01-01"),
    ("HL-VAR", "INTEREST_GL", "4100-02", "2024-01-01"),
    ("HL-VAR", "PRINCIPAL_GL", "1300-02", "2024-01-01"),
]
GL = [("4100-01", "Interest income, fixed-rate home loans"),
      ("4100-02", "Interest income, variable-rate home loans"),
      ("1300-01", "Loan principal, fixed-rate home loans"),
      ("1300-02", "Loan principal, variable-rate home loans")]
AUDIT = [
    ("2026-08-28 16:40:00", "HL-FIX", "LATE_FEE_AMOUNT", "500", "500", "ops.user1", "ops.manager1"),
    ("2026-09-01 09:12:00", "HL-VAR", "BASE_RATE", str(OLD_VAR_RATE), str(NEW_VAR_RATE), "ops.user2", "ops.manager1"),
]
# loan_id, branch, product, principal, due_day
LOANS = [
    ("L-1001", "B01", "HL-FIX", 2_400_000, 5),
    ("L-1002", "B02", "HL-FIX", 1_800_000, 10),
    ("L-1003", "B01", "HL-FIX", 3_000_000, 10),
    ("L-1004", "B03", "HL-VAR", 2_000_000, 30),
    ("L-1005", "B02", "HL-FIX", 1_200_000, 15),
    ("L-1006", "B01", "HL-VAR", 3_600_000, 30),
    ("L-1007", "B03", "HL-FIX", 2_500_000, 20),
    ("L-1008", "B02", "HL-VAR", 1_500_000, 30),
    ("L-1009", "B01", "HL-FIX", 900_000, 25),
    ("L-1010", "B03", "HL-FIX", 2_200_000, 28),
]
FIX_RATE = Decimal("15.0")
TERM_MONTHS = 240
MONTHS = [(7, 31), (8, 32), (9, 33)]  # month of 2026, installment number
UNPAID = {("L-1003", 9), ("L-1007", 9)}  # overdue on purpose
LATE_FEES = {("L-1003", 9): ("500", "2026-09-26")}  # due 10 Sep + 15 grace days -> charged 26 Sep


def money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build(out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    con = sqlite3.connect(out)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO branches VALUES (?,?,?)", BRANCHES)
    con.executemany("INSERT INTO products VALUES (?,?)", PRODUCTS)
    con.executemany("INSERT INTO product_settings VALUES (?,?,?,?)", SETTINGS)
    con.executemany("INSERT INTO gl_accounts VALUES (?,?)", GL)
    con.executemany("INSERT INTO settings_audit VALUES (?,?,?,?,?,?,?)", AUDIT)

    for i, (loan_id, branch, product, principal, due_day) in enumerate(LOANS, start=1):
        rate = NEW_VAR_RATE if product == "HL-VAR" else FIX_RATE
        con.execute("INSERT INTO loans VALUES (?,?,?,?,?,?,?,?,?)",
                    (loan_id, branch, product, f"CUST-{i:04d}", principal, float(rate),
                     f"2024-01-{due_day:02d}", due_day, "ACTIVE"))
        p = Decimal(principal)
        monthly_principal = money(p / TERM_MONTHS)
        for month, inst_no in MONTHS:
            due = f"2026-{month:02d}-{due_day:02d}"
            opening = p - monthly_principal * (inst_no - 1)
            if product == "HL-VAR" and month == 9:
                # Planted defect: the system stored the rate-change delta, not the new-rate interest.
                interest = money(opening * (NEW_VAR_RATE - OLD_VAR_RATE) / 1200)
            elif product == "HL-VAR":
                interest = money(opening * OLD_VAR_RATE / 1200)
            else:
                interest = money(opening * FIX_RATE / 1200)
            unpaid = (loan_id, month) in UNPAID or due >= RUN_DATE
            fee, fee_date = LATE_FEES.get((loan_id, month), ("0", None))
            con.execute("INSERT INTO installments VALUES (?,?,?,?,?,?,?,?,?)",
                        (loan_id, inst_no, due, float(opening), float(monthly_principal),
                         float(interest), None if unpaid else due, float(fee), fee_date))

    steps = ["DUE_POSTING", "INTEREST_ACCRUAL", "LATE_FEE", "GL_POSTING", "DAY_CLOSE"]
    for day in range(26, 31):
        run_date = f"2026-09-{day:02d}"
        failed = run_date == RUN_DATE
        for seq, step in enumerate(steps, start=1):
            if not failed:
                status, msg = "OK", None
            elif step == "DUE_POSTING":
                status, msg = "OK", None
            elif step == "INTEREST_ACCRUAL":
                status, msg = "FAILED", "Negative accrual amount; 3 accounts rejected; step aborted"
            else:
                status, msg = "SKIPPED", "Previous step failed"
            con.execute("INSERT INTO eod_process_log VALUES (?,?,?,?,?)", (run_date, seq, step, status, msg))
    con.commit()
    con.close()
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="sample/bank_lms.db")
    a = ap.parse_args()
    print("wrote", build(Path(a.out)))


if __name__ == "__main__":
    main()
