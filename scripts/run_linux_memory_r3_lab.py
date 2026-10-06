"""Non-root Linux: small owned mappings, proc accounting, PSI and vmstat availability."""
import argparse
import json
import mmap
import os
from pathlib import Path
import random
import re
import select
import statistics
import subprocess
import sys
import time
import uuid

from lab_r3_common import LabRun, ROOT, confined, linux_required, scenario, stamp

FIELDS = ('VmRSS', 'RssAnon', 'RssFile', 'RssShmem', 'VmSwap')


def kb_fields(text):
    result = {}
    for line in text.splitlines():
        m = re.fullmatch(r'(\w+):\s+(\d+) kB', line)
        if m:
            result[m[1]] = result.get(m[1], 0) + int(m[2])*1024
    return result


def psi_fields(text):
    result = {}
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0] not in ('some', 'full'):
            raise ValueError('Unknown PSI record type')
        values = dict(p.split('=', 1) for p in parts[1:])
        result[parts[0]] = {k: int(v) if k == 'total' else float(v) for k, v in values.items()}
        if not {'avg10', 'avg60', 'avg300', 'total'} <= values.keys():
            raise ValueError('Missing PSI fields')
    return result


def cgroup_path():
    rows = Path('/proc/self/cgroup').read_text().splitlines()
    row = next((s[3:] for s in rows if s.startswith('0::')), None)
    if row is None:
        return None
    base = Path('/sys/fs/cgroup').resolve()
    # Namespaced cgroup mounts may expose the current cgroup as their root.
    candidate = (base/row.lstrip('/')).resolve()
    if candidate.is_relative_to(base) and (candidate/'cgroup.procs').is_file():
        return candidate
    if (base/'cgroup.procs').is_file() and str(os.getpid()) in (base/'cgroup.procs').read_text().split():
        return base
    return None


def memory_guard(required):
    available = kb_fields(Path('/proc/meminfo').read_text()).get('MemAvailable', 0)
    observations = {'mem_available_bytes': available, 'required_headroom_bytes': required,
                    'finite_cgroup_headroom_bytes': [], 'cgroup_limit_scope': 'current cgroup and visible ancestors'}
    path = cgroup_path()
    base = Path('/sys/fs/cgroup').resolve()
    while path and path.is_relative_to(base):
        if (path/'memory.max').is_file():
            limit = (path/'memory.max').read_text().strip()
            if limit != 'max':
                current = int((path/'memory.current').read_text())
                observations['finite_cgroup_headroom_bytes'].append(int(limit)-current)
        if path == base:
            break
        path = path.parent
    observations['allowed'] = available >= required and all(
        v >= required for v in observations['finite_cgroup_headroom_bytes'])
    observations['limitation'] = 'Instant guard, not a reservation; hidden ancestor limits may be unknown'
    return observations


