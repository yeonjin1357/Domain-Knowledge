"""Real concurrency/visibility experiments in a new, private PostgreSQL cluster.

Run under Ubuntu 24.04 amd64 after get_postgres_lab.py. Uses libpq via ctypes.
Only a private Unix socket is enabled; no TCP listener or existing DB is used.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import ctypes as C
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


class DatabaseError(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def bind_libpq(path):
    lib = C.CDLL(str(path))
    signatures = {
        "PQconnectdb": (C.c_void_p, [C.c_char_p]),
        "PQstatus": (C.c_int, [C.c_void_p]),
        "PQerrorMessage": (C.c_char_p, [C.c_void_p]),
        "PQfinish": (None, [C.c_void_p]),
        "PQexec": (C.c_void_p, [C.c_void_p, C.c_char_p]),
        "PQresultStatus": (C.c_int, [C.c_void_p]),
        "PQresultErrorField": (C.c_char_p, [C.c_void_p, C.c_int]),
        "PQresultErrorMessage": (C.c_char_p, [C.c_void_p]),
        "PQntuples": (C.c_int, [C.c_void_p]),
        "PQnfields": (C.c_int, [C.c_void_p]),
        "PQfname": (C.c_char_p, [C.c_void_p, C.c_int]),
        "PQgetisnull": (C.c_int, [C.c_void_p, C.c_int, C.c_int]),
        "PQgetvalue": (C.c_char_p, [C.c_void_p, C.c_int, C.c_int]),
        "PQclear": (None, [C.c_void_p]),
    }
    for name, (result, args) in signatures.items():
        function = getattr(lib, name)
        function.restype, function.argtypes = result, args
    return lib


class Connection:
    def __init__(self, lib, socket_dir, name, role="dk_owner"):
        self.lib = lib
        self.pointer = lib.PQconnectdb(
            f"host={socket_dir} port=55432 dbname=postgres user={role} "
            f"application_name={name} connect_timeout=5".encode())
        if not self.pointer or lib.PQstatus(self.pointer) != 0:
            message = lib.PQerrorMessage(self.pointer).decode() if self.pointer else "allocation failed"
            self.close()
            raise RuntimeError(message)

    def execute(self, sql):
        lib = self.lib
        result = lib.PQexec(self.pointer, sql.encode())
        if not result:
            raise RuntimeError(lib.PQerrorMessage(self.pointer).decode())
        try:
            if lib.PQresultStatus(result) not in (1, 2):
                code = lib.PQresultErrorField(result, ord("C"))
                raise DatabaseError(code.decode() if code else None,
                                    lib.PQresultErrorMessage(result).decode())
            columns = [lib.PQfname(result, i).decode() for i in range(lib.PQnfields(result))]
            return [{name: None if lib.PQgetisnull(result, row, col)
                     else lib.PQgetvalue(result, row, col).decode()
                     for col, name in enumerate(columns)} for row in range(lib.PQntuples(result))]
        finally:
            lib.PQclear(result)

    def scalar(self, sql):
        return next(iter(self.execute(sql)[0].values()))

    def error(self, sql, expected):
        try:
            self.execute(sql)
        except DatabaseError as exc:
            assert exc.code == expected, (exc.code, expected)
            return exc.code
        raise AssertionError("SQL unexpectedly succeeded: " + sql)

    def close(self):
        if self.pointer:
            self.lib.PQfinish(self.pointer)
            self.pointer = None


def wait_for_lock(observer, pid):
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        rows = observer.execute(
            f"SELECT state, wait_event_type, wait_event, pg_blocking_pids(pid)::text AS blockers "
            f"FROM pg_stat_activity WHERE pid={int(pid)}")
        if rows and rows[0]["wait_event_type"] == "Lock":
            return rows[0]
        time.sleep(.025)
    raise AssertionError("Did not observe the intended lock wait")


def experiments(lib, socket_dir):
    connections = []
    def connect(name, role="dk_owner"):
        item = Connection(lib, socket_dir, name, role)
        connections.append(item)
        return item

    evidence = {}
    try:
        a, b, observer = [connect(name) for name in ("dk-holder", "dk-waiter", "dk-observer")]
        evidence["server_version"] = observer.scalar("SELECT version()")
        evidence["server_version_num"] = int(observer.scalar("SHOW server_version_num"))
        a.execute("CREATE TABLE balance (id integer PRIMARY KEY, value integer CHECK (value >= 0))")
        a.execute("INSERT INTO balance VALUES (1,10),(2,10)")
        for isolation, expected in (("READ COMMITTED", [10,20,20]), ("REPEATABLE READ", [10,10,20])):
            a.execute("UPDATE balance SET value=10 WHERE id=1")
            a.execute("BEGIN ISOLATION LEVEL " + isolation)
            values = [int(a.scalar("SELECT value FROM balance WHERE id=1"))]
            b.execute("UPDATE balance SET value=20 WHERE id=1")
            values.append(int(a.scalar("SELECT value FROM balance WHERE id=1")))
            a.execute("COMMIT")
            values.append(int(a.scalar("SELECT value FROM balance WHERE id=1")))
            assert values == expected, (isolation, values)
            evidence[isolation.lower().replace(" ", "_")] = {"status":"passed", "observations":values}

        pid_a, pid_b = [int(c.scalar("SELECT pg_backend_pid()")) for c in (a,b)]
        a.execute("UPDATE balance SET value=10 WHERE id=1")
        a.execute("BEGIN")
        a.execute("UPDATE balance SET value=value+1 WHERE id=1")
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(b.execute, "UPDATE balance SET value=value+1 WHERE id=1")
            waiting = wait_for_lock(observer, pid_b)
            holder = observer.execute(f"SELECT state FROM pg_stat_activity WHERE pid={pid_a}")[0]
            assert str(pid_a) in waiting["blockers"] and holder["state"] == "idle in transaction"
            a.execute("COMMIT")
            future.result(timeout=6)
        final = int(observer.scalar("SELECT value FROM balance WHERE id=1"))
        assert final == 12
        evidence["lock_wait"] = {"status":"passed", "waiter":waiting,"holder":holder,"final_value":final}

        a.execute("BEGIN")
        a.execute("UPDATE balance SET value=value+1 WHERE id=1")
        b.execute("BEGIN")
        b.execute("SET LOCAL lock_timeout='150ms'")
        lock_error = b.error("UPDATE balance SET value=value+1 WHERE id=1", "55P03")
        failed_txn = b.error("SELECT 1", "25P02")
        b.execute("ROLLBACK")
        a.execute("ROLLBACK")
        evidence["lock_timeout"] = {"status":"passed", "first_sqlstate":lock_error, "next_sqlstate":failed_txn}

        a.execute("BEGIN")
        a.execute("SET LOCAL statement_timeout='75ms'")
        cancelled = a.error("SELECT pg_sleep(1)", "57014")
        failed_txn = a.error("SELECT 1", "25P02")
        a.execute("ROLLBACK")
        evidence["statement_timeout"] = {"status":"passed","first_sqlstate":cancelled,"next_sqlstate":failed_txn}

        a.execute("UPDATE balance SET value=10 WHERE id=1")
        a.execute("BEGIN")
        a.execute("UPDATE balance SET value=40 WHERE id=1")
        invalid = a.error("UPDATE balance SET value=-1 WHERE id=1", "23514")
        failed_txn = a.error("SELECT value FROM balance WHERE id=1", "25P02")
        a.execute("ROLLBACK")
        restored = int(a.scalar("SELECT value FROM balance WHERE id=1"))
        assert restored == 10
        evidence["failed_transaction"] = {"status":"passed","first_sqlstate":invalid,
                                          "next_sqlstate":failed_txn,"after_rollback":restored}
        a.execute("BEGIN")
        a.execute("UPDATE balance SET value=40 WHERE id=1")
        a.execute("SAVEPOINT before_bad_statement")
        a.error("UPDATE balance SET value=-1 WHERE id=1", "23514")
        a.execute("ROLLBACK TO SAVEPOINT before_bad_statement")
        retained = int(a.scalar("SELECT value FROM balance WHERE id=1"))
        a.execute("COMMIT")
        assert retained == 40
        evidence["savepoint"] = {"status":"passed", "retained_earlier_update":retained}

        for connection, row_id in ((a,1),(b,2)):
            connection.execute("BEGIN")
            connection.execute("SET LOCAL deadlock_timeout='100ms'")
            connection.execute(f"UPDATE balance SET value=value+1 WHERE id={row_id}")
        def conflicting_update(connection, row_id):
            try:
                connection.execute(f"UPDATE balance SET value=value+1 WHERE id={row_id}")
                return "00000"
            except DatabaseError as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(conflicting_update, a, 2)
            wait_for_lock(observer, pid_a)
            second = pool.submit(conflicting_update, b, 1)
            outcomes = [first.result(timeout=6), second.result(timeout=6)]
        assert sorted(outcomes) == ["00000", "40P01"], outcomes
        a.execute("ROLLBACK")
        b.execute("ROLLBACK")
        evidence["deadlock"] = {"status":"passed","two_sqlstates":outcomes,"victim_is_not_assumed":True}

        observer.execute("CREATE ROLE dk_monitor LOGIN")
        monitor = connect("dk-monitor", "dk_monitor")
        before = monitor.execute(f"SELECT state, query FROM pg_stat_activity WHERE pid={pid_a}")[0]
        assert before["state"] is None and before["query"] == "<insufficient privilege>", before
        observer.execute("GRANT pg_read_all_stats TO dk_monitor")
        after = monitor.execute(f"SELECT state, query FROM pg_stat_activity WHERE pid={pid_a}")[0]
        assert after["state"] == "idle" and after["query"] != "<insufficient privilege>"
        evidence["statistics_privilege"] = {"status":"passed","before":before,"after":after}

        a.execute("SET stats_fetch_consistency='snapshot'")
        a.execute("BEGIN")
        query = "SELECT xact_commit FROM pg_stat_database WHERE datname=current_database()"
        old = int(a.scalar(query))
        b.execute("SELECT 1")
        b.execute("SELECT pg_stat_force_next_flush()")
        same = int(a.scalar(query))
        assert same == old
        deadline = time.monotonic() + 3
        refreshed = old
        while refreshed <= old and time.monotonic() < deadline:
            a.execute("SELECT pg_stat_clear_snapshot()")
            refreshed = int(a.scalar(query))
            if refreshed <= old:
                time.sleep(.025)
        assert refreshed > old, (old, refreshed)
        a.execute("COMMIT")
        evidence["statistics_snapshot"] = {"status":"passed", "initial":old,
                                           "same_transaction_cached":same,"after_clear":refreshed}

        source = ROOT / "labs/postgresql/collect-database.sql"
        captured = []
        for statement in source.read_text().split(";"):
            if statement.strip():
                rows = monitor.execute(statement)
                if rows:
                    captured.append(rows)
        evidence["collector_query"] = {"status":"passed", "role":"dk_monitor with pg_read_all_stats",
                                       "result_sets":captured}
        return evidence
    finally:
        for connection in reversed(connections):
            connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".lab-runs/postgresql.json")
    args = parser.parse_args()
    if platform.system() != "Linux" or os.geteuid() == 0:
        raise SystemExit("Run as a non-root Linux user after get_postgres_lab.py")
    extracted = ROOT / ".tools/pg18"
    binaries = extracted / "usr/lib/postgresql/18/bin"
    env = dict(os.environ, LD_LIBRARY_PATH=str(extracted / "usr/lib/x86_64-linux-gnu"), LC_ALL="C")
    lib = bind_libpq(extracted / "usr/lib/x86_64-linux-gnu/libpq.so.5")
    with tempfile.TemporaryDirectory(prefix="domain-knowledge-pg-") as temporary:
        workspace = Path(temporary)
        workspace.chmod(0o700)
        data = workspace / "data"
        subprocess.run([str(binaries / "initdb"), "-D", str(data), "-U", "dk_owner",
                        "-A", "trust", "--no-locale", "-E", "UTF8"], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, timeout=40)
        with (data / "postgresql.conf").open("a") as config:
            config.write(f"\nlisten_addresses=''\nunix_socket_directories='{workspace}'\nport=55432\n"
                         "max_connections=20\nshared_buffers='16MB'\nstatement_timeout='5s'\n"
                         "idle_in_transaction_session_timeout='15s'\ntimezone='UTC'\n")
        try:
            subprocess.run([str(binaries / "pg_ctl"), "-D", str(data), "-l", str(workspace / "server.log"),
                            "-w", "-t", "20", "start"], env=env, capture_output=True, check=True, timeout=25)
            result = {"run_at_utc":datetime.now(timezone.utc).isoformat(), "platform":platform.platform(),
                      "python":platform.python_version(), "network":"private Unix socket; TCP disabled",
                      "experiments":experiments(lib, workspace)}
        finally:
            if (data / "postmaster.pid").exists():
                subprocess.run([str(binaries / "pg_ctl"), "-D", str(data), "-w", "-t", "20", "stop", "-m", "fast"],
                               env=env, capture_output=True, check=True, timeout=25)
        result["cleanup"] = "private server stopped; temporary data directory removed on context exit"
    paths = ["scripts/run_postgres_lab.py", "scripts/get_postgres_lab.py",
             "labs/postgresql/packages.json", "labs/postgresql/collect-database.sql"]
    result["input_sha256"] = {p:hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    count = sum(isinstance(v, dict) and v.get("status") == "passed" for v in result["experiments"].values())
    print(f"PASS: PostgreSQL {result['experiments']['server_version_num']}; {count} real experiments; private cluster stopped")


if __name__ == "__main__":
    main()
