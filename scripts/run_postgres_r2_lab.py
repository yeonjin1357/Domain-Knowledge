"""Four xmin-horizon sources in private PostgreSQL 18 instances; never existing DBs."""
import argparse
import ctypes as C
import json
import os
from pathlib import Path
import re
import signal
import time

from lab_r2_common import ROOT, LabRun, confined, free_ports, linux_required, manifest, scenario, sha256, stamp
from run_postgres_lab import Connection as BaseConnection, bind_libpq

OBSERVE = 'labs/review-r2/postgresql-observe.sql'
ROWS = 128
CONTRACTS = {
    'prepared_transaction': ('prepared transaction의 XID가 일반 테이블의 회수 기준점을 붙잡는다.',
        'prepared XID 존재 중 DELETE한 128행이 VACUUM에서 제거 불가; ROLLBACK PREPARED 뒤 제거 불가 0.',
        'prepared 상태와 작업 순서를 확인했는데 제거 불가 행이 유지되지 않거나 해제 후에도 남음.'),
    'logical_catalog_xmin': ('비활성 logical slot의 catalog_xmin이 카탈로그 튜플 회수를 제한한다.',
        'pgoutput slot의 catalog_xmin 존재, catalog churn 후 pg_class에 제거 불가 행 존재; slot 삭제 뒤 0.',
        '전제 조건이 갖춰졌는데 카탈로그 보존/해제 차이가 없음. logical slot xmin의 NULL은 반증이 아니다.'),
    'standby_feedback': ('slot 없는 standby 질의의 hot_standby_feedback이 primary의 회수를 제한한다.',
        'standby RR snapshot과 primary walsender backend_xmin 확인; DELETE 행 보존 후 질의 종료·feedback 전진 시 제거 가능.',
        'feedback·snapshot·작업 순서가 확인됐는데 보존/해제 차이가 없음.'),
    'physical_slot_xmin': ('physical slot에 전달된 xmin은 standby 연결이 끊겨도 회수를 제한할 수 있다.',
        '연결 중 feedback xmin을 확보한 slot이 비활성화 후 xmin을 유지하며 행 보존; slot 삭제 뒤 제거 불가 0.',
        '연결 중 xmin·비활성 전환을 확인했는데 slot이 xmin을 유지하지 않거나 보존/해제 차이가 없음.')
}


class Connection(BaseConnection):
    def __init__(self, lib, port, name, expected_data):
        self.lib, self.pointer = lib, None
        self.notices, self.sql_history = [], []
        # All connection fields are supplied; no service, kubeconfig or production URI is accepted.
        self.pointer=lib.PQconnectdb(f'host=127.0.0.1 port={int(port)} dbname=postgres user=r2_owner application_name={name} connect_timeout=2'.encode())
        if not self.pointer or lib.PQstatus(self.pointer)!=0:
            message=lib.PQerrorMessage(self.pointer).decode() if self.pointer else 'allocation failed'
            self.close(); raise RuntimeError(message)
        callback_type=C.CFUNCTYPE(None,C.c_void_p,C.c_char_p)
        self.notice_callback=callback_type(lambda unused,message: self.notices.append({'at':stamp(),'message':message.decode('utf-8',errors='replace')}))
        # Keep callback alive until PQfinish; libpq calls it synchronously on this connection.
        lib.PQsetNoticeProcessor.restype=C.c_void_p
        lib.PQsetNoticeProcessor.argtypes=[C.c_void_p,callback_type,C.c_void_p]
        lib.PQsetNoticeProcessor(self.pointer,self.notice_callback,None)
        actual_data=self.scalar('SHOW data_directory')
        if Path(actual_data).resolve()!=expected_data.resolve():
            self.close()
            raise RuntimeError('Endpoint is not the private data directory; refusing further queries')

    def execute(self, sql):
        entry={'started':stamp(),'sql':sql}
        self.sql_history.append(entry)
        try:
            result=super().execute(sql)
            entry['rows']=result
            return result
        except Exception as exc:
            entry['error']=repr(exc)
            raise
        finally:
            entry['finished']=stamp()