def worker(kind, size, file):
    linux_required()
    file = confined('.lab-runs', file)
    if kind not in ('anonymous', 'file', 'memfd') or not 4*1024*1024 <= size <= 16*1024*1024 or size % 4096:
        raise ValueError('Invalid owned memory worker parameters')
    fd = None
    if kind == 'file':
        fd = os.open(file, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
        for _ in range(size//4096):
            os.write(fd, b'x'*4096)
    elif kind == 'memfd':
        fd = os.memfd_create('r3-owned-memory', os.MFD_CLOEXEC)
        os.ftruncate(fd, size)
    print(json.dumps({'ready': True, 'pid': os.getpid()}), flush=True)
    mapping = None
    for line in sys.stdin:
        command = line.strip()
        if command == 'allocate':
            if kind == 'anonymous':
                mapping = mmap.mmap(-1, size, flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS)
            elif kind == 'file':
                mapping = mmap.mmap(fd, size, flags=mmap.MAP_PRIVATE, prot=mmap.PROT_READ)
            else:
                mapping = mmap.mmap(fd, size, flags=mmap.MAP_SHARED)
            checksum = 0
            for offset in range(0, size, os.sysconf('SC_PAGE_SIZE')):
                if kind == 'file':
                    checksum += mapping[offset]
                else:
                    mapping[offset] = 1
            print(json.dumps({'allocated_bytes': size, 'touch_checksum': checksum}), flush=True)
        elif command == 'release':
            mapping.close()
            mapping = None
            print('{"released": true}', flush=True)
        elif command == 'exit':
            break
    if mapping is not None:
        mapping.close()
    if fd is not None:
        os.close(fd)


def acknowledge(process):
    if not select.select([process.stdout], [], [], 8)[0]:
        raise TimeoutError('Memory worker acknowledgement timed out')
    raw = process.stdout.readline()
    if not raw:
        raise RuntimeError('Memory worker exited')
    return json.loads(raw)


def snapshot(run, pid, name):
    values = {'started': stamp(), 'pid': pid, 'page_size_bytes': os.sysconf('SC_PAGE_SIZE')}
    for field in ('status', 'statm', 'smaps_rollup', 'smaps'):
        try:
            text = Path(f'/proc/{pid}/{field}').read_text()
            artifact = run.artifact(f'{name}-{field}', text)
            parsed = list(map(int, text.split())) if field == 'statm' else kb_fields(text)
            values[field] = {'artifact': artifact, 'values': parsed}
        except (PermissionError, FileNotFoundError) as error:
            values[field] = {'unavailable': repr(error)}
    status = values['status'].get('values', {})
    pages = values['statm'].get('values')
    values['comparison_bytes'] = {
        'status': {key: status.get(key) for key in FIELDS},
        'status_rss_components_sum': sum(status[k] for k in ('RssAnon', 'RssFile', 'RssShmem'))
            if all(k in status for k in ('RssAnon', 'RssFile', 'RssShmem')) else None,
        'statm_resident': pages[1]*values['page_size_bytes'] if pages else None,
        'statm_shared': pages[2]*values['page_size_bytes'] if pages else None,
        'smaps_rss': values['smaps'].get('values', {}).get('Rss'),
        'smaps_rollup_rss': values['smaps_rollup'].get('values', {}).get('Rss')}
    values['statm_columns'] = ['size', 'resident', 'shared', 'text', 'lib_unused', 'data', 'dt_unused']
    values['statm_unit'] = 'pages; comparisons above multiply by page_size_bytes'
    values['finished'] = stamp()
    return values


def cost(pid, samples):
    measurements = {key: [] for key in ('status', 'smaps_rollup', 'smaps')}
    rng = random.Random(3)
    clock = lambda: time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
    for _ in range(samples):
        order = list(measurements)
        rng.shuffle(order)
        for field in order:
            try:
                start = clock()
                data = Path(f'/proc/{pid}/{field}').read_bytes()
                elapsed = clock()-start
                measurements[field].append({'elapsed_raw_ns': elapsed, 'bytes': len(data)})
            except (PermissionError, FileNotFoundError):
                pass
    return {key: {'samples': vals, 'median_raw_ns': statistics.median(v['elapsed_raw_ns'] for v in vals),
                  'p95_raw_ns': sorted(v['elapsed_raw_ns'] for v in vals)[max(0, (95*len(vals)+99)//100-1)]}
            for key, vals in measurements.items() if vals}


def mapping_test(run, kind, size, samples):
    guard = memory_guard(256*1024*1024)
    if not guard['allowed'] or (kind == 'memfd' and not hasattr(os, 'memfd_create')):
        return scenario('Owned mapping appears in the corresponding RSS class',
                        'Expected smaps_rollup class rises by >=80% of mapping bytes',
                        'Complete rollup does not show that rise', guard, 'blocked', 'Memory headroom/API unavailable')
    args = [sys.executable, '-B', str(Path(__file__).resolve()), '--worker', kind,
            str(size), str(run.workspace/(kind+'.data'))]
    log = run.workspace/(kind+'.stderr')
    handle = log.open('wb')
    process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=handle,
                               bufsize=0, cwd=run.workspace, env=run.environment(), start_new_session=True)
    run.processes.append(process)
    run.logs.append((kind, log, handle))
    acks = [acknowledge(process)]
    before = snapshot(run, process.pid, kind+'-before')
    process.stdin.write(b'allocate\n')
    acks.append(acknowledge(process))
    allocated = snapshot(run, process.pid, kind+'-allocated')
    timings = cost(process.pid, samples)
    process.stdin.write(b'release\n')
    acks.append(acknowledge(process))
    released = snapshot(run, process.pid, kind+'-released')
    process.stdin.write(b'exit\n')
    process.wait(timeout=8)
    process.stdin.close()
    process.stdout.close()
    key = {'anonymous': 'Pss_Anon', 'file': 'Pss_File', 'memfd': 'Pss_Shmem'}[kind]
    old = before['smaps_rollup'].get('values', {}).get(key)
    new = allocated['smaps_rollup'].get('values', {}).get(key)
    delta = None if old is None or new is None else new-old
    verdict = 'inconclusive' if delta is None else ('supported' if delta >= size*.8 else 'refuted')
    observations = {'guard': guard, 'mapping_bytes': size, 'expected_class': key, 'class_delta_bytes': delta,
                    'worker_acknowledgements': acks, 'before': before, 'allocated': allocated,
                    'released': released, 'read_cost': timings}
    observations['status_delta_bytes'] = {
        k: allocated['status']['values'][k]-before['status']['values'][k]
        for k in FIELDS if k in allocated['status'].get('values', {}) and k in before['status'].get('values', {})}
    return scenario('Private anonymous/file/shared memfd map increases its own resident class',
                    'Quiescent child rollup class rises by >=80% of touched mapping bytes',
                    'Complete rollup class rises by less than 80%', observations, verdict,
                    'PSS equals RSS for these singly mapped owned pages. status/statm are approximate; reads are sequential. Timing is local, not a universal ranking.')


def facilities(run, probe):
    psi = {}
    for field in ('cpu', 'memory', 'io', 'irq'):
        try:
            text = Path('/proc/pressure', field).read_text()
            psi[field] = {'artifact': run.artifact('psi-'+field, text), 'values': psi_fields(text),
                          'units': 'avg: percent; total: microseconds'}
        except OSError as error:
            psi[field] = {'unavailable': repr(error)}
        except ValueError as error:
            psi[field] = {'parse_error': repr(error)}
    text = Path('/proc/vmstat').read_text()
    pattern = r'^(oom_kill|pgscan_\w+|pgsteal_\w+|allocstall_\w+|workingset_refault_\w+) (\d+)$'
    counters = {k: int(v) for k, v in re.findall(pattern, text, re.M)}
    vmstat = {'artifact': run.artifact('vmstat', text), 'selected_counters': counters,
              'missing_prefixes': [p for p in ('oom_kill', 'pgscan_', 'pgsteal_', 'allocstall_', 'workingset_refault_') if not any(k.startswith(p) for k in counters)]}
    cg = {'path': None, 'probe_requested': probe, 'child_created': False}
    path = cgroup_path()
    if path:
        cg['path'] = str(path)
        for field in ('cgroup.controllers', 'cgroup.subtree_control', 'memory.current', 'memory.max',
                      'memory.events', 'memory.events.local', 'memory.pressure', 'cpu.pressure', 'io.pressure'):
            try:
                cg[field] = {'artifact': run.artifact('cgroup-'+field, (path/field).read_bytes())}
            except OSError as error:
                cg[field] = {'unavailable': repr(error)}
        if probe:
            child = path/('domain-r3-empty-'+uuid.uuid4().hex)
            try:
                child.mkdir()  # no controller enable, limit write, or process migration
                cg['child_created'] = True
                cg['child_files'] = sorted(p.name for p in child.iterdir())
            except OSError as error:
                cg['creation_unavailable'] = repr(error)
            finally:
                if cg['child_created']:
                    child.rmdir()
                    cg['child_removed'] = True
    return scenario('Kernel exposes parseable PSI/vmstat and optional delegated cgroup facilities',
                    'Present files parse; missing capabilities are recorded explicitly',
                    'A present PSI file cannot be parsed', {'psi': psi, 'vmstat': vmstat, 'cgroup': cg},
                    'refuted' if any('parse_error' in v for v in psi.values()) else 'supported',
                    'Availability only; no induced pressure, OOM, reclaim, controller change, or child migration')


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--worker':
        worker(sys.argv[2], int(sys.argv[3]), sys.argv[4])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--mapping-mib', type=int, choices=range(4, 17), default=8)
    parser.add_argument('--cost-samples', type=int, choices=range(10, 101), default=30)
    parser.add_argument('--probe-delegated-cgroup', action='store_true')
    args = parser.parse_args()
    linux_required()
    with LabRun('linux-memory', args.output, ['scripts/run_linux_memory_r3_lab.py']) as run:
        run.record['configuration'] = vars(args)
        run.record['scenarios']['facilities'] = facilities(run, args.probe_delegated_cgroup)
        for kind in ('anonymous', 'file', 'memfd'):
            run.record['scenarios'][kind] = mapping_test(run, kind, args.mapping_mib*1024*1024, args.cost_samples)
    raise SystemExit(run.exit_code)


if __name__ == '__main__':
    main()
