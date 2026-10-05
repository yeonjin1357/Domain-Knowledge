"""Validate round-1 synthetic cases and published Linux clock evidence.

These do not execute the Linux experiment or certify the host's clock accuracy.
"""
import argparse
import copy
import ctypes
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

from adapter_contract import transform
from run_linux_lab import Timex64, clock_quality

ROOT = Path(__file__).resolve().parents[1]


def verify_clock_sample(sample):
    for key in ('monotonic_ns', 'process_cpu_ns', 'raw_before_ns', 'raw_after_ns',
                'raw_midpoint_ns', 'read_bracket_ns'):
        assert type(sample[key]) is int and sample[key] >= 0, key
    assert sample['raw_before_ns'] <= sample['raw_after_ns']
    assert sample['raw_midpoint_ns'] == (sample['raw_before_ns'] + sample['raw_after_ns']) // 2
    assert sample['read_bracket_ns'] == sample['raw_after_ns'] - sample['raw_before_ns']


def verify_adjtimex(state):
    if state['available']:
        assert state['modes'] == 0 and state['return_clock_state'] >= 0
        assert type(state['tick_microseconds']) is int and state['tick_microseconds'] > 0
        assert type(state['freq_scaled_ppm']) is int
        assert state['freq_ppm'] == state['freq_scaled_ppm'] / 65536
        assert type(state['status_bits']) is int and state['status_bits'] >= 0


def verify_linux_record(record):
    """Check raw field relationships, including every idle sample, without rerunning Linux."""
    script = ROOT / 'scripts/run_linux_lab.py'
    assert record['script_sha256'] == hashlib.sha256(script.read_bytes()).hexdigest()
    experiments = record['experiments']
    for name in ('process_name_parsing', 'virtual_vs_resident', 'logical_vs_storage_io'):
        assert experiments[name]['status'] == 'passed', name
    assert experiments['cgroup_read_only']['status'] == 'observed'
    observations = experiments['cpu_accounting']
    ticks = observations['clock_ticks_per_second']
    intervals = observations['intervals']
    assert ticks > 0 and observations['status'] == 'observed'
    assert [i['workload'] for i in intervals] == ['busy', 'busy', 'busy', 'sleep']
    for item in intervals:
        before, after = item['before'], item['after']
        verify_clock_sample(before)
        verify_clock_sample(after)
        mono = (after['monotonic_ns'] - before['monotonic_ns']) / 1e9
        raw = (after['raw_midpoint_ns'] - before['raw_midpoint_ns']) / 1e9
        cpu = (after['process_cpu_ns'] - before['process_cpu_ns']) / 1e9
        assert mono > 0 and raw > 0 and cpu >= 0
        assert [item['first']['num_threads'], item['second']['num_threads']] == item['thread_counts']
        for key in ('pid', 'starttime_ticks'):
            assert item['first'][key] == item['second'][key], key
        delta = sum(item['second'][k] - item['first'][k] for k in ('utime_ticks', 'stime_ticks'))
        assert delta >= 0 and delta == item['delta_ticks']
        for key, expected in [('monotonic_seconds', mono), ('raw_seconds', raw),
                              ('process_clock_seconds', cpu), ('cpu_seconds', delta/ticks),
                              ('process_over_monotonic', cpu/mono), ('process_over_raw', cpu/raw),
                              ('monotonic_over_raw', mono/raw), ('tick_cpu_over_monotonic', delta/ticks/mono)]:
            assert math.isclose(item[key], expected, rel_tol=1e-12), key
        flags = clock_quality(mono, raw, cpu, item['thread_counts'], observations['diagnostic_relative_tolerance'])
        agreement = abs(delta/ticks - cpu) <= 3/ticks
        assert item['accounting_views_within_three_ticks'] == agreement
        if not agreement:
            flags.append('cpu_accounting_views_disagree')
        assert item['quality_flags'] == flags
        for key in ('adjtimex_before', 'adjtimex_after'):
            verify_adjtimex(item[key])
    assert observations['quality_flags'] == sorted({f for i in intervals for f in i['quality_flags']})

    series = observations.get('idle_clock_series', [])
    if not series:
        return None
    assert len(series) >= 2
    for point in series:
        verify_clock_sample(point['clocks'])
        verify_adjtimex(point['adjtimex'])
    for previous, current in zip(series, series[1:]):
        for key in ('monotonic_ns', 'raw_midpoint_ns'):
            assert current['clocks'][key] > previous['clocks'][key], key
        assert current['clocks']['process_cpu_ns'] >= previous['clocks']['process_cpu_ns']
    mono = (series[-1]['clocks']['monotonic_ns'] - series[0]['clocks']['monotonic_ns']) / 1e9
    raw = (series[-1]['clocks']['raw_midpoint_ns'] - series[0]['clocks']['raw_midpoint_ns']) / 1e9
    states = [point['adjtimex'] for point in series if point['adjtimex']['available']]
    result = {'sample_count': len(series), 'adjtimex_available_count': len(states),
              'monotonic_seconds': mono, 'raw_seconds': raw, 'monotonic_over_raw': mono/raw}
    if states:
        tick_values = [s['tick_microseconds'] for s in states]
        freq_values = [s['freq_ppm'] for s in states]
        result.update(tick_min=min(tick_values), tick_max=max(tick_values),
                      tick_distinct_count=len(set(tick_values)), tick_sample_mean_us=mean(tick_values),
                      freq_ppm_min=min(freq_values), freq_ppm_max=max(freq_values),
                      status_bits=sorted({s['status_bits'] for s in states}))
    return result


