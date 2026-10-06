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
from run_mysql_r3_lab import parse_xml
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


def verify_published_review_r3():
    provenance = json.loads((ROOT/'review/evidence-provenance.json').read_text(encoding='utf-8'))
    entries = [p for p in provenance['published'] if p['id'].endswith('-r3')]
    require({p['id'] for p in entries} == {'linux-memory-r3', 'histograms-r3', 'clock-state-r3'}, 'Incomplete published r3 bundle set')
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
    print('PASS: round 3 published 7 supported scenarios, 61 complete gzip sidecars, provenance and publication arithmetic; no Linux rerun')


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
    print('PASS: preparation, histogram arithmetic, NULL/proc/PSI parsers, gzip integrity, deb path/link/ELF checks, boundaries and failure cleanup')


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
