"""Observe only this process and short, bounded workloads on Linux (including WSL).

No root, cgroup writes, cache dropping, OOM injection, or host reconfiguration.
"""

import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import mmap
import os
from pathlib import Path
import platform
import re
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


class Timeval64(ctypes.Structure):
    _fields_ = [('tv_sec', ctypes.c_int64), ('tv_usec', ctypes.c_int64)]


class Timex64(ctypes.Structure):
    """Linux glibc x86_64 LP64 ABI; do not call with an unverified ABI.

    Layout reference: glibc-2.39/sysdeps/unix/sysv/linux/bits/timex.h.
    Explicit 64-bit fields also allow layout checks on Windows without a syscall.
    """
    _fields_ = [
        ('modes', ctypes.c_uint32), ('offset', ctypes.c_int64),
        ('freq', ctypes.c_int64), ('maxerror', ctypes.c_int64),
        ('esterror', ctypes.c_int64), ('status', ctypes.c_int32),
        ('constant', ctypes.c_int64), ('precision', ctypes.c_int64),
        ('tolerance', ctypes.c_int64), ('time', Timeval64),
        ('tick', ctypes.c_int64), ('ppsfreq', ctypes.c_int64),
        ('jitter', ctypes.c_int64), ('shift', ctypes.c_int32),
        ('stabil', ctypes.c_int64), ('jitcnt', ctypes.c_int64),
        ('calcnt', ctypes.c_int64), ('errcnt', ctypes.c_int64),
        ('stbcnt', ctypes.c_int64), ('tai', ctypes.c_int32),
        ('reserved', ctypes.c_int32 * 11),
    ]


def read_adjtimex():
    # modes=0 only queries parameters; this runner never changes clock discipline.
    if (platform.system() != 'Linux' or platform.machine() != 'x86_64'
            or platform.libc_ver()[0] != 'glibc' or ctypes.sizeof(ctypes.c_long) != 8):
        return {'available': False, 'reason': 'unverified ABI; no syscall attempted'}
    assert ctypes.sizeof(Timex64) == 208 and Timex64.tick.offset == 88
    libc = ctypes.CDLL(None, use_errno=True)
    query = libc.adjtimex
    query.argtypes = [ctypes.POINTER(Timex64)]
    query.restype = ctypes.c_int
    state = Timex64()  # Zero initialization, including modes.
    result = query(ctypes.byref(state))
    if result == -1:
        return {'available': False, 'errno': ctypes.get_errno(), 'modes': 0}
    # TIME_ERROR (5) is a clock state, not an errno failure of this query.
    return {'available': True, 'modes': 0, 'return_clock_state': result,
            'tick_microseconds': state.tick, 'freq_scaled_ppm': state.freq,
            'freq_ppm': state.freq / 65536, 'status_bits': state.status}


def clock_sample():
    # Sequential reads are not simultaneous: preserve the RAW read bracket.
    raw_before = time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
    mono = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    cpu = time.clock_gettime_ns(time.CLOCK_PROCESS_CPUTIME_ID)
    raw_after = time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
    return {'monotonic_ns': mono, 'process_cpu_ns': cpu,
            'raw_before_ns': raw_before, 'raw_after_ns': raw_after,
            'raw_midpoint_ns': (raw_before + raw_after) // 2,
            'read_bracket_ns': raw_after - raw_before}


def clock_quality(mono, raw, cpu, threads, tolerance=0.01):
    """Diagnostic heuristics, not proof that RAW is calibrated physical time.

    One percent is a lab reporting threshold, not a universal clock-error bound.
    A small >1 CPU/MONO value is retained too; sampling noise is possible.
    """
    if mono <= 0 or raw <= 0 or cpu < 0:
        return ['invalid_clock_interval']
    flags = []
    single = threads == [1, 1]
    if single and cpu / mono > 1:
        flags.append('single_thread_cpu_over_monotonic')
    if abs(mono / raw - 1) > tolerance:
        flags.append('monotonic_raw_rate_difference')
    if (single and cpu / mono > 1 + tolerance and mono / raw < 1 - tolerance
            and abs(cpu / raw - 1) <= tolerance):
        flags.append('clock_slew_suspected')
    if single and cpu / raw > 1 + tolerance:
        flags.append('cpu_raw_disagreement')
    return flags


