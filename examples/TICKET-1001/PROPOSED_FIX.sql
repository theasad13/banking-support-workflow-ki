-- PROPOSED_FIX for TICKET-1001: generated 2026-10-28 16:13. NOT EXECUTED.
-- Table: installments. Keys: loan_id, inst_no. Columns changed: interest_amount.
-- Expected rows changed: 3
-- Steps: review -> run on a test copy -> record approval in CHANGE_LOG.md -> run for real.

-- @section backup
DROP TABLE IF EXISTS bak_TICKET_1001_installments;
CREATE TABLE bak_TICKET_1001_installments AS SELECT * FROM installments WHERE (loan_id = 'L-1004' AND inst_no = 33) OR (loan_id = 'L-1006' AND inst_no = 33) OR (loan_id = 'L-1008' AND inst_no = 33);
-- Check: SELECT COUNT(*) FROM bak_TICKET_1001_installments;  -- must be 3

-- @section change
UPDATE installments SET interest_amount = 16611.11 WHERE loan_id = 'L-1004' AND inst_no = 33;
UPDATE installments SET interest_amount = 29900.00 WHERE loan_id = 'L-1006' AND inst_no = 33;
UPDATE installments SET interest_amount = 12458.33 WHERE loan_id = 'L-1008' AND inst_no = 33;

-- @section guard
-- The result must be exactly 3. If not, do not commit: run the rollback section.
SELECT COUNT(*) AS changed_rows FROM installments WHERE (loan_id = 'L-1004' AND inst_no = 33 AND interest_amount = 16611.11) OR (loan_id = 'L-1006' AND inst_no = 33 AND interest_amount = 29900.00) OR (loan_id = 'L-1008' AND inst_no = 33 AND interest_amount = 12458.33);

-- @section rollback
-- Restores the values saved in bak_TICKET_1001_installments. Keep the backup table until the fix is signed off.
UPDATE installments SET interest_amount = (SELECT b.interest_amount FROM bak_TICKET_1001_installments b WHERE b.loan_id = installments.loan_id AND b.inst_no = installments.inst_no) WHERE EXISTS (SELECT 1 FROM bak_TICKET_1001_installments b WHERE b.loan_id = installments.loan_id AND b.inst_no = installments.inst_no);
