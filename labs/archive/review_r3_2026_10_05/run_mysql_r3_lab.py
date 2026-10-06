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
            env=self.run.environment(server.env), cwd=self.run.workspace, start_new_session=True)
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
        self.env = {'LD_LIBRARY_PATH': str(base/'lib/private')+':'+str(base/'lib')}
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
    a.query('ROLLBACK')
    insertion = b.finish()
    b.query('ROLLBACK')
    a.close()
    b.close()
    waiting = any(r.get('LOCK_STATUS') == 'WAITING' and 'INSERT_INTENTION' in r.get('LOCK_MODE', '') for r in rows)
    blocking = any(r.get('INDEX_NAME') == 'k' and r.get('LOCK_STATUS') == 'GRANTED' and
                   r.get('LOCK_TYPE') == 'RECORD' and
                   (('GAP' in r.get('LOCK_MODE', '') and 'INSERT_INTENTION' not in r.get('LOCK_MODE', '')) if gap
                    else r.get('LOCK_MODE') == 'X') for r in rows)
    ok = bool(waiting and blocking and waits and sys_waits and not insertion['error_codes'])
    return scenario('RR '+name+' blocks an insert in the selected gap',
                    'Granted gap/next-key and waiting INSERT_INTENTION, wait edge, sys row; rollback releases insert',
                    'Complete lock snapshots lack the predicted lock/wait relationship',
                    {'selected_rows': held, 'lock_rows': rows, 'wait_rows': waits, 'sys_rows': sys_waits,
                     'query_refs': [rows_ref, waits_ref, sys_ref], 'waiter_connection_id': b.connection_id,
                     'blocker_connection_id': a.connection_id}, 'supported' if ok else 'refuted',
                    'Forced secondary index and tiny local InnoDB table; not every production query plan')


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
    return {'sampled': stamp(), 'status': status, 'workers': workers, 'connection': connection,
            'source_gtid_executed': source.admin.query('SELECT @@GLOBAL.gtid_executed AS gtid')[0]['gtid'],
            'replica_gtid_executed': admin.query('SELECT @@GLOBAL.gtid_executed AS gtid')[0]['gtid'],
            'query_refs': [status_ref, workers_ref, connection_ref],
            'value_contract': 'XML SQL NULL is JSON null; zero timestamps and numeric 0 remain strings; sequential snapshots'}


def catch_up(source, replica):
    gtid = source.admin.query('SELECT @@GLOBAL.gtid_executed AS gtid')[0]['gtid']
    rows = replica.admin.query(f"SELECT WAIT_FOR_EXECUTED_GTID_SET('{gtid}',8) AS caught")
    if rows[0]['caught'] != '0':
        raise TimeoutError('GTID catch-up did not complete')


def replication(source, replica):
    admin = replica.admin
    source.admin.query("SET sql_log_bin=0; CREATE USER 'r3_repl'@'127.0.0.1' IDENTIFIED BY 'local-r3-only'; "
                       "GRANT REPLICATION SLAVE ON *.* TO 'r3_repl'@'127.0.0.1'; SET sql_log_bin=1")
    admin.query(f"CHANGE REPLICATION SOURCE TO SOURCE_HOST='127.0.0.1', SOURCE_PORT={source.port}, "
                "SOURCE_USER='r3_repl', SOURCE_PASSWORD='local-r3-only', SOURCE_AUTO_POSITION=1, GET_SOURCE_PUBLIC_KEY=1; START REPLICA")
    catch_up(source, replica)
    wait_until(lambda: admin.query('SHOW REPLICA STATUS'), lambda r: r and
               r[0]['Replica_IO_Running'] == 'Yes' and r[0]['Replica_SQL_Running'] == 'Yes')
    baseline = replication_snapshot(source, replica)
    admin.query('STOP REPLICA IO_THREAD')
    source.admin.query('INSERT INTO r3.repl VALUES (1)')
    wait_until(lambda: admin.query('SHOW REPLICA STATUS'), lambda r: r[0]['Replica_IO_Running'] == 'No')
    io_stopped = replication_snapshot(source, replica)
    admin.query('START REPLICA IO_THREAD')
    catch_up(source, replica)
    admin.query('STOP REPLICA SQL_THREAD')
    source.admin.query('INSERT INTO r3.repl VALUES (2)')
    gtid = source.admin.query('SELECT @@GLOBAL.gtid_executed AS gtid')[0]['gtid']
    wait_until(lambda: admin.query(f"SELECT GTID_SUBSET('{gtid}', RECEIVED_TRANSACTION_SET) AS received "
                                   'FROM performance_schema.replication_connection_status'),
               lambda r: r and r[0]['received'] == '1')
    sql_stopped = replication_snapshot(source, replica)
    admin.query('START REPLICA SQL_THREAD')
    catch_up(source, replica)
    resumed = replication_snapshot(source, replica)
    def status(s):
        return s['status'][0]
    ok = (status(baseline)['Seconds_Behind_Source'] == '0'
          and status(io_stopped)['Seconds_Behind_Source'] is None
          and status(io_stopped)['Replica_IO_Running'] == 'No'
          and status(io_stopped)['Replica_SQL_Running'] == 'Yes'
          and status(sql_stopped)['Seconds_Behind_Source'] is None
          and status(sql_stopped)['Replica_IO_Running'] == 'Yes'
          and status(sql_stopped)['Replica_SQL_Running'] == 'No'
          and io_stopped['source_gtid_executed'] != io_stopped['replica_gtid_executed']
          and sql_stopped['source_gtid_executed'] != sql_stopped['replica_gtid_executed']
          and resumed['source_gtid_executed'] == resumed['replica_gtid_executed'])
    return scenario('Caught-up zero differs from unknown lag when receiver/applier is stopped',
                    'Baseline 0; drained IO stop NULL; SQL stop NULL despite received GTID; resume catches up',
                    'Complete snapshots violate one of these state/value/GTID conditions',
                    {'baseline': baseline, 'io_stopped': io_stopped, 'sql_stopped': sql_stopped, 'resumed': resumed},
                    'supported' if ok else 'refuted',
                    'Worker timestamps are captured, including unset values; not a measurement of network lag or durability')


def version_lab(run, version):
    asset, base, receipt = checked_asset('mysql-'+version)
    env = {'LD_LIBRARY_PATH': str(base/'lib/private')+':'+str(base/'lib')}
    preflight = []
    for name in ('mysqld', 'mysql'):
        try:
            preflight.append(run.command([base/'bin'/name, '--no-defaults', '--version'], env=env))
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
    p.add_argument('--version', choices=('8.4.10', '9.7.2'), required=True)
    args = p.parse_args()
    linux_required()
    with LabRun('mysql-'+args.version, args.output, ['scripts/run_mysql_r3_lab.py',
                'scripts/get_review_r3_assets.py', 'scripts/run_linux_memory_r3_lab.py']) as run:
        version_lab(run, args.version)
    raise SystemExit(run.exit_code)


if __name__ == '__main__':
    main()