def observe_interval(duration, workload, ticks):
    adjustment_before = read_adjtimex()
    before_stat = process_stat()
    before = clock_sample()
    if workload == 'sleep':
        time.sleep(duration)
    else:
        deadline = before['monotonic_ns'] + int(duration * 1e9)
        work = 0
        while time.clock_gettime_ns(time.CLOCK_MONOTONIC) < deadline:
            work = (work + 1) % 1000003
    after = clock_sample()
    after_stat = process_stat()
    adjustment_after = read_adjtimex()
    mono = (after['monotonic_ns'] - before['monotonic_ns']) / 1e9
    raw = (after['raw_midpoint_ns'] - before['raw_midpoint_ns']) / 1e9
    cpu = (after['process_cpu_ns'] - before['process_cpu_ns']) / 1e9
    delta_ticks = sum(after_stat[k] - before_stat[k] for k in ('utime_ticks', 'stime_ticks'))
    assert before_stat['starttime_ticks'] == after_stat['starttime_ticks']
    assert mono > 0 and raw > 0 and cpu >= 0 and delta_ticks >= 0
    # Related kernel CPU-accounting views; agreement does NOT calibrate wall time.
    agreement = abs(delta_ticks / ticks - cpu) <= 3 / ticks
    threads = [before_stat['num_threads'], after_stat['num_threads']]
    flags = clock_quality(mono, raw, cpu, threads)
    if not agreement:
        flags.append('cpu_accounting_views_disagree')
    return {'workload': workload, 'target_monotonic_seconds': duration,
            'before': before, 'after': after,
            'first': before_stat, 'second': after_stat, 'thread_counts': threads,
            'monotonic_seconds': mono, 'raw_seconds': raw, 'process_clock_seconds': cpu,
            'delta_ticks': delta_ticks, 'cpu_seconds': delta_ticks / ticks,
            'process_over_monotonic': cpu / mono, 'process_over_raw': cpu / raw,
            'monotonic_over_raw': mono / raw,
            'tick_cpu_over_monotonic': delta_ticks / ticks / mono,
            'accounting_views_within_three_ticks': agreement,
            'adjtimex_before': adjustment_before, 'adjtimex_after': adjustment_after,
            'quality_flags': flags}


def process_stat():
    raw = Path('/proc/self/stat').read_text()
    start, end = raw.index('('), raw.rindex(')')
    fields = raw[end+2:].split()
    return {"pid":int(raw[:start]), "comm":raw[start+1:end], "state":fields[0],
            "utime_ticks":int(fields[11]), "stime_ticks":int(fields[12]),
            "num_threads":int(fields[17]),
            "starttime_ticks":int(fields[19]), "vsize_bytes":int(fields[20]),
            "rss_pages":int(fields[21])}


def key_values(path):
    return {key.rstrip(':'): int(value.split()[0]) for key, value in
            (line.split(None,1) for line in Path(path).read_text().splitlines())}


def mapping_stats(address):
    selected, result = False, {}
    for line in Path('/proc/self/smaps').read_text().splitlines():
        header = re.match(r'^([0-9a-f]+)-([0-9a-f]+) ', line)
        if header:
            if selected:
                break
            selected = int(header[1],16) <= address < int(header[2],16)
        elif selected and ':' in line:
            key, value = line.split(':',1)
            if key in {'Size','Rss','Pss','Private_Dirty','Anonymous','AnonHugePages'}:
                result[key+'_KiB'] = int(value.split()[0])
    assert result, 'Mapping not found in own smaps'
    return result


