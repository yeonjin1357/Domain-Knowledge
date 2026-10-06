"""Offline round-3 preparation/evidence checks; never launches Linux lab binaries."""
import argparse
import ast
import copy
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import statistics
import tarfile
import tempfile
from unittest.mock import patch

from lab_r3_common import (LabRun, MANIFEST, RAW_LIMIT, ROOT, SUMMARY_LIMIT, TOTAL_LIMIT,
                           checked_asset, confined, json_bytes, manifest, read_sidecar, scenario, sha256)
from run_histogram_r3_lab import parse_dump
from run_linux_memory_r3_lab import kb_fields, psi_fields
from run_mysql_r3_lab import (parse_xml, matching_lock_edge, matching_sys_wait,
                              coordinator_positions_equal, sys_visibility, checkpoint_visibility)
from get_review_r3_assets import archive_files, resolved_member
from prepare_mysql_r3_runtime import package_members, elf_amd64


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rejects(fn, message):
    try:
        fn()
    except (ValueError, FileExistsError, RuntimeError):
        return
    raise AssertionError(message)


def verify_result(path, allow_error=False, publication=None):
    path = confined('labs/results', path) if publication else confined('.lab-runs', path)
    record = json.loads(path.read_text(encoding='utf-8'))
    archives = {}
    if publication:
        require(sha256(path) == publication['sha256'], 'Published summary hash differs')
        provenance = json.loads((ROOT/'review/evidence-provenance.json').read_text(encoding='utf-8'))
        archives = {a['original_path']: a for a in provenance['archives']
                    if a['evidence'] == publication['evidence']}
    require(path.stat().st_size <= SUMMARY_LIMIT, 'Oversize summary')
    require(record.get('schema_version') == 3 and record.get('round') == 3, 'Not an r3 evidence record')
    require(record.get('status') == 'recorded' or (allow_error and record.get('status') == 'error'), 'Incomplete/error result')
    require(record['input_sha256'], 'Missing provenance')
    for name, value in record['input_sha256'].items():
        archive = archives.get(name)
        if archive:
            require(archive['sha256'] == value, 'Archived input hash differs from record')
        file = (ROOT/(archive['archived_path'] if archive else name)).resolve()
        require(file.is_relative_to(ROOT) and sha256(file) == value, f'Input differs: {name}')
    raw = {name: read_sidecar(path, item) for name, item in record['artifacts'].items()}
    require(sum(map(len, raw.values())) <= TOTAL_LIMIT, 'Oversize raw evidence bundle')
    if not allow_error:
        require(record['cleanup']['completed'] and record['native_directories_removed'], 'Cleanup incomplete')
    verdicts = []
    for name, case in record['scenarios'].items():
        for field in ('hypothesis', 'success_condition', 'refutation_condition', 'reason', 'observations', 'verdict'):
            require(field in case, f'{name}: missing {field}')
        require(case['verdict'] in ('supported', 'refuted', 'inconclusive', 'blocked', 'error'), 'Invalid verdict')
        verdicts.append(case['verdict'])
    require(record['verdict_counts'] == {v: verdicts.count(v) for v in sorted(set(verdicts))}, 'Verdict counts differ')
    for name, query in record.get('sql_queries', {}).items():
        require(parse_xml(raw[query['xml_artifact']].decode()) == query['results'], f'SQL rows differ: {name}')
    suite = record['suite']
    expected_names = {'linux-memory': {'facilities', 'anonymous', 'file', 'memfd'},
                      'histograms': {'3.13.4', '3.15.0'},
                      'clock-state': {'synchronization_metadata'}}
    if not allow_error and suite in expected_names:
        require(set(record['scenarios']) == expected_names[suite], 'Incomplete scenario matrix')
    if suite.startswith('mysql-') and not allow_error:
        version = suite.removeprefix('mysql-')
        cases = record['scenarios']
        expected = {version+'/'+n for n in ('defaults', 'gap_lock', 'next_key_lock', 'deadlock', 'replication')}
        if set(cases) == {version+'/preflight'}:
            require(cases[version+'/preflight']['verdict'] == 'blocked', 'Preflight-only result must be blocked')
        else:
            require(set(cases) == expected, 'Incomplete MySQL scenario matrix')
            queries = record['sql_queries']
            def rows(name):
                return queries[name]['results'][-1]['rows']
            default = cases[version+'/defaults']
            require(rows(default['observations']['query_ref']) == default['observations']['rows'], 'Defaults summary differs')
            for label in ('gap_lock', 'next_key_lock'):
                obs = cases[version+'/'+label]['observations']
                for key, ref in zip(('lock_rows', 'wait_rows', 'sys_rows'), obs['query_refs']):
                    require(rows(ref) == obs[key], f'{label} summary differs from raw SQL')
                if 'observed_lock_modes' in obs:
                    require(obs['observed_lock_modes'] == sorted({r['LOCK_MODE'] for r in obs['lock_rows']}), 'LOCK_MODE strings differ')
                    require(obs['record_lock_modes'] == sorted({r['LOCK_MODE'] for r in obs['lock_rows'] if r['LOCK_TYPE'] == 'RECORD'}), 'RECORD lock modes differ')
            obs = cases[version+'/replication']['observations']
            for phase in ('baseline', 'io_stopped', 'sql_stopped', 'resumed'):
                for key, ref in zip(('status', 'workers', 'connection'), obs[phase]['query_refs']):
                    require(rows(ref) == obs[phase][key], f'Replication {phase} differs from raw SQL')
            if cases[version+'/replication']['verdict'] == 'supported':
                require(obs['baseline']['status'][0]['Seconds_Behind_Source'] == '0', 'Baseline is not zero')
                require(obs['io_stopped']['status'][0]['Seconds_Behind_Source'] is None, 'Drained IO stop is not SQL NULL')
                require(obs['sql_stopped']['status'][0]['Seconds_Behind_Source'] is None, 'SQL stop is not SQL NULL')
                require(obs['resumed']['source_gtid_executed'] == obs['resumed']['replica_gtid_executed'], 'Resume GTID mismatch')
            if record.get('mysql_observation_revision') == 2:
                verify_mysql_v2(record)
    if suite == 'histograms':
        fixture = json.loads((ROOT/'labs/review-r3/histograms/fixture.json').read_text())
        for case in record['scenarios'].values():
            obs = case['observations']
            measured = parse_dump(raw[obs['test_command']['artifact']].decode())
            require(measured == obs['measured_values'], 'Debug dump differs from reported histogram values')
            expected = {k: v['expected'] for k, v in fixture['expressions'].items()}
            require(obs['expected_from_formulas'] == expected, 'Histogram expectation differs from fixture')
            complete = measured.keys() == expected.keys()
            matched = complete and all(math.isclose(measured[k], v, rel_tol=1e-12, abs_tol=1e-12) for k, v in expected.items())
            verdict = 'supported' if obs['test_command']['returncode'] == 0 and matched else 'refuted' if complete else 'inconclusive'
            require(case['verdict'] == verdict, 'Histogram verdict differs')
    if suite == 'linux-memory':
        for name in ('anonymous', 'file', 'memfd'):
            case = record['scenarios'].get(name)
            if not case or case['verdict'] == 'blocked':
                continue
            obs = case['observations']
            for phase in ('before', 'allocated', 'released'):
                for field in ('status', 'smaps', 'smaps_rollup', 'statm'):
                    entry = obs[phase][field]
                    if 'artifact' in entry:
                        text = raw[entry['artifact']].decode()
                        parsed = list(map(int, text.split())) if field == 'statm' else kb_fields(text)
                        require(parsed == entry['values'], 'Proc summary differs from raw source')
                snapshot = obs[phase]
                comparisons = snapshot['comparison_bytes']
                if 'values' in snapshot['statm']:
                    require(comparisons['statm_resident'] == snapshot['statm']['values'][1]*snapshot['page_size_bytes'], 'statm page conversion differs')
                    require(comparisons['statm_shared'] == snapshot['statm']['values'][2]*snapshot['page_size_bytes'], 'statm shared conversion differs')
            for cost in obs['read_cost'].values():
                samples = [s['elapsed_raw_ns'] for s in cost['samples']]
                require(samples and min(samples) >= 0 and statistics.median(samples) == cost['median_raw_ns'], 'Read cost median differs')
            key = obs['expected_class']
            old = obs['before']['smaps_rollup'].get('values', {}).get(key)
            new = obs['allocated']['smaps_rollup'].get('values', {}).get(key)
            delta = None if old is None or new is None else new-old
            require(delta == obs['class_delta_bytes'], 'RSS class delta differs')
            verdict = 'inconclusive' if delta is None else 'supported' if delta >= obs['mapping_bytes']*.8 else 'refuted'
            require(case['verdict'] == verdict, 'RSS verdict differs')
        facilities = record['scenarios'].get('facilities', {}).get('observations', {})
        for entry in facilities.get('psi', {}).values():
            if 'values' in entry:
                require(psi_fields(raw[entry['artifact']].decode()) == entry['values'], 'PSI summary differs')
        vmstat = facilities.get('vmstat', {})
        if 'artifact' in vmstat:
            counters = {key: int(value) for key, value in (line.split() for line in raw[vmstat['artifact']].decode().splitlines())}
            require(all(counters[k] == v for k, v in vmstat['selected_counters'].items()), 'vmstat summary differs')
    if suite == 'clock-state':
        obs = record['scenarios']['synchronization_metadata']['observations']
        for key in ('adjtimex_before', 'adjtimex_after'):
            value = obs[key]
            if value.get('available'):
                require(value['modes'] == 0 and value['freq_ppm'] == value['freq_scaled_ppm']/65536, 'adjtimex read-only/frequency conversion differs')
        for command in obs['systemd_commands']:
            require(command in record['commands'] and command['artifact'] in raw, 'Missing systemd command evidence')
    print(f'PASS: {path.name}: {len(raw)} complete gzip artifacts; {record["verdict_counts"]}; inputs match')
    return record


