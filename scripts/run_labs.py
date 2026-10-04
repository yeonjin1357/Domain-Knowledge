"""Run isolated learning experiments. No production service or existing database is used."""

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import platform
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def sqlite_lab():
    with tempfile.TemporaryDirectory(prefix="domain-book-") as temp:
        path = Path(temp) / "isolation.db"
        a = sqlite3.connect(path, timeout=0, isolation_level=None)
        b = sqlite3.connect(path, timeout=0, isolation_level=None)
        try:
            mode = a.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            assert mode == "wal"
            a.execute("CREATE TABLE item (id INTEGER PRIMARY KEY, value INTEGER CHECK(value >= 0))")
            a.execute("INSERT INTO item VALUES (1, 10)")
            a.execute("BEGIN")
            before = a.execute("SELECT value FROM item WHERE id=1").fetchone()[0]
            b.execute("UPDATE item SET value=20 WHERE id=1")
            snapshot = a.execute("SELECT value FROM item WHERE id=1").fetchone()[0]
            a.execute("COMMIT")
            after = a.execute("SELECT value FROM item WHERE id=1").fetchone()[0]
            assert (before, snapshot, after) == (10, 10, 20)
            a.execute("BEGIN IMMEDIATE")
            try:
                b.execute("UPDATE item SET value=30 WHERE id=1")
            except sqlite3.OperationalError as exc:
                busy_name = exc.sqlite_errorname
                assert exc.sqlite_errorcode == sqlite3.SQLITE_BUSY
            else:
                raise AssertionError("Second writer unexpectedly succeeded")
            finally:
                a.execute("ROLLBACK")
            a.execute("BEGIN")
            try:
                a.execute("UPDATE item SET value=40 WHERE id=1")
                a.execute("UPDATE item SET value=-1 WHERE id=1")
            except sqlite3.IntegrityError:
                # CHECK's default ABORT does not roll back the entire transaction.
                inside = a.execute("SELECT value FROM item WHERE id=1").fetchone()[0]
                assert inside == 40
                a.execute("ROLLBACK")
            else:
                raise AssertionError("CHECK constraint unexpectedly accepted negative value")
            restored = a.execute("SELECT value FROM item WHERE id=1").fetchone()[0]
            assert restored == 20
            return {"status": "passed", "sqlite_version": sqlite3.sqlite_version,
                    "journal_mode": mode, "reader_before": before,
                    "reader_in_same_transaction_after_writer_commit": snapshot,
                    "reader_after_transaction": after, "second_writer_error": busy_name,
                    "value_after_failed_statement_before_explicit_rollback": inside,
                    "value_after_explicit_rollback": restored}
        finally:
            a.close()
            b.close()


def http_lab():
    release = threading.Event()
    committed = threading.Event()
    lock = threading.Lock()
    state = {"attempts": 0, "effects": 0, "keys": set()}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            key = self.headers.get("Idempotency-Key")
            with lock:
                state["attempts"] += 1
                first = state["attempts"] == 1
            if first and not release.wait(3):
                return
            with lock:
                if key not in state["keys"]:
                    state["keys"].add(key)
                    state["effects"] += 1
            committed.set()
            try:
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"ok")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/order"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(timeout):
        req = urllib.request.Request(url, data=b"", headers={"Idempotency-Key": "demo-order-1"})
        with opener.open(req, timeout=timeout) as response:
            return response.status, response.read().decode()

    started = time.perf_counter()
    try:
        try:
            request(0.05)
        except (TimeoutError, socket.timeout):
            timeout_observed = True
        else:
            raise AssertionError("First request did not time out")
        elapsed = time.perf_counter() - started
        release.set()
        assert committed.wait(3), "Server did not commit after client timeout"
        status, body = request(2)
        assert status == 200 and body == "ok"
        assert state["attempts"] == 2 and state["effects"] == 1
        return {"status": "passed", "transport": "HTTP/1.0 on loopback",
                "client_timeout_observed": timeout_observed,
                "first_client_elapsed_seconds": elapsed,
                "attempts": state["attempts"], "business_effects": state["effects"],
                "retry_status": status,
                "limitation": "Demonstration uses an in-memory idempotency set, not durable deduplication."}
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def windows_lab():
    if os.name != "nt":
        return {"status": "skipped", "reason": "Win32 API requires Windows"}
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetSystemTimes.argtypes = [ctypes.POINTER(wintypes.FILETIME)] * 3
    kernel.GetSystemTimes.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL

    def number(ft):
        return (ft.dwHighDateTime << 32) | ft.dwLowDateTime

    def system_times():
        values = [wintypes.FILETIME() for _ in range(3)]
        if not kernel.GetSystemTimes(*(ctypes.byref(v) for v in values)):
            raise ctypes.WinError(ctypes.get_last_error())
        return [number(v) for v in values]  # idle, kernel INCLUDING idle, user

    def process_times():
        values = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(kernel.GetCurrentProcess(), *(ctypes.byref(v) for v in values)):
            raise ctypes.WinError(ctypes.get_last_error())
        return sum(number(v) for v in values[2:])

    start = time.perf_counter()
    s0, p0 = system_times(), process_times()
    time.sleep(0.2)
    until = time.perf_counter() + 0.2
    work = 0
    while time.perf_counter() < until:
        work += 1
    s1, p1 = system_times(), process_times()
    wall = time.perf_counter() - start
    idle, kernel_delta, user = [b - a for a, b in zip(s0, s1)]
    total = kernel_delta + user
    assert total > 0 and 0 <= idle <= total and p1 > p0
    busy = (total - idle) / total
    cpu_seconds = (p1 - p0) / 10_000_000
    return {"status": "passed", "logical_processors_reported": os.cpu_count(),
            "scope": "GetSystemTimes API processor-group scope; not a per-CPU measurement",
            "wall_seconds": wall, "system_delta_100ns": {"idle": idle, "kernel_including_idle": kernel_delta, "user": user},
            "system_busy_fraction": busy, "process_cpu_seconds": cpu_seconds,
            "process_mean_cpu_cores": cpu_seconds / wall,
            "limitation": "Short local observation; not a benchmark or hardware capacity estimate."}


def promql_lab(binary):
    if binary is None or not binary.exists():
        return {"status": "skipped", "reason": "Pass --promtool with a local verified executable"}
    version = subprocess.run([str(binary), "--version"], text=True, capture_output=True, check=True, timeout=15)
    result = subprocess.run([str(binary), "test", "rules", "tests.yml"],
                            cwd=ROOT / "labs/prometheus", text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    return {"status": "passed", "version": (version.stdout + version.stderr).strip(),
            "executable_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "output": (result.stdout + result.stderr).strip(), "input_kind": "synthetic fixture; real PromQL evaluation",
            "expression_assertions": 8, "alert_assertions": 5}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promtool", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / ".lab-runs/latest.json")
    args = parser.parse_args()
    record = {"run_at_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version.split()[0], "platform": platform.platform(),
              "experiments": {"sqlite_isolation": sqlite_lab(), "http_timeout": http_lab(),
                              "windows_cpu": windows_lab(), "promql": promql_lab(args.promtool.resolve() if args.promtool else None)}}
    record["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    record["fixture_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted((ROOT / "labs/prometheus").glob("*.yml"))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, result in record["experiments"].items():
        print(f"{name}: {result['status']}")
    print(f"Evidence: {args.output}")


if __name__ == "__main__":
    main()
