-- TICKET-1002 step 1: the installment the branch is asking about, with days overdue on 30 Sep.
SELECT i.loan_id, l.product_code, i.inst_no, i.due_date, i.paid_date, i.late_fee, i.late_fee_date,
       CASE WHEN i.paid_date IS NULL
            THEN CAST(julianday('2026-09-30') - julianday(i.due_date) AS INTEGER) END AS days_overdue
FROM installments i
JOIN loans l ON l.loan_id = i.loan_id
WHERE i.loan_id = 'L-1007'
ORDER BY i.inst_no;
