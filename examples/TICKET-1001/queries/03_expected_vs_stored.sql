-- TICKET-1001 step 3: compare the stored interest with (a) interest at the new rate
-- and (b) the rate-change delta, using the old and new rate from the settings audit.
WITH rate_change AS (
    SELECT product_code, CAST(old_value AS REAL) AS old_rate, CAST(new_value AS REAL) AS new_rate
    FROM settings_audit
    WHERE setting_name = 'BASE_RATE' AND changed_at >= '2026-09-01'
)
SELECT i.loan_id, i.inst_no, i.interest_amount AS stored,
       ROUND(i.opening_principal * rc.new_rate / 1200, 2) AS expected_at_new_rate,
       ROUND(i.opening_principal * (rc.new_rate - rc.old_rate) / 1200, 2) AS rate_change_delta,
       CASE WHEN ABS(i.interest_amount - i.opening_principal * (rc.new_rate - rc.old_rate) / 1200) < 0.01
            THEN 'stored = delta' ELSE 'other' END AS finding
FROM installments i
JOIN loans l ON l.loan_id = i.loan_id
JOIN rate_change rc ON rc.product_code = l.product_code
WHERE i.due_date >= '2026-09-01' AND i.due_date <= '2026-09-30'
ORDER BY i.loan_id;
