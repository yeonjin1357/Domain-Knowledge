"""Preparation and saved-evidence checks. Does not execute any Linux server/tool."""
import argparse
import ast
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import tarfile
import uuid

from lab_r2_common import ROOT, LabRun, binary, confined, manifest, sha256
from run_otel_r2_lab import counter, parse_metrics, retry_verdict, configuration
from run_postgres_r2_lab import parse_vacuum, horizon_verdict


def validate_preparation():
    checked=0
    for path in sorted((ROOT/'scripts').glob('*r2*.py')):
        ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
        checked+=1
    for value in ('docs/escape.json','.lab-runs/../labs/results/no.json','.lab-runs-other/no.json',str(ROOT.parent/'outside.json')):
        try:
            confined('.lab-runs',value)
        except ValueError:
            pass
        else:
            raise AssertionError('Output escape accepted: '+value)
    assert confined('.lab-runs','.lab-runs/r2/example.json') == ROOT/'.lab-runs/r2/example.json'
    # An actual preparation-only exception must be saved, cleaned up and never overwritten.
    output=confined('.lab-runs','.lab-runs/r2a/cleanup-check-'+uuid.uuid4().hex+'.json')
    try:
        with redirect_stdout(io.StringIO()):
            with LabRun('preparation-only',output,['scripts/verify_review_r2.py']) as smoke:
                workspace=smoke.workspace
                (workspace/'owned-marker').write_text('synthetic cleanup check',encoding='utf-8')
                raise RuntimeError('deliberate preparation-only failure')
        saved=json.loads(output.read_text(encoding='utf-8'))
        assert smoke.exit_code==1 and saved['status']=='error' and saved['cleanup']['completed']
        assert not workspace.exists() and 'deliberate preparation-only failure' in saved['error']
        try:
            LabRun('preparation-only',output,[])
        except FileExistsError:
            pass
        else:
            raise AssertionError('Existing evidence overwrite accepted')
    finally:
        output.unlink(missing_ok=True)
    # Counter absence, unrelated exporters and non-finite samples must not become zero.
    text='''# HELP ignored
otelcol_exporter_send_failed_spans{exporter="otlp_http/lab"} 2
otelcol_exporter_send_failed_spans{exporter="another"} 99
otelcol_receiver_accepted_spans{receiver="otlp"} 4
'''
    assert counter({'metrics':parse_metrics(text)})==2
    assert counter({'metrics':parse_metrics('')}) is None
    assert counter({'metrics':parse_metrics('otelcol_exporter_send_failed_spans{exporter="otlp_http/lab"} NaN')}) is None
    assert counter({'metrics':parse_metrics('otelcol_exporter_send_failed_spans_total{exporter="otlp_http/lab"} 4')})==4
    retry_cases=[(2,[2,2],2,0,'supported'),(2,[2,2],4,2,'supported'),
                 (2,[3,3],4,2,'refuted'),(None,[2],4,2,'inconclusive'),
                 (2,[],4,2,'inconclusive'),(2,[None],4,2,'inconclusive'),(2,[2],None,2,'inconclusive')]
    for baseline,held,final,delta,expected in retry_cases:
        assert retry_verdict(baseline,held,final,delta)==expected
    held=parse_vacuum('INFO: finished vacuuming "postgres.public.r2_prepared":\ntuples: 0 removed, 128 remain, 128 are dead but not yet removable\nremovable cutoff: 760')
    released=parse_vacuum('tuples: 128 removed, 0 remain, 0 are dead but not yet removable')
    assert held==[{'removed':0,'remain':128,'dead_not_removable':128}]
    assert parse_vacuum('unknown output format')==[]
    assert horizon_verdict(True,held,released,128)=='supported'
    assert horizon_verdict(True,held,held,128)=='refuted'
    assert horizon_verdict(False,held,released,128)=='inconclusive'
    assert horizon_verdict(True,[],released,128)=='inconclusive'
    assert horizon_verdict(True,held+held,released,128)=='inconclusive'
    for queue in (False,True):
        config=configuration(4318,14318,18888,queue)
        assert config['service']['telemetry']['logs']['level']=='debug'
        assert config['service']['telemetry']['metrics']['level']=='detailed'
        assert config['exporters']['otlp_http/lab']['sending_queue']['wait_for_result'] is False
        assert config['receivers']['otlp']['protocols']['http']['endpoint'].startswith('127.0.0.1:')
    m=manifest()
    unavailable=[]
    for asset in m['assets']:
        if asset['status']=='unavailable':
            assert asset['suite']=='kubernetes' and asset['http_status']==404 and asset['sha256'] is None
            unavailable.append(asset['id'])
            continue
        assert re.fullmatch('[a-f0-9]{64}',asset['sha256'])
        assert asset['url'].startswith('https://github.com/') and '/releases/download/' in asset['url']
        cache=confined('.tools','.tools/r2/archives/'+asset['name'])
        assert sha256(cache)==asset['sha256'] and cache.stat().st_size==asset['size']
        with tarfile.open(cache,'r:gz') as archive:
            for name in asset['members']:
                tool=binary(asset['id'],name)
                members=[a for a in archive.getmembers() if a.isfile() and Path(a.name).name==name]
                assert len(members)==1
                import hashlib
                with archive.extractfile(members[0]) as source:
                    digest=hashlib.file_digest(source,'sha256').hexdigest()
                assert sha256(tool)==digest
                with tool.open('rb') as stream:
                    header=stream.read(20)
                assert header[:6]==b'\x7fELF\x02\x01' and int.from_bytes(header[18:20],'little')==62
    for name,pin in m['postgresql']['file_sha256'].items():
        assert sha256(confined('.tools',ROOT/'.tools/pg18'/name))==pin['sha256']
    print(f'PASS: {checked} Python files parsed; path boundary, exception cleanup/no-overwrite, missing/NaN metric, retry counter and vacuum verdict cases')
    print('PASS: 3 official archives and extracted Linux amd64 tools; reused PostgreSQL file hashes')
    print('UNAVAILABLE (not executed): '+', '.join(unavailable))


