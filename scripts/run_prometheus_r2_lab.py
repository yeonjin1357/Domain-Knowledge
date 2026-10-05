"""Reevaluate unchanged book rules/tests with two pinned Linux promtool binaries."""
import argparse
import json
import shutil

from lab_r2_common import ROOT, LabRun, binary, linux_required, scenario, sha256

VERSIONS = ('3.13.4', '3.15.0')
INPUTS = ['scripts/run_prometheus_r2_lab.py', 'scripts/get_review_r2_assets.py',
          'labs/prometheus/rules.yml', 'labs/prometheus/tests.yml']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='.lab-runs/r2/prometheus.json')
    parser.add_argument('--plan', action='store_true')
    args = parser.parse_args()
    if args.plan:
        print(json.dumps({'versions': VERSIONS, 'inputs': INPUTS,
                          'success': 'check rules and test rules both exit 0',
                          'refutation': 'promtool accepts the fixture but reports a rule/expression/alert mismatch',
                          'failure_distinction': 'missing binary, unsupported invocation or startup error is an error, not a semantic refutation'}, indent=2))
        return
    linux_required()
    with LabRun('prometheus', args.output, INPUTS) as lab:
        fixtures = lab.workspace/'fixtures'
        fixtures.mkdir()
        for name in ('rules.yml', 'tests.yml'):
            shutil.copyfile(ROOT/'labs/prometheus'/name, fixtures/name)
        lab.record['fixture_sha256'] = {name: sha256(fixtures/name) for name in ('rules.yml','tests.yml')}
        for version in VERSIONS:
            tool = binary('prometheus-'+version, 'promtool')
            observed = lab.command([tool, '--version'])
            if observed['returncode'] or version not in observed['stdout']+observed['stderr']:
                raise RuntimeError('Unexpected promtool version: '+str(observed))
            commands = [lab.command([tool, 'check', 'rules', 'rules.yml'], cwd=fixtures, timeout=30),
                        lab.command([tool, 'test', 'rules', 'tests.yml'], cwd=fixtures, timeout=60)]
            success = all(c['returncode'] == 0 for c in commands)
            diagnostic = '\n'.join(c['stdout']+c['stderr'] for c in commands)
            semantic_failure = 'FAILED' in diagnostic or 'expected:' in diagnostic
            verdict = 'supported' if success else 'refuted' if semantic_failure else 'error'
            lab.record['scenarios'][version] = scenario(
                '기존 규칙과 표현식·alert 기대값이 이 promtool에서도 성립한다.',
                'check rules와 test rules가 모두 exit 0.',
                '입력을 평가한 promtool이 규칙·표현식·alert 불일치를 보고한다.',
                {'version': observed, 'executable_sha256': sha256(tool), 'commands': commands}, verdict,
                'Actual stdout/stderr and exit codes retained; no Prometheus server or production query.')
    raise SystemExit(lab.exit_code)


if __name__ == '__main__':
    main()