def verify_mysql_v2(record):
    """Check bounded visibility evidence and GTID barriers, without rewriting verdicts."""
    version = record['suite'].removeprefix('mysql-')
    queries = record['sql_queries']
    rows = lambda ref: queries[ref]['results'][-1]['rows']
    for label in ('gap_lock', 'next_key_lock'):
        case = record['scenarios'][version+'/'+label]
        obs = case['observations']
        visibility = obs['sys_visibility']
        require(rows(visibility['query_refs'][-1]) == visibility['last_rows'] == obs['sys_rows'], 'Sys visibility summary differs')
        require(1 <= len(visibility['query_refs']) <= visibility['max_retries']+1 and
                len(visibility['trx_query_refs']) == len(visibility['query_refs']), 'Sys polling trace incomplete')
        for ref in visibility['trx_query_refs']:
            require('information_schema.innodb_trx' in queries[ref]['sql'], 'Missing trx diagnostic query')
        release, insertion, visible, rollback = obs['release_query_refs']
        require(all(not queries[r]['error_codes'] for r in (release, rollback)), 'Release/cleanup SQL failed')
        require(queries[insertion]['finished']['monotonic_ns'] >= queries[release]['started']['monotonic_ns'], 'Insert finished before release evidence')
        direct = matching_lock_edge(obs['lock_rows'], obs['wait_rows'], label == 'gap_lock')
        joined = matching_sys_wait(obs['sys_rows'], obs['waiter_connection_id'], obs['blocker_connection_id'])
        inserted = not queries[insertion]['error_codes'] and rows(visible) == [{'id': '3', 'k': '15', 'v': '0'}]
        conditions = {'matching_direct_lock_edge': direct, 'matching_sys_wait': joined,
                      'insert_visible_after_release': inserted}
        require(obs['conditions'] == conditions and visibility['matched'] == joined, 'Lock condition differs')
        verdict = 'supported' if all(conditions.values()) else 'inconclusive' if direct and inserted and not joined else 'refuted'
        require(case['verdict'] == verdict, 'Lock verdict differs from observed conditions')
    case = record['scenarios'][version+'/replication']
    obs = case['observations']
    for snap in [obs[k] for k in ('baseline', 'io_stopped', 'sql_stopped', 'resumed')]+list(obs['immediate_after_gtid_or_stop'].values()):
        for key, ref in zip(('status', 'workers', 'connection'), snap['query_refs']):
            require(rows(ref) == snap[key], 'Immediate replication summary differs')
        require([rows(ref)[0]['gtid'] for ref in snap['gtid_query_refs']] ==
                [snap['source_gtid_executed'], snap['replica_gtid_executed']], 'GTID summary differs from SQL')
    for poll in obs['checkpoint_visibility'].values():
        require(1 <= len(poll['query_refs']) <= poll['max_retries']+1, 'Checkpoint poll exceeded bound')
        last = rows(poll['query_refs'][-1])
        matched = bool(last and coordinator_positions_equal(last[0]) and last[0]['Replica_SQL_Running'] == 'Yes' and
                       last[0]['Replica_IO_Running'] == poll['io_running'])
        require(poll['matched'] == matched, 'Checkpoint gate differs from file/position/thread states')
    for barrier in obs['gtid_barriers']:
        require(rows(barrier['source_query_ref'])[0]['gtid'] == barrier['target_gtid'] and
                rows(barrier['wait_query_ref']) == [{'caught': '0'}] and barrier['result'] == '0', 'GTID barrier differs')
        require('WAIT_FOR_EXECUTED_GTID_SET' in queries[barrier['wait_query_ref']]['sql'], 'Wrong barrier query')
    require(rows(obs['variables_query_ref']) == obs['variables'], 'Replication variables differ')
    received = obs['receive_barrier']
    require(rows(received['source_query_ref'])[0]['gtid'] == received['target_gtid'] and
            rows(received['query_ref']) == received['rows'] == [{'received': '1'}], 'Received target GTID barrier differs')
    b, io, sql, resumed = (obs[k] for k in ('baseline', 'io_stopped', 'sql_stopped', 'resumed'))
    status = lambda snap: snap['status'][0]
    ready = all(p['matched'] for p in obs['checkpoint_visibility'].values()) and all(coordinator_positions_equal(status(s)) for s in (b, io, resumed))
    conditions = {
        'baseline_gtid_caught': b['source_gtid_executed'] == b['replica_gtid_executed'],
        'baseline_zero_after_positions': status(b)['Seconds_Behind_Source'] == '0',
        'io_stopped_null_after_positions': status(io)['Seconds_Behind_Source'] is None,
        'io_stopped_threads': status(io)['Replica_IO_Running'] == 'No' and status(io)['Replica_SQL_Running'] == 'Yes',
        'sql_stopped_null': status(sql)['Seconds_Behind_Source'] is None,
        'sql_stopped_threads': status(sql)['Replica_IO_Running'] == 'Yes' and status(sql)['Replica_SQL_Running'] == 'No',
        'io_stopped_gtid_pending': io['source_gtid_executed'] != io['replica_gtid_executed'],
        'sql_stopped_gtid_pending': sql['source_gtid_executed'] != sql['replica_gtid_executed'],
        'sql_stopped_target_received': received['rows'][0]['received'] == '1',
        'resumed_gtid_caught': resumed['source_gtid_executed'] == resumed['replica_gtid_executed'],
        'resumed_zero_after_positions': status(resumed)['Seconds_Behind_Source'] == '0'}
    require(obs['conditions'] == conditions and obs['position_preconditions_met'] == ready, 'Replication condition differs')
    verdict = 'inconclusive' if not ready else 'supported' if all(conditions.values()) else 'refuted'
    require(case['verdict'] == verdict, 'Replication verdict differs from conditions')


