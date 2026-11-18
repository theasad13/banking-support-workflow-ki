-- TICKET-1002 step 3: is the late-fee rule working at all? Every unpaid installment
-- before 30 Sep, its days overdue, and whether a fee was charged.
SELECT i.loan_id, i.due_date,
       CAST(julianday('2026-09-30') - julianday(i.due_date) AS INTEGER) AS days_overdue,
       i.late_fee, i.late_fee_date
FROM installments i
WHERE i.paid_date IS NULL AND i.due_date < '2026-09-30'
ORDER BY days_overdue DESC;
