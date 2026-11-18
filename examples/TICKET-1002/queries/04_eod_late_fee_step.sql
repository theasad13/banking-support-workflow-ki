-- TICKET-1002 step 4: did the LATE_FEE step run on each EOD since the installment fell due?
SELECT run_date, step, status, message
FROM eod_process_log
WHERE step = 'LATE_FEE' AND run_date >= '2026-09-20'
ORDER BY run_date;