def validate_record(path):
    path=(path if path.is_absolute() else ROOT/path).resolve()
    assert path.is_relative_to(ROOT),'Evidence must be inside repository'
    record=json.loads(path.read_text(encoding='utf-8'))
    assert record['schema_version']==1
    assert record['suite'] in ('prometheus','otel','postgresql','kubernetes')
    assert record['platform'].startswith('Linux'), 'Plan output is not execution evidence'
    provenance=json.loads((ROOT/'review/evidence-provenance.json').read_text(encoding='utf-8'))
    # Historical input substitutions are allowed only for a byte-identical published
    # result. A new run must still name and hash the current inputs it actually used.
    published=next((p for p in provenance['published'] if p['sha256']==sha256(path)),None)
    archives={(a['evidence'],a['original_path']):a for a in provenance['archives']}
    for filename,digest in record['input_sha256'].items():
        archived=archives.get((published['evidence'],filename)) if published else None
        if archived:
            assert archived['sha256']==digest
            filename=archived['archived_path']
        source=(ROOT/filename).resolve()
        assert source.is_relative_to(ROOT)
        assert sha256(source)==digest,filename
    assert record['status']=='recorded' and record['cleanup']['completed'], 'Harness/cleanup failure; inspect error and logs'
    if record.get('native_directories'):
        assert record['native_directories_removed'] is True
        assert all(d['mode']=='0700' and d['reason'] for d in record['native_directories'])
    scenarios=record['scenarios']
    expected={'prometheus':2,'otel':14,'postgresql':4,'kubernetes':16}
    assert len(scenarios)==expected[record['suite']], 'Incomplete scenario matrix'
    for name,case in scenarios.items():
        for field in ('hypothesis','success_condition','refutation_condition','reason'):
            assert isinstance(case[field],str) and case[field],(name,field)
        assert case['verdict'] in ('supported','refuted','inconclusive','blocked'), name
        observation=case['observations']
        if record['suite']=='prometheus':
            results=[c['returncode'] for c in observation['commands']]
            if case['verdict']=='supported':
                assert results==[0,0]
        if record['suite']=='otel' and 'baseline_metrics' in observation:
            for key in ('initial_metrics','baseline_metrics','final_metrics'):
                assert parse_metrics(observation[key]['raw'])==observation[key]['metrics']
            assert counter(observation['baseline_metrics'])==observation['send_failed_baseline']
            assert counter(observation['final_metrics'])==observation['send_failed_final']
            if name.startswith('retry_') and case['verdict']=='supported':
                delta=2 if name.startswith('retry_exhausted') else 0
                assert retry_verdict(observation['send_failed_baseline'],observation['held_send_failed_values'],observation['send_failed_final'],delta)=='supported'
                assert not observation['increments_before_last_backend_attempt']
        if record['suite']=='otel' and name.endswith('/queue_boundary'):
            before=observation['upstream_completed_ns'] < observation['backend_unblocked_ns']
            assert before == observation['queue_enabled']
            assert observation['wait_for_result'] is False
        if record['suite']=='postgresql' and case['verdict']!='blocked':
            for phase in ('held','released'):
                vacuum=observation[phase]
                assert parse_vacuum('\n'.join(n['message'] for n in vacuum['notices']))==vacuum['parsed_tuple_summaries']
        if record['suite']=='kubernetes' and case['verdict']=='blocked':
            assert observation['asset']['status']=='unavailable'
    counts={v:sum(s['verdict']==v for s in scenarios.values()) for v in sorted({s['verdict'] for s in scenarios.values()})}
    assert counts==record['verdict_counts']
    print('PASS: saved evidence integrity',path.relative_to(ROOT),counts)
    print('Supported/refuted/inconclusive/blocked describe observations; integrity PASS is not universal product certification.')
    return record


