-- TICKET-1001 step 1: which EOD step failed on 30 Sep, and what ran after it?
SELECT run_date, seq, step, status, message
FROM eod_process_log
WHERE run_date = '2026-09-30'
ORDER BY seq;
