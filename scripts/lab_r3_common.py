"""Round 3: small summaries with complete, authenticated gzip sidecars.

No third-party Python modules. Linux runners inherit the reviewed native-directory
and process-group ownership rules without changing round-2 provenance.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import time
import traceback

from lab_r2_common import (ROOT, LabRun as PreviousRun, confined, free_ports,
                           linux_required, scenario, sha256, stamp)

MANIFEST = ROOT / 'labs/review-r3/assets.json'
RAW_LIMIT = 16 * 1024 * 1024
TOTAL_LIMIT = 64 * 1024 * 1024
SUMMARY_LIMIT = 1024 * 1024


def manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


def checked_asset(asset_id):
    asset = next(a for a in manifest()['assets'] if a['id'] == asset_id)
    directory = confined('.tools', asset['destination'])
    receipt = json.loads((directory / 'verified.json').read_text(encoding='utf-8'))
    if receipt['archive_sha256'] != asset['sha256']:
        raise ValueError('Asset receipt differs from pinned archive')
    hashes = receipt.get('files', receipt.get('binaries', {}))
    for name, digest in hashes.items():
        path = confined('.tools', directory / name)
        if not path.is_relative_to(directory) or sha256(path) != digest:
            raise ValueError(f'Asset file differs: {name}')
    if not hashes:
        raise ValueError('Empty asset receipt')
    return asset, directory, receipt


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')


def read_sidecar(result_path, item):
    base = Path(result_path).resolve().parent
    path = (base / item['path']).resolve()
    if not path.is_relative_to(base) or path == base or path.suffix != '.gz':
        raise ValueError('Sidecar outside result directory')
    if path.stat().st_size != item['gzip_bytes'] or sha256(path) != item['gzip_sha256']:
        raise ValueError('Compressed evidence hash/size differs')
    with gzip.open(path, 'rb') as stream:
        raw = stream.read(RAW_LIMIT+1)
    if len(raw) > RAW_LIMIT or len(raw) != item['raw_bytes']:
        raise ValueError('Raw evidence size differs or exceeds limit')
    if hashlib.sha256(raw).hexdigest() != item['raw_sha256']:
        raise ValueError('Raw evidence hash differs')
    return raw


class LabRun(PreviousRun):
    def __init__(self, suite, output, inputs):
        self.output = confined('.lab-runs', output)
        if self.output.exists():
            raise FileExistsError(f'Refusing to overwrite {self.output}')
        self.sidecars = confined('.lab-runs', self.output.with_suffix('.raw'))
        if self.sidecars.exists():
            raise FileExistsError(f'Refusing to reuse {self.sidecars}')
        self.processes, self.logs, self.native_dirs = [], [], []
        self.exit_code, self.raw_total, self.command_number = 0, 0, 0
        self.record = {
            'schema_version': 3, 'round': 3, 'suite': suite, 'started': stamp(),
            'platform': platform.platform(), 'python': platform.python_version(),
            'scope': 'Local synthetic observations; no production or external time calibration',
            'input_sha256': {p: sha256(ROOT/p) for p in sorted(set([
                'scripts/lab_r2_common.py', 'scripts/lab_r3_common.py',
                'labs/review-r3/assets.json', 'labs/review-r3/evidence-policy.md', *inputs]))},
            'limits': {'summary_bytes': SUMMARY_LIMIT, 'raw_artifact_bytes': RAW_LIMIT,
                       'total_raw_bytes': TOTAL_LIMIT},
            'artifacts': {}, 'scenarios': {}}

    def __enter__(self):
        self.output.parent.mkdir(parents=True, exist_ok=True)
        # Reserve exclusively before starting any process. A crash leaves a visible
        # incomplete record; a second run cannot silently reuse this name.
        self.summary_handle = self.output.open('xb')
        self.summary_handle.write(json_bytes({'status': 'incomplete', 'suite': self.record['suite']}))
        self.summary_handle.flush()
        try:
            self.sidecars.mkdir()
            parent = confined('.lab-runs', '.lab-runs/r3/work')
            parent.mkdir(parents=True, exist_ok=True)
            self.workspace = Path(tempfile.mkdtemp(prefix=self.record['suite']+'-', dir=parent))
            self.workspace.chmod(0o700)
            self.record['temporary_workspace'] = self.workspace.relative_to(ROOT).as_posix()
        except BaseException:
            if hasattr(self, 'workspace'):
                shutil.rmtree(confined('.lab-runs', self.workspace))
            self.summary_handle.close()
            raise
        return self

    def artifact(self, name, raw, media_type='text/plain; charset=utf-8'):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in self.record['artifacts']:
            raise ValueError('Artifact name must be unique and plain')
        if isinstance(raw, str):
            raw = raw.encode('utf-8')
        if len(raw) > RAW_LIMIT or self.raw_total + len(raw) > TOTAL_LIMIT:
            raise ValueError('Evidence budget exceeded; no silent truncation')
        path = self.sidecars / (name+'.gz')
        with path.open('xb') as dest:
            with gzip.GzipFile(filename='', fileobj=dest, mode='wb', mtime=0, compresslevel=6) as gz:
                gz.write(raw)
        item = {'path': path.relative_to(self.output.parent).as_posix(),
                'media_type': media_type, 'raw_bytes': len(raw),
                'raw_sha256': hashlib.sha256(raw).hexdigest(),
                'gzip_bytes': path.stat().st_size, 'gzip_sha256': sha256(path)}
        self.record['artifacts'][name] = item
        self.raw_total += len(raw)
        return name

    def data(self, name, value):
        return self.artifact(name, json_bytes(value), 'application/json')

    def raw(self, name):
        return read_sidecar(self.output, self.record['artifacts'][name])

    def environment(self, overrides=None):
        env = super().environment()
        for key in list(env):
            if key.startswith(('MYSQL', 'MARIADB')) or key in ('LD_PRELOAD', 'LD_LIBRARY_PATH'):
                env.pop(key)
        env.update(LC_ALL='C', TZ='UTC', PYTHONDONTWRITEBYTECODE='1')
        env.update(overrides or {})
        return env

    def command(self, args, timeout=20, env=None, cwd=None):
        self.command_number += 1
        name = f'command-{self.command_number:03}'
        path = self.workspace / (name+'.txt')
        started = stamp()
        failure = None
        with path.open('xb') as dest:
            p = subprocess.Popen([str(a) for a in args], cwd=cwd or self.workspace,
                                 env=self.environment(env), stdout=dest, stderr=subprocess.STDOUT,
                                 start_new_session=True)
            self.processes.append(p)
            deadline = time.monotonic()+timeout
            while p.poll() is None:
                if time.monotonic() > deadline or path.stat().st_size > RAW_LIMIT:
                    failure = 'timeout or output budget exceeded'
                    self.stop(p)
                    break
                time.sleep(.05)
        artifact = self.artifact(name, path.read_bytes())
        result = {'argv': [str(a) for a in args], 'started': started, 'finished': stamp(),
                  'returncode': p.returncode, 'artifact': artifact, 'failure': failure}
        self.record.setdefault('commands', []).append(result)
        if failure:
            raise RuntimeError(f'{name}: {failure}')
        return result

    def __exit__(self, exc_type, exc, tb):
        errors, stopped = [], True
        for process in reversed(self.processes):
            try:
                self.stop(process)
            except Exception as failure:
                stopped = False
                errors.append(f'stop: {failure!r}')
        for name, path, handle in self.logs:
            try:
                handle.close()
                if path.stat().st_size > RAW_LIMIT:
                    raise ValueError('Process log exceeds evidence budget')
                self.artifact('log-'+name, path.read_bytes())
            except Exception as failure:
                errors.append(f'log: {failure!r}')
        if exc:
            self.record['error'] = ''.join(traceback.format_exception(exc_type, exc, tb))
            self.exit_code = 1
        native_errors = []
        if stopped:
            for path in self.native_dirs:
                try:
                    shutil.rmtree(path)
                except Exception as failure:
                    native_errors.append(f'native cleanup: {failure!r}')
        errors.extend(native_errors)
        self.record['native_directories_removed'] = stopped and not native_errors
        # Retain uncompressed work on an evidence/cleanup failure, including logs
        # that could not be archived; never label an incomplete bundle publishable.
        target = confined('.lab-runs', self.workspace)
        if not errors and exc is None:
            try:
                shutil.rmtree(target)
            except Exception as failure:
                errors.append(f'workspace cleanup: {failure!r}')
        self.record['cleanup'] = {'completed': stopped and not errors,
                                  'errors': errors, 'workspace_retained': target.exists()}
        verdicts = [s['verdict'] for s in self.record['scenarios'].values()]
        self.record['verdict_counts'] = {v: verdicts.count(v) for v in sorted(set(verdicts))}
        if errors or 'error' in verdicts:
            self.exit_code = 1
        self.record['finished'] = stamp()
        self.record['status'] = 'error' if self.exit_code else 'recorded'
        data = json_bytes(self.record)
        if len(data) > SUMMARY_LIMIT:
            self.exit_code = 1
            self.record['status'] = 'error'
            data = json_bytes({'schema_version': 3, 'status': 'error',
                               'error': 'Summary budget exceeded; not publishable',
                               'cleanup': self.record['cleanup']})
        self.summary_handle.seek(0)
        self.summary_handle.truncate()
        self.summary_handle.write(data)
        self.summary_handle.close()
        print(f'RECORDED: {self.output}; status={self.record["status"]}', flush=True)
        return isinstance(exc, Exception) if exc is not None else False
