-- TICKET-1001 step 4: rule out configuration. Is the rate change approved, and do the
-- product's GL mappings point to GL accounts that exist?
SELECT 'audit' AS check_type, product_code, setting_name AS item,
       old_value || ' -> ' || new_value AS detail,
       CASE WHEN approved_by IS NOT NULL THEN 'approved by ' || approved_by ELSE 'NOT APPROVED' END AS result
FROM settings_audit
WHERE product_code = 'HL-VAR'
UNION ALL
SELECT 'gl_mapping', s.product_code, s.setting_name, s.setting_value,
       CASE WHEN g.gl_code IS NOT NULL THEN 'GL exists' ELSE 'GL MISSING' END
FROM product_settings s
LEFT JOIN gl_accounts g ON g.gl_code = s.setting_value
WHERE s.product_code = 'HL-VAR' AND s.setting_name LIKE '%_GL';
