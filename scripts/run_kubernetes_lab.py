"""Exercise a private Kubernetes API server and etcd, not a workload cluster.

Pinned envtest binaries; loopback endpoints, temporary certificates/data, no
existing kubeconfig, no scheduler/kubelet/CNI. All child processes are stopped.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def unused_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        return sock.getsockname()[1]


def certificates(workspace):
    def openssl(*args):
        subprocess.run(['openssl',*args],cwd=workspace,check=True,capture_output=True,timeout=20)
    openssl('req','-x509','-newkey','rsa:2048','-nodes','-keyout','ca.key','-out','ca.crt',
            '-days','1','-subj','/CN=domain-knowledge-lab-ca')
    for name,subject,usage in [('server','/CN=localhost','serverAuth'),
                               ('admin','/CN=dk-admin/O=system:masters','clientAuth'),
                               ('reader','/CN=dk-reader','clientAuth')]:
        openssl('req','-newkey','rsa:2048','-nodes','-keyout',name+'.key','-out',name+'.csr',
                '-subj',subject)
        (workspace/(name+'.ext')).write_text('extendedKeyUsage='+usage+'\n'+
                                            ('subjectAltName=IP:127.0.0.1\n' if name=='server' else ''))
        openssl('x509','-req','-in',name+'.csr','-CA','ca.crt','-CAkey','ca.key','-CAcreateserial',
                '-out',name+'.crt','-days','1','-extfile',name+'.ext')
    openssl('genrsa','-out','service-account.key','2048')


class API:
    def __init__(self,port,workspace,identity='admin'):
        self.base=f'https://127.0.0.1:{port}'
        self.context=ssl.create_default_context(cafile=str(workspace/'ca.crt'))
        self.context.load_cert_chain(str(workspace/(identity+'.crt')),str(workspace/(identity+'.key')))

    def call(self,path,method='GET',body=None,query=None,expected=200,content_type='application/json'):
        url=self.base+path+('?' + urllib.parse.urlencode(query) if query else '')
        request=urllib.request.Request(url,method=method,data=json.dumps(body).encode() if body is not None else None,
                                       headers={'Content-Type':content_type})
        try:
            with urllib.request.urlopen(request,context=self.context,timeout=8) as response:
                code,raw=response.status,response.read()
        except urllib.error.HTTPError as error:
            code,raw=error.code,error.read()
        assert code==expected,(method,path,code,raw.decode()[:400])
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw.decode()

    def watch(self,path,version,selector,name,event_type):
        query=urllib.parse.urlencode({'watch':'true','resourceVersion':version,'labelSelector':selector,'timeoutSeconds':4})
        with urllib.request.urlopen(self.base+path+'?'+query,context=self.context,timeout=7) as response:
            for line in response:
                event=json.loads(line)
                if event.get('type')==event_type and event.get('object',{}).get('metadata',{}).get('name')==name:
                    return event
        raise AssertionError('Expected watch event not observed: '+name+' '+event_type)


def experiments(api,reader,etcd_port):
    namespace='domain-knowledge-lab'
    api.call('/api/v1/namespaces','POST',{'apiVersion':'v1','kind':'Namespace','metadata':{'name':namespace}},expected=201)
    path=f'/api/v1/namespaces/{namespace}/configmaps'
    def create(name):
        return api.call(path,'POST',{'apiVersion':'v1','kind':'ConfigMap',
            'metadata':{'name':name,'labels':{'suite':'domain-book'}},'data':{'value':'first'}},expected=201)
    for i in range(3):
        create(f'cm-{i}')
    first=api.call(path,query={'limit':1,'labelSelector':'suite=domain-book'})
    snapshot=first['metadata']['resourceVersion']
    late=create('cm-late')
    names=[item['metadata']['name'] for item in first['items']]
    versions=[snapshot]
    token=first['metadata'].get('continue')
    while token:
        page=api.call(path,query={'limit':1,'labelSelector':'suite=domain-book','continue':token})
        names.extend(item['metadata']['name'] for item in page['items'])
        versions.append(page['metadata']['resourceVersion'])
        token=page['metadata'].get('continue')
    assert sorted(names)==['cm-0','cm-1','cm-2'] and all(v==snapshot for v in versions)
    current=api.call(path,query={'labelSelector':'suite=domain-book'})
    assert len(current['items'])==4
    evidence={'pagination':{'status':'passed','original_list_names':names,
                            'collection_versions':versions,'fresh_list_count':len(current['items'])}}
    event=api.watch(path,snapshot,'suite=domain-book','cm-late','ADDED')
    evidence['list_then_watch']={'status':'passed','event_type':event['type'],
                                'name':event['object']['metadata']['name'],'watch_from':snapshot}

    old=api.call(path+'/cm-1')
    api.call(path+'/cm-1','DELETE')
    new=create('cm-1')
    assert old['metadata']['uid'] != new['metadata']['uid']
    evidence['name_reuse']={'status':'passed','same_name':'cm-1','old_uid':old['metadata']['uid'],
                            'new_uid':new['metadata']['uid']}

    updated=json.loads(json.dumps(late))
    updated['data']['value']='second'
    api.call(path+'/cm-late','PUT',updated)
    late['data']['value']='stale overwrite'
    conflict=api.call(path+'/cm-late','PUT',late,expected=409)
    evidence['optimistic_conflict']={'status':'passed','http_status':conflict['code'],'reason':conflict['reason']}

    denied=reader.call(path,expected=403)
    rbac=f'/apis/rbac.authorization.k8s.io/v1/namespaces/{namespace}'
    api.call(rbac+'/roles','POST',{'apiVersion':'rbac.authorization.k8s.io/v1','kind':'Role',
        'metadata':{'name':'inventory-reader'},'rules':[{'apiGroups':[''],'resources':['configmaps'],'verbs':['get','list','watch']}]},expected=201)
    api.call(rbac+'/rolebindings','POST',{'apiVersion':'rbac.authorization.k8s.io/v1','kind':'RoleBinding',
        'metadata':{'name':'inventory-reader'},'subjects':[{'kind':'User','name':'dk-reader','apiGroup':'rbac.authorization.k8s.io'}],
        'roleRef':{'kind':'Role','name':'inventory-reader','apiGroup':'rbac.authorization.k8s.io'}},expected=201)
    deadline=time.monotonic()+5
    while True:
        try:
            allowed=reader.call(path)
            break
        except AssertionError:
            if time.monotonic()>deadline:
                raise
            time.sleep(.05)
    secret_denied=reader.call(f'/api/v1/namespaces/{namespace}/secrets',expected=403)
    other_denied=reader.call('/api/v1/namespaces/default/configmaps',expected=403)
    evidence['rbac_scope']={'status':'passed','before_grant':denied['code'],'allowed_count':len(allowed['items']),
        'secrets_status':secret_denied['code'],'other_namespace_status':other_denied['code']}

    before=api.call(path,query={'labelSelector':'suite=domain-book'})
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(api.watch,path,before['metadata']['resourceVersion'],'suite=domain-book','cm-0','DELETED')
        api.call(path+'/cm-0','PATCH',{'metadata':{'labels':{'suite':'other'}}},content_type='application/merge-patch+json')
        departed=future.result(timeout=8)
    still_exists=api.call(path+'/cm-0')
    assert still_exists['metadata']['uid']==departed['object']['metadata']['uid']
    evidence['selector_exit']={'status':'passed','watch_event':departed['type'],'get_after_event':200,
        'remaining_label':still_exists['metadata']['labels']['suite'],
        'meaning':'DELETED from this selected watch set; object still exists'}

    def etcd_request(endpoint,body):
        request=urllib.request.Request(f'http://127.0.0.1:{etcd_port}'+endpoint,
                                       data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=5) as response:
            return json.load(response)
    status=etcd_request('/v3/maintenance/status',{})
    revision=status['header']['revision']
    etcd_request('/v3/kv/compaction',{'revision':revision,'physical':True})
    expired=api.call(path,query={'resourceVersion':'1','resourceVersionMatch':'Exact'},expected=410)
    fresh=api.call(path)
    evidence['expired_history']={'status':'passed','compacted_private_etcd_revision':revision,
        'expired_http_status':expired['code'],'fresh_list_count':len(fresh['items'])}
    return evidence


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'.lab-runs/kubernetes.json')
    args=parser.parse_args()
    if platform.system()!='Linux':
        raise SystemExit('Linux amd64 tools required')
    binaries=ROOT/'.tools/envtest-1.34.1'
    processes=[]
    logs=[]
    with tempfile.TemporaryDirectory(prefix='dk-k8s-') as temporary:
        workspace=Path(temporary)
        workspace.chmod(0o700)
        certificates(workspace)
        etcd_port,peer_port,api_port=[unused_port() for _ in range(3)]
        def launch(name,args):
            log=(workspace/(name+'.log')).open('wb')
            logs.append(log)
            process=subprocess.Popen([str(binaries/name),*args],stdout=log,stderr=subprocess.STDOUT,cwd=workspace)
            processes.append(process)
            return process
        try:
            launch('etcd',['--name=default','--data-dir='+str(workspace/'etcd'),
                f'--listen-client-urls=http://127.0.0.1:{etcd_port}',f'--advertise-client-urls=http://127.0.0.1:{etcd_port}',
                f'--listen-peer-urls=http://127.0.0.1:{peer_port}',f'--initial-advertise-peer-urls=http://127.0.0.1:{peer_port}',
                f'--initial-cluster=default=http://127.0.0.1:{peer_port}','--initial-cluster-token=domain-knowledge-lab',
                '--quota-backend-bytes=67108864','--log-level=error'])
            launch('kube-apiserver',[f'--etcd-servers=http://127.0.0.1:{etcd_port}',
                '--bind-address=127.0.0.1','--advertise-address=127.0.0.1',f'--secure-port={api_port}',
                '--watch-cache=false','--endpoint-reconciler-type=none',
                '--service-cluster-ip-range=10.250.0.0/24','--authorization-mode=RBAC',
                '--client-ca-file='+str(workspace/'ca.crt'),'--tls-cert-file='+str(workspace/'server.crt'),
                '--tls-private-key-file='+str(workspace/'server.key'),'--service-account-issuer=https://localhost',
                '--service-account-signing-key-file='+str(workspace/'service-account.key'),
                '--service-account-key-file='+str(workspace/'service-account.key')])
            api,reader=API(api_port,workspace),API(api_port,workspace,'reader')
            deadline=time.monotonic()+35
            while True:
                if any(process.poll() is not None for process in processes):
                    raise RuntimeError('Private control-plane child exited')
                try:
                    if api.call('/readyz')=='ok':
                        break
                except (OSError,AssertionError):
                    if time.monotonic()>deadline:
                        raise
                    time.sleep(.2)
            result={'run_at_utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),
                    'server_version':api.call('/version'),'etcd_version':subprocess.check_output([str(binaries/'etcd'),'--version'],text=True).strip(),
                    'scope':'isolated API server + etcd; watch cache disabled for deterministic history expiry; no scheduler, controller-manager, kubelet, CNI, or workloads',
                    'experiments':experiments(api,reader,etcd_port)}
        except BaseException:
            for name in ('etcd','kube-apiserver'):
                path=workspace/(name+'.log')
                if path.exists():
                    print(name+' last log lines:\n'+'\n'.join(path.read_text(errors='replace').splitlines()[-12:]))
            raise
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            for log in logs:
                log.close()
    result['cleanup']='all private child processes stopped; temporary certificates and data removed'
    result['input_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
        ('scripts/run_kubernetes_lab.py','scripts/get_runtime_lab_assets.py','labs/runtime-assets.json')}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"PASS: Kubernetes {result['server_version']['gitVersion']}; {len(result['experiments'])} API experiments; private processes stopped")


if __name__=='__main__':
    main()