def run(clock_observation_seconds=0):
    evidence = {}
    libc = ctypes.CDLL(None, use_errno=True)
    previous = ctypes.create_string_buffer(16)
    assert libc.prctl(16, previous, 0, 0, 0) == 0  # PR_GET_NAME
    try:
        assert libc.prctl(15, ctypes.c_char_p(b'dk ) worker'),0,0,0) == 0  # PR_SET_NAME
        parsed = process_stat()
        assert parsed['comm'] == 'dk ) worker' and parsed['pid'] == os.getpid()
        evidence['process_name_parsing'] = {'status':'passed','observed_comm':parsed['comm'],
                                           'starttime_ticks':parsed['starttime_ticks']}
    finally:
        libc.prctl(15, previous, 0, 0, 0)

    ticks = os.sysconf('SC_CLK_TCK')
    intervals = [observe_interval(duration, 'busy', ticks) for duration in (.2, 1.0, 2.0)]
    intervals.append(observe_interval(2.0, 'sleep', ticks))
    evidence['cpu_accounting'] = {
        'status': 'observed', 'clock_ticks_per_second': ticks, 'intervals': intervals,
        'quality_flags': sorted({flag for interval in intervals for flag in interval['quality_flags']}),
        'diagnostic_relative_tolerance': 0.01,
        'interpretation': 'Self-process CPU-accounting agreement is not elapsed-time calibration. '
                          'RAW is an unadjusted comparison clock, not proof of accurate physical time. '
                          'Thread counts are endpoint observations; this runner creates no worker threads.'}
    evidence['cpu_accounting']['clock_implementations']={
        name:vars(time.get_clock_info(name)) for name in ('monotonic','process_time')}
    if clock_observation_seconds:
        series = []
        for _ in range(clock_observation_seconds):
            series.append({'clocks': clock_sample(), 'adjtimex': read_adjtimex()})
            time.sleep(1)
        series.append({'clocks': clock_sample(), 'adjtimex': read_adjtimex()})
        evidence['cpu_accounting']['idle_clock_series'] = series

    allocation = 32*1024*1024
    with mmap.mmap(-1, allocation, flags=mmap.MAP_PRIVATE|mmap.MAP_ANONYMOUS) as region:
        address = ctypes.addressof(ctypes.c_char.from_buffer(region))
        reserved = mapping_stats(address)
        page_size = os.sysconf('SC_PAGE_SIZE')
        for offset in range(0,allocation,page_size):
            region[offset] = 1
        touched = mapping_stats(address)
        assert touched['Rss_KiB']-reserved['Rss_KiB'] >= allocation/1024*.9
        evidence['virtual_vs_resident'] = {'status':'passed','requested_bytes':allocation,
            'page_size_bytes':page_size,'after_mapping_before_touch':reserved,'after_touch':touched,
            'interpretation':'mapping can merge with adjacent mappings; not a leak or cgroup OOM experiment'}

    scratch = ROOT / '.lab-runs'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='domain-knowledge-io-', dir=scratch) as directory:
        payload = b'x' * (1024*1024)
        file = Path(directory) / 'payload.bin'
        with file.open('wb') as stream:
            before = key_values('/proc/self/io')
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            after_write = key_values('/proc/self/io')
        assert file.read_bytes() == payload and file.read_bytes() == payload
        after_read = key_values('/proc/self/io')
        assert after_write['wchar']-before['wchar'] >= len(payload)
        assert after_read['rchar']-after_write['rchar'] >= 2*len(payload)
        evidence['logical_vs_storage_io'] = {'status':'passed','payload_bytes':len(payload),
            'before':before,'after_write_and_fsync':after_write,'after_two_reads':after_read,
            'interpretation':'own proc-file reads also contribute to rchar; no cache was dropped'}

    membership = Path('/proc/self/cgroup').read_text().strip()
    entry = next((line[3:] for line in membership.splitlines() if line.startswith('0::')), None)
    counters = {}
    if entry is not None:
        root = Path('/sys/fs/cgroup').resolve()
        group = (root / entry.lstrip('/')).resolve()
        if group.is_relative_to(root):
            for name in ('cpu.stat','cpu.max','cpuset.cpus.effective','memory.current','memory.max',
                         'memory.high','memory.events','memory.events.local','memory.swap.current','memory.swap.max'):
                try:
                    counters[name] = (group / name).read_text().strip()
                except OSError as exc:
                    counters[name] = {'unavailable':exc.__class__.__name__}
    evidence['cgroup_read_only'] = {'status':'observed','membership':membership,'fields':counters,
        'interpretation':'existing group may contain other processes; no isolated cgroup workload or limit experiment'}
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.lab-runs/linux.json')
    parser.add_argument('--clock-observation-seconds', type=int, default=0,
                        help='Additional idle clock/adjtimex series, 0..120 seconds')
    args = parser.parse_args()
    if not 0 <= args.clock_observation_seconds <= 120:
        parser.error('--clock-observation-seconds must be between 0 and 120')
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / '.lab-runs').resolve()):
        parser.error('--output must stay inside this repository\'s .lab-runs directory')
    if platform.system() != 'Linux':
        raise SystemExit('This experiment requires Linux procfs')
    result = {'run_at_utc':datetime.now(timezone.utc).isoformat(),'kernel':platform.release(),
              'python':platform.python_version(),'environment':'Linux; WSL if identified in kernel release',
              'experiments':run(args.clock_observation_seconds),
              'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('RECORDED: process parsing, memory and I/O checks; CPU clock quality and cgroup observations')
    print('CPU quality flags:', result['experiments']['cpu_accounting']['quality_flags'])


if __name__ == '__main__':
    main()