def verify_mysql_r1_publication(record):
    version = record['suite'].removeprefix('mysql-')
    require(record.get('mysql_observation_revision', 1) == 1, 'Expected unchanged historical r1')
    require(record['verdict_counts'] == {'refuted': 2, 'supported': 3}, 'Historical verdicts changed')
    queries = record['sql_queries']
    review = json.loads((ROOT/'review/mysql-r3e-analysis.json').read_text(encoding='utf-8'))['runs'][version]
    require(sha256(ROOT/review['evidence']) == review['evidence_sha256'], 'Analysis refers to other evidence')
    require(review['parallel_workers_configured'] == 2 and all('--replica-parallel-workers=2' in s['argv']
            for s in record['servers'].values()), 'Historical worker setting differs')
    default = record['scenarios'][version+'/defaults']['observations']['rows'][0]
    require(default['innodb_flush_log_at_trx_commit'] == default['sync_binlog'] == '1', 'Published defaults differ')
    deadlock = record['scenarios'][version+'/deadlock']['observations']
    require(deadlock['error_codes'] == deadlock['first_query']['error_codes']+deadlock['second_query']['error_codes'] == [1213]
            and 'LATEST DETECTED DEADLOCK' in str(queries[deadlock['engine_status_query']]['results']), 'Published deadlock differs')
    for name in ('gap_lock', 'next_key_lock'):
        case = record['scenarios'][version+'/'+name]
        obs = case['observations']; findings = review['locks'][name]
        require(matching_lock_edge(obs['lock_rows'], obs['wait_rows'], name == 'gap_lock') and
                findings['direct_id_join_matches'], 'Missing historical direct lock edge')
        require(len(obs['sys_rows']) == findings['sys_row_count'] == (1 if name == 'gap_lock' else 0), 'Historical sys row mismatch')
        insertion = queries[findings['insert_query_ref']]
        release = queries[findings['blocker_release_query_ref']]
        require(not insertion['error_codes'] and insertion['sql'] == 'INSERT INTO r3.t VALUES (3,15,0)' and
                release['sql'] == 'ROLLBACK' and insertion['finished']['monotonic_ns'] >= release['started']['monotonic_ns'], 'Historical insert/release differs')
        require(case['verdict'] == ('supported' if name == 'gap_lock' else 'refuted'), 'Historical lock verdict changed')
        require(findings['observed_lock_modes'] == sorted({r['LOCK_MODE'] for r in obs['lock_rows']}), 'Analysis lock modes differ')
        require(findings['snapshot_query_refs'] == obs['query_refs'] and
                findings['sys_xml_sha256'] == record['artifacts'][queries[obs['query_refs'][2]]['xml_artifact']]['raw_sha256'],
                'Analysis sys evidence differs')
    first = queries[record['scenarios'][version+'/gap_lock']['observations']['query_refs'][2]]['started']
    last = queries[record['scenarios'][version+'/next_key_lock']['observations']['query_refs'][2]]['finished']
    for key in ('monotonic_ns', 'monotonic_raw_ns'):
        span = (last[key]-first[key])/1e6
        require(span == review['max_gap_sys_start_to_next_key_sys_end_ms'][key] and 0 < span < 100, 'Sys/cache timing span differs')
    obs = record['scenarios'][version+'/replication']['observations']
    expected = ['13', '13', None, '0' if version == '8.4.11' else '1']
    for phase, sbs in zip(('baseline', 'io_stopped', 'sql_stopped', 'resumed'), expected):
        snap = obs[phase]; status = snap['status'][0]
        finding = review['replication'][phase]
        require(status['Seconds_Behind_Source'] == review['replication'][phase]['sbs'] == sbs, 'Historical SBS differs')
        require(status['Read_Source_Log_Pos'] == review['replication'][phase]['read_pos'] and
                status['Exec_Source_Log_Pos'] == review['replication'][phase]['exec_pos'], 'Historical checkpoint differs')
        for field, key in (('Replica_IO_Running', 'io'), ('Replica_SQL_Running', 'sql'),
                           ('Source_Log_File', 'source_log_file'), ('Relay_Source_Log_File', 'group_log_file'),
                           ('Retrieved_Gtid_Set', 'retrieved_gtid')):
            require(status[field] == finding[key], 'Analysis replication status differs')
        require(snap['source_gtid_executed'] == finding['source_gtid'] and
                snap['replica_gtid_executed'] == finding['replica_gtid'], 'Analysis GTID differs')
        require(finding['status_query_ref'] == snap['query_refs'][0] and
                finding['status_started_utc'] == queries[snap['query_refs'][0]]['started']['utc'], 'Analysis status time differs')
        require([{key: worker[key] for key in finding['workers'][0]} for worker in snap['workers']] == finding['workers'],
                'Analysis worker completion differs')
    require(obs['baseline']['source_gtid_executed'] == obs['baseline']['replica_gtid_executed'] and
            obs['resumed']['source_gtid_executed'] == obs['resumed']['replica_gtid_executed'], 'Historical applied GTIDs differ')
    require(not coordinator_positions_equal(obs['baseline']['status'][0]), 'Missing historical checkpoint lag')
    for barrier in review['barriers']:
        q = queries[barrier['query_ref']]
        require(q['results'][-1]['rows'] == barrier['rows'] == [{'caught': '0'}] and
                q['finished'] == barrier['finished'], 'Historical GTID barrier differs')
    require(queries[review['barriers'][0]['query_ref']]['finished']['monotonic_ns'] <
            queries[obs['baseline']['query_refs'][0]]['started']['monotonic_ns'], 'Baseline preceded execution barrier')


