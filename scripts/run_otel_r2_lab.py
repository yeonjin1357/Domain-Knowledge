"""Observe real Collector retries, partial rejection and queue completion boundaries."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import re
import socket
import threading
import time
import urllib.error
import urllib.request

from lab_r2_common import LabRun, binary, free_ports, linux_required, scenario, sha256, stamp

EXPORTER = 'otlp_http/lab'
CASES = ('success', 'partial_success', 'retry_success', 'retry_exhausted')
METRIC = 'otelcol_exporter_send_failed_spans'
CONTRACTS = {
    'partial_success': ('목적지의 부분 거절을 Collector 내부 관측에서 확인할 수 있다.',
        '목적지의 rejectedSpans=1 응답과 고유 거절 문구를 포함한 Collector 로그, 또는 대응하는 내부 계수 증가.',
        '목적지 응답 이후 충분히 수집한 로그·metric에 거절 관측이 없으면 이 구성의 가시성 가설이 성립하지 않는다. 수신 여부 자체를 부정하지는 않는다.'),
    'retry_timing': ('send_failed_spans는 진행 중인 개별 재시도마다 증가하지 않고 최종 실패에서 증가한다.',
        'primer로 존재를 확인한 counter가 2번째 요청 보류 중 유지되고, 재시도 성공 후 유지 / 소진 후 2 증가.',
        '보류 중 counter 증가 또는 소진 뒤 다른 증가량. metric 누락이나 보류 구간 미관측은 반증 대신 관측 불충분.'),
    'queue_boundary': ('wait_for_result=false인 queue는 목적지의 완료 전에 upstream에 응답할 수 있다.',
        'queue on에서 보류 요청 해제 전 upstream 200, queue off에서 upstream 응답은 해제 뒤.',
        '같은 보류 조건에서 응답 순서가 가정과 다름; 구간 경계가 겹치거나 보류가 없으면 관측 불충분.')
}


def configuration(receiver, backend, metrics, queue, exporter=EXPORTER):
    return {'receivers': {'otlp': {'protocols': {'http': {'endpoint': f'127.0.0.1:{receiver}'}}}},
            'exporters': {exporter: {'endpoint': f'http://127.0.0.1:{backend}', 'encoding':'json',
                 'compression':'none', 'timeout':'2s',
                 'sending_queue': {'enabled':queue,'num_consumers':1,'queue_size':10,'sizer':'requests','wait_for_result':False},
                 'retry_on_failure': {'enabled':True,'initial_interval':'200ms','max_interval':'400ms','max_elapsed_time':'3s'}}},
            'service': {'telemetry': {'logs': {'level':'debug','encoding':'json'},
                 'metrics': {'level':'detailed','readers':[{'pull':{'exporter':{'prometheus':{
                     'host':'127.0.0.1','port':metrics,'without_type_suffix':True,'without_units':True}}}}]}},
                 'pipelines': {'traces': {'receivers':['otlp'],'exporters':[exporter]}}}}


def parse_metrics(text):
    samples = []
    for line in text.splitlines():
        match = re.fullmatch(r'(otelcol_(?:exporter|receiver)_[A-Za-z0-9_]+)(\{.*\})?\s+(\S+)(?:\s+\S+)?', line)
        if not match:
            continue
        name, raw_labels, value = match.groups()
        labels = {k:json.loads('"'+v+'"') for k,v in re.findall(r'(\w+)="((?:\\.|[^"\\])*)"',raw_labels or '')}
        numeric = float(value)
        samples.append({'name':name,'labels':labels,'value':numeric if math.isfinite(numeric) else None,'raw':line})
    return samples


def counter(snapshot, name=METRIC):
    matches=[s['value'] for s in snapshot['metrics'] if s['name'] in (name,name+'_total') and s['labels'].get('exporter')==EXPORTER]
    return sum(matches) if matches and all(v is not None for v in matches) else None


def retry_verdict(baseline, held, final, expected_delta):
    if baseline is None or final is None or not held or any(v is None for v in held):
        return 'inconclusive'
    return 'supported' if all(v==baseline for v in held) and final-baseline==expected_delta else 'refuted'


def payload(phase, case):
    started=time.time_ns()
    return {'resourceSpans':[{'resource':{'attributes':[{'key':'service.name','value':{'stringValue':'r2-fixture'}}]},
            'scopeSpans':[{'scope':{'name':'domain-knowledge-r2'},'spans':[
                {'traceId':('1' if phase=='primer' else '2')*32,'spanId':f'{i:016x}','name':phase+'/'+case,'kind':2,
                 'startTimeUnixNano':str(started),'endTimeUnixNano':str(started+1000000)} for i in (1,2)]}]}]}


def run_case(lab, tool, case, queue):
    name=f'{case}-queue-{str(queue).lower()}'
    attempts, lock = [], threading.Lock()
    entered, release = threading.Event(), threading.Event()
    gate = {}
    class Backend(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass

        def do_POST(self):
            received=stamp()
            raw=self.rfile.read(int(self.headers.get('Content-Length','0')))
            if self.headers.get('Content-Encoding')=='gzip':
                raw=gzip.decompress(raw)
            body=json.loads(raw)
            spans=[s for r in body.get('resourceSpans',[]) for scope in r.get('scopeSpans',[]) for s in scope.get('spans',[])]
            phase='primer' if spans and spans[0]['name'].startswith('primer/') else 'probe'
            with lock:
                number=1+sum(a['phase']==phase for a in attempts)
                observation={'received':received,'phase':phase,'number':number,'path':self.path,'spans':spans}
                attempts.append(observation)
            if phase=='primer':
                code, response=400,{'message':'r2-primer-permanent-failure'}
            elif case in ('retry_success','retry_exhausted'):
                if number==2:
                    gate['entered']=stamp(); entered.set()
                    gate['released_by_coordinator']=release.wait(timeout=1.5)
                    gate['unblocked']=stamp()
                code=200 if case=='retry_success' and number>=2 else 503
                response={} if code==200 else {'message':'r2-temporary-failure'}
            elif case=='partial_success':
                code, response=200,{'partialSuccess':{'rejectedSpans':'1','errorMessage':'r2-partial-rejected-one'}}
            else:
                code,response=200,{}
            data=json.dumps(response).encode()
            self.send_response(code)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
                observation.update(response_code=code,response_body=response,response_written=stamp())
            except (BrokenPipeError,ConnectionResetError) as exc:
                observation['write_error']=repr(exc)
    server=ThreadingHTTPServer(('127.0.0.1',0),Backend)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    receiver_port,metric_port=free_ports(2)
    config=configuration(receiver_port,server.server_port,metric_port,queue)
    config_path=lab.workspace/(name+'.yaml')
    config_path.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    partial_evidence={'configuration':config,'backend_attempts':attempts,'gate':gate,'metric_samples':[]}
    lab.record.setdefault('raw_cases',{})[name]=partial_evidence
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def scrape():
        before=stamp()
        with opener.open(f'http://127.0.0.1:{metric_port}/metrics',timeout=2) as response:
            raw=response.read().decode()
        return {'started':before,'finished':stamp(),'metrics':parse_metrics(raw),'raw':raw}
    def send(phase):
        request_body=payload(phase,case)
        req=urllib.request.Request(f'http://127.0.0.1:{receiver_port}/v1/traces',data=json.dumps(request_body).encode(),headers={'Content-Type':'application/json'})
        before=stamp()
        try:
            with opener.open(req,timeout=10) as response:
                code,body=response.status,response.read().decode()
        except urllib.error.HTTPError as exc:
            code,body=exc.code,exc.read().decode()
        return {'started':before,'finished':stamp(),'status':code,'body':body,'request_body':request_body}
    process=None
    try:
        validation=lab.command([tool,'validate','--config='+str(config_path)])
        partial_evidence['validation']=validation
        if validation['returncode']:
            raise RuntimeError('Collector configuration rejected: '+json.dumps(validation))
        process=lab.launch(name,[tool,'--config='+str(config_path)])
        deadline=time.monotonic()+15
        while True:
            if process.poll() is not None:
                raise RuntimeError('Collector exited; see log '+name)
            try:
                initial=scrape()
                with socket.create_connection(('127.0.0.1',receiver_port),timeout=.2):
                    pass
                break
            except OSError:
                if time.monotonic()>deadline:
                    raise
                time.sleep(.05)
        # Primer creates a known nonzero counter. Missing metric is never treated as zero.
        primer=send('primer')
        partial_evidence['primer']=primer
        deadline=time.monotonic()+3
        baseline=scrape()
        while (counter(baseline) is None or counter(baseline)<2) and time.monotonic()<deadline:
            time.sleep(.05); baseline=scrape()
        samples,held=[],[]
        partial_evidence['metric_samples']=samples
        partial_evidence['baseline_metrics']=baseline
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(send,'probe')
            finish_at=time.monotonic()+(5 if case.startswith('retry') else 1.5)
            while time.monotonic()<finish_at or not future.done():
                if process.poll() is not None:
                    raise RuntimeError('Collector exited during probe')
                sample=scrape()
                sample['phase']='held' if entered.is_set() and not release.is_set() and 'unblocked' not in gate else 'probe'
                # Keep complete raw text at initial/baseline/final; intermediate selected samples preserve exact lines.
                sample.pop('raw')
                samples.append(sample)
                if sample['phase']=='held':
                    held.append(counter(sample))
                    if sample['finished']['monotonic_ns']-gate['entered']['monotonic_ns']>=600_000_000:
                        gate['release_requested']=stamp(); release.set()
                time.sleep(.05)
                if time.monotonic()>finish_at+6:
                    release.set(); raise TimeoutError('Bounded probe deadline exceeded')
            upstream=future.result(timeout=1)
        final=scrape()
        lab.stop(process)
        log=(lab.workspace/(name+'.log')).read_text(encoding='utf-8',errors='replace')
        probe=[a for a in attempts if a['phase']=='probe']
        valid_requests=bool(probe) and all(len(a['spans'])==2 and a.get('response_written') for a in probe)
        observation={'configuration':config,'configuration_sha256':sha256(config_path),'validation':validation,
            'primer':primer,'primer_purpose':'Create send_failed_spans=2 before the probe; do not count primer as probe traffic.',
            'initial_metrics':initial,'baseline_metrics':baseline,'samples':samples,'final_metrics':final,
            'backend_attempts':attempts,'upstream':upstream,'gate':gate,
            'send_failed_baseline':counter(baseline),'send_failed_final':counter(final),'held_send_failed_values':held,
            'send_failed_first_change_interval':next(({'started':s['started'],'finished':s['finished'],'value':counter(s)} for s in samples
                if counter(s) is not None and counter(baseline) is not None and counter(s)!=counter(baseline)),None),
            'partial_rejection_log_lines':[line for line in log.splitlines() if 'r2-partial-rejected-one' in line],
            'retry_and_failure_log_lines':[line for line in log.splitlines() if re.search(r'retry|failed|Dropping|reject',line,re.IGNORECASE)],
            'interpretation_limit':'Scrapes bracket a change; they do not identify its exact CPU instruction time. Backend response/write and caller read times are different events.'}
        # Main case stores all evidence once; auxiliary verdicts point to the same observation key.
        if case=='partial_success':
            start_count,end_count=counter(baseline),counter(final)
            counted=start_count is not None and end_count is not None and end_count>start_count
            seen=bool(observation['partial_rejection_log_lines']) or counted
            verdict='supported' if seen and valid_requests else 'refuted' if valid_requests else 'inconclusive'
            lab.record['scenarios'][name]=scenario(*CONTRACTS['partial_success'],observation,verdict,
                'Internal rejection visibility is judged from the unique backend message; send_failed is reported separately, not assumed to count rejected spans.')
        elif case.startswith('retry'):
            verdict=retry_verdict(counter(baseline),held,counter(final),2 if case=='retry_exhausted' else 0)
            # A completed scrape with a higher counter before a later retry is definite counterevidence.
            early_increments=[s for s in samples if counter(s) is not None and counter(baseline) is not None
                and counter(s)>counter(baseline) and probe and s['finished']['monotonic_ns']<probe[-1]['received']['monotonic_ns']]
            observation['increments_before_last_backend_attempt']=early_increments
            if early_increments:
                verdict='refuted'
            if not valid_requests or len(probe)<2 or not gate.get('released_by_coordinator'):
                verdict='inconclusive'
            lab.record['scenarios'][name]=scenario(*CONTRACTS['retry_timing'],observation,verdict,
                'A bounded second attempt supplies an observable in-flight interval; final failure delta is expected to count 2 spans, not attempts.')
            unblocked=gate.get('unblocked',{}).get('monotonic_ns')
            completed=upstream['finished']['monotonic_ns']
            if unblocked is None or not gate.get('released_by_coordinator'):
                queue_verdict='inconclusive'
            else:
                matched=(completed<unblocked and upstream['status']==200) if queue else completed>=unblocked
                queue_verdict='supported' if matched else 'refuted'
            lab.record['scenarios'][name+'/queue_boundary']=scenario(*CONTRACTS['queue_boundary'],
                {'evidence_case':name,'upstream_completed_ns':completed,'backend_unblocked_ns':unblocked,
                 'queue_enabled':queue,'wait_for_result':False},queue_verdict,
                'Asynchronous acceptance is not end-to-end delivery; on/off cases use separate fresh Collector processes.')
        else:
            matched=valid_requests and len(probe)==1 and upstream['status']==200 and counter(final)==counter(baseline) and counter(baseline) is not None
            verdict='supported' if matched else 'inconclusive' if counter(baseline) is None or counter(final) is None else 'refuted'
            lab.record['scenarios'][name]=scenario('정상 전송 대조군은 재시도나 추가 send_failed 없이 완료된다.',
                '목적지 1회·upstream 200·send_failed delta=0.', '정상 응답에도 추가 실패 계수·중복 전송·upstream 실패가 발생.',
                observation,verdict,'Primer excluded from probe counts.')
    finally:
        release.set()
        if process is not None:
            lab.stop(process)
        server.shutdown(); server.server_close(); thread.join(timeout=3)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='.lab-runs/r2/otel.json')
    parser.add_argument('--plan',action='store_true')
    args=parser.parse_args()
    if args.plan:
        print(json.dumps({'version':'0.162.0','cases':CASES,'queue':[False,True],'contracts':CONTRACTS,
                          'probe':'two spans; separate permanent-error primer makes the failure counter observable',
                          'config':configuration(4318,14318,18888,True)},ensure_ascii=False,indent=2))
        return
    linux_required()
    with LabRun('otel',args.output,['scripts/run_otel_r2_lab.py','scripts/get_review_r2_assets.py']) as lab:
        tool=binary('collector-0.162.0','otelcol')
        version=lab.command([tool,'--version'])
        if version['returncode'] or '0.162.0' not in version['stdout']+version['stderr']:
            raise RuntimeError('Unexpected Collector version')
        lab.record['version']=version
        lab.record['binary_sha256']=sha256(tool)
        lab.record['components']=lab.command([tool,'components'])
        for kind in ('otlp_http','otlphttp'):
            config=configuration(4318,14318,18888,False,kind+'/lab')
            path=lab.workspace/(kind+'-validate.yaml'); path.write_text(json.dumps(config),encoding='utf-8')
            result=lab.command([tool,'validate','--config='+str(path)])
            lab.record['scenarios']['component-name/'+kind]=scenario('새 이름과 deprecated 별칭의 구성 수용 상태를 확인한다.',
                'validate exit 0; stdout/stderr의 deprecation 표시도 보존.',
                '알려지지 않은 구성요소 등으로 해당 구성을 거절.',result,
                'supported' if result['returncode']==0 else 'refuted','Core v0.144.0 introduced exporter renames; receiver otlp is unchanged.')
        for queue in (False,True):
            for case in CASES:
                run_case(lab,tool,case,queue)
                print('Observed',case,'queue=',queue,flush=True)
    raise SystemExit(lab.exit_code)


if __name__=='__main__':
    main()
