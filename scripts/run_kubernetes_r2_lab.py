"""Pinned-version watch-cache matrix; absent official envtest assets stay blocked."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from lab_r2_common import ROOT, LabRun, confined, free_ports, linux_required, scenario, sha256, stamp
from get_review_r2_assets import obtain
from run_kubernetes_lab import certificates

VERSIONS = ('1.34.1', '1.37.0')
PATCH_SCOPE = {'review_date': '2026-10-05',
               'latest_patches': {'1.34': '1.34.12', '1.37': '1.37.1'},
               'execution_versions_are_latest_patch': False,
               'purpose': 'Minor-version API contracts and watch-cache behavior; not latest-patch certification.'}


def manifest():
    """Separate pins preserve the input hash of concurrent non-Kubernetes labs."""
    return json.loads((ROOT/'labs/review-r2/kubernetes-assets.json').read_text(encoding='utf-8'))


def binary(asset_id, name):
    asset = next(a for a in manifest()['assets'] if a['id'] == asset_id)
    directory = confined('.tools', asset['destination'])
    receipt = json.loads(confined('.tools', directory/'verified.json').read_text(encoding='utf-8'))
    path = confined('.tools', directory/name)
    if receipt['archive_sha256'] != asset['sha256'] or name not in asset['members']:
        raise ValueError('Kubernetes asset receipt differs from pinned manifest')
    if sha256(path) != receipt['binaries'][name]:
        raise ValueError('Kubernetes executable differs from verified extraction')
    return path


CONTRACTS = {
    'selector_exit': ('선택 집합 이탈은 DELETED로 관측되며 객체 자체는 남아 있다.',
                      'DELETED 수신, 직접 GET 200, UID 동일, label 변경 확인.',
                      'watch가 정상 연결·완료됐지만 해당 DELETED가 없거나 직접 GET/UID가 가정과 다르다.'),
    'pagination': ('continue로 이은 페이지들은 첫 목록 snapshot을 유지한다.',
                   '3개 원래 이름·같은 collection RV, 중간 생성 항목은 fresh LIST에서만 나타남.',
                   '성공한 페이지에 중간 생성 항목 포함, 원래 항목 누락/중복 또는 collection RV 변화.'),
    'history_expiry': ('이 실험의 compaction 뒤 Exact RV=1 조회는 410이고 fresh LIST는 성공한다.',
                       'Exact 조회 HTTP 410과 fresh LIST HTTP 200.',
                       'Exact 조회 HTTP 200. 이는 이 조건에서 만료가 유발되지 않았다는 반증이며 API 규약 위반을 뜻하지 않는다.'),
    'resource_version': ('같은 클러스터·core/v1 ConfigMap의 순차 변경에서 RV가 증가한다.',
                         '각 RV가 십진 정수 문자열이며 순차 변경마다 int 비교 증가.',
                         '완료된 순차 변경에서 수치가 증가하지 않음. 1.34의 비수치 RV는 opaque 규약상 허용되므로 관측 불충분으로 분리.')
}


class API:
    def __init__(self, port, workspace):
        self.base = f'https://127.0.0.1:{port}'
        context = ssl.create_default_context(cafile=str(workspace/'ca.crt'))
        context.load_cert_chain(str(workspace/'admin.crt'), str(workspace/'admin.key'))
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context))

    def request(self, path, method='GET', body=None, query=None, content_type='application/json'):
        request = urllib.request.Request(self.base+path+('?' + urllib.parse.urlencode(query) if query else ''),
                                         method=method, data=json.dumps(body).encode() if body is not None else None,
                                         headers={'Content-Type':content_type})
        started = stamp()
        try:
            with self.opener.open(request, timeout=8) as response:
                code, raw = response.status, response.read().decode()
        except urllib.error.HTTPError as exc:
            code, raw = exc.code, exc.read().decode()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = raw
        return {'started': started, 'finished': stamp(), 'http_status': code, 'body': data,
                'request': {'path': path, 'method':method, 'query':query}}

    def call(self, *args, expected=200, **kwargs):
        response = self.request(*args, **kwargs)
        if response['http_status'] != expected:
            raise RuntimeError(json.dumps(response))
        return response['body']

    def watch(self, path, rv, selector, name):
        query = urllib.parse.urlencode({'watch':'true','resourceVersion':rv,'labelSelector':selector,'timeoutSeconds':5})
        events = []
        with self.opener.open(self.base+path+'?'+query, timeout=8) as response:
            for line in response:
                event = json.loads(line)
                events.append({'observed':stamp(), 'event':event})
                if event.get('type') == 'DELETED' and event.get('object',{}).get('metadata',{}).get('name') == name:
                    break
        return events


def experiments(api, etcd_port, version, results=None):
    if results is None:
        results = {}
    namespace = 'r2-observation'
    api.call('/api/v1/namespaces','POST',{'apiVersion':'v1','kind':'Namespace','metadata':{'name':namespace}},expected=201)
    path = f'/api/v1/namespaces/{namespace}/configmaps'
    selector = 'suite=r2'
    def create(name):
        return api.call(path,'POST',{'apiVersion':'v1','kind':'ConfigMap',
                        'metadata':{'name':name,'labels':{'suite':'r2'}},'data':{'value':'0'}},expected=201)
    originals = [create(f'cm-{i}') for i in range(3)]
    first = api.call(path,query={'labelSelector':selector,'limit':1})
    late = create('cm-late')
    pages, token = [first], first['metadata'].get('continue')
    while token:
        if len(pages) >= 10:
            raise RuntimeError('Pagination exceeded fixture bound')
        page = api.call(path,query={'labelSelector':selector,'limit':1,'continue':token})
        pages.append(page)
        token = page['metadata'].get('continue')
    fresh = api.call(path,query={'labelSelector':selector})
    names = [obj['metadata']['name'] for page in pages for obj in page['items']]
    rvs = [p['metadata']['resourceVersion'] for p in pages]
    matched = sorted(names)==['cm-0','cm-1','cm-2'] and len(set(rvs))==1 and len(fresh['items'])==4
    results['pagination'] = scenario(*CONTRACTS['pagination'], {'pages':pages,'created_between_pages':late,'fresh':fresh},
                                     'supported' if matched else 'refuted', 'Raw continue tokens and each collection RV retained.')
    before = api.call(path,query={'labelSelector':selector})
    with ThreadPoolExecutor(max_workers=1) as pool:
        watched = pool.submit(api.watch,path,before['metadata']['resourceVersion'],selector,'cm-0')
        changed = api.call(path+'/cm-0','PATCH',{'metadata':{'labels':{'suite':'outside'}}},content_type='application/merge-patch+json')
        events = watched.result(timeout=9)
    direct = api.request(path+'/cm-0')
    departed = [e['event'] for e in events if e['event'].get('type')=='DELETED' and e['event'].get('object',{}).get('metadata',{}).get('name')=='cm-0']
    matched = bool(departed) and direct['http_status']==200 and departed[-1]['object']['metadata']['uid']==direct['body']['metadata']['uid']==originals[0]['metadata']['uid'] and direct['body']['metadata']['labels']['suite']=='outside'
    results['selector_exit'] = scenario(*CONTRACTS['selector_exit'], {'watch_from':before['metadata']['resourceVersion'],
                                         'events':events,'patch_response':changed,'direct_get':direct},
                                        'supported' if matched else 'refuted', 'Object lifetime and selected watch membership are compared independently.')
    sequence = [create('rv-probe')]
    for value in ('1','2'):
        item = json.loads(json.dumps(sequence[-1])); item['data']['value']=value
        sequence.append(api.call(path+'/rv-probe','PUT',item))
    values = [s['metadata']['resourceVersion'] for s in sequence]
    numeric = all(re.fullmatch(r'[0-9]+',rv) for rv in values)
    ordered = numeric and all(int(b)>int(a) for a,b in zip(values,values[1:]))
    permitted = int(version.split('.')[1]) >= 35
    verdict = 'supported' if ordered else 'refuted' if numeric or permitted else 'inconclusive'
    results['resource_version'] = scenario(*CONTRACTS['resource_version'], {'sequence':sequence, 'rv_strings':values,
          'ordered_comparison_contract':permitted,'scope':'same cluster, core API group, ConfigMaps only; arbitrary-precision integers; no cross-resource/server generalization'},
          verdict, '1.34 numerical observations do not grant an ordering guarantee; 1.35+ observations do not prove all executions.')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def etcd(endpoint, body):
        req=urllib.request.Request(f'http://127.0.0.1:{etcd_port}'+endpoint,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        with opener.open(req, timeout=5) as response:
            return json.load(response)
    status = etcd('/v3/maintenance/status',{})
    revision = status['header']['revision']
    compaction = etcd('/v3/kv/compaction',{'revision':revision,'physical':True})
    exact = api.request(path,query={'resourceVersion':'1','resourceVersionMatch':'Exact'})
    fresh = api.request(path)
    verdict = 'supported' if (exact['http_status'],fresh['http_status'])==(410,200) else 'refuted' if exact['http_status']==200 else 'inconclusive'
    results['history_expiry'] = scenario(*CONTRACTS['history_expiry'], {'etcd_status':status,'compaction':compaction,
            'exact_rv_one':exact,'fresh_list':fresh,'first_continue_after_compaction':api.request(path,query={'labelSelector':selector,'limit':1,'continue':first['metadata']['continue']})},
            verdict,'Etcd compaction is not assumed to evict an apiserver cache snapshot. Continue expiry is recorded separately and may differ.')
    return results


def run_matrix_case(lab, version, cache):
    key = f'{version}-cache-{str(cache).lower()}'
    workspace = lab.workspace/key
    workspace.mkdir(mode=0o700)
    certificates(workspace)
    etcd_bin, api_bin = [binary('envtest-'+version, name) for name in ('etcd','kube-apiserver')]
    etcd_port, peer_port, api_port = free_ports(3)
    etcd_args=[etcd_bin,'--name=default','--data-dir='+str(workspace/'etcd'),
        f'--listen-client-urls=http://127.0.0.1:{etcd_port}',f'--advertise-client-urls=http://127.0.0.1:{etcd_port}',
        f'--listen-peer-urls=http://127.0.0.1:{peer_port}',f'--initial-advertise-peer-urls=http://127.0.0.1:{peer_port}',
        f'--initial-cluster=default=http://127.0.0.1:{peer_port}','--quota-backend-bytes=67108864','--log-level=warn']
    api_args=[api_bin,f'--etcd-servers=http://127.0.0.1:{etcd_port}','--bind-address=127.0.0.1','--advertise-address=127.0.0.1',
        f'--secure-port={api_port}',f'--watch-cache={str(cache).lower()}','--endpoint-reconciler-type=none',
        '--service-cluster-ip-range=10.250.0.0/24','--authorization-mode=RBAC',
        '--client-ca-file='+str(workspace/'ca.crt'),'--tls-cert-file='+str(workspace/'server.crt'),
        '--tls-private-key-file='+str(workspace/'server.key'),'--service-account-issuer=https://localhost',
        '--service-account-signing-key-file='+str(workspace/'service-account.key'),'--service-account-key-file='+str(workspace/'service-account.key')]
    processes=[]
    try:
        processes.append(lab.launch(key+'-etcd',etcd_args))
        processes.append(lab.launch(key+'-apiserver',api_args))
        api = API(api_port,workspace)
        deadline=time.monotonic()+45
        while True:
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('Private control plane exited; see captured logs')
            try:
                if api.call('/readyz')=='ok':
                    break
            except (OSError,RuntimeError):
                pass
            if time.monotonic()>deadline:
                raise TimeoutError('API readiness timeout')
            time.sleep(.2)
        actual=api.call('/version')
        if actual.get('gitVersion') != 'v'+version:
            raise RuntimeError('Server does not match requested version: '+str(actual))
        metrics=api.request('/metrics')
        feature_lines=[line for line in str(metrics['body']).splitlines() if 'kubernetes_feature_enabled' in line and not line.startswith('#')]
        lab.record.setdefault('servers',{})[key]={'version':actual,'watch_cache':cache,
            'argv':[str(a) for a in api_args], 'feature_gate_overrides':{},
            'feature_gate_metrics':feature_lines,'list_from_cache_snapshot_metric':[s for s in feature_lines if 'ListFromCacheSnapshot' in s],
            'feature_state_limit':'Absent metric means unobserved, not disabled; no feature-gate state inferred solely from documentation.',
            'etcd_version':lab.command([etcd_bin,'--version']),
            'binary_sha256':{'etcd':sha256(etcd_bin),'kube-apiserver':sha256(api_bin)}}
        partial={}
        lab.record.setdefault('partial_matrix_observations',{})[key]=partial
        return experiments(api,etcd_port,version,partial)
    finally:
        for process in reversed(processes):
            lab.stop(process)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='.lab-runs/r2/kubernetes.json')
    parser.add_argument('--plan',action='store_true')
    parser.add_argument('--prepare-assets',action='store_true',help='Verify/extract only the dedicated official Kubernetes assets; no server execution')
    args=parser.parse_args()
    if args.prepare_assets:
        for asset in manifest()['assets']:
            receipt = obtain(asset)
            print(f"VERIFIED: {asset['id']} {receipt['archive_sha256']} (not executed)",flush=True)
        return
    if args.plan:
        print(json.dumps({'versions':VERSIONS,'patch_scope':PATCH_SCOPE,'watch_cache':[True,False],'contracts':CONTRACTS,
                          'assets':[a for a in manifest()['assets'] if a['suite']=='kubernetes']},ensure_ascii=False,indent=2))
        return
    linux_required()
    with LabRun('kubernetes',args.output,['scripts/run_kubernetes_r2_lab.py','scripts/run_kubernetes_lab.py','scripts/get_review_r2_assets.py','labs/review-r2/kubernetes-assets.json']) as lab:
        lab.record['patch_scope'] = PATCH_SCOPE
        for version in VERSIONS:
            asset=next(a for a in manifest()['assets'] if a['id']=='envtest-'+version)
            for cache in (True,False):
                prefix=f'{version}-cache-{str(cache).lower()}'
                if asset['status']!='available':
                    cases={name:scenario(*contract,{'asset':asset},'blocked',asset['reason']) for name,contract in CONTRACTS.items()}
                else:
                    cases=run_matrix_case(lab,version,cache)
                lab.record['scenarios'].update({prefix+'/'+name:case for name,case in cases.items()})
    raise SystemExit(lab.exit_code)


if __name__=='__main__':
    main()