def verify_mysql_r2_publication(record):
    """Check the fixed r2 publication, including the samples before convergence."""
    version = record['suite'].removeprefix('mysql-')
    require(record.get('mysql_observation_revision') == 2 and
            record['verdict_counts'] == {'supported': 5} and len(record['artifacts']) == 132,
            'Published MySQL r2 revision/count differs')
    queries = record['sql_queries']
    rows = lambda ref: queries[ref]['results'][-1]['rows']
    cases = record['scenarios']
    defaults = cases[version+'/defaults']['observations']['rows'][0]
    require(defaults['innodb_flush_log_at_trx_commit'] == defaults['sync_binlog'] == '1', 'r2 defaults differ')
    deadlock = cases[version+'/deadlock']['observations']
    require(deadlock['error_codes'] == deadlock['first_query']['error_codes']+deadlock['second_query']['error_codes'] == [1213]
            and 'LATEST DETECTED DEADLOCK' in str(rows(deadlock['engine_status_query'])), 'r2 deadlock differs')
    for label, counts in (('gap_lock', [1]), ('next_key_lock', [0, 1])):
        obs = cases[version+'/'+label]['observations']
        initial = obs['initial_query_refs']
        require(matching_lock_edge(rows(initial[0]), rows(initial[1]), label == 'gap_lock'), 'r2 initial direct edge missing')
        poll = obs['sys_visibility']
        require([len(rows(ref)) for ref in poll['query_refs']] == counts and poll['matched'], 'r2 sys visibility transition differs')
        require(queries[poll['query_refs'][-1]]['finished']['monotonic_ns'] <
                queries[obs['release_query_refs'][0]]['started']['monotonic_ns'], 'sys visibility sampled after blocker release')
    obs = cases[version+'/replication']['observations']
    expected = {'baseline': ('Yes', 'Yes', '1073', '1073', '0'),
                'io_stopped': ('No', 'Yes', '1073', '1073', None),
                'sql_stopped': ('Yes', 'No', '1611', '1342', None),
                'resumed': ('Yes', 'Yes', '1611', '1611', '0')}
    for phase, values in expected.items():
        status = obs[phase]['status'][0]
        require(tuple(status[k] for k in ('Replica_IO_Running', 'Replica_SQL_Running', 'Read_Source_Log_Pos',
                                         'Exec_Source_Log_Pos', 'Seconds_Behind_Source')) == values, 'r2 final status differs')
        require(status['Source_Log_File'] == status['Relay_Source_Log_File'] == 'binlog.000001', 'r2 log files differ')
    initial = obs['immediate_after_gtid_or_stop']['baseline']
    require(initial['source_gtid_executed'] == initial['replica_gtid_executed'] and
            initial['status'][0]['Seconds_Behind_Source'] == {'8.4.11': '12', '9.7.2': '14'}[version] and
            initial['status'][0]['Read_Source_Log_Pos'] == '1073' and initial['status'][0]['Exec_Source_Log_Pos'] == '158',
            'r2 immediate GTID/checkpoint observation differs')
    resumed = obs['immediate_after_gtid_or_stop']['resumed']['status'][0]
    require(resumed['Seconds_Behind_Source'] == '0' and not coordinator_positions_equal(resumed), 'r2 early zero observation differs')
    require({k: len(v['query_refs']) for k, v in obs['checkpoint_visibility'].items()} ==
            {'baseline': 2, 'io_stopped': 1, 'resumed': 3}, 'r2 position polling trace differs')
    require(dict((r['Variable_name'], r['Value']) for r in obs['variables'])['replica_parallel_workers'] == '2',
            'r2 observed worker setting differs')