def verify_published_review_r2():
    """Read-only: no tool cache, private .lab-runs data or running server required."""
    provenance=json.loads((ROOT/'review/evidence-provenance.json').read_text(encoding='utf-8'))
    records={}
    for suite in ('kubernetes','prometheus','otel','postgresql'):
        entries=[p for p in provenance['published'] if p['id']==suite+'-r2']
        assert len(entries)==1
        entry=entries[0]
        path=(ROOT/entry['evidence']).resolve()
        assert path.is_relative_to(ROOT/'labs/results')
        assert sha256(path)==entry['sha256'], 'Published evidence bytes changed'
        record=validate_record(path)
        assert record['suite']==suite and record['started']['utc']==entry['run_at_utc']
        assert record['input_sha256'][entry['runner']]==entry['runner_sha256']
        assert record['verdict_counts']==entry['verdict_counts']
        records[suite]=record
    kube=records['kubernetes']
    assert kube['verdict_counts']=={'supported':14,'refuted':2}
    published_rvs={
        '1.34.1-cache-true':['205','206','207'],
        '1.34.1-cache-false':['205','206','207'],
        '1.37.0-cache-true':['218','219','220'],
        '1.37.0-cache-false':['217','218','219'],
    }
    assert set(kube['servers'])==set(published_rvs)
    for server,metadata in kube['servers'].items():
        cache=metadata['watch_cache']
        cases={name:case['observations'] for name,case in kube['scenarios'].items() if name.startswith(server+'/')}
        expiry=cases[server+'/history_expiry']
        exact=expiry['exact_rv_one']
        assert exact['request']['query']=={'resourceVersion':'1','resourceVersionMatch':'Exact'}
        assert int(expiry['compaction']['header']['revision'])>1
        assert exact['http_status']==(200 if cache else 410)
        if cache:
            assert exact['body']['kind']=='ConfigMapList'
            assert exact['body']['metadata']['resourceVersion']=='1' and exact['body']['items']==[]
        assert expiry['fresh_list']['http_status']==200
        assert expiry['first_continue_after_compaction']['http_status']==(200 if cache else 410)
        assert metadata['feature_gate_overrides']=={}
        assert metadata['list_from_cache_snapshot_metric']==['kubernetes_feature_enabled{name="ListFromCacheSnapshot",stage="BETA"} 1']
        pagination=cases[server+'/pagination']
        pages=pagination['pages']
        assert len({p['metadata']['resourceVersion'] for p in pages})==1
        assert sorted(i['metadata']['name'] for p in pages for i in p['items'])==['cm-0','cm-1','cm-2']
        assert 'cm-late' in [i['metadata']['name'] for i in pagination['fresh']['items']]
        selector=cases[server+'/selector_exit']
        event=next(e['event'] for e in selector['events'] if e['event']['type']=='DELETED')
        assert selector['direct_get']['http_status']==200
        assert event['object']['metadata']['uid']==selector['direct_get']['body']['metadata']['uid']
        rv=cases[server+'/resource_version']
        assert rv['rv_strings']==[o['metadata']['resourceVersion'] for o in rv['sequence']]
        assert rv['rv_strings']==published_rvs[server]
        nums=[int(v) for v in rv['rv_strings']]
        assert nums[0]<nums[1]<nums[2]
        assert rv['ordered_comparison_contract']==server.startswith('1.37.0-')
    otel=records['otel']
    assert otel['verdict_counts']=={'supported':14}
    for alias in ('otlp_http','otlphttp'):
        validation=otel['scenarios']['component-name/'+alias]['observations']
        assert validation['returncode']==0 and validation['argv'][1]=='validate'
    for name,case in otel['scenarios'].items():
        o=case['observations']
        if 'baseline_metrics' not in o:
            continue
        assert o['send_failed_baseline']==2
        delta=2 if name.startswith('retry_exhausted') else 0
        assert o['send_failed_final']-o['send_failed_baseline']==delta
        if name.startswith('partial_success'):
            entries=[json.loads(line) for line in o['partial_rejection_log_lines']]
            assert any(e.get('dropped_spans')==1 and e.get('message')=='r2-partial-rejected-one' for e in entries)
            attempts=[a for a in o['backend_attempts'] if a['phase']=='probe']
            assert len(attempts)==1 and attempts[0]['response_code']==200
            assert o['upstream']['status']==200
            assert json.loads(o['upstream']['body'])=={'partialSuccess':{}}
    pg=records['postgresql']
    assert pg['verdict_counts']=={'supported':4}
    published_ages={'prepared_transaction':(14,15),'logical_catalog_xmin':(63,63),
                    'standby_feedback':(70,71),'physical_slot_xmin':(72,73)}
    for name,case in pg['scenarios'].items():
        o=case['observations']; rows=24 if name=='logical_catalog_xmin' else 128
        assert horizon_verdict(True,o['held']['parsed_tuple_summaries'],o['released']['parsed_tuple_summaries'],rows)=='supported'
        for phase,dead in (('held',rows),('released',0)):
            state=o[phase]['state_after']
            table=o[phase]['table'].split('.')[-1]
            assert int(next(t for t in state['table_statistics'] if t['relname']==table)['n_dead_tup'])==dead
            assert all(d['datfrozenxid']=='744' for d in state['databases'])
            age=int(next(d for d in state['databases'] if d['datname']=='postgres')['datfrozenxid_age'])
            assert age==published_ages[name][0 if phase=='held' else 1]
    physical=pg['scenarios']['physical_slot_xmin']['observations']
    assert physical['before_delete']['slots'][0]['xmin']=='815'
    assert physical['before_delete']['replication'][0]['backend_xmin'] is None
    assert physical['after_disconnect']['rows'][0]['active']=='f'
    assert physical['after_disconnect']['rows'][0]['xmin']=='815'
    logical=pg['scenarios']['logical_catalog_xmin']['observations']['held']['state_after']['slots'][0]
    assert logical['xmin'] is None and logical['catalog_xmin']=='759'
    assert pg['scenarios']['standby_feedback']['observations']['held']['state_after']['replication'][0]['backend_xmin']=='813'
    assert records['prometheus']['verdict_counts']=={'supported':2}
    print('PASS: 36 published round-2 scenarios (34 supported, 2 refuted); archive provenance and reported observations')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result',action='append',type=Path,default=[])
    parser.add_argument('--published',action='store_true',help='Read published evidence only; no assets or preparation fixtures required')
    args=parser.parse_args()
    if args.published:
        verify_published_review_r2()
    else:
        validate_preparation()
    for path in args.result:
        validate_record(path)
    if not args.result and not args.published:
        print('PREPARATION ONLY: no Linux experiments executed or runtime outcomes asserted.')


if __name__=='__main__':
    main()