def parse_vacuum(text):
    matches=re.findall(r'tuples:\s*(\d+) removed,\s*(\d+) remain,\s*(\d+) are dead but not yet removable',text)
    return [{'removed':int(a),'remain':int(b),'dead_not_removable':int(c)} for a,b,c in matches]


def horizon_verdict(preconditions, held, released, minimum):
    if not preconditions or len(held)!=1 or len(released)!=1:
        return 'inconclusive'
    return 'supported' if held[0]['dead_not_removable']>=minimum and released[0]['dead_not_removable']==0 else 'refuted'


class Experiment:
    def __init__(self, lab):
        self.lab=lab
        self.root=confined('.tools','.tools/pg18')
        pg=manifest()['postgresql']
        self.file_hashes={}
        for name, expected in pg['file_sha256'].items():
            path=confined('.tools',self.root/name)
            digest=sha256(path)
            if digest!=expected['sha256']:
                raise RuntimeError('Existing PostgreSQL file differs from pinned package member: '+name)
            self.file_hashes[name]=digest
        self.bin=self.root/'usr/lib/postgresql/18/bin'
        self.env={'LD_LIBRARY_PATH':str(self.root/'usr/lib/x86_64-linux-gnu'),'LC_ALL':'C','TZ':'UTC'}
        self.lib=bind_libpq(self.root/'usr/lib/x86_64-linux-gnu/libpq.so.5.18')
        self.port,self.standby_port=free_ports(2)
        self.data_root=lab.native_directory('dk-r2-pgdata-',
            'PostgreSQL data directories require 0700/0750; DrvFs under /mnt/c does not keep these modes')
        self.connections=[]
        self.standby_process=None

    def connect(self,name,standby=False):
        conn=Connection(self.lib,self.standby_port if standby else self.port,name,self.data_root/('s' if standby else 'p'))
        self.connections.append(conn)
        return conn

    def wait_connection(self,process,standby=False):
        deadline=time.monotonic()+35
        last=None
        while time.monotonic()<deadline:
            if process.poll() is not None:
                raise RuntimeError('PostgreSQL exited; see server log')
            try:
                return self.connect('r2-standby-observer' if standby else 'r2-primary-observer',standby)
            except RuntimeError as exc:
                last=str(exc); time.sleep(.1)
        raise TimeoutError('PostgreSQL readiness: '+str(last))

    def setup(self):
        data=self.data_root/'p'
        initialized=self.lab.command([self.bin/'initdb','-D',data,'-U','r2_owner','-A','trust','--no-locale','-E','UTF8'],timeout=60,env=self.env)
        self.lab.record['initdb']=initialized
        if initialized['returncode']:
            raise RuntimeError('initdb failed; no external directory fallback. See captured output.')
        config=(
            "\nlisten_addresses='127.0.0.1'\nunix_socket_directories=''\n"
            f"port={self.port}\nmax_connections=20\nshared_buffers='16MB'\n"
            "wal_level=logical\nmax_wal_senders=6\nmax_replication_slots=6\nmax_prepared_transactions=10\n"
            "wal_keep_size='16MB'\nmax_slot_wal_keep_size='64MB'\nmax_wal_size='128MB'\n"
            "autovacuum=off\nstatement_timeout='15s'\nlock_timeout='3s'\n"
            "idle_in_transaction_session_timeout='60s'\nclient_min_messages=info\nlog_min_messages=info\n"
            "logging_collector=off\ntimezone='UTC'\n")
        with (data/'postgresql.conf').open('a',encoding='utf-8') as f:
            f.write(config)
        self.primary_process=self.lab.launch('postgres-primary',[self.bin/'postgres','-D',data],env=self.env)
        self.observer=self.wait_connection(self.primary_process)
        self.writer=self.connect('r2-writer')
        self.holder=self.connect('r2-holder')
        version=int(self.observer.scalar('SHOW server_version_num'))
        if version//10000!=18:
            raise RuntimeError('Expected PostgreSQL 18, got '+str(version))
        self.lab.record['server']={'version':self.observer.scalar('SELECT version()'),'version_num':version,
            'configuration_appended':config,'file_sha256':self.file_hashes,'primary_port':self.port,'standby_port':self.standby_port,
            'settings':self.observer.execute("SELECT name, setting, unit FROM pg_settings WHERE name IN ('wal_level','max_replication_slots','max_prepared_transactions','autovacuum','shared_buffers','max_slot_wal_keep_size') ORDER BY name")}
        self.writer.execute('CREATE TABLE r2_anchor(id integer) WITH (autovacuum_enabled=false)')

    def create_table(self,name):
        assert re.fullmatch(r'r2_[a-z_]+',name)
        self.writer.execute(f'CREATE TABLE {name}(id integer) WITH (autovacuum_enabled=false)')
        self.writer.execute(f'INSERT INTO {name} SELECT generate_series(1,{ROWS})')
        self.writer.execute(f'VACUUM (FREEZE, ANALYZE) {name}')

    def delete(self,name):
        assert re.fullmatch(r'r2_[a-z_]+',name)
        self.writer.execute('BEGIN')
        xid=int(self.writer.scalar('SELECT pg_current_xact_id()::text'))
        self.writer.execute(f'DELETE FROM {name}')
        self.writer.execute('COMMIT')
        self.writer.execute('SELECT pg_stat_force_next_flush()')
        return xid

    def snapshot(self):
        self.observer.execute('SELECT pg_stat_clear_snapshot()')
        labels=('databases','activity','prepared','slots','replication','table_statistics')
        statements=[s.strip() for s in (ROOT/OBSERVE).read_text(encoding='utf-8').split(';') if s.strip()]
        assert len(statements)==len(labels)
        result={'started':stamp()}
        for label,sql in zip(labels,statements):
            result[label]=self.observer.execute(sql)
        result['finished']=stamp()
        result['numeric_observations']={
            'datfrozenxid_age':{r['datname']:int(r['datfrozenxid_age']) for r in result['databases']},
            'n_dead_tup':{r['schemaname']+'.'+r['relname']:int(r['n_dead_tup']) for r in result['table_statistics']}}
        result['limits']='Statement timestamps differ between queries; n_dead_tup is an estimate. A single-table VACUUM need not advance database-wide datfrozenxid.'
        return result

    def vacuum(self,table):
        assert re.fullmatch(r'(r2_[a-z_]+|pg_catalog\.pg_class)',table)
        before=len(self.writer.notices)
        self.writer.execute(f'VACUUM (VERBOSE, FREEZE, DISABLE_PAGE_SKIPPING) {table}')
        notices=self.writer.notices[before:]
        text='\n'.join(n['message'] for n in notices)
        self.writer.execute('SELECT pg_stat_force_next_flush()')
        return {'table':table,'notices':notices,'parsed_tuple_summaries':parse_vacuum(text),'state_after':self.snapshot()}

    def wait(self,sql,predicate,seconds=10):
        start=stamp(); deadline=time.monotonic()+seconds; count=0; rows=[]
        while time.monotonic()<deadline:
            self.observer.execute('SELECT pg_stat_clear_snapshot()')
            rows=self.observer.execute(sql); count+=1
            if predicate(rows):
                return {'matched':True,'started':start,'finished':stamp(),'queries':count,'rows':rows}
            time.sleep(.1)
        return {'matched':False,'started':start,'finished':stamp(),'queries':count,'rows':rows}

    def prepared(self):
        table='r2_prepared'
        self.create_table(table)
        initial=self.snapshot()
        self.holder.execute('BEGIN ISOLATION LEVEL REPEATABLE READ')
        self.holder.execute('INSERT INTO r2_anchor VALUES (1)')
        held_count=int(self.holder.scalar(f'SELECT count(*) FROM {table}'))
        self.holder.execute("PREPARE TRANSACTION 'r2-held'")
        try:
            before=self.snapshot()
            xid=self.delete(table)
            held=self.vacuum(table)
        finally:
            self.writer.execute("ROLLBACK PREPARED 'r2-held'")
        released=self.vacuum(table)
        preconditions=held_count==ROWS and any(r['gid']=='r2-held' for r in before['prepared'])
        self.lab.record['scenarios']['prepared_transaction']=scenario(*CONTRACTS['prepared_transaction'],
            {'initial':initial,'before_delete':before,'delete_xid':xid,'held':held,'released':released},
            horizon_verdict(preconditions,held['parsed_tuple_summaries'],released['parsed_tuple_summaries'],ROWS),
            'Holder connection is idle after PREPARE; prepared XID, rather than a still-open application transaction, is observed.')

    def catalog(self):
        initial=self.vacuum('pg_catalog.pg_class')
        created=self.writer.execute("SELECT * FROM pg_create_logical_replication_slot('r2_catalog','pgoutput')")
        try:
            before=self.snapshot()
            for i in range(24):
                self.writer.execute(f'CREATE TABLE r2_catalog_churn_{i}(id integer)')
                self.writer.execute(f'DROP TABLE r2_catalog_churn_{i}')
            self.writer.execute('SELECT pg_stat_force_next_flush()')
            held=self.vacuum('pg_catalog.pg_class')
        finally:
            self.writer.execute("SELECT pg_drop_replication_slot('r2_catalog')")
        released=self.vacuum('pg_catalog.pg_class')
        preconditions=any(r['slot_name']=='r2_catalog' and r['catalog_xmin'] is not None and r['active']=='f' for r in before['slots'])
        self.lab.record['scenarios']['logical_catalog_xmin']=scenario(*CONTRACTS['logical_catalog_xmin'],
            {'initial':initial,'slot_creation':created,'before_churn':before,'ddl_pairs':24,'held':held,'released':released},
            horizon_verdict(preconditions,held['parsed_tuple_summaries'],released['parsed_tuple_summaries'],1),
            'pgoutput is shipped in the existing official package. This experiment concerns catalog tuples; logical-slot xmin may remain NULL.')

    def setup_standby(self):
        self.create_table('r2_feedback')
        self.create_table('r2_slot')
        self.standby_data=self.data_root/'s'
        backup=self.lab.command([self.bin/'pg_basebackup','-D',self.standby_data,'-h','127.0.0.1','-p',self.port,
             '-U','r2_owner','--no-password','-X','stream','--checkpoint=fast'],timeout=90,env=self.env)
        self.lab.record['basebackup']=backup
        if backup['returncode']:
            raise RuntimeError('Private base backup failed')
        configuration=(f"\nport={self.standby_port}\nprimary_conninfo='host=127.0.0.1 port={self.port} user=r2_owner application_name=r2_standby'\n"
                       "primary_slot_name=''\nhot_standby=on\nhot_standby_feedback=on\nwal_receiver_status_interval='1s'\n"
                       "max_standby_streaming_delay='30s'\n")
        with (self.standby_data/'postgresql.conf').open('a',encoding='utf-8') as f:
            f.write(configuration)
        (self.standby_data/'standby.signal').touch()
        self.lab.record['standby_configuration_appended']=configuration
        self.start_standby('postgres-standby-no-slot')

    def start_standby(self,name):
        self.standby_process=self.lab.launch(name,[self.bin/'postgres','-D',self.standby_data],env=self.env)
        self.standby=self.wait_connection(self.standby_process,True)
        assert self.standby.scalar('SELECT pg_is_in_recovery()')=='t'
        assert self.standby.scalar('SHOW hot_standby_feedback')=='on'

    def feedback(self):
        self.standby.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        count=int(self.standby.scalar('SELECT count(*) FROM r2_feedback'))
        feedback=self.wait("SELECT backend_xmin::text FROM pg_stat_replication WHERE application_name='r2_standby'",
                           lambda rows:bool(rows) and rows[0]['backend_xmin'] is not None)
        before=self.snapshot()
        xid=self.delete('r2_feedback')
        held=self.vacuum('r2_feedback')
        self.standby.execute('ROLLBACK')
        released_feedback=self.wait("SELECT backend_xmin::text FROM pg_stat_replication WHERE application_name='r2_standby'",
            lambda rows:bool(rows) and (rows[0]['backend_xmin'] is None or int(rows[0]['backend_xmin'])>xid))
        released=self.vacuum('r2_feedback')
        preconditions=count==ROWS and feedback['matched'] and released_feedback['matched'] and not before['slots']
        self.lab.record['scenarios']['standby_feedback']=scenario(*CONTRACTS['standby_feedback'],
            {'standby_snapshot_count':count,'feedback_wait':feedback,'before_delete':before,'delete_xid':xid,'held':held,
             'feedback_after_rollback':released_feedback,'released':released},
            horizon_verdict(preconditions,held['parsed_tuple_summaries'],released['parsed_tuple_summaries'],ROWS),
            'No permanent replication slot is configured in this case; feedback and query completion are bounded-poll observations.')

    def physical_slot(self):
        self.standby.close()
        self.lab.stop(self.standby_process)
        creation=self.writer.execute("SELECT * FROM pg_create_physical_replication_slot('r2_physical', true)")
        with (self.standby_data/'postgresql.conf').open('a',encoding='utf-8') as f:
            f.write("\nprimary_slot_name='r2_physical'\n")
        self.start_standby('postgres-standby-physical-slot')
        self.standby.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        count=int(self.standby.scalar('SELECT count(*) FROM r2_slot'))
        feedback=self.wait("SELECT active, xmin::text, catalog_xmin::text FROM pg_replication_slots WHERE slot_name='r2_physical'",
                           lambda rows:bool(rows) and rows[0]['active']=='t' and rows[0]['xmin'] is not None)
        before=self.snapshot()
        xid=self.delete('r2_slot')
        # Intentionally end only this private standby process group without clearing feedback.
        os.killpg(self.standby_process.pid,signal.SIGKILL)
        self.standby_process.wait(timeout=5)
        self.standby.close()
        disconnected=self.wait("SELECT active, xmin::text, catalog_xmin::text FROM pg_replication_slots WHERE slot_name='r2_physical'",
                               lambda rows:bool(rows) and rows[0]['active']=='f')
        held=self.vacuum('r2_slot')
        self.writer.execute("SELECT pg_drop_replication_slot('r2_physical')")
        released=self.vacuum('r2_slot')
        preconditions=count==ROWS and feedback['matched'] and disconnected['matched']
        verdict=horizon_verdict(preconditions,held['parsed_tuple_summaries'],released['parsed_tuple_summaries'],ROWS)
        if preconditions and disconnected['rows'][0]['xmin'] is None:
            verdict='refuted'
        self.lab.record['scenarios']['physical_slot_xmin']=scenario(*CONTRACTS['physical_slot_xmin'],
            {'slot_creation':creation,'standby_snapshot_count':count,'feedback_wait':feedback,'before_delete':before,
             'delete_xid':xid,'after_disconnect':disconnected,'held':held,'released':released},verdict,
            'Private standby was deliberately killed; primary remains running. Inactive slot xmin is compared before dropping that slot. No other process group is signaled.')

    def close(self):
        self.lab.record['connection_sql_history']=[c.sql_history for c in self.connections]
        self.lab.record['connection_notices']=[c.notices for c in self.connections]
        for connection in reversed(self.connections):
            connection.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='.lab-runs/r2/postgresql.json')
    parser.add_argument('--skip-standby',action='store_true',help='Explicitly record the two replication scenarios as blocked')
    parser.add_argument('--plan',action='store_true')
    args=parser.parse_args()
    if args.plan:
        print(json.dumps({'version_family':'18','reuse':'.tools/pg18','contracts':CONTRACTS,
                          'rows':ROWS,'catalog_ddl_pairs':24,'skip_standby':args.skip_standby,
                          'limits':'No XID wraparound acceleration; n_dead_tup is estimated; datfrozenxid need not move after a table-only vacuum.'},ensure_ascii=False,indent=2))
        return
    linux_required()
    with LabRun('postgresql',args.output,['scripts/run_postgres_r2_lab.py','scripts/run_postgres_lab.py',OBSERVE,'labs/postgresql/packages.json']) as lab:
        experiment=Experiment(lab)
        try:
            experiment.setup()
            experiment.prepared()
            experiment.catalog()
            if args.skip_standby:
                for name in ('standby_feedback','physical_slot_xmin'):
                    lab.record['scenarios'][name]=scenario(*CONTRACTS[name],{},'blocked','Explicit --skip-standby; not an executed result.')
            else:
                experiment.setup_standby()
                experiment.feedback()
                experiment.physical_slot()
        finally:
            experiment.close()
    raise SystemExit(lab.exit_code)


if __name__=='__main__':
    main()
