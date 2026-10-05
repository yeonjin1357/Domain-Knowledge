SELECT statement_timestamp() AS observed_at, datname, datfrozenxid::text,
       age(datfrozenxid) AS datfrozenxid_age
FROM pg_database ORDER BY datname;

SELECT statement_timestamp() AS observed_at, pid, application_name, state,
       backend_xid::text, backend_xmin::text, wait_event_type, wait_event
FROM pg_stat_activity WHERE datname=current_database() ORDER BY pid;

SELECT statement_timestamp() AS observed_at, transaction::text, gid, prepared, owner, database
FROM pg_prepared_xacts ORDER BY gid;

SELECT statement_timestamp() AS observed_at, slot_name, slot_type, plugin, active,
       xmin::text, catalog_xmin::text, restart_lsn::text, confirmed_flush_lsn::text, wal_status
FROM pg_replication_slots ORDER BY slot_name;

SELECT statement_timestamp() AS observed_at, pid, application_name, state,
       backend_xmin::text, sent_lsn::text, write_lsn::text, flush_lsn::text, replay_lsn::text
FROM pg_stat_replication ORDER BY application_name;

SELECT statement_timestamp() AS observed_at, s.schemaname, s.relname, s.n_live_tup,
       s.n_dead_tup, s.last_vacuum, c.relfrozenxid::text, age(c.relfrozenxid) AS relfrozenxid_age
FROM pg_stat_all_tables s JOIN pg_class c ON c.oid=s.relid
WHERE (s.schemaname='public' AND s.relname LIKE 'r2_%')
   OR (s.schemaname='pg_catalog' AND s.relname='pg_class')
ORDER BY s.schemaname, s.relname;
