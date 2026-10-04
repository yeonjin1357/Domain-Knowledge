BEGIN READ ONLY;
SET LOCAL statement_timeout = '2s';
SELECT current_setting('server_version_num')::integer AS server_version_num;
SELECT clock_timestamp() AS collected_at,
       datid, datname, xact_commit, xact_rollback,
       blks_read, blks_hit, stats_reset
FROM pg_stat_database
WHERE datid <> 0;
COMMIT;
