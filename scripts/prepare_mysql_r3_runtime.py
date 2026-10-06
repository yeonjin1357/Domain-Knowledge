"""Authenticated private MySQL runtime libraries; never install system packages.

Windows: --download-only. Linux amd64: default extracts with dpkg-deb, validates
the owned package tree, and creates private SONAME aliases. No system links.
"""
import argparse
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import struct
import subprocess
import tarfile
import tempfile

from lab_r3_common import ROOT, confined, json_bytes, sha256
from get_review_r3_assets import fetch

PIN = ROOT / 'labs/review-r3/mysql-runtime.json'


def specification():
    return json.loads(PIN.read_text(encoding='utf-8'))


def elf_amd64(path):
    header = path.read_bytes()[:20]
    if len(header) != 20 or header[:6] != b'\x7fELF\x02\x01' or struct.unpack('<H', header[18:20])[0] != 62:
        raise ValueError(f'Expected ELF64 little-endian AMD64: {path}')


def checked_runtime():
    spec = specification()
    dest = confined('.tools', spec['destination'])
    receipt = json.loads((dest/'verified.json').read_text(encoding='utf-8'))
    if receipt['manifest_sha256'] != sha256(PIN):
        raise ValueError('Private runtime manifest changed; refuse stale receipt')
    expected = {Path(p['member']).name for p in spec['packages']}
    if set(receipt['files']) != expected:
        raise ValueError('Incomplete runtime receipt')
    for name, digest in receipt['files'].items():
        pin = next(p for p in spec['packages'] if Path(p['member']).name == name)
        if digest != pin['member_sha256']:
            raise ValueError('Runtime receipt differs from pinned ELF digest')
        path = confined('.tools', dest/'lib'/name)
        if not path.is_relative_to(dest) or sha256(path) != digest:
            raise ValueError('Private runtime library differs')
        elf_amd64(path)
    for package in spec['packages']:
        if sha256(confined('.tools', package['archive'])) != package['sha256']:
            raise ValueError('Runtime package archive differs')
        target = Path(package['member']).name
        for alias in (package['alias'], package.get('upstream_alias')):
            if alias and (not (dest/'lib'/alias).is_symlink() or os.readlink(dest/'lib'/alias) != target):
                raise ValueError('Private runtime alias differs')
    return dest/'lib', receipt


def package_members(data):
    """Reject path/link escapes before dpkg-deb writes any package files."""
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        seen = set()
        for member in tf.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or '\\' in member.name or str(path) in seen:
                raise ValueError('Unsafe/duplicate deb member')
            seen.add(str(path))
            if not (member.isdir() or member.isfile() or member.issym()):
                raise ValueError('Unsupported deb member type')
            if member.issym():
                link = PurePosixPath(member.linkname)
                if link.is_absolute() or '..' in link.parts or '\\' in member.linkname:
                    raise ValueError('Unsafe deb link')


def prepare():
    if platform.system() != 'Linux' or platform.machine() != 'x86_64' or struct.calcsize('P') != 8:
        raise RuntimeError('Runtime extraction/aliases require Linux AMD64 LP64; Windows may --download-only')
    if os.geteuid() == 0:
        raise RuntimeError('Use an unprivileged user')
    dpkg = shutil.which('dpkg-deb')
    if not dpkg:
        raise RuntimeError('dpkg-deb unavailable; no automatic installation')
    spec = specification()
    dest = confined('.tools', spec['destination'])
    if dest.exists():
        checked_runtime()
        print('VERIFIED existing private runtime')
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='mysql-runtime-stage-', dir=dest.parent))
    stage = confined('.tools', stage)
    destination_owned = False
    try:
        (stage/'lib').mkdir()
        files, reuse = {}, {}
        for package in spec['packages']:
            archive = confined('.tools', package['archive'])
            if sha256(archive) != package['sha256']:
                raise ValueError('Package differs before extraction')
            command = subprocess.run([dpkg, '--fsys-tarfile', str(archive)], check=True,
                                     capture_output=True, timeout=20)
            if len(command.stdout) > 4*1024*1024:
                raise ValueError('Unexpected package payload size')
            package_members(command.stdout)
            tree = stage/package['id']
            tree.mkdir()
            subprocess.run([dpkg, '--extract', str(archive), str(tree)], check=True,
                           capture_output=True, timeout=20)
            member = (tree/package['member']).resolve()
            if not member.is_relative_to(tree) or not member.is_file():
                raise ValueError('Missing/escaped library member')
            elf_amd64(member)
            digest = sha256(member)
            if digest != package['member_sha256']:
                raise ValueError('Extracted ELF differs from the pinned package member')
            source = member
            if package.get('reuse_file'):
                old = confined('.tools', package['reuse_file'])
                if old.exists():
                    if sha256(old) != digest:
                        raise ValueError('Existing PostgreSQL libnuma differs from authenticated package')
                    source = old
                    reuse[package['id']] = package['reuse_file']
            target = stage/'lib'/member.name
            with source.open('rb') as inp, target.open('xb') as out:
                shutil.copyfileobj(inp, out)
            target.chmod(0o644)
            files[member.name] = digest
            for alias in (package['alias'], package.get('upstream_alias')):
                if alias:
                    (stage/'lib'/alias).symlink_to(member.name)
            shutil.rmtree(confined('.tools', tree))
        receipt = {'manifest_sha256': sha256(PIN), 'files': files,
                   'reused_after_package_comparison': reuse,
                   'package_sha256': {p['id']: p['sha256'] for p in spec['packages']},
                   'abi_scope': spec['abi']['scope'], 'system_installation': False}
        with (stage/'verified.json').open('xb') as out:
            out.write(json_bytes(receipt))
        # An existing complete or partial destination must never be overwritten.
        dest.mkdir()
        destination_owned = True
        for child in stage.iterdir():
            child.rename(dest/child.name)
        checked_runtime()
        print('PREPARED private libaio/libnuma; no system files changed')
    except BaseException:
        # Ownership starts only after exclusive mkdir succeeds. Never remove an
        # existing destination, including a partial tree from someone else's run.
        if destination_owned:
            resolved = confined('.tools', dest)
            if resolved != dest or dest.is_symlink():
                raise RuntimeError('Owned runtime destination changed; refuse cleanup')
            shutil.rmtree(resolved)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(confined('.tools', stage))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download-only', action='store_true')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if args.verify_only:
        checked_runtime()
        print('PASS: runtime package/file hashes and private aliases')
        return
    for package in specification()['packages']:
        fetch(package['url'], confined('.tools', package['archive']), package['sha256'], package.get('size'))
        print('VERIFIED package: '+package['id'])
    if not args.download_only:
        prepare()


if __name__ == '__main__':
    main()
