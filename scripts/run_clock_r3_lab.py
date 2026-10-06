"""Read-only WSL/Linux synchronization metadata; no external accuracy assertion."""
import argparse
import shutil
import time
from lab_r3_common import LabRun, linux_required, scenario
from run_linux_lab import read_adjtimex, clock_sample


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    linux_required()
    with LabRun('clock-state', args.output, ['scripts/run_clock_r3_lab.py', 'scripts/run_linux_lab.py']) as run:
        observations = {'adjtimex_before': read_adjtimex(), 'clock_before': clock_sample()}
        time.sleep(2)
        observations.update(clock_after=clock_sample(), adjtimex_after=read_adjtimex())
        observations['systemd_commands'] = []
        binary = shutil.which('timedatectl')
        if binary:
            for command in ('show', 'show-timesync', 'timesync-status'):
                result = run.command([binary, '--no-pager', '--no-ask-password', command], timeout=8,
                                     env={'SYSTEMD_PAGER': 'cat', 'SYSTEMD_COLORS': '0'})
                observations['systemd_commands'].append(result)
        else:
            observations['timedatectl_unavailable'] = True
        run.record['scenarios']['synchronization_metadata'] = scenario(
            'Read-only metadata may identify the local synchronization service state',
            'At least one synchronization-specific timedatectl command succeeds',
            'No attribution hypothesis: unavailable service is not proof that the clock is unsynchronized',
            observations,
            'supported' if any(r['returncode'] == 0 for r in observations['systemd_commands'][1:]) else 'blocked',
            'CLOCK_MONOTONIC_RAW and adjtimex are context only, not UTC calibration or proof of who set tick')
    raise SystemExit(run.exit_code)


if __name__ == '__main__':
    main()
