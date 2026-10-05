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


def process_stat():
    raw = Path('/proc/self/stat').read_text()
    start, end = raw.index('('), raw.rindex(')')
    fields = raw[end+2:].split()
    return {"pid":int(raw[:start]), "comm":raw[start+1:end], "state":fields[0],
            "utime_ticks":int(fields[11]), "stime_ticks":int(fields[12]),
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


def run():
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
    first = process_stat()
    wall_start, cpu_start = time.monotonic(), time.process_time()
    work = 0
    while time.process_time() - cpu_start < .2:
        work = (work+1) % 1000003
    cpu_elapsed, wall_elapsed = time.process_time()-cpu_start, time.monotonic()-wall_start
    second = process_stat()
    delta_ticks = second['utime_ticks'] + second['stime_ticks'] - first['utime_ticks'] - first['stime_ticks']
    assert first['starttime_ticks'] == second['starttime_ticks'] and delta_ticks > 0
    cpu_seconds = delta_ticks / ticks
    assert abs(cpu_seconds-cpu_elapsed) <= 3/ticks, (cpu_seconds,cpu_elapsed)
    evidence['cpu_accounting'] = {'status':'passed','clock_ticks_per_second':ticks,
        'first':first,'second':second,'delta_ticks':delta_ticks,'cpu_seconds':cpu_seconds,
        'wall_seconds':wall_elapsed,'process_clock_seconds':cpu_elapsed,
        'mean_cpu_cores':cpu_seconds/wall_elapsed,
        'interpretation':'short self-process observation, not whole Windows host or performance benchmark'}
    longer=[]
    for duration in (1.0,2.0):
        first_sample=process_stat()
        wall_begin,cpu_begin=time.monotonic(),time.process_time()
        while time.monotonic()-wall_begin < duration:
            work=(work+1)%1000003
        cpu_delta=time.process_time()-cpu_begin
        wall_delta=time.monotonic()-wall_begin
        last_sample=process_stat()
        tick_delta=(last_sample['utime_ticks']+last_sample['stime_ticks']
                    -first_sample['utime_ticks']-first_sample['stime_ticks'])
        longer.append({'target_wall_seconds':duration,'wall_seconds':wall_delta,
                       'process_clock_seconds':cpu_delta,'delta_ticks':tick_delta,
                       'accounting_ratio':tick_delta/ticks/wall_delta})
    evidence['cpu_accounting']['additional_intervals']=longer
    evidence['cpu_accounting']['clock_implementations']={
        name:vars(time.get_clock_info(name)) for name in ('monotonic','process_time')}
    evidence['cpu_accounting']['quality_note']='Ratios compare independently sampled clock/accounting sources; retain values, do not silently clamp or infer hardware throughput.'

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

    with tempfile.TemporaryDirectory(prefix='domain-knowledge-io-') as directory:
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
    args = parser.parse_args()
    if platform.system() != 'Linux':
        raise SystemExit('This experiment requires Linux procfs')
    result = {'run_at_utc':datetime.now(timezone.utc).isoformat(),'kernel':platform.release(),
              'python':platform.python_version(),'environment':'Linux; WSL if identified in kernel release',
              'experiments':run(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS: 4 bounded Linux experiments; existing cgroup read separately; no host configuration changed')


if __name__ == '__main__':
    main()
