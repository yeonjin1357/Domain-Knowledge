"""Download pinned official Linux amd64 lab tools without installing services."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--which', choices=('all','envtest','otelcol'), default='all')
    args = parser.parse_args()
    manifest = json.loads((ROOT/'labs/runtime-assets.json').read_text())
    for asset in manifest['archives']:
        kind = 'envtest' if asset['name'].startswith('envtest') else 'otelcol'
        if args.which not in ('all',kind):
            continue
        cache = ROOT/'.tools'/asset['name']
        cache.parent.mkdir(exist_ok=True)
        if cache.exists() and hashlib.sha256(cache.read_bytes()).hexdigest() == asset['sha256']:
            data = cache.read_bytes()
        else:
            with urllib.request.urlopen(asset['url'],timeout=60) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != asset['sha256']:
                raise SystemExit('SHA256 mismatch: '+asset['name'])
            cache.write_bytes(data)
        destination = ROOT/'.tools'/('envtest-1.34.1' if kind=='envtest' else 'otelcol-0.137.0')
        destination.mkdir(exist_ok=True)
        names = ('kube-apiserver','etcd','kubectl') if kind=='envtest' else ('otelcol',)
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            for name in names:
                matches=[m for m in archive.getmembers() if m.isfile() and Path(m.name).name==name]
                if len(matches)!=1:
                    raise SystemExit('Unexpected archive member: '+name)
                with archive.extractfile(matches[0]) as source:
                    (destination/name).write_bytes(source.read())
                (destination/name).chmod(0o755)
        print(kind+': pinned archive SHA256 verified; local binaries extracted',flush=True)


if __name__=='__main__':
    main()
