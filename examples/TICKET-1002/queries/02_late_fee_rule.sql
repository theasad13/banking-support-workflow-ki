-- TICKET-1002 step 2: the late-fee rule configured for the loan's product.
SELECT s.product_code, s.setting_name, s.setting_value, s.effective_from
FROM product_settings s
JOIN loans l ON l.product_code = s.product_code
WHERE l.loan_id = 'L-1007' AND s.setting_name LIKE 'LATE_FEE%'
ORDER BY s.setting_name;