def verify_published_review_r3():
    provenance = json.loads((ROOT/'review/evidence-provenance.json').read_text(encoding='utf-8'))
    entries = [p for p in provenance['published'] if p['id'].endswith('-r3')]
    require({p['id'] for p in entries} == {'linux-memory-r3', 'histograms-r3', 'clock-state-r3',
            'mysql-8.4.11-r1-r3', 'mysql-9.7.2-r1-r3',
            'mysql-8.4.11-r2-r3', 'mysql-9.7.2-r2-r3'}, 'Incomplete published r3 bundle set')
    records = {}
    for entry in entries:
        records[entry['id']] = verify_result(entry['evidence'], publication=entry)
    memory = records['linux-memory-r3']['scenarios']
    for name in ('anonymous', 'file', 'memfd'):
        require(memory[name]['observations']['class_delta_bytes'] == 8*1024**2, 'Published 8 MiB observation differs')
    a = memory['anonymous']['observations']['allocated']
    require(a['statm']['values'][1] == 7320 and a['status']['values']['VmRSS']/1024 == 29280, 'Published resident observation differs')
    m = memory['memfd']['observations']['allocated']
    require(m['statm']['values'][2] == 4709 and (m['status']['values']['RssFile']+m['status']['values']['RssShmem'])/1024 == 18836, 'Published shared observation differs')
    clock = records['clock-state-r3']['scenarios']['synchronization_metadata']['observations']
    mono = (clock['clock_after']['monotonic_ns']-clock['clock_before']['monotonic_ns'])/1e9
    raw = (clock['clock_after']['raw_midpoint_ns']-clock['clock_before']['raw_midpoint_ns'])/1e9
    require(math.isclose(mono/raw, .9633570846333227, rel_tol=1e-12), 'Published clock ratio differs')
    for version in ('8.4.11', '9.7.2'):
        verify_mysql_r1_publication(records[f'mysql-{version}-r1-r3'])
        verify_mysql_r2_publication(records[f'mysql-{version}-r2-r3'])
    chapter = (ROOT/'docs/database/mysql-operations.md').read_text(encoding='utf-8')
    for token in ('| 위치 일치 후(baseline) | Yes / Yes | 1073 / 1073 | 0 | 1–4 / 1–4 |',
                  '| io_stopped | No / Yes | 1073 / 1073 | NULL | 1–5 / 1–4 |',
                  '| sql_stopped | Yes / No | 1611 / 1342 | NULL | 1–6 / 1–5 |',
                  '| resumed | Yes / Yes | 1611 / 1611 | 0 | 1–6 / 1–6 |',
                  '`supported 3, refuted 2`', '`supported 5`', 'replica_parallel_workers=2',
                  '8.4.11은 12, 9.7.2는 14'):
        require(token in chapter, 'Published MySQL text drifted from checked observations: '+token)
    require(sum(len(r['scenarios']) for r in records.values()) == 27 and
            sum(len(r['artifacts']) for r in records.values()) == 525 and
            sum(r['verdict_counts'].get('supported', 0) for r in records.values()) == 23 and
            sum(r['verdict_counts'].get('refuted', 0) for r in records.values()) == 4, 'Round 3 publication totals differ')
    print('PASS: round 3 published 7 bundles, 27 recorded verdicts (23 supported, 4 historical refuted), 525 complete gzip sidecars; r1/r2 and pre/post visibility preserved; no Linux rerun')