def verify_published_linux():
    """Verify immutable round-1b evidence and the numbers quoted by the book."""
    provenance = json.loads((ROOT/'review/evidence-provenance.json').read_text(encoding='utf-8'))
    entries = [entry for entry in provenance['published'] if entry['id'] == 'linux-clock-r1']
    assert len(entries) == 1
    entry = entries[0]
    assert entry['evidence'] == 'labs/results/1.1-linux-clock-r1.json'
    assert entry['runner'] == 'scripts/run_linux_lab.py'
    data = (ROOT/entry['evidence']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry['sha256']
    record = json.loads(data)
    assert record['script_sha256'] == entry['runner_sha256']
    assert record['run_at_utc'] == entry['run_at_utc']
    summary = verify_linux_record(record)
    assert record['kernel'] == '6.18.33.2-microsoft-standard-WSL2'
    assert record['python'] == '3.12.3'
    cpu = record['experiments']['cpu_accounting']
    assert cpu['clock_ticks_per_second'] == 100
    assert summary['sample_count'] == summary['adjtimex_available_count'] == 61
    assert summary['monotonic_seconds'] == 60.011948727
    assert summary['raw_seconds'] == 64.089720449
    assert (summary['tick_min'], summary['tick_max'], summary['tick_distinct_count']) == (9353, 9371, 7)
    assert summary['tick_sample_mean_us'] == 571189 / 61
    assert summary['freq_ppm_min'] == -49.82659912109375
    assert summary['freq_ppm_max'] == 40.45188903808594
    assert summary['status_bits'] == [8192]
    summary['nominal_tick_us_for_this_environment'] = 10000
    summary['tick_sample_mean_ratio'] = summary['tick_sample_mean_us'] / 10000

    chapter = (ROOT/'docs/host/linux-observation-lab.md').read_text(encoding='utf-8')
    for item in cpu['intervals']:
        assert item['thread_counts'] == [1, 1]
        assert item['adjtimex_before']['available'] and item['adjtimex_after']['available']
        for key in ('monotonic_seconds', 'raw_seconds', 'process_clock_seconds'):
            assert f'{item[key]:.6f}' in chapter, key
        if item['workload'] == 'busy':
            assert 'clock_slew_suspected' in item['quality_flags']
            assert 0.9999 < item['process_over_raw'] < 1.0001
    for key in ('monotonic_over_raw', 'tick_sample_mean_ratio'):
        assert f'{summary[key]:.8f}' in chapter, key
    for key in ('freq_ppm_min', 'freq_ppm_max'):
        assert f'{summary[key]:.5f}' in chapter, key
    print('PASS: published Linux clock evidence SHA256, runner hash, 4 intervals, 61 idle samples and chapter values')
    print('Idle MONO/RAW:', summary['monotonic_over_raw'],
          'sample mean tick/10000:', summary['tick_sample_mean_ratio'],
          'freq ppm range:', summary['freq_ppm_min'], summary['freq_ppm_max'])
    return summary


def verify_rejected_clock_records():
    """Ensure inconsistent raw samples fail without editing the published fixture."""
    record = json.loads((ROOT/'labs/results/1.1-linux-clock-r1.json').read_text(encoding='utf-8'))
    for defect in ('freq_conversion', 'raw_midpoint', 'idle_order'):
        changed = copy.deepcopy(record)
        series = changed['experiments']['cpu_accounting']['idle_clock_series']
        if defect == 'freq_conversion':
            series[0]['adjtimex']['freq_ppm'] += 1
        elif defect == 'raw_midpoint':
            series[0]['clocks']['raw_midpoint_ns'] += 1
        else:
            series[1]['clocks']['monotonic_ns'] = series[0]['clocks']['monotonic_ns']
        try:
            verify_linux_record(changed)
        except AssertionError:
            continue
        raise AssertionError(f'inconsistent record accepted: {defect}')
    print('PASS: 3 malformed evidence cases rejected (freq conversion, RAW midpoint, idle ordering)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linux-result', type=Path,
                        help='Optionally validate the corrected runner\'s real output, without rerunning it')
    args = parser.parse_args()
    cases = [
        (2, 2, 2, [1, 1], []),
        (2, 2.14, 2.1399, [1, 1],
         ['single_thread_cpu_over_monotonic', 'monotonic_raw_rate_difference', 'clock_slew_suspected']),
        (2, 2.13, .001, [1, 1], ['monotonic_raw_rate_difference']),
        (2, 2, 2.000001, [1, 1], ['single_thread_cpu_over_monotonic']),
        (2, 2, 2.2, [1, 1], ['single_thread_cpu_over_monotonic', 'cpu_raw_disagreement']),
        (2, 2, 4, [2, 2], []),
        (2, 2, 4, [1, 2], []),
        (2.2, 2, .001, [1, 1], ['monotonic_raw_rate_difference']),
        (0, 2, 1, [1, 1], ['invalid_clock_interval']),
        (2, 0, 1, [1, 1], ['invalid_clock_interval']),
        (2, 2, -1, [1, 1], ['invalid_clock_interval']),
    ]
    for mono, raw, cpu, threads, expected in cases:
        assert clock_quality(mono, raw, cpu, threads) == expected
    assert ctypes.sizeof(Timex64) == 208 and Timex64.tick.offset == 88
    assert Timex64().modes == 0

    previous = dict(collection_status='ok', unit='ms', value=2**32 - 10, time=0,
                    identity='device-1', epoch='boot-1', clock_epoch='clock-1', definition='io_ticks')
    current = dict(previous, value=20, time=1)
    # Without external evidence a decrease must not be labeled a known reset or
    # silently unwrapped. A confirmed epoch change is a different case.
    assert transform(previous, current) == {'quality': 'decrease', 'rate': None}
    assert transform(previous, dict(current, epoch='boot-2')) == {'quality': 'reset', 'rate': None}
    assert (20 - (2**32 - 10)) % 2**32 == 30  # hypothetical single-wrap delta
    assert math.isclose(2**32 / 1000 / 86400, 49.71026962962963)
    # Multiple wraps are indistinguishable from the same endpoints without a bound.
    assert (20 + 2**32) % 2**32 == 20
    print(f'PASS: {len(cases)} synthetic clock-quality cases, 2 ABI layout checks, 5 counter/wrap checks')
    print('No Linux syscall, clock calibration or real counter-wrap experiment was executed')
    verify_published_linux()
    verify_rejected_clock_records()
    if args.linux_result:
        record = json.loads(args.linux_result.read_text(encoding='utf-8'))
        summary = verify_linux_record(record)
        for item in record['experiments']['cpu_accounting']['intervals']:
            print(item['workload'], 'CPU/MONO', item['process_over_monotonic'],
                  'CPU/RAW', item['process_over_raw'], 'quality', item['quality_flags'])
        print('Supplied idle summary:', summary)
        print('PASS: supplied Linux evidence hash, arithmetic, quality flags and idle samples; not a clock calibration certificate')


if __name__ == '__main__':
    main()
