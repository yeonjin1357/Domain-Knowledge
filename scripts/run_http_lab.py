"""Actual HTTP/1.1 connection reuse and incomplete-body behavior on loopback."""

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import platform
import threading

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'.lab-runs/http11.json')
    args=parser.parse_args()
    accepted=[]
    handled=[]
    lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,*args):
            pass
        def setup(self):
            super().setup()
            with lock:
                self.connection_number=len(accepted)+1
                accepted.append(self.connection_number)
        def do_GET(self):
            handled.append({'path':self.path,'connection':self.connection_number})
            self.send_response(200)
            if self.path=='/truncated':
                self.send_header('Content-Length','10')
                self.send_header('Connection','close')
                self.end_headers()
                self.wfile.write(b'12345')
                self.wfile.flush()
                self.close_connection=True
            else:
                self.send_header('Content-Length','2')
                self.end_headers()
                self.wfile.write(b'OK')
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    worker=threading.Thread(target=server.serve_forever,daemon=True)
    worker.start()
    connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
    try:
        for path in ('/first','/second'):
            connection.request('GET',path)
            response=connection.getresponse()
            assert response.status==200 and response.read()==b'OK'
        assert len(accepted)==1 and handled[0]['connection']==handled[1]['connection']
        reuse={'status':'passed','requests':2,'accepted_tcp_connections':len(accepted),
               'condition':'sequential HTTP/1.1 requests with fully consumed Content-Length bodies'}
        connection.request('GET','/truncated')
        response=connection.getresponse()
        header_status=response.status
        try:
            response.read()
            raise AssertionError('Incomplete response was not detected')
        except http.client.IncompleteRead as error:
            incomplete={'status':'passed','response_status':header_status,'declared_bytes':10,
                        'received_bytes':len(error.partial),'missing_bytes':error.expected,
                        'client_error':error.__class__.__name__}
        assert header_status==200 and incomplete['received_bytes']==5 and incomplete['missing_bytes']==5
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
    result={'run_at_utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),
            'platform':platform.platform(),'scope':'loopback HTTP/1.1 only; no DNS, TLS, HTTP/2 or real proxy experiment',
            'experiments':{'connection_reuse':reuse,'incomplete_body':incomplete},
            'cleanup':'client, loopback server, and worker closed',
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS: HTTP/1.1 reuses one connection for two requests; HTTP 200 with incomplete body raises IncompleteRead')


if __name__=='__main__':
    main()