def preparation():
    for file in (ROOT/'scripts').glob('*r3*.py'):
        ast.parse(file.read_text(encoding='utf-8'))
    for asset in manifest()['assets']:
        require(len(asset['sha256']) == 64 and asset['url'].startswith(('https://cdn.mysql.com/', 'https://github.com/prometheus/prometheus/')), 'Unexpected asset')
    fixture = json.loads((ROOT/'labs/review-r3/histograms/fixture.json').read_text())
    values = fixture['observations_example']
    require(len(values) == 4 and sum(values) == 9 and [sum(v <= b for v in values) for b in (1, 2, 4)] == [0, 2, 4], 'Distribution mismatch')
    expected = fixture['expressions']
    require(expected['classic_q25']['expected'] == 1+(2-1)/2, 'Linear quantile mismatch')
    require(math.isclose(expected['native_q25']['expected'], 2**.5, rel_tol=1e-15), 'Exponential quantile mismatch')
    require(math.isclose(expected['native_fraction']['expected'], math.log(1.5)/math.log(2)/2, rel_tol=1e-15), 'Logarithmic fraction mismatch')
    tests = json.loads((ROOT/'labs/review-r3/histograms/tests.yml').read_text())
    rules = json.loads((ROOT/'labs/review-r3/histograms/rules.yml').read_text())
    require({r['record']: r['expr'] for r in rules['groups'][0]['rules']} == {'r3:'+k:v['expr'] for k,v in expected.items()}, 'Rule/fixture drift')
    for test, (name, value) in zip(tests['tests'][0]['promql_expr_test'][:-1], expected.items()):
        require(test['expr'] == f'round(r3:{name} * 1000000000)' and
                test['exp_samples'] == [{'labels': '{}', 'value': math.floor(value['expected']*1e9+.5)}], 'Test/fixture drift')
    require(parse_dump('{__name__="r3:native_q25"} =>\n1.4142135623730951 @[60000]\n') == {'native_q25': math.sqrt(2)}, 'Prometheus dump parser')
    require(parse_dump('{__name__="other"} =>\n2 @[60000]\n') == {}, 'Foreign series accepted')
    xml = '<resultset xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><row><field name="null" xsi:nil="true"/><field name="zero">0</field><field name="empty"></field><field name="literal">NULL</field></row></resultset>'
    require(parse_xml(xml)[0]['rows'][0] == {'null': None, 'zero': '0', 'empty': '', 'literal': 'NULL'}, 'SQL NULL conflated with value')
    require(kb_fields('RssAnon:\t2 kB\nRssAnon: 3 kB\n') == {'RssAnon': 5120}, 'RSS units/aggregation')
    require(psi_fields('some avg10=0.00 avg60=1.00 avg300=2.00 total=42\n')['some']['total'] == 42, 'PSI parse')
    rejects(lambda: psi_fields('some total=1'), 'Missing PSI averages accepted')
    rejects(lambda: confined('.lab-runs', '../escape'), 'Path escape accepted')
    rejects(lambda: confined('.tools', '.lab-runs/asset'), 'Wrong boundary accepted')
    # Real r1 regressions: a cached empty sys join does not remove a direct lock
    # edge; an executed GTID does not advance the coordinator checkpoint.
    historical = json.loads((ROOT/'labs/results/1.1-r3/mysql-8.4.11-r1.json').read_text())
    observed = historical['scenarios']['8.4.11/next_key_lock']['observations']
    require(matching_lock_edge(observed['lock_rows'], observed['wait_rows'], False) and not observed['sys_rows'],
            'Historical empty sys join confused with missing next-key lock')
    altered = copy.deepcopy(observed['wait_rows']); altered[0]['BLOCKING_ENGINE_LOCK_ID'] = 'unrelated'
    require(not matching_lock_edge(observed['lock_rows'], altered, False), 'Unrelated lock IDs accepted')
    altered = copy.deepcopy(observed['lock_rows'])
    for row in altered:
        if row.get('LOCK_STATUS') == 'GRANTED' and row.get('INDEX_NAME') == 'k':
            row['LOCK_MODE'] = 'X,REC_NOT_GAP'
    require(not matching_lock_edge(altered, observed['wait_rows'], True), 'REC_NOT_GAP mistaken for GAP')
    baseline = historical['scenarios']['8.4.11/replication']['observations']['baseline']
    require(baseline['source_gtid_executed'] == baseline['replica_gtid_executed'] and
            not coordinator_positions_equal(baseline['status'][0]), 'GTID/checkpoint distinction lost')
    settled = dict(baseline['status'][0], Exec_Source_Log_Pos=baseline['status'][0]['Read_Source_Log_Pos'])
    require(coordinator_positions_equal(settled) and settled['Seconds_Behind_Source'] == '13', 'Position gate inspects SBS')
    require(not coordinator_positions_equal(dict(settled, Relay_Source_Log_File='different')), 'Rotation/name mismatch accepted')
    require(not coordinator_positions_equal(dict(settled, Read_Source_Log_Pos='0', Exec_Source_Log_Pos='0')), 'Invalid zero positions accepted')
    class FakeAdmin:
        def __init__(self, responses):
            self.responses, self.count = iter(responses), 0
        def query(self, sql):
            self.count += 1; self.last_query = 'synthetic-'+str(self.count)
            return next(self.responses)
    fake = FakeAdmin([[], [{'waiting_pid': '11', 'blocking_pid': '10'}], []])
    with patch('run_mysql_r3_lab.time.sleep') as delay:
        poll = sys_visibility(fake, 11, 10, [{'waiting_pid': '9', 'blocking_pid': '8'}], 'previous')
    require(poll['matched'] and len(poll['query_refs']) == 2 and delay.call_args.args == (.2,), 'Sys retry matched another transaction or omitted idle window')
    fake = FakeAdmin([[baseline['status'][0]], [settled]])
    replica = type('ReplicaFixture', (), {'admin': fake})()
    with patch('run_mysql_r3_lab.time.sleep'):
        poll = checkpoint_visibility(replica, 'Yes')
    require(poll['matched'] and len(poll['query_refs']) == 2, 'Checkpoint polling waited for expected SBS instead of positions')
    # Real gzip output and destructive-path fault injections stay inside the repo.
    parent = confined('.lab-runs', '.lab-runs/r3/preparation')
    parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='verify-', dir=parent))
    fixture_workspaces = []
    try:
        output = temporary/'bundle.json'
        with LabRun('verification-fixture', output, ['scripts/verify_review_r3.py']) as run:
            run.artifact('raw', b'complete raw data\n')
            run.record['scenarios']['fixture'] = scenario('test', 'test', 'test', {}, 'supported', 'synthetic verifier fixture, not a lab')
        record = verify_result(output)
        rejects(lambda: LabRun('duplicate', output, []), 'Result overwrite accepted')
        item = record['artifacts']['raw']
        bad = dict(item, path='../escape.gz')
        rejects(lambda: read_sidecar(output, bad), 'Sidecar path escape accepted')
        bad = dict(item, raw_sha256='0'*64)
        rejects(lambda: read_sidecar(output, bad), 'Tampered raw digest accepted')
        bad = dict(item, gzip_sha256='0'*64)
        rejects(lambda: read_sidecar(output, bad), 'Tampered gzip digest accepted')
        bad = dict(item, raw_bytes=1)
        rejects(lambda: read_sidecar(output, bad), 'Tampered raw length accepted')
        with LabRun('budget-fixture', temporary/'budget.json', []) as run:
            with patch('lab_r3_common.RAW_LIMIT', 4):
                rejects(lambda: run.artifact('too-large', b'12345'), 'Raw limit ignored')
            require(not run.record['artifacts'] and not list(run.sidecars.iterdir()), 'Oversize file silently published')
        with LabRun('failure-fixture', temporary/'failure.json', []) as run:
            fixture_workspaces.append(run.workspace)
            owned = run.workspace/'owned-native-fixture'
            owned.mkdir()
            run.native_dirs.append(owned)  # no outside-repository creation in preparation tests
            raise RuntimeError('Injected lab failure')
        failed = json.loads((temporary/'failure.json').read_text())
        require(failed['status'] == 'error' and failed['native_directories_removed'] and not owned.exists(), 'Exception cleanup failed')
        run = LabRun('log-failure-fixture', temporary/'log-failure.json', [])
        run.__enter__()
        fixture_workspaces.append(run.workspace)
        path = run.workspace/'log'
        handle = path.open('wb')
        run.logs.append(('fixture', path, handle))
        with patch.object(run, 'artifact', side_effect=RuntimeError('Injected archive failure')):
            run.__exit__(None, None, None)
        log_failed = json.loads((temporary/'log-failure.json').read_text())
        require(log_failed['status'] == 'error' and not log_failed['cleanup']['completed'], 'Archive failure reported as complete')
        run = LabRun('stop-failure-fixture', temporary/'stop-failure.json', [])
        run.__enter__()
        fixture_workspaces.append(run.workspace)
        owned = run.workspace/'native-data-fixture'
        owned.mkdir()
        run.native_dirs.append(owned)
        run.processes.append(object())
        with patch.object(run, 'stop', side_effect=RuntimeError('Injected stop failure')):
            run.__exit__(None, None, None)
        stopped = json.loads((temporary/'stop-failure.json').read_text())
        require(stopped['status'] == 'error' and not stopped['native_directories_removed'] and owned.exists(),
                'Data removed while process could still own it')
        run = LabRun('native-failure-fixture', temporary/'native-failure.json', [])
        run.__enter__()
        fixture_workspaces.append(run.workspace)
        owned = run.workspace/'native-data-fixture'
        owned.mkdir()
        run.native_dirs.append(owned)
        with patch('lab_r3_common.shutil.rmtree', side_effect=OSError('Injected native cleanup failure')):
            run.__exit__(None, None, None)
        native = json.loads((temporary/'native-failure.json').read_text())
        require(native['status'] == 'error' and not native['cleanup']['completed'] and owned.exists(), 'Native cleanup failure hidden')
        # Tar traversal/link-cycle tests never unpack anything.
        class FakeTar:
            def __init__(self, entries): self.entries = entries
            def getmembers(self): return self.entries
        entry = tarfile.TarInfo('../escape')
        rejects(lambda: archive_files(FakeTar([entry]), 'root'), 'Tar traversal accepted')
        link = tarfile.TarInfo('root/link'); link.type = tarfile.SYMTYPE; link.linkname = 'link'
        rejects(lambda: resolved_member({'root/link': link}, link), 'Tar link cycle accepted')
        # Runtime .deb validation: inspect tar streams without extracting them.
        def deb_stream(entries):
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode='w') as tf:
                for member in entries:
                    tf.addfile(member)
            return stream.getvalue()
        directory = tarfile.TarInfo('./usr/lib'); directory.type = tarfile.DIRTYPE
        library = tarfile.TarInfo('./usr/lib/libaio.so.1t64.0.2')
        alias = tarfile.TarInfo('./usr/lib/libaio.so.1t64')
        alias.type = tarfile.SYMTYPE; alias.linkname = 'libaio.so.1t64.0.2'
        package_members(deb_stream([directory, library, alias]))
        for bad_name in ('../escape', '/absolute', 'usr/../../escape', 'usr\\escape'):
            bad = tarfile.TarInfo(bad_name)
            rejects(lambda: package_members(deb_stream([bad])), 'Unsafe deb path accepted')
        for bad_target in ('../escape', '/absolute', 'dir/../../escape', 'dir\\escape'):
            bad = copy.copy(alias); bad.linkname = bad_target
            rejects(lambda: package_members(deb_stream([bad])), 'Unsafe deb link accepted')
        rejects(lambda: package_members(deb_stream([library, library])), 'Duplicate deb member accepted')
        bad = tarfile.TarInfo('device'); bad.type = tarfile.CHRTYPE
        rejects(lambda: package_members(deb_stream([bad])), 'Deb device member accepted')
        elf = temporary/'library'
        elf.write_bytes(b'\x7fELF\x02\x01'+bytes(12)+b'\x3e\x00')
        elf_amd64(elf)
        elf.write_bytes(b'\x7fELF\x01\x01'+bytes(12)+b'\x03\x00')
        rejects(lambda: elf_amd64(elf), '32-bit runtime library accepted as AMD64')
    finally:
        for path in fixture_workspaces:
            if path.exists():
                shutil.rmtree(confined('.lab-runs', path))
        shutil.rmtree(confined('.lab-runs', temporary))
    print('PASS: preparation, histogram arithmetic, NULL/proc/PSI parsers, MySQL lock/sys/checkpoint regressions, gzip integrity, deb path/link/ELF checks, boundaries and failure cleanup')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--result', action='append', default=[])
    p.add_argument('--allow-error', action='store_true', help='Inspect complete failure evidence; not publication approval')
    p.add_argument('--assets', action='store_true', help='Also hash extracted assets; no download or execution')
    p.add_argument('--published', action='store_true', help='Check immutable published summaries, gzip raw and archived inputs')
    args = p.parse_args()
    if not args.result and not args.published:
        preparation()
    if args.published:
        verify_published_review_r3()
    if args.assets:
        for asset in manifest()['assets']:
            checked_asset(asset['id'])
            archive = ROOT/('.tools/r3/archives' if asset['suite'] == 'mysql' else '.tools/r2/archives')/asset['name']
            require(sha256(archive) == asset['sha256'], 'Archive differs from pinned official asset')
            print('PASS: authenticated extraction receipt and file hashes:', asset['id'])
    for result in args.result:
        verify_result(result, args.allow_error)


if __name__ == '__main__':
    main()
