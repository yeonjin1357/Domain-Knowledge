"""Official signed MySQL assets; verify before safe, symlink-free extraction."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

from lab_r3_common import ROOT, MANIFEST, checked_asset, confined, json_bytes, manifest, sha256


def fetch(url, path, expected, size=None):
    path = confined('.tools', path)
    if path.exists():
        if sha256(path) != expected or (size is not None and path.stat().st_size != size):
            raise ValueError(f'Existing asset differs: {path}; no overwrite')
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name+'.partial')
    owned_partial = False
    try:
        with partial.open('xb') as dest:
            owned_partial = True
            with urllib.request.urlopen(url, timeout=60) as source:
                shutil.copyfileobj(source, dest)
        if sha256(partial) != expected or (size is not None and partial.stat().st_size != size):
            raise ValueError(f'Official asset hash/size mismatch: {url}')
        # Refuse to overwrite an asset placed there concurrently.
        with path.open('xb') as dest, partial.open('rb') as source:
            shutil.copyfileobj(source, dest)
    finally:
        if owned_partial and partial.exists():
            partial.unlink()
    return path


def program(name):
    found = shutil.which(name)
    if not found and os.name == 'nt':
        candidate = Path('C:/Program Files/Git/usr/bin')/(name+'.exe')
        if candidate.is_file():
            found = str(candidate)
    if not found:
        raise FileNotFoundError(f'{name} unavailable; install nothing; use an existing trusted GPG environment')
    return found


def signed_archive(asset, directory):
    directory.mkdir(parents=True, exist_ok=True)
    key = manifest()['mysql_signing_key']
    keyfile = fetch(key['url'], directory / 'RPM-GPG-KEY-mysql-2025', key['sha256'])
    archive = fetch(asset['url'], directory/asset['name'], asset['sha256'], asset['size'])
    signature = fetch(asset['signature_url'], directory/(asset['name']+'.asc'), asset['signature_sha256'])
    # gpg --dearmor does not import keys, start an agent, or modify the user's keyring.
    work = Path(tempfile.mkdtemp(prefix='signature-', dir=directory))
    try:
        keyring = work/'key.gpg'
        cmd = [program('gpg'), '--no-options', '--homedir', str(work), '--batch',
               '--no-autostart', '--output', str(keyring), '--dearmor', str(keyfile)]
        p = subprocess.run(cmd, capture_output=True, timeout=15)
        if p.returncode:
            raise RuntimeError(p.stderr.decode('utf-8', 'replace'))
        # Relative keyring works in both GnuPG for Windows and Linux.
        cmd = [program('gpgv'), '--homedir', str(work), '--status-fd', '1',
               '--keyring', 'key.gpg', str(signature), str(archive)]
        p = subprocess.run(cmd, capture_output=True, timeout=45)
        status = p.stdout.decode('utf-8', 'replace')
        valid = [line.split() for line in status.splitlines() if line.startswith('[GNUPG:] VALIDSIG ')]
        if p.returncode or len(valid) != 1 or valid[0][2] != key['fingerprint']:
            raise ValueError(f'GPG authentication failed: {status} {p.stderr.decode("utf-8", "replace")}')
        return archive, {'method': 'GPG detached signature with pinned official fingerprint',
                         'status': status, 'stderr': p.stderr.decode('utf-8', 'replace'),
                         'fingerprint': key['fingerprint'], 'returncode': p.returncode}
    finally:
        target = confined('.tools', work)
        shutil.rmtree(target)


def archive_files(tf, prefix):
    entries = {}
    for entry in tf.getmembers():
        path = PurePosixPath(entry.name)
        if path.is_absolute() or '..' in path.parts or '\\' in entry.name or not path.parts or path.parts[0] != prefix:
            raise ValueError(f'Unsafe tar path: {entry.name}')
        if entry.name in entries:
            if entry.isdir() and entries[entry.name].isdir():
                continue  # Official MySQL tar repeats parent directory headers.
            raise ValueError('Duplicate non-directory tar member')
        if not (entry.isdir() or entry.isfile() or entry.issym() or entry.islnk()):
            raise ValueError(f'Unsupported tar member: {entry.name}')
        entries[entry.name] = entry
    return entries


def resolved_member(entries, entry):
    seen = set()
    while entry.issym() or entry.islnk():
        if entry.name in seen:
            raise ValueError('Tar link cycle')
        seen.add(entry.name)
        link = entry.linkname
        if link.startswith('/') or '\\' in link:
            raise ValueError('Unsafe tar link')
        target = posixpath.normpath(posixpath.join(posixpath.dirname(entry.name), link) if entry.issym() else link)
        if target not in entries:
            raise ValueError('Tar link escapes or has no target')
        entry = entries[target]
    if not entry.isfile():
        raise ValueError('Tar link does not resolve to a regular file')
    return entry


def extract(asset, archive, signature):
    dest = confined('.tools', asset['destination'])
    if dest.exists():
        checked_asset(asset['id'])
        print(f'VERIFIED existing: {asset["id"]}')
        return
    dest.mkdir(parents=True)  # no exist_ok: incomplete extraction is never reused
    hashes, links = {}, {}
    with tarfile.open(archive, 'r:xz') as tf:
        entries = archive_files(tf, asset['archive_root'])
        total = sum(e.size for e in entries.values() if e.isfile())
        if total > 1024*1024*1024:
            raise ValueError('Unexpected expanded archive size')
        for entry in entries.values():
            name = PurePosixPath(entry.name).relative_to(asset['archive_root']).as_posix()
            if name == '.' or entry.isdir():
                continue
            original = resolved_member(entries, entry)
            path = confined('.tools', dest/name)
            if not path.is_relative_to(dest):
                raise ValueError('Extraction escaped destination')
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as output, tf.extractfile(original) as source:
                shutil.copyfileobj(source, output)
            path.chmod(0o755 if original.mode & 0o111 else 0o644)
            hashes[name] = sha256(path)
            if entry.issym() or entry.islnk():
                links[name] = original.name
    receipt = {'asset_id': asset['id'], 'archive_sha256': asset['sha256'],
               'signature_verification': signature, 'files': hashes,
               'materialized_links': links,
               'extraction': 'regular files; links materialized from authenticated in-archive targets'}
    with (dest/'verified.json').open('xb') as output:
        output.write(json_bytes(receipt))
    print(f'VERIFIED and extracted: {asset["id"]}; {len(hashes)} files')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    for asset in manifest()['assets']:
        if asset['suite'] == 'prometheus' or args.verify_only:
            checked_asset(asset['id'])
            print(f'VERIFIED existing: {asset["id"]}')
        else:
            archive, signature = signed_archive(asset, confined('.tools', '.tools/r3/archives'))
            extract(asset, archive, signature)


if __name__ == '__main__':
    main()
