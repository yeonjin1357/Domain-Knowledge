"""Round-2 lab boundaries, evidence and owned-process cleanup (stdlib only)."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'labs/review-r2/assets.json'


def confined(directory, value):
    """Reject traversal and resolved symlink/junction escapes, including the base."""
    base = (ROOT / directory).resolve()
    if not base.is_relative_to(ROOT) or base == ROOT:
        raise ValueError(f'{directory} resolves outside its repository boundary')
    path = Path(value)
    path = (path if path.is_absolute() else ROOT / path).resolve()
    if not path.is_relative_to(base) or path == base:
        raise ValueError(f'Path must be a child of {directory}: {value}')
    return path


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def stamp():
    value = {'utc': datetime.now(timezone.utc).isoformat(), 'monotonic_ns': time.monotonic_ns()}
    if hasattr(time, 'CLOCK_MONOTONIC_RAW'):
        value['monotonic_raw_ns'] = time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)
    return value


def free_ports(count):
    sockets = []
    try:
        for _ in range(count):
            sock = socket.socket()
            sock.bind(('127.0.0.1', 0))
            sockets.append(sock)
        return [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()


def linux_required():
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise RuntimeError('Execution requires Linux amd64; no WSL launch is performed by this script')
    if os.geteuid() == 0:
        raise RuntimeError('Run as a non-root user')


def manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


def binary(asset_id, name):
    asset = next(a for a in manifest()['assets'] if a['id'] == asset_id)
    if asset['status'] != 'available':
        raise FileNotFoundError(f"{asset_id}: {asset['reason']}")
    directory = confined('.tools', asset['destination'])
    receipt = json.loads(confined('.tools', directory/'verified.json').read_text(encoding='utf-8'))
    if receipt['archive_sha256'] != asset['sha256']:
        raise ValueError('Archive receipt differs from pinned manifest')
    path = confined('.tools', directory/name)
    if name not in asset['members'] or sha256(path) != receipt['binaries'][name]:
        raise ValueError('Executable differs from verified extraction')
    return path


def scenario(hypothesis, success, refutation, observations, verdict, reason):
    if verdict not in ('supported', 'refuted', 'inconclusive', 'blocked', 'error'):
        raise ValueError(verdict)
    return {'hypothesis': hypothesis, 'success_condition': success,
            'refutation_condition': refutation, 'verdict': verdict,
            'reason': reason, 'observations': observations}


class LabRun:
    """Save failures too; only own temporary directories and process groups are removed."""
    def __init__(self, suite, output, inputs):
        self.output = confined('.lab-runs', output)
        if self.output.exists():
            raise FileExistsError(f'Refusing to overwrite evidence: {self.output}; choose a new --output')
        self.exit_code = 0
        self.processes, self.logs, self.native_dirs = [], [], []
        self.record = {'schema_version': 1, 'suite': suite, 'started': stamp(),
                       'platform': platform.platform(), 'python': platform.python_version(),
                       'scope': 'local synthetic lab; no production, cloud or external clock calibration',
                       'input_sha256': {p: sha256(ROOT/p) for p in sorted(set([
                           'scripts/lab_r2_common.py', 'labs/review-r2/assets.json', *inputs]))},
                       'scenarios': {}}

    def __enter__(self):
        parent = confined('.lab-runs', '.lab-runs/r2/work')
        parent.mkdir(parents=True, exist_ok=True)
        self.workspace = Path(tempfile.mkdtemp(prefix=self.record['suite']+'-', dir=parent))
        self.workspace.chmod(0o700)
        self.record['temporary_workspace'] = self.workspace.relative_to(ROOT).as_posix()
        return self

    def native_directory(self, prefix, reason):
        """Private Linux-native directory for tools that need POSIX modes.

        DrvFs (/mnt/c) does not keep chmod 0700 without the metadata mount option,
        so e.g. PostgreSQL rejects a data directory under .lab-runs. The directory is
        created by mkdtemp outside the repository, verified to be 0700 and removed
        after owned processes stop.
        """
        path = Path(tempfile.mkdtemp(prefix=prefix)).resolve()
        if path.is_relative_to(ROOT):
            shutil.rmtree(path)
            raise RuntimeError(f'Native directory unexpectedly inside repository: {path}')
        path.chmod(0o700)
        if path.stat().st_mode & 0o777 != 0o700:
            shutil.rmtree(path)
            raise RuntimeError(f'Filesystem did not keep mode 0700: {path}')
        self.native_dirs.append(path)
        self.record.setdefault('native_directories', []).append(
            {'path': str(path), 'mode': '0700', 'reason': reason})
        return path

    def command(self, args, timeout=20, env=None, cwd=None):
        started = stamp()
        p = subprocess.Popen([str(a) for a in args], cwd=cwd or self.workspace, env=self.environment(env),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             encoding='utf-8', errors='replace', start_new_session=True)
        self.processes.append(p)
        try:
            stdout, stderr = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.stop(p)
            p.communicate()
            raise
        return {'argv': [str(a) for a in args], 'started': started, 'finished': stamp(),
                'returncode': p.returncode, 'stdout': stdout, 'stderr': stderr}

    def environment(self, overrides=None):
        # Do not inherit telemetry destinations or libpq service/connection overrides.
        env = {k: v for k, v in os.environ.items() if not k.startswith(('OTEL_', 'PG'))}
        env.update(overrides or {})
        env.update(TMPDIR=str(self.workspace), TMP=str(self.workspace), TEMP=str(self.workspace))
        return env

    def launch(self, name, args, env=None):
        path = confined('.lab-runs', self.workspace/(name+'.log'))
        handle = path.open('wb')
        try:
            p = subprocess.Popen([str(a) for a in args], cwd=self.workspace, env=self.environment(env),
                                 stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
        except BaseException:
            handle.close()
            raise
        self.logs.append((name, path, handle))
        self.processes.append(p)
        return p

    def stop(self, process):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)

    def __exit__(self, exc_type, exc, tb):
        errors = []
        for process in reversed(self.processes):
            try:
                self.stop(process)
            except Exception as failure:
                errors.append(repr(failure))
        self.record['logs'] = {}
        for name, path, handle in self.logs:
            handle.close()
            self.record['logs'][name] = path.read_text(encoding='utf-8', errors='replace')
        if exc:
            self.record['error'] = ''.join(traceback.format_exception(exc_type, exc, tb))
            self.exit_code = 1
        if errors:
            self.exit_code = 1
        verdicts = [s['verdict'] for s in self.record['scenarios'].values()]
        self.record['verdict_counts'] = {name: verdicts.count(name) for name in sorted(set(verdicts))}
        if 'error' in verdicts:
            self.exit_code = 1
        # Registered native directories were created by mkdtemp and checked outside ROOT.
        if not errors:
            for path in self.native_dirs:
                try:
                    shutil.rmtree(path)
                except Exception as failure:
                    errors.append(repr(failure))
            self.record['native_directories_removed'] = not errors
        # Both target and parent were resolved and checked before recursive removal.
        target = confined('.lab-runs', self.workspace)
        if errors:
            self.record['cleanup'] = {'completed': False, 'errors': errors, 'retained_workspace': str(target)}
        else:
            try:
                shutil.rmtree(target)
                self.record['cleanup'] = {'completed': True, 'owned_processes_stopped': len(self.processes)}
            except Exception as failure:
                self.exit_code = 1
                self.record['cleanup'] = {'completed': False, 'errors': [repr(failure)]}
        self.record['finished'] = stamp()
        self.record['status'] = 'error' if self.exit_code else 'recorded'
        self.output.parent.mkdir(parents=True, exist_ok=True)
        with self.output.open('x', encoding='utf-8', newline='\n') as dest:
            json.dump(self.record, dest, ensure_ascii=False, indent=2, allow_nan=False)
            dest.write('\n')
        print(f"RECORDED: {self.record['suite']} -> {self.output}; status={self.record['status']}", flush=True)
        return isinstance(exc, Exception) if exc is not None else False
