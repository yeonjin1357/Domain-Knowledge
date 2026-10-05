"""Download only manifest-pinned official release assets; never execute them."""
import argparse
import json
from pathlib import Path
import tarfile
import urllib.request

from lab_r2_common import ROOT, confined, manifest, sha256, stamp


def obtain(asset):
    cache = confined('.tools', '.tools/r2/archives/'+asset['name'])
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.exists() or sha256(cache) != asset['sha256']:
        partial = confined('.tools', str(cache)+'.partial')
        try:
            request = urllib.request.Request(asset['url'], headers={'User-Agent': 'Domain-Knowledge-lab-review'})
            with urllib.request.urlopen(request, timeout=60) as response, partial.open('wb') as out:
                for block in iter(lambda: response.read(1024*1024), b''):
                    out.write(block)
            if partial.stat().st_size != asset['size'] or sha256(partial) != asset['sha256']:
                raise ValueError('Size or SHA256 mismatch: '+asset['name'])
            partial.replace(cache)
        finally:
            partial.unlink(missing_ok=True)
    if sha256(cache) != asset['sha256']:
        raise ValueError('Archive hash mismatch before extraction')
    destination = confined('.tools', asset['destination'])
    destination.mkdir(parents=True, exist_ok=True)
    hashes = {}
    with tarfile.open(cache, 'r:gz') as archive:
        for name in asset['members']:
            members = [m for m in archive.getmembers() if m.isfile() and Path(m.name).name == name]
            if len(members) != 1:
                raise ValueError('Missing/ambiguous regular binary member: '+name)
            target = confined('.tools', destination/name)
            # Never extract archive paths, links, owners or permissions wholesale.
            with archive.extractfile(members[0]) as src, target.open('wb') as dest:
                for block in iter(lambda: src.read(1024*1024), b''):
                    dest.write(block)
            target.chmod(0o755)
            hashes[name] = sha256(target)
    receipt = {'asset_id': asset['id'], 'checked': stamp(), 'archive_sha256': asset['sha256'],
               'archive': cache.relative_to(ROOT).as_posix(), 'binaries': hashes,
               'execution': 'not executed by downloader'}
    confined('.tools', destination/'verified.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--which', choices=('all', 'otel', 'prometheus', 'kubernetes'), default='all')
    args = parser.parse_args()
    for asset in manifest()['assets']:
        if args.which not in ('all', asset['suite']):
            continue
        if asset['status'] != 'available':
            print(f"UNAVAILABLE: {asset['id']}: {asset['reason']}", flush=True)
            continue
        receipt = obtain(asset)
        print(f"VERIFIED: {asset['id']} {receipt['archive_sha256']} (downloaded/extracted, not run)", flush=True)


if __name__ == '__main__':
    main()
