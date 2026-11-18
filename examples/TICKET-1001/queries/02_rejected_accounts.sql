-- TICKET-1001 step 2: installments due on the EOD date with a negative interest amount.
SELECT i.loan_id, l.product_code, l.branch_code, i.inst_no, i.due_date,
       i.opening_principal, i.interest_amount
FROM installments i
JOIN loans l ON l.loan_id = i.loan_id
WHERE i.due_date = '2026-09-30' AND i.interest_amount < 0
ORDER BY i.loan_id;
