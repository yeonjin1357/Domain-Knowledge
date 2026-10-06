"""Evaluate fixed classic/native distributions with the authenticated r2 promtools."""
import argparse
import json
import math
import re
import shutil
from lab_r3_common import LabRun, ROOT, checked_asset, linux_required, scenario, sha256

FIXTURES = 'labs/review-r3/histograms/'


def parse_dump(text):
    """Parse actual scalar recording-rule samples, not copied expected values."""
    values, current = {}, None
    for line in text.splitlines():
        if line.startswith('{'):
            match = re.search(r'__name__="r3:([a-z0-9_]+)"', line)
            current = match[1] if match else None
        point = re.search(r'(?:^|=>\s*)(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?) @\[(\d+)\]', line)
        if current and point and int(point[2]) == 60000:
            if current in values:
                raise ValueError('Duplicate recording-rule point')
            values[current] = float(point[1])
    return values


def evaluate(run, asset_id):
    asset, directory, receipt = checked_asset(asset_id)
    tool = directory/'promtool'
    version = run.command([tool, '--version'])
    help_result = run.command([tool, 'test', 'rules', '--help'])
    result = run.command([tool, 'test', 'rules', '--debug', run.workspace/'tests.yml'], timeout=60)
    fixture = json.loads((ROOT/FIXTURES/'fixture.json').read_text())
    measured = parse_dump(run.raw(result['artifact']).decode('utf-8', 'strict'))
    expected = {key: value['expected'] for key, value in fixture['expressions'].items()}
    complete = measured.keys() == expected.keys()
    matched = complete and all(math.isclose(measured[k], v, rel_tol=1e-12, abs_tol=1e-12) for k, v in expected.items())
    verdict = 'supported' if result['returncode'] == 0 and matched else 'refuted' if complete else 'inconclusive'
    return scenario('Matching bucket populations retain count but differ by interpolation schema',
                    'Without feature flags all tests pass and actual debug values match independent formulas',
                    'Complete measured values disagree or rule assertions fail',
                    {'version': asset['version'], 'binary_sha256': sha256(tool),
                     'version_command': version, 'help_command': help_result, 'test_command': result,
                     'measured_values': measured, 'expected_from_formulas': expected,
                     'feature_status': fixture['feature_status'], 'feature_sources': fixture['feature_sources']},
                    verdict, 'Debug dump supplies numbers; missing/unrecognized output is inconclusive, never replaced with expectations')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    linux_required()
    inputs = ['scripts/run_histogram_r3_lab.py']+[FIXTURES+n for n in ('fixture.json', 'rules.yml', 'tests.yml')]
    with LabRun('histograms', args.output, inputs) as run:
        for name in ('rules.yml', 'tests.yml'):
            shutil.copyfile(ROOT/FIXTURES/name, run.workspace/name)
        for version in ('3.13.4', '3.15.0'):
            run.record['scenarios'][version] = evaluate(run, 'prometheus-'+version)
    raise SystemExit(run.exit_code)


if __name__ == '__main__':
    main()
