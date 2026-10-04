"""Probe a pinned real Collector against a synthetic loopback OTLP/HTTP backend.

This verifies exporter behavior for controlled responses, not a durable store.
The exporter queue is deliberately disabled to expose synchronous outcomes.
"""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import platform
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        return sock.getsockname()[1]


def run_case(binary,name,responses,expected_min,expected_max):
    attempts=[]
    class Backend(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass
        def do_POST(self):
            raw=self.rfile.read(int(self.headers['Content-Length']))
            if self.headers.get('Content-Encoding')=='gzip':
                raw=gzip.decompress(raw)
            payload=json.loads(raw)
            spans=[s for resource in payload.get('resourceSpans',[]) for scope in resource.get('scopeSpans',[]) for s in scope.get('spans',[])]
            attempts.append({'path':self.path,'span_ids':[s['spanId'] for s in spans],'span_count':len(spans)})
            code,body=responses[min(len(attempts)-1,len(responses)-1)]
            if code=='disconnect':
                self.close_connection=True
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            data=json.dumps(body).encode()
            self.send_response(code)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    server=ThreadingHTTPServer(('127.0.0.1',0),Backend)
    worker=threading.Thread(target=server.serve_forever,daemon=True)
    worker.start()
    receiver_port=free_port()
    process=None
    try:
        with tempfile.TemporaryDirectory(prefix='dk-otel-') as temporary:
            config=Path(temporary)/'collector.yaml'
            config.write_text(f'''receivers:
  otlp:
    protocols:
      http:
        endpoint: "127.0.0.1:{receiver_port}"
exporters:
  otlphttp/lab:
    endpoint: "http://127.0.0.1:{server.server_port}"
    encoding: json
    compression: none
    timeout: 1s
    sending_queue:
      enabled: false
    retry_on_failure:
      enabled: true
      initial_interval: 100ms
      max_interval: 200ms
      max_elapsed_time: 800ms
service:
  telemetry:
    logs:
      level: error
    metrics:
      level: none
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [otlphttp/lab]
''')
            with (Path(temporary)/'collector.log').open('w+') as log:
                process=subprocess.Popen([str(binary),'--config='+str(config)],stdout=log,stderr=subprocess.STDOUT)
                try:
                    deadline=time.monotonic()+10
                    while True:
                        if process.poll() is not None:
                            log.seek(0)
                            raise RuntimeError(log.read())
                        try:
                            with socket.create_connection(('127.0.0.1',receiver_port),timeout=.2):
                                break
                        except OSError:
                            if time.monotonic()>deadline:
                                raise
                            time.sleep(.025)
                    started=time.time_ns()
                    payload={'resourceSpans':[{'resource':{'attributes':[{'key':'service.name','value':{'stringValue':'domain-knowledge-fixture'}}]},
                        'scopeSpans':[{'scope':{'name':'lab'},'spans':[
                            {'traceId':'1'*32,'spanId':f'{i:016x}','name':name,'kind':2,
                             'startTimeUnixNano':str(started),'endTimeUnixNano':str(started+1000000)} for i in (1,2)]}]}]}
                    request=urllib.request.Request(f'http://127.0.0.1:{receiver_port}/v1/traces',data=json.dumps(payload).encode(),
                                                   headers={'Content-Type':'application/json'})
                    try:
                        with urllib.request.urlopen(request,timeout=5) as response:
                            incoming_code=response.status
                            incoming_body=response.read().decode()
                    except urllib.error.HTTPError as error:
                        incoming_code=error.code
                        incoming_body=error.read().decode()
                    assert expected_min<=len(attempts)<=expected_max,(name,attempts)
                    assert all(a['span_count']==2 for a in attempts),attempts
                    if len(attempts)>1:
                        assert all(a['span_ids']==attempts[0]['span_ids'] for a in attempts)
                    result={'status':'passed','backend_attempts':attempts,'receiver_http_status':incoming_code,
                            'receiver_body':incoming_body,'sending_queue_enabled':False}
                finally:
                    if process.poll() is None:
                        process.terminate()
                    try:
                        process.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=3)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'.lab-runs/otel.json')
    args=parser.parse_args()
    binary=ROOT/'.tools/otelcol-0.137.0/otelcol'
    cases=[('success',[(200,{})],1,1),
           ('retry_503',[(503,{'message':'temporary'}),(200,{})],2,2),
           ('permanent_400',[(400,{'message':'bad fixture'})],1,1),
           ('permanent_500',[(500,{'message':'not an OTLP retryable status'})],1,1),
           ('partial_success',[(200,{'partialSuccess':{'rejectedSpans':'1','errorMessage':'fixture rejection'}})],1,1),
           ('response_lost', [('disconnect',{}),(200,{})],2,2),
           ('retry_exhausted',[(503,{'message':'still unavailable'})],2,20)]
    experiments={}
    for name,responses,minimum,maximum in cases:
        experiments[name]=run_case(binary,name,responses,minimum,maximum)
        print(f"{name}: {len(experiments[name]['backend_attempts'])} backend attempts, receiver HTTP {experiments[name]['receiver_http_status']}",flush=True)
    result={'run_at_utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),
        'collector_version':subprocess.check_output([str(binary),'--version'],text=True).strip(),
        'input_kind':'two synthetic spans through the real otlp receiver and otlphttp exporter',
        'scope':'OTLP/HTTP JSON, no sending queue, bounded retries; no gRPC or durable storage validation',
        'experiments':experiments,'cleanup':'all temporary collectors and loopback servers stopped',
        'input_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ('scripts/run_otel_lab.py','scripts/get_runtime_lab_assets.py','labs/runtime-assets.json')}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS: 7 real Collector experiments against a synthetic backend')


if __name__=='__main__':
    main()
