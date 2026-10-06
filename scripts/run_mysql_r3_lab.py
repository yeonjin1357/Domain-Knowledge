"""Two owned MySQL instances: RR locks, deadlock, GTID stop states, default settings.

Uses only the authenticated distribution's mysql CLI (XML preserves SQL NULL).
All SQL is confined to newly initialized private datadirs. No crash/power-loss test.
"""
import argparse
import os
from pathlib import Path
import re
import select
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET

from lab_r3_common import (LabRun, RAW_LIMIT, checked_asset, free_ports, linux_required,
                           scenario, sha256, stamp)
from run_linux_memory_r3_lab import memory_guard
from prepare_mysql_r3_runtime import checked_runtime


def parse_xml(text):
    results = []
    for block in re.findall(r'<resultset\b.*?</resultset>', text, flags=re.S):
        tree = ET.fromstring(block)
        rows = []
        for row in tree.findall('row'):
            rows.append({field.attrib['name']: None if field.attrib.get(
                '{http://www.w3.org/2001/XMLSchema-instance}nil') == 'true'
                else (field.text or '') for field in row.findall('field')})
        if rows and 'r3_marker' in rows[0]:
            continue
        results.append({'statement': tree.attrib.get('statement'), 'rows': rows})
    return results


class Session:
    def __init__(self, server):
        self.server, self.run = server, server.run
        self.number = len(server.sessions)
        server.sessions.append(self)
        self.name = f'{server.name}-client-{self.number}'
        self.stderr = self.run.workspace/(self.name+'.stderr')
        handle = self.stderr.open('wb')
        self.process = subprocess.Popen([
            str(server.base/'bin/mysql'), '--no-defaults', '--no-login-paths',
            '--protocol=SOCKET', '--socket='+str(server.socket), '--user=root',
            '--connect-timeout=3', '--xml', '--unbuffered', '--force', '--binary-mode'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=handle, bufsize=0,
            env=self.run.environment(server.client_env), cwd=self.run.workspace, start_new_session=True)
        self.run.processes.append(self.process)
        self.run.logs.append((self.name, self.stderr, handle))
        self.pending = None
        self.query_number = 0
        identity = self.query('SELECT @@datadir AS datadir, @@server_uuid AS uuid, CONNECTION_ID() AS id')
        if Path(identity[0]['datadir']).resolve() != server.data.resolve():
            raise RuntimeError('Refusing a connection to any other datadir')
        self.connection_id = int(identity[0]['id'])
        self.query("SET SESSION time_zone='+00:00'; SET SESSION innodb_lock_wait_timeout=12")

    def send(self, sql):
        if self.pending is not None:
            raise RuntimeError('A query is already pending')
        self.query_number += 1
        marker = 'r3_done_'+uuid.uuid4().hex
        self.pending = (sql, marker, self.stderr.stat().st_size, stamp())
        self.process.stdin.write((sql.rstrip(';')+f";\nSELECT '{marker}' AS r3_marker;\n").encode())

    def finish(self, allow_error=False, timeout=20):
        sql, marker, offset, started = self.pending
        marker_xml = f'<field name="r3_marker">{marker}</field>'.encode()
        deadline, raw = time.monotonic()+timeout, bytearray()
        try:
            while True:
                if time.monotonic() >= deadline:
                    raise TimeoutError('mysql client response timed out')
                if not select.select([self.process.stdout], [], [], .2)[0]:
                    continue
                chunk = os.read(self.process.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError('mysql client exited: '+self.stderr.read_text(errors='replace'))
                raw.extend(chunk)
                if len(raw) > RAW_LIMIT:
                    raise ValueError('mysql response exceeds evidence budget')
                found = raw.find(marker_xml)
                if found >= 0 and b'</resultset>' in raw[found:]:
                    break
        except BaseException:
            if raw:
                self.run.artifact(f'{self.name}-{self.query_number}-incomplete', bytes(raw))
            raise
        finally:
            self.pending = None
        errors = self.stderr.read_bytes()[offset:].decode('utf-8', 'replace')
        codes = [int(s) for s in re.findall(r'ERROR (\d+)', errors)]
        name = f'{self.name}-{self.query_number}'
        result = {'started': started, 'finished': stamp(), 'sql': sql,
                  'xml_artifact': self.run.artifact(name+'.xml', bytes(raw), 'application/xml'),
                  'errors': errors, 'error_codes': codes, 'results': parse_xml(raw.decode('utf-8'))}
        self.run.record.setdefault('sql_queries', {})[name] = result
        self.last_query = name
        if codes and not allow_error:
            raise RuntimeError(f'{name}: {errors}')
        return result

    def query(self, sql):
        self.send(sql)
        result = self.finish()
        return result['results'][-1]['rows'] if result['results'] else []

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.run.stop(self.process)
        self.process.stdout.close()


class Server:
    def __init__(self, run, base, version, number, port, root):
        self.run, self.base = run, base
        self.name = version+'-'+str(number)
        self.data = root/('d'+str(number))
        self.socket = root/(str(number)+'.sock')
        self.port, self.sessions = port, []
        private, _ = checked_runtime()
        self.client_env = {'LD_LIBRARY_PATH': str(base/'lib/private')+':'+str(base/'lib')}
        self.env = {'LD_LIBRARY_PATH': str(private)+':'+self.client_env['LD_LIBRARY_PATH']}
        self.data.mkdir(mode=0o700)
        init = run.command([base/'bin/mysqld', '--no-defaults', '--initialize-insecure',
                            '--basedir='+str(base), '--datadir='+str(self.data),
                            '--innodb-buffer-pool-size=64M'], timeout=120, env=self.env)
        if init['returncode']:
            raise RuntimeError('initdb failed; see '+init['artifact'])
        args = [base/'bin/mysqld', '--no-defaults', '--basedir='+str(base),
                '--datadir='+str(self.data), '--socket='+str(self.socket), '--port='+str(port),
                '--bind-address=127.0.0.1', '--mysqlx=OFF', '--skip-name-resolve',
                '--pid-file='+str(root/(str(number)+'.pid')), '--secure-file-priv='+str(root),
                '--tmpdir='+str(root), '--server-id='+str(number), '--gtid-mode=ON',
                '--enforce-gtid-consistency=ON', '--log-bin='+str(self.data/'binlog'),
                '--relay-log='+str(self.data/'relay'), '--skip-replica-start',
                '--replica-parallel-workers=2', '--innodb-buffer-pool-size=64M',
                '--innodb-redo-log-capacity=32M', '--max-connections=16', '--table-open-cache=128',
                '--performance-schema=ON']
        run.record.setdefault('servers', {})[self.name] = {'argv': list(map(str, args)),
                                                         'data_directory': str(self.data)}
        self.process = run.launch(self.name, args, env=self.env)
        deadline = time.monotonic()+45
        while not self.socket.exists():
            if self.process.poll() is not None:
                raise RuntimeError('mysqld exited before socket creation')
            if time.monotonic() >= deadline:
                raise TimeoutError('mysqld socket readiness timed out')
            time.sleep(.1)
        self.admin = Session(self)

    def close(self):
        for session in reversed(self.sessions):
            session.close()
        self.run.stop(self.process)


def wait_until(fn, predicate, seconds=8):
    deadline = time.monotonic()+seconds
    while True:
        value = fn()
        if predicate(value):
            return value
        if time.monotonic() >= deadline:
            raise TimeoutError('Observation precondition did not occur')
        time.sleep(.1)


def matching_sys_wait(rows, waiter, blocker):
    return any(str(row.get('waiting_pid')) == str(waiter) and
               str(row.get('blocking_pid')) == str(blocker) for row in rows)


def matching_lock_edge(rows, waits, gap):
    """Join exact engine lock IDs; never mistake REC_NOT_GAP for GAP."""
    indexed = {(r.get('ENGINE'), r.get('ENGINE_LOCK_ID')): r for r in rows}
    for edge in waits:
        request = indexed.get((edge.get('ENGINE'), edge.get('REQUESTING_ENGINE_LOCK_ID')), {})
        holder = indexed.get((edge.get('ENGINE'), edge.get('BLOCKING_ENGINE_LOCK_ID')), {})
        if not all(r.get('OBJECT_SCHEMA') == 'r3' and r.get('OBJECT_NAME') == 't' and
                   r.get('INDEX_NAME') == 'k' and r.get('LOCK_TYPE') == 'RECORD'
                   for r in (request, holder)):
            continue
        mode = set(holder.get('LOCK_MODE', '').split(','))
        expected_holder = ('GAP' in mode and 'INSERT_INTENTION' not in mode) if gap else mode == {'X'}
        if (request.get('LOCK_STATUS') == 'WAITING' and
                'INSERT_INTENTION' in request.get('LOCK_MODE', '').split(',') and
                holder.get('LOCK_STATUS') == 'GRANTED' and expected_holder):
            return True
    return False


def sys_visibility(admin, waiter, blocker, rows, query_ref):
    """INNODB_TRX cache needs >100 ms idle in the pinned sources.

    Keep the transactions blocked, preserve every attempted query, and allow
    200 ms between attempts. A missing materialized view is not a missing lock.
    """
    refs, trx_refs = [query_ref], []
    for attempt in range(21):
        admin.query('SELECT trx_id,trx_mysql_thread_id,trx_state,trx_started,trx_wait_started '
                    'FROM information_schema.innodb_trx '
                    f'WHERE trx_mysql_thread_id IN ({waiter},{blocker})')
        trx_refs.append(admin.last_query)
        if matching_sys_wait(rows, waiter, blocker) or attempt == 20:
            break
        time.sleep(.2)
        rows = admin.query('SELECT * FROM sys.innodb_lock_waits '
                           f'WHERE waiting_pid={waiter} AND blocking_pid={blocker}')
        refs.append(admin.last_query)
    return {'query_refs': refs, 'trx_query_refs': trx_refs,
            'matched': matching_sys_wait(rows, waiter, blocker), 'last_rows': rows,
            'retry_interval_seconds': .2, 'max_retries': 20}


def locks(server, gap):
    run, admin = server.run, server.admin
    a, b = Session(server), Session(server)
    name = 'gap_lock' if gap else 'next_key_lock'
    for client in (a, b):
        client.query('SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ; START TRANSACTION')
    predicate = 'k=15' if gap else 'k>=10 AND k<20'
    held = a.query('SELECT * FROM r3.t FORCE INDEX(k) WHERE '+predicate+' FOR UPDATE')
    b.send('INSERT INTO r3.t VALUES (3,15,0)')
    wait_until(lambda: admin.query('SELECT * FROM performance_schema.data_lock_waits'), bool)
    rows = admin.query("SELECT * FROM performance_schema.data_locks WHERE OBJECT_SCHEMA='r3'")
    rows_ref = admin.last_query
    waits = admin.query('SELECT * FROM performance_schema.data_lock_waits')
    waits_ref = admin.last_query
    sys_waits = admin.query('SELECT * FROM sys.innodb_lock_waits')
    sys_ref = admin.last_query
    initial_refs = [rows_ref, waits_ref, sys_ref]
    visibility = sys_visibility(admin, b.connection_id, a.connection_id, sys_waits, sys_ref)
    sys_waits, sys_ref = visibility['last_rows'], visibility['query_refs'][-1]
    # Sample direct lock tables again while the same owner still holds the lock.
    rows = admin.query("SELECT * FROM performance_schema.data_locks WHERE OBJECT_SCHEMA='r3'")
    rows_ref = admin.last_query
    waits = admin.query('SELECT * FROM performance_schema.data_lock_waits')
    waits_ref = admin.last_query
    a.query('ROLLBACK')
    release_ref = a.last_query
    insertion = b.finish()
    insertion_ref = b.last_query
    visible = b.query('SELECT id,k,v FROM r3.t WHERE id=3')
    visible_ref = b.last_query
    b.query('ROLLBACK')
    rollback_ref = b.last_query
    a.close()
    b.close()
    direct = matching_lock_edge(rows, waits, gap)
    inserted = not insertion['error_codes'] and visible == [{'id': '3', 'k': '15', 'v': '0'}]
    conditions = {'matching_direct_lock_edge': direct, 'matching_sys_wait': visibility['matched'],
                  'insert_visible_after_release': inserted}
    verdict = ('supported' if all(conditions.values()) else 'inconclusive'
               if direct and inserted and not visibility['matched'] else 'refuted')
    return scenario('RR '+name+' blocks an insert in the selected gap',
                    'Matching granted RECORD lock and waiting INSERT_INTENTION edge; sys joins the same sessions after bounded visibility polling; rollback releases a visible insert',
                    'Matching direct lock edge or successful insert after release is absent; unresolved sys visibility alone is inconclusive',
                    {'selected_rows': held, 'lock_rows': rows, 'wait_rows': waits, 'sys_rows': sys_waits,
                     'observed_lock_modes': sorted({r['LOCK_MODE'] for r in rows}),
                     'record_lock_modes': sorted({r['LOCK_MODE'] for r in rows if r['LOCK_TYPE'] == 'RECORD'}),
                     'lock_mode_scope': 'Exact engine strings; X means next-key only in RECORD/index context, not for a TABLE lock',
                     'initial_query_refs': initial_refs, 'sys_visibility': visibility,
                     'release_query_refs': [release_ref, insertion_ref, visible_ref, rollback_ref],
                     'conditions': conditions,
                     'query_refs': [rows_ref, waits_ref, sys_ref], 'waiter_connection_id': b.connection_id,
                     'blocker_connection_id': a.connection_id}, verdict,
                    'Separate direct lock evidence from cached INNODB_TRX/sys visibility; no production query-plan guarantee')


def deadlock(server):
    admin = server.admin
    a, b = Session(server), Session(server)
    a.query('START TRANSACTION; UPDATE r3.t SET v=v+1 WHERE id=1')
    b.query('START TRANSACTION; UPDATE r3.t SET v=v+1 WHERE id=2')
    a.send('UPDATE r3.t SET v=v+1 WHERE id=2')
    wait_until(lambda: admin.query('SELECT * FROM performance_schema.data_lock_waits'), bool)
    b.send('UPDATE r3.t SET v=v+1 WHERE id=1')
    # InnoDB rolls one victim back; both pending queries can then complete.
    first, second = a.finish(allow_error=True), b.finish(allow_error=True)
    codes = first['error_codes']+second['error_codes']
    engine = admin.query('SHOW ENGINE INNODB STATUS')
    engine_ref = admin.last_query
    for client in (a, b):
        client.query('ROLLBACK')
        client.close()
    return scenario('InnoDB detects the constructed two-transaction wait cycle',
                    'Exactly one ERROR 1213 and a latest detected deadlock in engine status',
                    'The cycle completes with a different error or no deadlock evidence',
                    {'error_codes': codes, 'first_query': first, 'second_query': second,
                     'engine_status_query': engine_ref},
                    'supported' if codes == [1213] and any('LATEST DETECTED DEADLOCK' in str(row) for row in engine) else 'refuted',
                    'Victim identity is deliberately not assumed')


def replication_snapshot(source, replica):
    admin = replica.admin
    status = admin.query('SHOW REPLICA STATUS')
    status_ref = admin.last_query
    workers = admin.query('SELECT * FROM performance_schema.replication_applier_status_by_worker')
    workers_ref = admin.last_query
    connection = admin.query('SELECT * FROM performance_schema.replication_connection_status')
    connection_ref = admin.last_query
    source_gtid = source.admin.query('SELECT @@GLOBAL.gtid_executed AS gtid')[0]['gtid']
    source_gtid_ref = source.admin.last_query
    replica_gtid = admin.query('SELECT @@GLOBAL.gtid_executed AS gtid')[0]['gtid']
    replica_gtid_ref = admin.last_query
    return {'sampled': stamp(), 'status': status, 'workers': workers, 'connection': connection,
            'source_gtid_executed': source_gtid, 'replica_gtid_executed': replica_gtid,
            'gtid_query_refs': [source_gtid_ref, replica_gtid_ref],
            'query_refs': [status_ref, workers_ref, connection_ref],
            'value_contract': 'XML SQL NULL is JSON null; zero timestamps and numeric 0 remain strings; sequential snapshots'}


def catch_up(source, replica):
    gtid = source.admin.query('SELECT @@GLOBAL.gtid_executed AS gtid')[0]['gtid']
    source_ref = source.admin.last_query
    rows = replica.admin.query(f"SELECT WAIT_FOR_EXECUTED_GTID_SET('{gtid}',8) AS caught")
    if rows[0]['caught'] != '0':
        raise TimeoutError('GTID catch-up did not complete')
    return {'target_gtid': gtid, 'source_query_ref': source_ref,
            'wait_query_ref': replica.admin.last_query, 'result': rows[0]['caught'],
            'scope': 'Target GTID execution barrier; not a coordinator position or SBS barrier'}


def coordinator_positions_equal(status):
    name = status.get('Source_Log_File')
    return bool(name and name != 'INVALID' and name == status.get('Relay_Source_Log_File') and
                str(status.get('Read_Source_Log_Pos', '')).isdigit() and
                int(status['Read_Source_Log_Pos']) > 0 and
                status['Read_Source_Log_Pos'] == status.get('Exec_Source_Log_Pos'))


def checkpoint_visibility(replica, io_running):
    """Poll positions/thread states, never poll for the expected SBS value."""
    refs = []
    reached = False
    for attempt in range(25):
        rows = replica.admin.query('SHOW REPLICA STATUS')
        refs.append(replica.admin.last_query)
        reached = bool(rows and coordinator_positions_equal(rows[0]) and
                       rows[0]['Replica_SQL_Running'] == 'Yes' and
                       rows[0]['Replica_IO_Running'] == io_running)
        if reached or attempt == 24:
            break
        time.sleep(.2)
    return {'query_refs': refs, 'matched': reached, 'io_running': io_running,
            'retry_interval_seconds': .2, 'max_retries': 24,
            'predicate': 'Valid matching source/group log file+position; SQL Yes; expected IO state; SBS is not a prerequisite'}


def replication(source, replica):
    admin = replica.admin
    variables = admin.query("SHOW GLOBAL VARIABLES WHERE Variable_name IN "
                            "('replica_parallel_workers','replica_checkpoint_period',"
                            "'replica_checkpoint_group','replica_preserve_commit_order')")
    variables_ref = admin.last_query
    source.admin.query("SET sql_log_bin=0; CREATE USER 'r3_repl'@'127.0.0.1' IDENTIFIED BY 'local-r3-only'; "
                       "GRANT REPLICATION SLAVE ON *.* TO 'r3_repl'@'127.0.0.1'; SET sql_log_bin=1")
    admin.query(f"CHANGE REPLICATION SOURCE TO SOURCE_HOST='127.0.0.1', SOURCE_PORT={source.port}, "
                "SOURCE_USER='r3_repl', SOURCE_PASSWORD='local-r3-only', SOURCE_AUTO_POSITION=1, GET_SOURCE_PUBLIC_KEY=1; START REPLICA")
    initial_barrier = catch_up(source, replica)
    wait_until(lambda: admin.query('SHOW REPLICA STATUS'), lambda r: r and
               r[0]['Replica_IO_Running'] == 'Yes' and r[0]['Replica_SQL_Running'] == 'Yes')
    baseline_immediate = replication_snapshot(source, replica)
    baseline_checkpoint = checkpoint_visibility(replica, 'Yes')
    baseline = replication_snapshot(source, replica)
    admin.query('STOP REPLICA IO_THREAD')
    source.admin.query('INSERT INTO r3.repl VALUES (1)')
    wait_until(lambda: admin.query('SHOW REPLICA STATUS'), lambda r: r[0]['Replica_IO_Running'] == 'No')
    io_stopped_immediate = replication_snapshot(source, replica)
    io_checkpoint = checkpoint_visibility(replica, 'No')
    io_stopped = replication_snapshot(source, replica)
    admin.query('START REPLICA IO_THREAD')
    after_io_barrier = catch_up(source, replica)
    admin.query('STOP REPLICA SQL_THREAD')
    source.admin.query('INSERT INTO r3.repl VALUES (2)')
    gtid = source.admin.query('SELECT @@GLOBAL.gtid_executed AS gtid')[0]['gtid']
    received_target_ref = source.admin.last_query
    received_rows = wait_until(lambda: admin.query(f"SELECT GTID_SUBSET('{gtid}', RECEIVED_TRANSACTION_SET) AS received "
                                   'FROM performance_schema.replication_connection_status'),
               lambda r: r and r[0]['received'] == '1')
    received_ref = admin.last_query
    sql_stopped = replication_snapshot(source, replica)
    admin.query('START REPLICA SQL_THREAD')
    resumed_barrier = catch_up(source, replica)
    resumed_immediate = replication_snapshot(source, replica)
    resumed_checkpoint = checkpoint_visibility(replica, 'Yes')
    resumed = replication_snapshot(source, replica)
    def status(s):
        return s['status'][0]
    positions_ready = (all(p['matched'] for p in (baseline_checkpoint, io_checkpoint, resumed_checkpoint)) and
                       all(coordinator_positions_equal(status(s)) for s in (baseline, io_stopped, resumed)))
    conditions = {
        'baseline_gtid_caught': baseline['source_gtid_executed'] == baseline['replica_gtid_executed'],
        'baseline_zero_after_positions': status(baseline)['Seconds_Behind_Source'] == '0',
        'io_stopped_null_after_positions': status(io_stopped)['Seconds_Behind_Source'] is None,
        'io_stopped_threads': status(io_stopped)['Replica_IO_Running'] == 'No' and status(io_stopped)['Replica_SQL_Running'] == 'Yes',
        'sql_stopped_null': status(sql_stopped)['Seconds_Behind_Source'] is None,
        'sql_stopped_threads': status(sql_stopped)['Replica_IO_Running'] == 'Yes' and status(sql_stopped)['Replica_SQL_Running'] == 'No',
        'io_stopped_gtid_pending': io_stopped['source_gtid_executed'] != io_stopped['replica_gtid_executed'],
        'sql_stopped_gtid_pending': sql_stopped['source_gtid_executed'] != sql_stopped['replica_gtid_executed'],
        'sql_stopped_target_received': received_rows[0]['received'] == '1',
        'resumed_gtid_caught': resumed['source_gtid_executed'] == resumed['replica_gtid_executed'],
        'resumed_zero_after_positions': status(resumed)['Seconds_Behind_Source'] == '0'}
    return scenario('GTID execution and coordinator checkpoint are separate; SBS stop-state rules are checked after position convergence',
                    'Independent file/position gates reached; baseline/resume SBS 0; IO-stop SBS NULL with applied received GTIDs; SQL-stop NULL with received pending GTID',
                    'After independent position gates, a state/value/GTID condition differs; unavailable checkpoint convergence is inconclusive',
                    {'baseline': baseline, 'io_stopped': io_stopped, 'sql_stopped': sql_stopped, 'resumed': resumed,
                     'immediate_after_gtid_or_stop': {'baseline': baseline_immediate, 'io_stopped': io_stopped_immediate, 'resumed': resumed_immediate},
                     'checkpoint_visibility': {'baseline': baseline_checkpoint, 'io_stopped': io_checkpoint, 'resumed': resumed_checkpoint},
                     'gtid_barriers': [initial_barrier, after_io_barrier, resumed_barrier],
                     'receive_barrier': {'target_gtid': gtid, 'source_query_ref': received_target_ref,
                                         'query_ref': received_ref, 'rows': received_rows},
                     'variables': variables, 'variables_query_ref': variables_ref,
                     'position_preconditions_met': positions_ready, 'conditions': conditions},
                    'inconclusive' if not positions_ready else 'supported' if all(conditions.values()) else 'refuted',
                    'Immediate observations are retained regardless of SBS; no clock_diff_with_master or external-clock calibration claim')


def version_lab(run, version):
    asset, base, receipt = checked_asset('mysql-'+version)
    private, runtime = checked_runtime()
    client_env = {'LD_LIBRARY_PATH': str(base/'lib/private')+':'+str(base/'lib')}
    env = {'LD_LIBRARY_PATH': str(private)+':'+client_env['LD_LIBRARY_PATH']}
    run.record['private_runtime'] = {'directory': str(private), 'receipt': runtime,
                                    'mysqld_environment': env, 'client_environment': client_env}
    preflight = []
    for name in ('mysqld', 'mysql'):
        try:
            binary_env = env if name == 'mysqld' else client_env
            preflight.append(run.command([base/'bin'/name, '--no-defaults', '--version'], env=binary_env))
            # Official, hash-verified binaries only. Keep the actual loader paths in gzip evidence.
            run.command(['ldd', base/'bin'/name], env=binary_env)
        except OSError as error:
            preflight.append({'returncode': None, 'launch_error': repr(error), 'binary': name})
    guard = memory_guard(1024*1024*1024)
    if any(v['returncode'] != 0 for v in preflight) or not guard['allowed']:
        run.record['scenarios'][version+'/preflight'] = scenario('Authenticated binaries can run with available dependencies/headroom',
            'Both version commands succeed and >=1 GiB visible headroom', 'Dependency/headroom unavailable',
            {'commands': preflight, 'guard': guard}, 'blocked', 'No system package installation or alternative binary')
        return
    run.record.setdefault('assets', {})[version] = {'archive_sha256': asset['sha256'],
        'mysqld_sha256': sha256(base/'bin/mysqld'), 'mysql_sha256': sha256(base/'bin/mysql'), 'guard': guard}
    root = run.native_directory('dk-r3-', 'Private MySQL datadirs and Unix sockets need POSIX modes and short paths')
    source, replica = None, None
    ports = free_ports(2)
    try:
        source = Server(run, base, version, 1, ports[0], root)
        values = source.admin.query('SELECT @@version AS version, @@innodb_flush_log_at_trx_commit AS innodb_flush_log_at_trx_commit, '
            '@@sync_binlog AS sync_binlog, @@innodb_deadlock_detect AS innodb_deadlock_detect, '
            '@@transaction_isolation AS transaction_isolation, @@performance_schema AS performance_schema')
        run.record['scenarios'][version+'/defaults'] = scenario('Pinned local MySQL reports default durability controls',
            'Unmodified innodb_flush_log_at_trx_commit=1 and sync_binlog=1', 'Either default differs',
            {'rows': values, 'query_ref': source.admin.last_query},
            'supported' if values[0]['innodb_flush_log_at_trx_commit'] == values[0]['sync_binlog'] == '1' else 'refuted',
            'Configuration observation only; no persistence, power loss, fsync, or replication durability claim')
        source.admin.query('CREATE DATABASE r3; CREATE TABLE r3.t(id INT PRIMARY KEY, k INT, v INT, KEY k(k)) ENGINE=InnoDB; '
                           'INSERT INTO r3.t VALUES(1,10,0),(2,20,0); CREATE TABLE r3.repl(id INT PRIMARY KEY) ENGINE=InnoDB')
        for gap in (True, False):
            run.record['scenarios'][version+('/gap_lock' if gap else '/next_key_lock')] = locks(source, gap)
        run.record['scenarios'][version+'/deadlock'] = deadlock(source)
        replica = Server(run, base, version, 2, ports[1], root)
        run.record['scenarios'][version+'/replication'] = replication(source, replica)
    finally:
        # The outer LabRun also owns partially constructed servers/clients.
        if replica is not None:
            replica.close()
        if source is not None:
            source.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--version', choices=('8.4.11', '9.7.2'), required=True)
    args = p.parse_args()
    linux_required()
    with LabRun('mysql-'+args.version, args.output, ['scripts/run_mysql_r3_lab.py',
                'scripts/get_review_r3_assets.py', 'scripts/run_linux_memory_r3_lab.py',
                'scripts/prepare_mysql_r3_runtime.py', 'labs/review-r3/mysql-runtime.json',
                'labs/postgresql/packages.json']) as run:
        run.record['mysql_observation_revision'] = 2
        version_lab(run, args.version)
    raise SystemExit(run.exit_code)


if __name__ == '__main__':
    main()
