-- PROPOSED_FIX for TICKET-XXXX. NOT EXECUTED.
-- Table: <table>. Keys: <key columns>. Columns changed: <columns>.
-- Expected rows changed: <N>
-- Steps: review -> run on a test copy -> record approval in CHANGE_LOG.md -> run for real.
-- Tip: build this file from a CSV with tools/csv_to_sql_changes.py instead of by hand.

-- @section backup
CREATE TABLE bak_TICKET_XXXX_<table> AS SELECT * FROM <table> WHERE <same filter as the change>;
-- Check: SELECT COUNT(*) FROM bak_TICKET_XXXX_<table>;  -- must be <N>

-- @section change
UPDATE <table> SET <column> = <new value> WHERE <key column> = <key value>;

-- @section guard
-- The result must be exactly <N>. If not, do not commit: run the rollback section.
SELECT COUNT(*) AS changed_rows FROM <table> WHERE <key filter> AND <column> = <new value>;

-- @section rollback
UPDATE <table> SET <column> = (SELECT b.<column> FROM bak_TICKET_XXXX_<table> b WHERE b.<key> = <table>.<key>)
WHERE EXISTS (SELECT 1 FROM bak_TICKET_XXXX_<table> b WHERE b.<key> = <table>.<key>);
